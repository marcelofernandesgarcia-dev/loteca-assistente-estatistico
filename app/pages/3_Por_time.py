import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from util import formatar_data_br, mostrar_aviso_responsabilidade, obter_conexao

from stats.desempenho import (
    aproveitamento_casa_fora,
    contagem_por_resultado,
    gerar_insight,
    kpis,
    tendencia_por_ano,
)
from stats.forma import forma_recente
from stats.temporada import desempenho_no_ano

AZUL = "#1a4fa0"
VERMELHO = "#e30613"
VERDE = "#2e8b57"
CINZA = "#9aa5b1"

st.title("Por time")
mostrar_aviso_responsabilidade()
st.caption(
    "Painel de desempenho de um participante (clube ou seleção) nos jogos que caíram na grade da Loteca. "
    "Atenção: isto NÃO é a classificação oficial de nenhum campeonato -- a base só tem os jogos que foram "
    "escolhidos para a Loteca, não o calendário completo."
)

conexao = obter_conexao()
participantes = conexao.execute("SELECT id, nome, tipo FROM participantes ORDER BY nome").fetchall()

if not participantes:
    st.info("Nenhum participante importado ainda -- veja a página 'Concurso atual'.")
    conexao.close()
    st.stop()

opcoes = {f"{p['nome']} ({p['tipo']})": p["id"] for p in participantes}
escolha = st.selectbox("Participante (clube ou seleção)", list(opcoes.keys()))
participante_id = opcoes[escolha]

# Filtros -- aplicam-se a KPIs, gauges, contagem, insight e tabela
anos_disponiveis = [
    linha["ano"]
    for linha in conexao.execute(
        "SELECT DISTINCT substr(data_jogo, 1, 4) AS ano FROM jogos "
        "WHERE (casa_id = ? OR fora_id = ?) AND data_jogo IS NOT NULL ORDER BY ano DESC",
        (participante_id, participante_id),
    )
]
campeonatos_disponiveis = [
    linha["campeonato"]
    for linha in conexao.execute(
        "SELECT DISTINCT campeonato FROM jogos WHERE (casa_id = ? OR fora_id = ?) AND campeonato IS NOT NULL",
        (participante_id, participante_id),
    )
]

col_f1, col_f2, col_f3 = st.columns(3)
ano_escolhido = col_f1.selectbox("Ano", ["Todos"] + anos_disponiveis)
campeonato_escolhido = col_f2.selectbox("Campeonato", ["Todos"] + campeonatos_disponiveis)
mando_escolhido = col_f3.selectbox("Mando", ["Ambos", "Só em casa", "Só fora"])

ano_filtro = int(ano_escolhido) if ano_escolhido != "Todos" else None
campeonato_filtro = campeonato_escolhido if campeonato_escolhido != "Todos" else None
mando_filtro = {"Só em casa": "casa", "Só fora": "fora"}.get(mando_escolhido)

contagem = contagem_por_resultado(conexao, participante_id, ano_filtro, campeonato_filtro, mando_filtro)
aproveitamento = aproveitamento_casa_fora(conexao, participante_id, ano_filtro, campeonato_filtro)
indicadores = kpis(conexao, participante_id, ano_filtro, campeonato_filtro, mando_filtro)

if contagem["jogos"] == 0:
    st.warning("Nenhum jogo encontrado com esses filtros para este participante.")
else:
    # 1. KPIs
    k1, k2, k3, k4, k5, k6 = st.columns(6)
    k1.metric("Jogos", indicadores["jogos"])
    k2.metric("Vitórias", contagem["vitorias"])
    k3.metric("Empates", contagem["empates"])
    k4.metric("Derrotas", contagem["derrotas"])
    k5.metric("Gols feitos / sofridos", f"{indicadores['gols_marcados']} / {indicadores['gols_sofridos']}")
    k6.metric("Média de gols", f"{indicadores['media_gols']:.2f}", delta=f"saldo {indicadores['saldo']:+d}")

    # 2. Insight por regra (não IA)
    st.info("**Leitura rápida:** " + gerar_insight(aproveitamento, contagem))

    # 3. Aproveitamento casa x fora (gauges)
    st.subheader("Aproveitamento (% de vitórias)")
    g1, g2 = st.columns(2)

    def _gauge(valor: float, titulo: str, jogos: int):
        figura = go.Figure(
            go.Indicator(
                mode="gauge+number",
                value=valor,
                number={"suffix": "%"},
                title={"text": f"{titulo} ({jogos} jogos)"},
                gauge={
                    "axis": {"range": [0, 100]},
                    "bar": {"color": AZUL},
                    "steps": [{"range": [0, 100], "color": "#eef3f8"}],
                },
            )
        )
        figura.update_layout(height=220, margin=dict(l=20, r=20, t=50, b=10))
        return figura

    g1.plotly_chart(_gauge(aproveitamento["casa"], "Em casa", aproveitamento["jogos_casa"]), use_container_width=True)
    g2.plotly_chart(_gauge(aproveitamento["fora"], "Fora de casa", aproveitamento["jogos_fora"]), use_container_width=True)

    # 4. Contagem por resultado (barra empilhada horizontal)
    st.subheader("Contagem por resultado")
    barra = go.Figure()
    for nome, chave, cor in (("Vitórias", "pct_vitorias", VERDE), ("Empates", "pct_empates", CINZA), ("Derrotas", "pct_derrotas", VERMELHO)):
        barra.add_trace(
            go.Bar(
                y=[""], x=[contagem[chave]], name=nome, orientation="h", marker_color=cor,
                text=f"{contagem[chave]:.0f}%", textposition="inside",
            )
        )
    barra.update_layout(barmode="stack", height=120, margin=dict(l=0, r=0, t=10, b=10), xaxis=dict(range=[0, 100], showticklabels=False))
    st.plotly_chart(barra, use_container_width=True)

    # 5. Tendência por ano (combo barra + linha)
    st.subheader("Tendência por ano")
    tendencia = tendencia_por_ano(conexao, participante_id)
    if len(tendencia) >= 1:
        anos = [t["ano"] for t in tendencia]
        combo = go.Figure()
        combo.add_trace(go.Bar(x=anos, y=[t["jogos"] for t in tendencia], name="Jogos", marker_color=AZUL, yaxis="y2", opacity=0.55))
        combo.add_trace(
            go.Scatter(x=anos, y=[t["pct_aproveitamento"] for t in tendencia], name="% vitórias", mode="lines+markers", line=dict(color=VERMELHO))
        )
        combo.update_layout(
            height=300,
            margin=dict(l=10, r=10, t=10, b=10),
            yaxis=dict(title="% de vitórias", range=[0, 100]),
            yaxis2=dict(title="Jogos", overlaying="y", side="right"),
            legend=dict(orientation="h"),
        )
        st.plotly_chart(combo, use_container_width=True)
    else:
        st.caption("Ainda sem jogos datados suficientes para montar a tendência.")

