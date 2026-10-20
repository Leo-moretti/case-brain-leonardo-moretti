"""Agente de perguntas sobre o Pontua+: texto -> SQL (só camada gold, somente leitura) -> resposta com ressalvas.

Provedores (variável LLM_PROVIDER):
  gemini (padrão): usa GEMINI_API_KEY e GEMINI_MODEL (padrão gemini-3.8-flash)
  ollama: usa OLLAMA_HOST (padrão http://localhost:11434) e OLLAMA_MODEL (padrão llama3.1)
"""
import hashlib
import json
import os
from datetime import datetime, timezone
import re
import sqlite3
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB = Path(os.getenv("PONTUA_DB", ROOT / "warehouse" / "pontua.db"))
AUDIT_LOG = Path(os.getenv("AGENT_AUDIT_LOG", ROOT / "warehouse" / "auditoria_agente.jsonl"))
MAX_ROWS = 200
IDENTIFICADORES = {"user_id", "order_id", "order_item_id", "account_id", "device_id", "cart_id", "movement_id"}
RODAPE = "_Valores gerenciais (não contábeis), calculados a partir dos sistemas de origem · versão dos dados: {versao}_"

FORBIDDEN = re.compile(r"\b(insert|update|delete|drop|alter|create|attach|detach|pragma|replace|vacuum)\b", re.I)


def connect_ro() -> sqlite3.Connection:
    return sqlite3.connect(f"file:{DB}?mode=ro", uri=True)


def schema_context() -> str:
    """Monta o contexto a partir das tabelas de metadados do warehouse (meta_*)."""
    con = connect_ro()
    regras = [r[0] for r in con.execute("SELECT regra FROM meta_regras")]
    inferidas = con.execute("SELECT id, regra, status FROM meta_regras_inferidas").fetchall()
    partes = (["REGRAS DE NEGÓCIO E RESSALVAS:"] + [f"- {r}" for r in regras]
              + ["", "REGRAS INFERIDAS (cite o id na ressalva quando a resposta depender de uma com status pendente):"]
              + [f"- {i} [{s}]: {r}" for i, r, s in inferidas] + ["", "TABELAS:"])
    for tabela, grao, desc in con.execute("SELECT tabela, grao, descricao FROM meta_tabelas"):
        partes.append(f"\n{tabela} (grão: {grao}) — {desc}")
        for col, cdesc in con.execute("SELECT coluna, descricao FROM meta_colunas WHERE tabela = ?", (tabela,)):
            partes.append(f"  - {col}: {cdesc}")
    con.close()
    return "\n".join(partes)


SYSTEM_SQL = """Você é o analista de dados do programa de pontos Pontua+ e responde à diretoria.
Responda SOMENTE com um JSON: {{"acao": "sql", "sql": "..."}} ou {{"acao": "recusar", "motivo": "..."}}.

Regras:
- Use apenas as tabelas listadas abaixo (prefixos gold_ e dq_). Uma única instrução SELECT (CTE permitido), dialeto SQLite.
- Recuse (acao=recusar) se a pergunta: pedir dados pessoais ou listar usuários individualmente; pedir previsões
  ou dados que não existem nas tabelas (ex.: quanto o banco paga por ponto, margem, NPS, dados após 30/09/2026);
  ou não tiver relação com o programa.
- Prefira tabelas agregadas (gold_metas_mensal, gold_resgates_mensal, gold_pontos_mensal) quando bastarem.
- Pergunta ambígua mas próxima de uma métrica existente (ex.: "quanto o programa está pagando" = custo_pontos_reais):
  responda com essa métrica em vez de recusar. Recuse só quando nenhuma coluna corresponder ao que foi pedido.

{schema}
"""

SYSTEM_ANSWER = """Você é o analista de dados do programa de pontos Pontua+ e responde à diretoria em português, de forma objetiva.
Use apenas os números do resultado da consulta. Cite os números. Se alguma regra/ressalva do catálogo se aplicar
(lote de 12/01/2026, definição de varejo, Pix no denominador, breakage não mensurável, CRM sem grupo de controle),
mencione em uma linha "Ressalva:". Se a pergunta era ambígua, diga em uma linha como ela foi interpretada. Não invente dados.

{schema}
"""


def _gemini(system: str, user: str, json_mode: bool) -> str:
    from google import genai
    from google.genai import types

    key = os.getenv("GEMINI_API_KEY")
    if not key:
        raise RuntimeError("GEMINI_API_KEY não definida")
    client = genai.Client(api_key=key)
    cfg = types.GenerateContentConfig(
        system_instruction=system,
        temperature=0,
        response_mime_type="application/json" if json_mode else "text/plain",
    )
    resp = client.models.generate_content(model=os.getenv("GEMINI_MODEL", "gemini-3.8-flash"), contents=user, config=cfg)
    return resp.text


def _ollama(system: str, user: str, json_mode: bool) -> str:
    host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
    body = {
        "model": os.getenv("OLLAMA_MODEL", "llama3.1"),
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
        "stream": False,
        "options": {"temperature": 0},
    }
    if json_mode:
        body["format"] = "json"
    req = urllib.request.Request(f"{host}/api/chat", data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read())["message"]["content"]


def llm(system: str, user: str, json_mode: bool = False) -> str:
    provider = os.getenv("LLM_PROVIDER", "gemini").lower()
    return _ollama(system, user, json_mode) if provider == "ollama" else _gemini(system, user, json_mode)


