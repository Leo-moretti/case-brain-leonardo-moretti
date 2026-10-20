"""Guardrails de qualidade: dados v1 passam; dados corrompidos bloqueiam (ou alertam) sem afetar o warehouse publicado."""
import json
import sqlite3
from pathlib import Path

import pytest

from conftest import ROOT, one
from pipeline.build import build
from pipeline.quality import QualidadeBloqueante


def make_dados(tmp: Path, alterar: dict) -> Path:
    """Cópia dos CSVs v1: arquivos alterados são reescritos, os demais viram symlink (crm_events tem 62 MB)."""
    dados = tmp / "dados"
    dados.mkdir()
    for src in (ROOT / "dados").glob("*.csv"):
        nome = src.stem
        if nome in alterar:
            linhas = src.read_text(encoding="utf-8").splitlines()
            novas = alterar[nome](linhas)
            if novas is not None:
                (dados / src.name).write_text("\n".join(novas) + "\n", encoding="utf-8")
        else:
            (dados / src.name).symlink_to(src)
    return dados


def falhas(db_dir: Path) -> set[str]:
    hist = db_dir / "dq_historico.jsonl"
    return {r["check"] for r in map(json.loads, hist.read_text().splitlines()) if r["status"] != "ok"}


def test_v1_passes_without_blocking_failures(con):
    assert one(con, "SELECT COUNT(*) FROM dq_resultados WHERE severidade = 'bloqueante' AND status <> 'ok'") == 0
    assert one(con, "SELECT COUNT(*) FROM dq_resultados") >= 40


def test_v1_known_operator_issue_raises_dummy_alert(tmp_path):
    build(make_dados(tmp_path, {}), tmp_path / "wh" / "pontua.db")
    alertas = [json.loads(x) for x in (tmp_path / "wh" / "alertas.jsonl").read_text().splitlines()]
    assert [a["check"] for a in alertas] == ["gold_operador_diverge_pix_pontos_pct"]


@pytest.mark.parametrize("alterar,check_esperado", [
    # status novo no sistema de pedidos sumiria das métricas
    ({"orders": lambda ls: ls[:1] + [ls[1].replace("CANCELADO", "PENDENTE_ANTIFRAUDE")] + ls[2:]},
     "bronze_dominio_status"),
    # coluna renomeada na origem
    ({"carts": lambda ls: ["cart_id,user_id,canal"] + ls[1:]}, "contrato_carts"),
    # item duplicado (reenvio de carga)
    ({"order_items": lambda ls: ls + [ls[1]]}, "bronze_pk_duplicada"),
    # timestamp em UTC quebraria a derivação de mês
    ({"order_items": lambda ls: ls[:1] + [ls[1].replace("-03:00", "+00:00", 1)] + ls[2:]}, "bronze_formato_timestamp"),
    # arquivo não entregue
    ({"cards": lambda ls: None}, "arquivo_cards.csv"),
])
def test_corrupted_input_blocks_and_keeps_published_warehouse(tmp_path, alterar, check_esperado):
    db = tmp_path / "wh" / "pontua.db"
    db.parent.mkdir()
    sqlite3.connect(db).execute("CREATE TABLE versao_anterior (ok INTEGER)").connection.commit()

    with pytest.raises(QualidadeBloqueante) as exc:
        build(make_dados(tmp_path, alterar), db)

    assert check_esperado in {f.check for f in exc.value.falhas}
    assert check_esperado in falhas(db.parent)
    # warehouse publicado intacto e sem arquivo temporário
    assert sqlite3.connect(db).execute("SELECT name FROM sqlite_master").fetchall() == [("versao_anterior",)]
    assert not db.with_suffix(".tmp.db").exists()
    alertas = (db.parent / "alertas.jsonl").read_text()
    assert check_esperado in alertas


def test_pix_rate_change_alerts_but_publishes(tmp_path):
    def nova_taxa(ls):
        out = [ls[0]]
        for linha in ls[1:]:
            if ",Pix Pontua+," in linha:
                c = linha.split(",")
                c[10] = f"{int(c[8]) * 0.015:.2f}"  # product_value com R$ 0,015/ponto
                linha = ",".join(c)
            out.append(linha)
        return out

    db = build(make_dados(tmp_path, {"order_items": nova_taxa}), tmp_path / "wh" / "pontua.db")
    assert "gold_taxa_pix" in falhas(db.parent)
    assert one(sqlite3.connect(db), "SELECT COUNT(*) FROM gold_fct_resgate WHERE modalidade = 'PIX'") > 0
