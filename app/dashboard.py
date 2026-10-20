"""Dashboard estratégico do Pontua+ (Streamlit). Lê apenas a camada gold do warehouse SQLite."""
import os
import sqlite3
import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
DB = Path(os.getenv("PONTUA_DB", ROOT / "warehouse" / "pontua.db"))

st.set_page_config(page_title="Pontua+ · Diretoria", layout="wide")


@st.cache_data
def q(sql: str) -> pd.DataFrame:
    with sqlite3.connect(f"file:{DB}?mode=ro", uri=True) as con:
        return pd.read_sql_query(sql, con)


if not DB.exists():
    st.error("Warehouse não encontrado. Rode `python -m pipeline.build`.")
    st.stop()

metas = q("SELECT * FROM gold_metas_mensal ORDER BY mes")
resg = q("SELECT * FROM gold_resgates_mensal ORDER BY mes")
pontos = q("SELECT * FROM gold_pontos_mensal ORDER BY mes")
conc = q("SELECT * FROM gold_conciliacao_operador ORDER BY mes")
camp = q("SELECT * FROM gold_campanha_pix ORDER BY grupo")
brk = q("SELECT * FROM gold_breakage")

st.title("Pontua+ · Painel da diretoria")
versao_dados = q("SELECT MAX(run_id) v FROM dq_resultados").v.iloc[0]
st.caption("Dados de 01/10/2025 a 30/09/2026 · resgates = itens APROVADOS · Pix lançado em 27/05/2026 · "
           f"**valores gerenciais, não contábeis** · versão dos dados: `{versao_dados}`")

ult = metas.iloc[-1]
c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Aéreas (set/26)", f"{ult.aereas_pct:.1f}%", "meta ≥ 50%")
c2.metric("Varejo (set/26)", f"{ult.varejo_pct:.1f}%", "meta ≥ 20%", delta_color="inverse" if ult.varejo_pct < 20 else "normal")
c3.metric("Pix (set/26)", f"{ult.pix_pct:.1f}%")
c4.metric("Pontos resgatados (set/26)", f"{ult.pontos_total / 1e6:.1f} M")
c5.metric("Passivo de pontos", f"{pontos.saldo_acumulado.iloc[-1] / 1e6:.0f} M")

dq = q("SELECT check_id, camada, severidade, status, valor, regra, descricao, executado_em FROM dq_resultados")
dq_falhas = dq[dq.status != "ok"]
if (dq_falhas.severidade == "alerta").any():
    st.warning(f"Qualidade de dados: {(dq_falhas.severidade == 'alerta').sum()} alerta(s) na última carga. Veja a aba 'Qualidade de dados'.")

abas = st.tabs(["Metas", "Resgates e custo", "Pix e CRM", "Saldo e breakage", "Conciliação operador",
                "Qualidade de dados", "Pergunte aos dados"])

with abas[0]:
    st.subheader("Participação nos pontos resgatados")
    var = st.radio("Definição", ["Contrato (Pix no denominador)", "Pix fora do denominador", "Varejo só produtos"], horizontal=True)
    if var.startswith("Contrato"):
        df = metas[["mes", "aereas_pct", "varejo_pct", "pix_pct"]]
    elif var.startswith("Pix fora"):
        df = metas[["mes", "aereas_pct_sem_pix", "varejo_pct_sem_pix"]]
    else:
        df = metas[["mes", "aereas_pct", "varejo_produto_pct", "pix_pct"]]
    fig = px.line(df.melt("mes", var_name="serie", value_name="pct"), x="mes", y="pct", color="serie", markers=True)
    fig.add_hline(y=50, line_dash="dot", annotation_text="meta aéreas 50%")
    fig.add_hline(y=20, line_dash="dot", annotation_text="meta varejo 20%")
    st.plotly_chart(fig, width="stretch")
    st.info("Jan/26 é distorcido por um lote de 1.520 resgates de aéreas em 12/01 (aéreas sem o lote: "
            f"{metas.loc[metas.mes == '2026-01', 'aereas_pct_sem_lote'].iloc[0]:.1f}%). "
            "A definição contratual de varejo e do denominador ainda precisa ser confirmada.")

