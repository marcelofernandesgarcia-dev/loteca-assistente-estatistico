"""Premiações da Loteca ao longo dos concursos (pedido do usuário, 30/09/2026): arrecadação,
ganhadores e valor por ganhador, totais pagos e concursos em que ninguém fez 14. Só apresentação:
as contas estão em stats/premiacao.py."""
import html
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import plotly.graph_objects as go
import streamlit as st
from estilo_caixa import renderizar_tabela
from paleta import AZUL, CINZA, VERMELHO
from premiacao_ui import mostrar_premiacao
from util import formatar_data_br, mostrar_aviso_responsabilidade, obter_conexao

from stats.premiacao import estatisticas_do_historico, reais, serie_historica

st.title("Premiações")
mostrar_aviso_responsabilidade()
st.caption(
    "Quanto a Loteca arrecadou, quantas apostas ganharam e quanto cada uma recebeu, concurso a concurso. Valores "
    "publicados pela CAIXA; o total pago é a soma de ganhadores x prêmio por ganhador. É histórico: não indica quanto "
    "um concurso futuro vai pagar."
)

conexao = obter_conexao()
serie = serie_historica(conexao)
if not serie:
    st.info("Nenhuma premiação importada ainda -- veja a página 'Concurso atual' e o README (scripts/importar_valores.py).")
    conexao.close()
    st.stop()

est = estatisticas_do_historico(serie)
st.header("Resumo do histórico")
with st.container(horizontal=True, wrap=True):
    st.metric("Concursos apurados", f"{est['concursos']:,}".replace(",", "."), border=True)
    if est["percentual_sem_ganhador_14"] is not None:
        st.metric("Sem ganhador de 14 acertos", f"{est['sem_ganhador_14']:,} ({est['percentual_sem_ganhador_14']:.0f}%)".replace(",", "."),
                  border=True, help="Concursos em que ninguém acertou os 14 jogos e o prêmio acumulou.")
    if est["maior_premio_14"]:
        st.metric("Maior prêmio de 14 acertos", reais(est["maior_premio_14"]["valor"]), border=True,
                  help=f"Concurso {est['maior_premio_14']['numero']}.")
    if est["arrecadacao_mediana"] is not None:
        st.metric("Arrecadação mediana", reais(est["arrecadacao_mediana"]), border=True,
                  help=f"Dos {est['com_arrecadacao']} concursos com arrecadação registrada.")
if est["com_arrecadacao"] < est["concursos"]:
    st.caption(
        f"Arrecadação registrada em {est['com_arrecadacao']} de {est['concursos']} concursos: a CAIXA não informa "
        "esse valor nos demais."
    )

st.header("Ao longo dos concursos")
primeiro, ultimo = serie[0]["numero"], serie[-1]["numero"]
inicio, fim = st.slider("Concursos", min_value=primeiro, max_value=ultimo, value=(max(primeiro, ultimo - 199), ultimo),
                        key="intervalo_premiacoes")
recorte = [s for s in serie if inicio <= s["numero"] <= fim]

com_ganhador = [s for s in recorte if s["ganhadores_14"] and s["premio_14"]]
sem_ganhador = [s for s in recorte if s["ganhadores_14"] == 0]
figura = go.Figure()
figura.add_trace(go.Scatter(
    x=[s["numero"] for s in com_ganhador], y=[s["premio_14"] for s in com_ganhador], mode="lines+markers",
    name="Prêmio por ganhador de 14 acertos", line=dict(color=AZUL), marker=dict(symbol="circle", size=5),
    hovertemplate="Concurso %{x}: R$ %{y:,.2f}<extra></extra>",
))
figura.add_trace(go.Scatter(
    x=[s["numero"] for s in sem_ganhador], y=[0] * len(sem_ganhador), mode="markers",
    name="Ninguém fez 14 (prêmio acumulou)", marker=dict(symbol="x", size=8, color=VERMELHO),
    hovertemplate="Concurso %{x}: sem ganhador de 14<extra></extra>",
))
figura.update_layout(
    title="Prêmio por ganhador de 14 acertos", height=360, margin=dict(l=10, r=10, t=50, b=40),
    xaxis=dict(title="Número do concurso"), yaxis=dict(title="R$", tickformat=",.0f"),
    legend=dict(orientation="h", y=-0.25), colorway=[AZUL, VERMELHO, CINZA],
    separators=",.",  # vírgula decimal e ponto de milhar, como no resto do app
)
st.plotly_chart(figura, width="stretch", key="grafico_premio_14")
st.caption(
    "O prêmio de 14 acertos varia muito porque soma o que acumulou quando ninguém acertou e é dividido entre os ganhadores. "
    "Os X marcam os concursos sem ganhador de 14."
)

arrecadacao = [s for s in recorte if s["valor_arrecadado"]]
if arrecadacao:
    fig2 = go.Figure(go.Bar(
        x=[s["numero"] for s in arrecadacao], y=[s["valor_arrecadado"] for s in arrecadacao], marker=dict(color=AZUL),
        hovertemplate="Concurso %{x}: R$ %{y:,.2f}<extra></extra>", name="Arrecadação",
    ))
    fig2.update_layout(title="Arrecadação por concurso", height=300, margin=dict(l=10, r=10, t=50, b=40),
                       xaxis=dict(title="Número do concurso"), yaxis=dict(title="R$", tickformat=",.0f"), showlegend=False,
                       separators=",.")
    st.plotly_chart(fig2, width="stretch", key="grafico_arrecadacao")

st.header("Tabela do período")
ordenada = sorted(recorte, key=lambda s: s["numero"], reverse=True)[:50]
linhas = []
for s in ordenada:
    g14 = "ninguém" if s["ganhadores_14"] == 0 else ("sem dado" if s["ganhadores_14"] is None else str(s["ganhadores_14"]))
    linhas.append([
        str(s["numero"]), html.escape(formatar_data_br(s["data_apuracao"])), reais(s["valor_arrecadado"]), g14,
        "-" if not s["ganhadores_14"] else reais(s["premio_14"]),
        "sem dado" if s["ganhadores_13"] is None else f"{s['ganhadores_13']:,}".replace(",", "."),
        reais(s["premio_13"]), reais(s["total_pago"]),
    ])
st.markdown(
    renderizar_tabela(
        f"Concursos {inicio} a {fim} (os 50 mais recentes do período)",
        ["Concurso", "Apuração", "Arrecadação", "Ganhadores de 14", "Prêmio de 14", "Ganhadores de 13", "Prêmio de 13", "Total pago"],
        linhas,
    ),
    unsafe_allow_html=True,
)

st.header("Um concurso em detalhe")
numero = st.selectbox("Concurso", [s["numero"] for s in reversed(serie)], key="concurso_detalhe_premiacao")
mostrar_premiacao(conexao, numero)
conexao.close()
