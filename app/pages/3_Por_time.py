import datetime as dt
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from util import formatar_data_br, mostrar_aviso_responsabilidade, obter_conexao

import config
from stats.cbf import (
    classificacao_do_participante,
    cod_time_do_participante,
    estatisticas_do_participante,
    partidas_do_participante,
)
from stats.competicao import (
    aproveitamento_movel,
    carregar_partidas,
    evolucao_do_time,
    frases_visao_geral,
    jogos_do_time,
    serie_do_time,
    tabela_por_rodada,
    validar_temporada,
)
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
NOMES_SERIE = {"serie-a": "Série A", "serie-b": "Série B"}


def renderizar_classificacao_oficial(conexao, participante_id, classif):
    st.subheader("Classificação oficial (CBF)")
    if classif is None:
        st.caption(
            "Sem dado da CBF para este participante -- só clubes das Séries A e B do Brasileirão são coletados "
            "(atualize com scripts/coleta_cbf.py)."
        )
    else:
        serie = {"serie-a": "Série A", "serie-b": "Série B"}.get(classif["serie"], classif["serie"])
        est = estatisticas_do_participante(conexao, participante_id) or {}
        c1, c2, c3, c4, c5, c6 = st.columns(6)
        c1.metric(f"Posição ({serie})", f"{classif['posicao']}º")
        c2.metric("Pontos", classif["pontos"])
        c3.metric("Aproveitamento", f"{(classif['aproveitamento'] or 0):.0f}%")
        c4.metric("V-E-D", f"{classif['vitorias']}-{classif['empates']}-{classif['derrotas']}")
        c5.metric("Gols (pró / contra)", f"{classif['gols_pro']} / {classif['gols_contra']}", delta=f"saldo {classif['saldo']:+d}")
        c6.metric("Jogos sem sofrer gol", est.get("jogos_sem_sofrer_gol", "-"))
        ultimos = (classif.get("ultimos_jogos") or "").replace(",", " ") or "-"
        st.write(
            f"Últimos jogos: **{ultimos}** · Cartões: {classif['cartoes_amarelo']} amarelos, "
            f"{classif['cartoes_vermelho']} vermelhos · Próximo adversário: {classif.get('proximo_adversario') or '-'}"
        )
        coletado = dt.datetime.fromisoformat(classif["coletado_em"]).strftime("%d/%m/%Y %H:%M")
        st.caption(
            f"Fonte: páginas públicas da CBF ({serie} {classif['ano']}, após a rodada {classif['rodada']}); coletado em {coletado}. "
            "Dado guardado só neste computador."
        )
        with st.expander("Calendário e resultados da temporada (CBF)"):
            partidas = partidas_do_participante(conexao, participante_id)
            st.dataframe(
                pd.DataFrame(
                    [
                        {
                            "Rodada": x["rodada"],
                            "Data": formatar_data_br(x["data"]),
                            "Hora": x["hora"] or "-",
                            "Mando": x["mando"],
                            "Adversário": x["adversario"],
                            "Placar (feitos x sofridos)": f"{x['gols_feitos']} x {x['gols_sofridos']}" if x["realizada"] else "a jogar",
                            "Local": x["local"] or "-",
                        }
                        for x in partidas
                    ]
                ),
                width="stretch",
                hide_index=True,
            )


def renderizar_aba_loteca(conexao, participante_id):
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

        g1.plotly_chart(_gauge(aproveitamento["casa"], "Em casa", aproveitamento["jogos_casa"]), width="stretch")
        g2.plotly_chart(_gauge(aproveitamento["fora"], "Fora de casa", aproveitamento["jogos_fora"]), width="stretch")

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
        st.plotly_chart(barra, width="stretch")

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
            st.plotly_chart(combo, width="stretch")
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
        st.dataframe(pd.DataFrame(linhas_tabela), width="stretch", hide_index=True)
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
            width="stretch",
            hide_index=True,
        )
    else:
        st.caption("Nenhuma varredura rodada para este participante ainda.")