with abas[1]:
    st.subheader("Pontos resgatados por modalidade (M)")
    resg["pontos_m"] = resg.pontos_aprovados / 1e6
    st.plotly_chart(px.bar(resg, x="mes", y="pontos_m", color="modalidade"), width="stretch")
    a, b = st.columns(2)
    custo = resg.groupby("modalidade", as_index=False)[["custo_pontos_reais", "pontos_aprovados"]].sum()
    custo["R$ por ponto"] = (custo.custo_pontos_reais / custo.pontos_aprovados).round(4)
    a.markdown("**Custo por ponto (líquido de copagamento)**")
    a.dataframe(custo[["modalidade", "R$ por ponto"]], hide_index=True)
    usu = resg.pivot_table(index="mes", columns="modalidade", values="usuarios_aprovados", aggfunc="sum").reset_index()
    b.markdown("**Usuários com resgate aprovado**")
    b.dataframe(usu, hide_index=True)

with abas[2]:
    st.subheader("A campanha de lançamento explica o Pix?")
    st.plotly_chart(px.bar(camp, x="grupo", y="adocao_pix_pct", text="adocao_pix_pct",
                           labels={"adocao_pix_pct": "% que usou Pix"}), width="stretch")
    st.dataframe(camp, hide_index=True)
    st.caption("Adoção praticamente igual com ou sem o e-mail. Observacional: o CRM não tem grupo de controle.")
    pix = resg[resg.modalidade == "PIX"].copy()
    pix["cancel_pct"] = (100 * pix.itens_cancelados_invalidos / pix.itens_total).round(1)
    st.markdown("**Pix por mês**")
    st.dataframe(pix[["mes", "itens_aprovados", "pontos_aprovados", "valor_produto_reais", "usuarios_aprovados", "cancel_pct"]], hide_index=True)

with abas[3]:
    st.subheader("Movimentação do saldo de pontos")
    mov = pontos[["mes", "pontos_creditados", "pontos_migrados", "pontos_resgatados", "pontos_expirados"]]
    st.plotly_chart(px.bar(mov.melt("mes"), x="mes", y="value", color="variable", barmode="group"), width="stretch")
    st.plotly_chart(px.line(pontos, x="mes", y="saldo_acumulado", markers=True, title="Passivo de pontos (saldo acumulado)"),
                    width="stretch")
    st.markdown("**Breakage: métricas candidatas**")
    st.dataframe(brk.astype(str), hide_index=True)

with abas[4]:
    st.subheader("Relatório do operador x recálculo")
    st.dataframe(conc, hide_index=True)
    st.caption("O operador soma pontos Pix de todos os status (inclusive cancelados) e divide o valor dos aprovados por eles: "
               "daí os ~R$ 0,016/ponto. A taxa real é R$ 0,019.")

with abas[5]:
    st.subheader("Guardrails de qualidade da última carga")
    st.caption(f"Executado em {dq.executado_em.iloc[0]} (UTC) · checks definidos em quality/checks.yml · "
               "bloqueante interrompe a carga e mantém a versão anterior publicada")
    a, b, c = st.columns(3)
    a.metric("Checks executados", len(dq))
    b.metric("Alertas", int((dq_falhas.severidade == "alerta").sum()))
    c.metric("Bloqueantes", int((dq_falhas.severidade == "bloqueante").sum()))
    st.dataframe(dq.sort_values(["status", "camada"]).drop(columns="executado_em").astype({"valor": str}), hide_index=True)

with abas[6]:
    st.subheader("Pergunte aos dados")
    st.caption("O agente consulta só a camada gold e cita ressalvas. Requer GEMINI_API_KEY (ou LLM_PROVIDER=ollama).")
    pergunta = st.text_input("Pergunta", placeholder="Ex.: quantos usuários usaram Pix em agosto?")
    if pergunta:
        from agent.core import ask
        try:
            with st.spinner("Consultando..."):
                out = ask(pergunta)
            # escapa "$": o markdown do Streamlit trata "R$ ... R$" como LaTeX e some com os cifrões
            st.markdown(out["resposta"].replace("$", "\\$"))
            if out["sql"]:
                with st.expander("SQL e resultado"):
                    st.code(out["sql"], language="sql")
                    st.dataframe(pd.DataFrame(out["linhas"], columns=out["colunas"]), hide_index=True)
        except Exception as e:
            # detalhe técnico fica na trilha de auditoria, não na tela
            print(f"erro do agente: {type(e).__name__}: {e}", file=sys.stderr)
            st.error("Agente indisponível no momento. A tentativa foi registrada na trilha de auditoria.")
