"""Agente de perguntas sobre o Pontua+: texto -> SQL (só camada gold, somente leitura) -> resposta com ressalvas.

Provedores (variável LLM_PROVIDER):
  gemini (padrão): usa GEMINI_API_KEY e GEMINI_MODEL (padrão gemini-2.5-flash)
  ollama: usa OLLAMA_HOST (padrão http://localhost:11434) e OLLAMA_MODEL (padrão llama3.1)
"""
import json
import os
import re
import sqlite3
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB = Path(os.getenv("PONTUA_DB", ROOT / "warehouse" / "pontua.db"))
MAX_ROWS = 200

FORBIDDEN = re.compile(r"\b(insert|update|delete|drop|alter|create|attach|detach|pragma|replace|vacuum)\b", re.I)


def connect_ro() -> sqlite3.Connection:
    return sqlite3.connect(f"file:{DB}?mode=ro", uri=True)


def schema_context() -> str:
    """Monta o contexto a partir das tabelas de metadados do warehouse (meta_*)."""
    con = connect_ro()
    regras = [r[0] for r in con.execute("SELECT regra FROM meta_regras")]
    partes = ["REGRAS DE NEGÓCIO E RESSALVAS:"] + [f"- {r}" for r in regras] + ["", "TABELAS:"]
    for tabela, grao, desc in con.execute("SELECT tabela, grao, descricao FROM meta_tabelas"):
        partes.append(f"\n{tabela} (grão: {grao}) — {desc}")
        for col, cdesc in con.execute("SELECT coluna, descricao FROM meta_colunas WHERE tabela = ?", (tabela,)):
            partes.append(f"  - {col}: {cdesc}")
    con.close()
    return "\n".join(partes)


SYSTEM_SQL = """Você é o analista de dados do programa de pontos Pontua+ e responde à diretoria.
Responda SOMENTE com um JSON: {{"acao": "sql", "sql": "..."}} ou {{"acao": "recusar", "motivo": "..."}}.

Regras:
- Use apenas as tabelas listadas abaixo (prefixo gold_). Uma única instrução SELECT (CTE permitido), dialeto SQLite.
- Recuse (acao=recusar) se a pergunta: pedir dados pessoais ou listar usuários individualmente; pedir previsões
  ou dados que não existem nas tabelas (ex.: quanto o banco paga por ponto, margem, NPS, dados após 30/09/2026);
  ou não tiver relação com o programa.
- Prefira tabelas agregadas (gold_metas_mensal, gold_resgates_mensal, gold_pontos_mensal) quando bastarem.

{schema}
"""

SYSTEM_ANSWER = """Você é o analista de dados do programa de pontos Pontua+ e responde à diretoria em português, de forma objetiva.
Use apenas os números do resultado da consulta. Cite os números. Se alguma regra/ressalva do catálogo se aplicar
(lote de 12/01/2026, definição de varejo, Pix no denominador, breakage não mensurável, CRM sem grupo de controle),
mencione em uma linha "Ressalva:". Não invente dados.

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
    resp = client.models.generate_content(model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash"), contents=user, config=cfg)
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
    fora = {t for t in tabelas - ctes if not t.lower().startswith("gold_")}
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


def ask(pergunta: str) -> dict:
    """Retorna {"resposta", "sql", "colunas", "linhas"}; sql vazio quando o agente recusa."""
    schema = schema_context()
    plano = json.loads(llm(SYSTEM_SQL.format(schema=schema), pergunta, json_mode=True))
    if plano.get("acao") != "sql":
        return {"resposta": f"Não posso responder com estes dados: {plano.get('motivo', '')}", "sql": "", "colunas": [], "linhas": []}

    sql = validate_sql(plano["sql"])
    try:
        cols, rows = run_sql(sql)
    except sqlite3.Error as e:
        # uma tentativa de correção com a mensagem de erro
        plano = json.loads(llm(SYSTEM_SQL.format(schema=schema), f"{pergunta}\n\nO SQL abaixo falhou com '{e}'. Corrija.\n{sql}", json_mode=True))
        sql = validate_sql(plano["sql"])
        cols, rows = run_sql(sql)

    resultado = json.dumps({"colunas": cols, "linhas": rows}, ensure_ascii=False, default=str)
    resposta = llm(SYSTEM_ANSWER.format(schema=schema), f"Pergunta: {pergunta}\nSQL: {sql}\nResultado: {resultado}")
    return {"resposta": resposta, "sql": sql, "colunas": cols, "linhas": rows}


if __name__ == "__main__":
    import sys

    out = ask(" ".join(sys.argv[1:]) or "Qual o percentual de aéreas e varejo por mês?")
    print(out["sql"], "\n")
    print(out["resposta"])
