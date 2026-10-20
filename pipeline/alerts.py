"""Envio de alertas de qualidade. POC: canal dummy (arquivo JSONL + stderr).

Para plugar um canal real (Slack, e-mail, Teams), implemente uma subclasse de Notifier e registre em CHANNELS.
Canal escolhido por DQ_ALERT_CHANNEL (padrão: dummy).
"""
import json
import os
import sys
from pathlib import Path


class Notifier:
    def send(self, alerta: dict) -> None:
        raise NotImplementedError


class DummyNotifier(Notifier):
    """Simula o envio: grava cada alerta em JSONL e imprime no stderr."""

    def __init__(self, path: Path):
        self.path = path

    def send(self, alerta: dict) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(json.dumps(alerta, ensure_ascii=False) + "\n")
        print(f"[ALERTA DQ][{alerta['severidade'].upper()}] {alerta['check']}: {alerta['descricao']} "
              f"(valor={alerta['valor']}, regra={alerta['regra']})", file=sys.stderr)


CHANNELS = {"dummy": DummyNotifier}


def get_notifier(alert_dir: Path) -> Notifier:
    canal = os.getenv("DQ_ALERT_CHANNEL", "dummy")
    return CHANNELS[canal](alert_dir / "alertas.jsonl")