def _figura_base(titulo_y: str, altura: int = 300):
    figura = go.Figure()
    figura.update_layout(
        height=altura, margin=dict(l=10, r=10, t=10, b=10), yaxis=dict(title=titulo_y),
        xaxis=dict(title="Rodada", dtick=2), legend=dict(orientation="h"),
    )
    return figura


def renderizar_evolucao(evolucao, jogos_time, quantidade_times, aviso_divergencia):
    if aviso_divergencia:
        st.warning(aviso_divergencia)
    rodadas = [e["rodada"] for e in evolucao]
    ultimo = evolucao[-1]

    st.markdown("**Posição na tabela, rodada a rodada**")
    melhor = min(e["posicao"] for e in evolucao)
    pior = max(e["posicao"] for e in evolucao)
    st.caption(
        f"Estreou na {evolucao[0]['posicao']}ª posição, está na {ultimo['posicao']}ª (após a rodada {ultimo['rodada']}); "
        f"melhor posição {melhor}ª, pior {pior}ª. Quanto mais alto no gráfico, melhor a posição."
    )
    posicao = _figura_base("Posição", 320)
    posicao.add_trace(
        go.Scatter(x=rodadas, y=[e["posicao"] for e in evolucao], mode="lines+markers", name="Posição",
                   line=dict(color=AZUL), marker=dict(symbol="circle", size=7))
    )
    posicao.update_yaxes(autorange=False, range=[quantidade_times + 0.5, 0.5], dtick=1)
    st.plotly_chart(posicao, width="stretch")

    st.markdown("**Pontos acumulados x média da série**")
    diferenca = ultimo["pontos"] - ultimo["pontos_media_serie"]
    st.caption(
        f"{ultimo['pontos']} pontos contra média de {ultimo['pontos_media_serie']:.1f} entre os times da série "
        f"({diferenca:+.1f})."
    )
    pontos = _figura_base("Pontos")
    pontos.add_trace(go.Scatter(x=rodadas, y=[e["pontos"] for e in evolucao], mode="lines+markers", name="Este time",
                                line=dict(color=AZUL), marker=dict(symbol="circle")))
    pontos.add_trace(go.Scatter(x=rodadas, y=[e["pontos_media_serie"] for e in evolucao], mode="lines", name="Média da série",
                                line=dict(color=CINZA, dash="dash")))
    st.plotly_chart(pontos, width="stretch")

    st.markdown("**Aproveitamento: temporada e últimos jogos**")
    movel = {m["rodada"]: m["aproveitamento_movel"] for m in aproveitamento_movel(jogos_time)}
    st.caption(
        f"Aproveitamento acumulado: {ultimo['aproveitamento']:.0f}%. "
        + (f"Nos últimos {config.COMPETICAO_JANELA_MOVEL} jogos: {list(movel.values())[-1]:.0f}%." if movel else "Ainda sem jogos suficientes para a média móvel.")
    )
    aprov = _figura_base("Aproveitamento (%)")
    aprov.update_yaxes(range=[0, 100])
    aprov.add_trace(go.Scatter(x=rodadas, y=[e["aproveitamento"] for e in evolucao], mode="lines+markers", name="Acumulado",
                               line=dict(color=AZUL), marker=dict(symbol="circle")))
    if movel:
        aprov.add_trace(go.Scatter(x=list(movel), y=list(movel.values()), mode="lines+markers",
                                   name=f"Últimos {config.COMPETICAO_JANELA_MOVEL} jogos",
                                   line=dict(color=VERMELHO, dash="dot"), marker=dict(symbol="diamond")))
    st.plotly_chart(aprov, width="stretch")

    st.markdown("**Saldo de gols acumulado**")
    saldo = _figura_base("Saldo de gols")
    saldo.add_trace(go.Bar(x=rodadas, y=[e["saldo"] for e in evolucao], name="Saldo", marker_color=AZUL,
                           text=[f"{e['saldo']:+d}" for e in evolucao], textposition="outside"))
    st.plotly_chart(saldo, width="stretch")

    with st.expander("Ver os números em tabela"):
        st.dataframe(
            pd.DataFrame(
                [
                    {
                        "Rodada": e["rodada"], "Posição": e["posicao"], "Jogos": e["jogos"], "Pontos": e["pontos"],
                        "Média de pontos da série": round(e["pontos_media_serie"], 1),
                        "Aproveitamento (%)": round(e["aproveitamento"], 1),
                        f"Aproveitamento últimos {config.COMPETICAO_JANELA_MOVEL} jogos (%)": (
                            round(movel[e["rodada"]], 1) if e["rodada"] in movel else None
                        ),
                        "Saldo de gols": e["saldo"],
                    }
                    for e in evolucao
                ]
            ),
            width="stretch", hide_index=True,
        )
    st.caption(
        "Tabela reconstruída a partir dos placares (pontos, vitórias, saldo, gols pró); confronto direto e cartões "
        "não são aplicados. Um jogo adiado conta na rodada a que pertence."
    )


