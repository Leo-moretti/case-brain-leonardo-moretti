"""Nenhuma coluna de identificador carrega número de cartão (PAN)."""
import csv

import pytest

from conftest import ROOT
from pipeline.pan_check import COLUNAS, analisar, luhn_ok


def test_luhn_known_values():
    assert luhn_ok("4111111111111111")      # número de teste Visa
    assert luhn_ok("5555555555554444")      # número de teste Mastercard
    assert not luhn_ok("4111111111111112")


@pytest.mark.parametrize("arquivo,col", [(a, c) for a, cs in COLUNAS.items() for c in cs])
def test_identifier_columns_are_not_pan(arquivo, col):
    with open(ROOT / "dados" / f"{arquivo}.csv", encoding="utf-8", newline="") as f:
        r = analisar(list({ln[col] for ln in csv.DictReader(f)}))
    assert r["tamanho_de_pan"] == 0
    assert 8 < r["luhn_pct"] < 12  # taxa de acaso (~10%), não de PAN (~100%)
