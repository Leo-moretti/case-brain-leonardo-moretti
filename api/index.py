"""Função serverless (Vercel, runtime Python) — NÃO TESTADA em deploy real.

GET  /api?tabela=gold_metas_mensal  -> JSON da tabela (somente gold_* agregadas)
POST /api  {"pergunta": "..."}       -> resposta do agente (mesmas guardas e trilha de auditoria)
"""
import json
import os
import sqlite3
import sys
from http.server import BaseHTTPRequestHandler
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
os.environ.setdefault("PONTUA_DB", str(Path(__file__).resolve().parent / "pontua_gold.db"))
os.environ.setdefault("AGENT_AUDIT_LOG", "/tmp/auditoria_agente.jsonl")  # efêmero na Vercel: enviar a log externo
sys.path.insert(0, str(ROOT))

# só agregados; tabelas de grão individual não são servidas
TABELAS = {"gold_metas_mensal", "gold_resgates_mensal", "gold_pontos_mensal", "gold_conciliacao_operador",
           "gold_campanha_pix", "gold_breakage", "dq_resultados"}


class handler(BaseHTTPRequestHandler):
    def _json(self, status: int, body) -> None:
        data = json.dumps(body, ensure_ascii=False, default=str).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        from urllib.parse import parse_qs, urlparse

        tabela = parse_qs(urlparse(self.path).query).get("tabela", ["gold_metas_mensal"])[0]
        if tabela not in TABELAS:
            return self._json(400, {"erro": "tabela não permitida"})
        con = sqlite3.connect(f"file:{os.environ['PONTUA_DB']}?mode=ro", uri=True)
        cur = con.execute(f"SELECT * FROM {tabela}")
        cols = [d[0] for d in cur.description]
        self._json(200, [dict(zip(cols, r)) for r in cur.fetchall()])

    def do_POST(self):
        from agent.core import ask

        body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
        try:
            out = ask(body.get("pergunta", ""))
            self._json(200, {"resposta": out["resposta"], "status": out["status"]})
        except Exception:
            self._json(503, {"erro": "agente indisponível; tentativa registrada na trilha de auditoria"})
