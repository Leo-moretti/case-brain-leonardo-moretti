"""Verifica se colunas de identificador contêm número de cartão (PAN) exposto.

Critérios: algoritmo de Luhn (mod 10), comprimento de PAN (13 a 19 dígitos) e prefixo (IIN) de bandeira.
Identificador aleatório passa no Luhn em ~10% dos casos por acaso; uma coluna de PAN real passaria em ~100%.

Uso: python -m pipeline.pan_check [--dados dados]
"""
import argparse
import csv
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

COLUNAS = {
    "carts": ["cart_id", "user_id"],
    "cards": ["account_id", "user_id"],
    "orders": ["order_id", "cart_id"],
    "order_items": ["order_item_id", "order_id"],
    "points_ledger": ["movement_id", "account_id", "user_id"],
    "redeemed_points": ["order_item_id", "account_id"],
}

# prefixos das bandeiras presentes em cards.card_flag
IIN = {
    "VISA": re.compile(r"^4"),
    "MASTERCARD": re.compile(r"^(5[1-5]|2(2[2-9][1-9]|2[3-9]\d|[3-6]\d\d|7[01]\d|720))"),
    "ELO": re.compile(r"^(401178|401179|431274|438935|451416|457393|457631|457632|504175|506[67]|509|627780|636297|636368|650|6516|6550)"),
}


def luhn_ok(numero: str) -> bool:
    total = 0
    for i, d in enumerate(reversed(numero)):
        n = int(d)
        if i % 2 == 1:
            n *= 2
            if n > 9:
                n -= 9
        total += n
    return total % 10 == 0


def analisar(valores: list[str]) -> dict:
    v = [x for x in valores if x]
    tamanhos = Counter(len(x) for x in v)
    luhn = sum(luhn_ok(x) for x in v if x.isdigit())
    return {
        "valores": len(v),
        "tamanhos": dict(tamanhos),
        "tamanho_de_pan": sum(c for t, c in tamanhos.items() if 13 <= t <= 19),
        "luhn_pct": round(100 * luhn / len(v), 2) if v else 0,
        "prefixo_bandeira_pct": {b: round(100 * sum(bool(p.match(x)) for x in v) / len(v), 2) for b, p in IIN.items()},
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dados", default=str(ROOT / "dados"))
    args = parser.parse_args()
    for arquivo, colunas in COLUNAS.items():
        with open(Path(args.dados) / f"{arquivo}.csv", encoding="utf-8", newline="") as f:
            linhas = list(csv.DictReader(f))
        for col in colunas:
            r = analisar(list({ln[col] for ln in linhas}))
            veredito = "POSSÍVEL PAN" if r["tamanho_de_pan"] and r["luhn_pct"] > 90 else "identificador de sistema"
            print(f"{arquivo}.{col}: {r} -> {veredito}")


if __name__ == "__main__":
    main()