# 6. Tabela detalhada (respeita os filtros; mando aplicado aqui também)
st.subheader("Jogos do participante (com filtros aplicados)")
condicoes = ["(j.casa_id = ? OR j.fora_id = ?)"]
parametros = [participante_id, participante_id]
if ano_filtro:
    condicoes.append("substr(j.data_jogo, 1, 4) = ?")
    parametros.append(str(ano_filtro))
if campeonato_filtro:
    condicoes.append("j.campeonato = ?")
    parametros.append(campeonato_filtro)
if mando_escolhido == "Só em casa":
    condicoes.append("j.casa_id = ?")
    parametros.append(participante_id)
elif mando_escolhido == "Só fora":
    condicoes.append("j.fora_id = ?")
    parametros.append(participante_id)

jogos = conexao.execute(
    f"""
    SELECT j.concurso_numero, j.data_jogo, j.gols_casa, j.gols_fora, j.resultado, j.campeonato,
           pc.nome AS casa, pf.nome AS fora, (j.casa_id = ?) AS em_casa
    FROM jogos j
    JOIN participantes pc ON pc.id = j.casa_id
    JOIN participantes pf ON pf.id = j.fora_id
    WHERE {' AND '.join(condicoes)}
    ORDER BY j.data_jogo DESC
    """,
    [participante_id] + parametros,
).fetchall()

if jogos:
    linhas_tabela = []
    total_feitos = total_sofridos = 0
    for j in jogos:
        feitos = j["gols_casa"] if j["em_casa"] else j["gols_fora"]
        sofridos = j["gols_fora"] if j["em_casa"] else j["gols_casa"]
        total_feitos += feitos or 0
        total_sofridos += sofridos or 0
        linhas_tabela.append(
            {
                "Concurso": j["concurso_numero"],
                "Data": formatar_data_br(j["data_jogo"]),
                "Jogo": "casa" if j["em_casa"] else "fora",
                "Adversário": j["fora"] if j["em_casa"] else j["casa"],
                "Gols feitos": feitos,
                "Gols sofridos": sofridos,
                "Coluna": j["resultado"] or "-",
                "Campeonato": j["campeonato"] or "-",
            }
        )
    st.dataframe(pd.DataFrame(linhas_tabela), use_container_width=True, hide_index=True)
    st.caption(f"Total: {len(jogos)} jogos · {total_feitos} gols feitos · {total_sofridos} gols sofridos.")
else:
    st.caption("Nenhum jogo com esses filtros.")

# 7. Seções que já existiam (forma recente, ano em curso, fatores externos)
st.subheader("Forma recente (últimos jogos, qualquer ano)")
forma = forma_recente(conexao, participante_id)
st.write(
    f"Últimos {forma['jogos_considerados']} jogos: {forma['vitorias']}V {forma['empates']}E {forma['derrotas']}D · "
    f"{forma['gols_marcados']} gols marcados, {forma['gols_sofridos']} sofridos, {forma['clean_sheets']} clean sheets."
)

st.subheader("Desempenho no ano em curso")
st.caption("Só os jogos deste ano civil -- é a base usada no card 'Seu bilhete' da página Concurso atual para confrontar com sua marcação.")
desempenho = desempenho_no_ano(conexao, participante_id)
if desempenho["jogos"] == 0:
    st.write(f"Nenhum jogo importado em {desempenho['ano']} para este participante ainda.")
else:
    st.write(
        f"{desempenho['ano']}: {desempenho['jogos']} jogos · {desempenho['vitorias']}V {desempenho['empates']}E {desempenho['derrotas']}D · "
        f"{desempenho['gols_marcados']} gols marcados, {desempenho['gols_sofridos']} sofridos."
    )

st.subheader("Fatores externos já coletados (varredura semanal)")
fatores = conexao.execute(
    "SELECT concurso_numero, coletado_em, resumo, ajuste_aplicado FROM fatores_externos "
    "WHERE participante_id = ? ORDER BY coletado_em DESC",
    (participante_id,),
).fetchall()
if fatores:
    st.dataframe(
        pd.DataFrame(
            [
                {"Concurso": f["concurso_numero"], "Coletado em": f["coletado_em"], "Resumo": f["resumo"], "Ajuste (p.p.)": f["ajuste_aplicado"]}
                for f in fatores
            ]
        ),
        use_container_width=True,
        hide_index=True,
    )
else:
    st.caption("Nenhuma varredura rodada para este participante ainda.")

conexao.close()