def validate_sql(sql: str) -> str:
    s = sql.strip().rstrip(";")
    if ";" in s:
        raise ValueError("apenas uma instrução é permitida")
    if not re.match(r"^\s*(select|with)\b", s, re.I) or FORBIDDEN.search(s):
        raise ValueError("apenas SELECT é permitido")
    tabelas = set(re.findall(r"\b(?:from|join)\s+([a-zA-Z_][\w]*)", s, re.I))
    ctes = set(re.findall(r"\b([a-zA-Z_]\w*)\s+as\s*\(", s, re.I))
    fora = {t for t in tabelas - ctes if not t.lower().startswith(("gold_", "dq_"))}
    if fora:
        raise ValueError(f"tabelas fora da camada gold: {', '.join(sorted(fora))}")
    return s


def run_sql(sql: str) -> tuple[list[str], list[tuple]]:
    con = connect_ro()
    try:
        cur = con.execute(sql)
        cols = [d[0] for d in cur.description]
        return cols, cur.fetchmany(MAX_ROWS)
    finally:
        con.close()


class DadoIndividualBloqueado(ValueError):
    pass


def guard_identifiers(cols: list[str], rows: list[tuple]) -> None:
    """Bloqueia resultado que exponha identificador individual (dado pessoal pseudonimizado / sigilo bancário).

    Verifica os VALORES devolvidos (não o texto do SQL), então alias não burla; contagens continuam permitidas.
    """
    if any(c.lower() in IDENTIFICADORES for c in cols):
        raise DadoIndividualBloqueado("o resultado contém coluna de identificador individual")
    candidatos = {str(v) for r in rows for v in r if v is not None and re.fullmatch(r"\d{12}", str(v))}
    if not candidatos:
        return
    con = connect_ro()
    try:
        marcas = ",".join("?" * len(candidatos))
        achou = con.execute(
            f"SELECT 1 FROM gold_dim_usuario WHERE user_id IN ({marcas}) "
            f"UNION ALL SELECT 1 FROM gold_fct_resgate WHERE order_id IN ({marcas}) OR order_item_id IN ({marcas}) LIMIT 1",
            [*candidatos, *candidatos, *candidatos],
        ).fetchone()
    finally:
        con.close()
    if achou:
        raise DadoIndividualBloqueado("o resultado contém identificador individual de cliente ou pedido")


def data_version() -> str:
    con = connect_ro()
    try:
        return con.execute("SELECT MAX(run_id) FROM dq_resultados").fetchone()[0]
    finally:
        con.close()


def audit(registro: dict) -> None:
    """Trilha de auditoria append-only de cada pergunta ao agente (em produção: armazenamento WORM)."""
    AUDIT_LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(AUDIT_LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(registro, ensure_ascii=False, default=str) + "\n")


def _modelo() -> tuple[str, str]:
    provider = os.getenv("LLM_PROVIDER", "gemini").lower()
    modelo = os.getenv("OLLAMA_MODEL", "llama3.1") if provider == "ollama" else os.getenv("GEMINI_MODEL", "gemini-3.8-flash")
    return provider, modelo


def ask(pergunta: str) -> dict:
    """Retorna {"resposta", "sql", "colunas", "linhas", "status"}; toda chamada é registrada na trilha de auditoria."""
    provider, modelo = _modelo()
    versao = data_version()
    reg = {"ts": datetime.now(timezone.utc).isoformat(timespec="seconds"), "pergunta": pergunta,
           "provedor": provider, "modelo": modelo, "versao_dados": versao, "sql": "", "resultado_sha256": "",
           "n_linhas": 0, "resposta": "", "status": ""}
    try:
        schema = schema_context()
        plano = json.loads(llm(SYSTEM_SQL.format(schema=schema), pergunta, json_mode=True))
        if plano.get("acao") != "sql":
            reg.update(status="recusado", resposta=f"Não posso responder com estes dados: {plano.get('motivo', '')}")
            return {**_saida(reg), "colunas": [], "linhas": []}

        sql = validate_sql(plano["sql"])
        try:
            cols, rows = run_sql(sql)
        except sqlite3.Error as e:
            # uma tentativa de correção com a mensagem de erro
            plano = json.loads(llm(SYSTEM_SQL.format(schema=schema),
                                   f"{pergunta}\n\nO SQL abaixo falhou com '{e}'. Corrija.\n{sql}", json_mode=True))
            sql = validate_sql(plano["sql"])
            cols, rows = run_sql(sql)
        reg["sql"] = sql
        guard_identifiers(cols, rows)  # antes de enviar o resultado à LLM ou exibir

        resultado = json.dumps({"colunas": cols, "linhas": rows}, ensure_ascii=False, default=str)
        reg.update(resultado_sha256=hashlib.sha256(resultado.encode()).hexdigest(), n_linhas=len(rows))
        resposta = llm(SYSTEM_ANSWER.format(schema=schema), f"Pergunta: {pergunta}\nSQL: {sql}\nResultado: {resultado}")
        reg.update(status="respondido", resposta=f"{resposta}\n\n{RODAPE.format(versao=versao)}")
        return {**_saida(reg), "colunas": cols, "linhas": rows}
    except DadoIndividualBloqueado as e:
        reg.update(status="bloqueado_dado_individual",
                   resposta=f"Não posso exibir dados individuais de clientes ou pedidos ({e}). Reformule com agregação.")
        return {**_saida(reg), "colunas": [], "linhas": []}
    except Exception as e:
        reg.update(status="erro", resposta=f"{type(e).__name__}: {e}")
        raise
    finally:
        audit(reg)


def _saida(reg: dict) -> dict:
    return {"resposta": reg["resposta"], "sql": reg["sql"], "status": reg["status"]}


if __name__ == "__main__":
    import sys

    out = ask(" ".join(sys.argv[1:]) or "Qual o percentual de aéreas e varejo por mês?")
    print(out["sql"], "\n")
    print(out["resposta"])