st.title("Ficha do time")
mostrar_aviso_responsabilidade()
st.caption(
    "Desempenho de um clube ou seleção. Para clubes das Séries A e B do Brasileirão, a ficha usa a temporada "
    "completa lida da CBF. Para os demais, só os jogos que caíram na grade da Loteca -- e isso NÃO é a classificação "
    "oficial de nenhum campeonato."
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

classif = classificacao_do_participante(conexao, participante_id)
cod_time = cod_time_do_participante(conexao, participante_id)
contexto = serie_do_time(conexao, cod_time) if cod_time else None

evolucao, jogos_time, aviso_divergencia, quantidade_times = [], [], None, 0
if contexto:
    serie_time, ano_time = contexto
    partidas_liga = carregar_partidas(conexao, serie_time, ano_time)
    tabelas = tabela_por_rodada(partidas_liga)
    evolucao = evolucao_do_time(tabelas, cod_time)
    jogos_time = jogos_do_time(partidas_liga, cod_time)
    quantidade_times = len(tabelas[max(tabelas)]) if tabelas else 0
    validacao = validar_temporada(conexao, serie_time, ano_time)
    if any(d["cod_time"] == cod_time for d in validacao["divergencias_numeros"]):
        aviso_divergencia = (
            "A tabela reconstruída deste time difere da classificação oficial da CBF: falta ao menos um jogo na "
            "última coleta (a página do time na CBF pode estar atrasada). Os gráficos podem estar uma rodada "
            "defasados; a classificação oficial está na aba 'Visão geral'."
        )

aba_visao, aba_evolucao, aba_loteca = st.tabs(["Visão geral", "Evolução na competição", "Na Loteca"])

with aba_visao:
    if contexto:
        st.success(
            f"Ficha completa: dados da CBF ({NOMES_SERIE.get(contexto[0], contexto[0])} {contexto[1]}, "
            f"{len(jogos_time)} jogos com placar)."
        )
        for frase in frases_visao_geral(evolucao, jogos_time):
            st.write("- " + frase)
        if aviso_divergencia:
            st.warning(aviso_divergencia)
    else:
        st.info(
            "Ficha reduzida: este participante não tem dados da CBF (só clubes das Séries A e B são coletados). "
            "As informações disponíveis estão na aba 'Na Loteca', com base apenas nos jogos que caíram na grade."
        )
    renderizar_classificacao_oficial(conexao, participante_id, classif)

with aba_evolucao:
    if evolucao:
        renderizar_evolucao(evolucao, jogos_time, quantidade_times, aviso_divergencia)
    else:
        st.info("A evolução rodada a rodada só existe para clubes das Séries A e B, cujos jogos vêm da CBF.")

with aba_loteca:
    renderizar_aba_loteca(conexao, participante_id)

conexao.close()
