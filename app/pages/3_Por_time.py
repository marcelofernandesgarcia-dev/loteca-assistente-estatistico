import datetime as dt
import html
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from paleta import AZUL, CINZA, COR_RESULTADO, VERDE, VERMELHO
from util import formatar_data_br, mostrar_aviso_responsabilidade, obter_conexao

import config
from stats.concursos import concurso_a_jogar
from stats.cbf import (
    classificacao_do_participante,
    cod_time_do_participante,
    estatisticas_do_participante,
    nomes_dos_times,
    partidas_do_participante,
)
from stats.competicao import (
    aproveitamento_movel,
    carregar_partidas,
    comparar_com_liga,
    disciplina_da_liga,
    evolucao_do_time,
    forca_do_calendario,
    frases_visao_geral,
    gols_com_media_movel,
    jogos_do_time,
    medias_da_liga,
    perfil_de_gols,
    resumo_por_mando,
    serie_do_time,
    tabela_por_rodada,
    validar_temporada,
)
from stats.desempenho import (
    aproveitamento_casa_fora,
    contagem_por_resultado,
    frases_da_loteca,
    gerar_insight,
    jogos_da_loteca,
    kpis,
    tendencia_por_ano,
)
from stats.forma import forma_recente
from stats.frequencia import frequencia_global, frequencia_participante
from stats.modelo_temporada import analisar_confronto, forcas_da_serie
from stats.percentual import origem_do_percentual, percentual_historico
from stats.temporada import desempenho_no_ano

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


def renderizar_resumo_loteca(conexao, participante_id):
    st.subheader("Resumo na grade da Loteca")
    jogos = jogos_da_loteca(conexao, participante_id)
    if not jogos:
        st.caption("Nenhum jogo apurado deste participante na Loteca ainda.")
        return
    por_mando = frequencia_participante(conexao, participante_id)
    referencia = frequencia_global(conexao)
    for frase in frases_da_loteca(jogos, por_mando, referencia):
        st.write("- " + frase)

    def linha(nome, dados):
        total = dados["total"]
        return {"Situação": nome, "Jogos": total,
                **{coluna: (f"{dados[coluna]} ({100 * dados[coluna] / total:.0f}%)" if total else "-") for coluna in ("1", "X", "2")}}

    st.dataframe(
        pd.DataFrame(
            [
                linha("Como mandante", por_mando["mandante"]),
                linha("Como visitante", por_mando["visitante"]),
                {"Situação": "Todos os jogos da Loteca (referência)", "Jogos": referencia.get("total_jogos", 0),
                 **{coluna: f"{100 * referencia[coluna]:.0f}%" for coluna in ("1", "X", "2")}},
            ]
        ),
        width="stretch", hide_index=True,
    )
    st.caption("Colunas: 1 = vitória do mandante, X = empate, 2 = vitória do visitante.")


def renderizar_aba_loteca(conexao, participante_id):
    renderizar_resumo_loteca(conexao, participante_id)
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


NOME_RESULTADO = {"V": "Vitória", "E": "Empate", "D": "Derrota"}


def renderizar_jogo_a_jogo(jogos_time, nomes, rotulo="Rodada", recorte="da temporada"):
    st.caption(f"Do primeiro ao último jogo {recorte}. Cada quadrado traz a letra do resultado (V, E ou D); passe o mouse para ver o jogo.")
    quadrados = []
    for j in jogos_time:
        descricao = (
            f"{rotulo} {j['rodada']}: {NOME_RESULTADO[j['resultado']].lower()} {'em casa' if j['mando'] == 'casa' else 'fora'} "
            f"contra {nomes.get(j['adversario_id'], '?')} ({j['gols_pro']} x {j['gols_contra']})"
            + (" (decidido por sorteio)" if j.get("sorteio") else "")
        )
        descricao = html.escape(descricao, quote=True)
        quadrados.append(
            f'<span role="listitem" aria-label="{descricao}" title="{descricao}" style="display:inline-block;min-width:1.9em;text-align:center;margin:2px;'
            f'padding:3px 0;border-radius:4px;color:#fff;font-weight:700;background:{COR_RESULTADO[j["resultado"]]}">'
            f'{j["resultado"]}</span>'
        )
    st.markdown(
        '<div role="list" aria-label="Resultados, do primeiro ao último jogo">' + "".join(quadrados) + "</div>",
        unsafe_allow_html=True,
    )

    col1, col2 = st.columns(2)
    mando = col1.radio("Mando", ["Todos", "Em casa", "Fora"], horizontal=True, key="jj_mando")
    resultados = col2.multiselect(
        "Resultado", ["Vitória", "Empate", "Derrota"], default=["Vitória", "Empate", "Derrota"], key="jj_resultado"
    )
    aceitos = {chave for chave, nome in NOME_RESULTADO.items() if nome in resultados}
    acumulado, linhas = 0, []
    for j in jogos_time:
        acumulado += j["pontos"]
        if (mando == "Em casa" and j["mando"] != "casa") or (mando == "Fora" and j["mando"] != "fora"):
            continue
        if j["resultado"] not in aceitos:
            continue
        linhas.append(
            {
                rotulo: j["rodada"], "Data": formatar_data_br(j["data"]), "Mando": j["mando"],
                "Adversário": nomes.get(j["adversario_id"], "?"),
                "Placar (feitos x sofridos)": f"{j['gols_pro']} x {j['gols_contra']}",
                "Resultado": NOME_RESULTADO[j["resultado"]] + (" (sorteio)" if j.get("sorteio") else ""),
                "Pontos": j["pontos"], "Pontos acumulados": acumulado,
            }
        )
    if linhas:
        st.dataframe(pd.DataFrame(linhas), width="stretch", hide_index=True)
        st.caption(f"{len(linhas)} jogos nesta seleção.")
    else:
        st.caption("Nenhum jogo com esses filtros.")


def _texto_extremo(extremo, nomes):
    if not extremo:
        return "nenhuma"
    return (
        f"{extremo['gols_pro']} x {extremo['gols_contra']} contra {nomes.get(extremo['adversario_id'], '?')} "
        f"({extremo['mando']}, rodada {extremo['rodada']})"
    )


def renderizar_ataque_defesa_mando(jogos_time, partidas_liga, nomes):
    liga = medias_da_liga(partidas_liga)
    perfil = perfil_de_gols(jogos_time)
    mando = resumo_por_mando(jogos_time)
    media_liga = liga["gols_por_time_por_jogo"]

    st.subheader("Gols marcados e sofridos por jogo")
    st.caption(
        f"Média de {perfil['gols_pro_media']:.2f} gols marcados e {perfil['gols_contra_media']:.2f} sofridos por jogo; "
        f"a média da série é {media_liga:.2f} gols por time por jogo. As linhas mostram a média dos últimos "
        f"{config.COMPETICAO_JANELA_MOVEL} jogos."
    )
    linhas = gols_com_media_movel(jogos_time)
    rodadas = [x["rodada"] for x in linhas]
    figura = go.Figure()
    figura.add_trace(go.Bar(x=rodadas, y=[x["gols_pro"] for x in linhas], name="Marcados", marker_color=AZUL, opacity=0.6))
    figura.add_trace(go.Bar(x=rodadas, y=[x["gols_contra"] for x in linhas], name="Sofridos", marker_color=VERMELHO,
                            opacity=0.6, marker_pattern_shape="/"))
    figura.add_trace(go.Scatter(x=rodadas, y=[x["pro_movel"] for x in linhas], mode="lines+markers",
                                name="Marcados (média móvel)", line=dict(color=AZUL), marker=dict(symbol="circle")))
    figura.add_trace(go.Scatter(x=rodadas, y=[x["contra_movel"] for x in linhas], mode="lines+markers",
                                name="Sofridos (média móvel)", line=dict(color=VERMELHO, dash="dot"),
                                marker=dict(symbol="diamond")))
    figura.add_hline(y=media_liga, line_dash="dash", line_color=CINZA, annotation_text=f"média da série {media_liga:.2f}")
    figura.update_layout(height=340, margin=dict(l=10, r=10, t=10, b=10), barmode="group",
                         xaxis=dict(title="Rodada", dtick=2), yaxis=dict(title="Gols"), legend=dict(orientation="h"))
    st.plotly_chart(figura, width="stretch")

    st.subheader("Em casa e fora")
    casa, fora = mando["casa"], mando["fora"]
    if casa["jogos"] and fora["jogos"]:
        dif = casa["aproveitamento"] - fora["aproveitamento"]
        st.caption(
            f"Aproveitamento de {casa['aproveitamento']:.0f}% em casa e {fora['aproveitamento']:.0f}% fora "
            f"(diferença de {abs(dif):.0f} p.p.). Na série, os mandantes somam {liga['aproveitamento_casa']:.0f}% e os "
            f"visitantes {liga['aproveitamento_fora']:.0f}%."
        )
    barras = go.Figure()
    barras.add_trace(go.Bar(x=["Em casa", "Fora"], y=[casa["aproveitamento"] or 0, fora["aproveitamento"] or 0],
                            name="Este time", marker_color=AZUL,
                            text=[f"{casa['aproveitamento'] or 0:.0f}%", f"{fora['aproveitamento'] or 0:.0f}%"],
                            textposition="outside"))
    barras.add_trace(go.Bar(x=["Em casa", "Fora"], y=[liga["aproveitamento_casa"], liga["aproveitamento_fora"]],
                            name="Média da série", marker_color=CINZA, marker_pattern_shape="x",
                            text=[f"{liga['aproveitamento_casa']:.0f}%", f"{liga['aproveitamento_fora']:.0f}%"],
                            textposition="outside"))
    barras.update_layout(height=280, margin=dict(l=10, r=10, t=10, b=10), barmode="group",
                         yaxis=dict(title="Aproveitamento (%)", range=[0, 110]), legend=dict(orientation="h"))
    st.plotly_chart(barras, width="stretch")
    st.dataframe(
        pd.DataFrame(
            [
                {
                    "Mando": nome, "Jogos": r["jogos"], "V": r["vitorias"], "E": r["empates"], "D": r["derrotas"],
                    "Pontos": r["pontos"],
                    "Gols marcados por jogo": round(r["gols_pro_media"], 2) if r["gols_pro_media"] is not None else None,
                    "Gols sofridos por jogo": round(r["gols_contra_media"], 2) if r["gols_contra_media"] is not None else None,
                }
                for nome, r in (("Em casa", casa), ("Fora", fora))
            ]
        ),
        width="stretch", hide_index=True,
    )

    st.subheader("Regularidade")
    r1, r2, r3, r4 = st.columns(4)
    r1.metric("Jogos marcando", f"{perfil['jogos_marcando']} de {perfil['jogos']}")
    r2.metric("Jogos sem sofrer gol", f"{perfil['jogos_sem_sofrer_gol']} de {perfil['jogos']}")
    r3.metric("3+ gols marcados", perfil["jogos_3_ou_mais_gols_marcados"])
    r4.metric("3+ gols sofridos", perfil["jogos_3_ou_mais_gols_sofridos"])
    desvio_pro = f"{perfil['desvio_gols_pro']:.2f}" if perfil["desvio_gols_pro"] is not None else "-"
    desvio_contra = f"{perfil['desvio_gols_contra']:.2f}" if perfil["desvio_gols_contra"] is not None else "-"
    st.write(
        f"Maior vitória: **{_texto_extremo(perfil['maior_vitoria'], nomes)}**. "
        f"Pior derrota: **{_texto_extremo(perfil['pior_derrota'], nomes)}**. "
        f"Variação dos gols (desvio-padrão): {desvio_pro} marcados, {desvio_contra} sofridos -- quanto menor, mais regular."
    )


ROTULOS_METRICAS = {
    "aproveitamento": ("Aproveitamento", "%", False),
    "ataque": ("Gols marcados por jogo", "", False),
    "defesa": ("Gols sofridos por jogo", "", True),
    "saldo_por_jogo": ("Saldo de gols por jogo", "", False),
    "aproveitamento_casa": ("Aproveitamento em casa", "%", False),
    "aproveitamento_fora": ("Aproveitamento fora de casa", "%", False),
    "cartoes_por_jogo": ("Cartões por jogo", "", True),
}
EIXOS_RADAR = ("aproveitamento", "ataque", "defesa", "aproveitamento_casa", "aproveitamento_fora")
NOMES_GRUPO = {"fortes": "Adversários fortes", "medios": "Adversários médios", "fracos": "Adversários fracos"}


def renderizar_comparacao_liga(comparacao, calendario):
    if not comparacao:
        st.info("Sem jogos suficientes para comparar com a série.")
        return
    total = comparacao["aproveitamento"]["de"]
    st.subheader("Posição do time entre os da série")
    st.caption(
        f"Cada linha compara o time com os {total} clubes da série. Posição 1 = melhor; em gols sofridos e cartões, "
        "menos é melhor. O gráfico usa o percentil (100 = melhor da série, 50 = meio da tabela)."
    )
    eixos = [e for e in EIXOS_RADAR if e in comparacao]
    if len(eixos) >= 3:
        rotulos = ["Defesa (poucos gols sofridos)" if e == "defesa" else ROTULOS_METRICAS[e][0] for e in eixos]
        valores = [comparacao[e]["percentil"] for e in eixos]
        radar = go.Figure()
        radar.add_trace(go.Scatterpolar(r=valores + valores[:1], theta=rotulos + rotulos[:1], fill="toself", name="Este time",
                                        line=dict(color=AZUL), marker=dict(symbol="circle")))
        radar.add_trace(go.Scatterpolar(r=[50] * (len(eixos) + 1), theta=rotulos + rotulos[:1], name="Meio da série (50)",
                                        line=dict(color=CINZA, dash="dash")))
        radar.update_layout(height=380, margin=dict(l=40, r=40, t=20, b=20), polar=dict(radialaxis=dict(range=[0, 100])),
                            legend=dict(orientation="h"))
        st.plotly_chart(radar, width="stretch")
    linhas = []
    for chave, (rotulo, unidade, _) in ROTULOS_METRICAS.items():
        if chave not in comparacao:
            continue
        r = comparacao[chave]
        sufixo = "%" if unidade == "%" else ""
        linhas.append(
            {
                "Indicador": rotulo, "Este time": f"{r['valor']:.2f}{sufixo}", "Média da série": f"{r['media_da_serie']:.2f}{sufixo}",
                "Posição": f"{r['posicao']}º de {r['de']}", "Percentil": round(r["percentil"]),
            }
        )
    st.dataframe(pd.DataFrame(linhas), width="stretch", hide_index=True)

    st.subheader("Força do calendário já enfrentado")
    if not calendario:
        st.caption("Sem jogos suficientes para avaliar o calendário.")
        return
    diferenca = calendario["forca_media_adversarios"] - calendario["forca_media_da_serie"]
    if abs(diferenca) < 2:
        leitura = "dificuldade próxima da média"
    else:
        leitura = "adversários mais fortes que a média" if diferenca > 0 else "adversários mais fracos que a média"
    st.caption(
        f"Os adversários enfrentados somam {calendario['forca_media_adversarios']:.1f}% de aproveitamento médio "
        f"(média da série: {calendario['forca_media_da_serie']:.1f}%): {leitura}. Calendário {calendario['posicao_dificuldade']}º "
        f"mais difícil entre {calendario['times_comparados']} (1º = mais difícil). O aproveitamento de cada adversário não "
        "conta o jogo contra este time. A temporada ainda está em andamento, então a força dos adversários muda a cada rodada."
    )
    grupos = calendario["grupos"]
    barras = go.Figure()
    nomes_grupo = [NOMES_GRUPO[g] for g in grupos]
    valores = [grupos[g]["aproveitamento"] or 0 for g in grupos]
    barras.add_trace(go.Bar(x=nomes_grupo, y=valores, marker_color=AZUL, name="Aproveitamento",
                            text=[f"{v:.0f}% em {grupos[g]['jogos']} jogos" for v, g in zip(valores, grupos)], textposition="outside"))
    barras.update_layout(height=300, margin=dict(l=10, r=10, t=10, b=10), yaxis=dict(title="Aproveitamento (%)", range=[0, 115]))
    st.plotly_chart(barras, width="stretch")
    st.dataframe(
        pd.DataFrame(
            [
                {"Grupo": NOMES_GRUPO[g], "Jogos": r["jogos"], "V": r["vitorias"], "E": r["empates"], "D": r["derrotas"],
                 "Pontos": r["pontos"], "Aproveitamento (%)": round(r["aproveitamento"], 1) if r["aproveitamento"] is not None else None}
                for g, r in grupos.items()
            ]
        ),
        width="stretch", hide_index=True,
    )
    st.caption(
        "Fortes, médios e fracos são os terços da série ordenados pelo aproveitamento (o terço de cima, o do meio e o de baixo). "
        "Não é uma previsão: mostra contra quem o time já pontuou."
    )


AVISO_MODELO_TEMPORADA = (
    "Modelo experimental da temporada: estima a força de ataque e de defesa de cada time com os jogos da série "
    f"(com peso de {config.MODELO_TEMPORADA_PESO_PRIOR:g} jogos de um time médio para não exagerar em quem tem pouca amostra) "
    "e calcula as chances de cada placar. Ainda não foi testado contra resultados passados (etapa de backtest) e é uma "
    "estimativa para análise, não previsão nem garantia."
)


def _barra_resultado(nome_casa, nome_fora, analise):
    figura = go.Figure()
    for nome, valor, cor in (
        (f"Vitória {nome_casa}", analise["p_casa"], AZUL),
        ("Empate", analise["p_empate"], CINZA),
        (f"Vitória {nome_fora}", analise["p_fora"], VERMELHO),
    ):
        figura.add_trace(go.Bar(y=[""], x=[valor * 100], name=nome, orientation="h", marker_color=cor,
                                text=f"{valor * 100:.0f}%", textposition="inside", textfont=dict(color="#ffffff")))
    figura.update_layout(barmode="stack", height=120, margin=dict(l=0, r=0, t=10, b=10),
                         xaxis=dict(range=[0, 100], showticklabels=False), legend=dict(orientation="h"))
    return figura


def _mapa_de_placares(nome_casa, nome_fora, matriz, limite=6):
    z = [[matriz[c][f] * 100 for f in range(limite + 1)] for c in range(limite + 1)]
    figura = go.Figure(
        go.Heatmap(z=z, x=list(range(limite + 1)), y=list(range(limite + 1)), colorscale="Blues",
                   text=[[f"{v:.1f}" for v in linha] for linha in z], texttemplate="%{text}", showscale=False)
    )
    figura.update_layout(height=380, margin=dict(l=10, r=10, t=10, b=10),
                         xaxis=dict(title=f"Gols de {nome_fora}", dtick=1), yaxis=dict(title=f"Gols de {nome_casa}", dtick=1))
    return figura


def renderizar_analise_de_confronto(nome_casa, nome_fora, analise):
    c1, c2, c3 = st.columns(3)
    c1.metric(f"Gols esperados: {nome_casa}", f"{analise['gols_esperados_casa']:.2f}")
    c2.metric(f"Gols esperados: {nome_fora}", f"{analise['gols_esperados_fora']:.2f}")
    c3.metric("Base de jogos", f"{analise['jogos_casa']} e {analise['jogos_fora']}")
    st.plotly_chart(_barra_resultado(nome_casa, nome_fora, analise), width="stretch")
    st.write(
        f"Vitória {nome_casa}: **{analise['p_casa'] * 100:.0f}%** · Empate: **{analise['p_empate'] * 100:.0f}%** · "
        f"Vitória {nome_fora}: **{analise['p_fora'] * 100:.0f}%**"
    )
    st.subheader("Placares mais prováveis")
    st.dataframe(
        pd.DataFrame(
            [
                {"Placar": f"{nome_casa} {x['gols_casa']} x {x['gols_fora']} {nome_fora}", "Chance": f"{x['probabilidade'] * 100:.1f}%"}
                for x in analise["placares_mais_provaveis"]
            ]
        ),
        width="stretch", hide_index=True,
    )
    m1, m2, m3, m4 = st.columns(4)
    m1.metric(f"{nome_casa} marca", f"{analise['p_casa_marca'] * 100:.0f}%")
    m2.metric(f"{nome_fora} marca", f"{analise['p_fora_marca'] * 100:.0f}%")
    m3.metric("Os dois marcam", f"{analise['p_ambos_marcam'] * 100:.0f}%")
    m4.metric("3 ou mais gols no jogo", f"{analise['p_3_ou_mais_gols'] * 100:.0f}%")
    with st.expander("Ver todos os placares (chance em %)"):
        st.plotly_chart(_mapa_de_placares(nome_casa, nome_fora, analise["matriz"]), width="stretch")
        limite = 6
        st.dataframe(
            pd.DataFrame(
                [[round(analise["matriz"][c][f] * 100, 1) for f in range(limite + 1)] for c in range(limite + 1)],
                index=[f"{nome_casa}: {c} gols" for c in range(limite + 1)],
                columns=[f"{nome_fora}: {f}" for f in range(limite + 1)],
            ),
            width="stretch",
        )


def renderizar_proximo_jogo(conexao, participante_id, cod_time, classif, partidas_liga, nomes):
    if cod_time and classif:
        st.subheader("Próximo adversário (CBF)")
        if classif.get("proximo_adversario"):
            st.write(
                f"Próximo adversário na tabela: **{classif['proximo_adversario']}**. A página da CBF não informa "
                "mando nem data desse jogo; por isso o simulador abaixo deixa você escolher o mando."
            )
        else:
            st.caption("A CBF não informou o próximo adversário (temporada encerrada ou rodada sem jogo definido).")

    forcas = forcas_da_serie(partidas_liga) if partidas_liga else None
    if cod_time and forcas and cod_time in forcas["jogos"]:
        st.subheader("Simulador de confronto (jogos da temporada)")
        st.caption(AVISO_MODELO_TEMPORADA)
        outros = [cod for cod in forcas["jogos"] if cod != cod_time]
        outros.sort(key=lambda cod: nomes.get(cod, ""))
        padrao = classif.get("proximo_adversario_id") if classif else None
        indice = outros.index(padrao) if padrao in outros else 0
        col1, col2 = st.columns(2)
        adversario = col1.selectbox("Adversário", outros, index=indice, format_func=lambda cod: nomes.get(cod, str(cod)), key="sim_adversario")
        mando = col2.radio("Este time joga", ["Em casa", "Fora de casa"], horizontal=True, key="sim_mando")
        casa, fora = (cod_time, adversario) if mando == "Em casa" else (adversario, cod_time)
        analise = analisar_confronto(forcas, casa, fora)
        if analise:
            renderizar_analise_de_confronto(nomes.get(casa, "?"), nomes.get(fora, "?"), analise)
    elif cod_time:
        st.info("Sem jogos suficientes da série para simular um confronto.")

    st.subheader("Jogo na Loteca (concurso a jogar)")
    a_jogar = concurso_a_jogar(conexao)
    jogos_loteca = []
    if a_jogar:
        jogos_loteca = conexao.execute(
            """
            SELECT j.num_jogo, j.data_jogo, j.casa_id, j.fora_id, pc.nome AS casa, pf.nome AS fora
            FROM jogos j JOIN participantes pc ON pc.id = j.casa_id JOIN participantes pf ON pf.id = j.fora_id
            WHERE j.concurso_numero = ? AND (j.casa_id = ? OR j.fora_id = ?) ORDER BY j.num_jogo
            """,
            (a_jogar["numero"], participante_id, participante_id),
        ).fetchall()
    if not jogos_loteca:
        st.caption("Este participante não está na grade do concurso a jogar.")
        return
    for jogo in jogos_loteca:
        st.write(f"**Concurso {a_jogar['numero']} · jogo {jogo['num_jogo']}: {jogo['casa']} x {jogo['fora']}** ({formatar_data_br(jogo['data_jogo'])})")
        atual = percentual_historico(conexao, jogo["casa_id"], jogo["fora_id"])
        origem = origem_do_percentual(conexao, jogo["casa_id"], jogo["fora_id"])
        linhas = [{
            "Modelo": "Atual (histórico da Loteca)",
            f"Vitória {jogo['casa']}": f"{atual['1']:.0f}%", "Empate": f"{atual['X']:.0f}%", f"Vitória {jogo['fora']}": f"{atual['2']:.0f}%",
        }]
        cod_casa, cod_fora = cod_time_do_participante(conexao, jogo["casa_id"]), cod_time_do_participante(conexao, jogo["fora_id"])
        analise = None
        if cod_casa and cod_fora and forcas:
            analise = analisar_confronto(forcas, cod_casa, cod_fora)
        if analise:
            linhas.append({
                "Modelo": "Temporada (experimental)",
                f"Vitória {jogo['casa']}": f"{analise['p_casa'] * 100:.0f}%", "Empate": f"{analise['p_empate'] * 100:.0f}%",
                f"Vitória {jogo['fora']}": f"{analise['p_fora'] * 100:.0f}%",
            })
        st.dataframe(pd.DataFrame(linhas), width="stretch", hide_index=True)
        if origem["metodo"] == "frequencia_global":
            st.caption(
                f"Modelo atual: amostra pequena na base da Loteca (menor cenário com {origem['menor_amostra']} jogos, mínimo "
                f"{origem['minimo_necessario']}); por isso o resultado é a frequência global de 1/X/2, igual para vários jogos, "
                "e não diz nada específico sobre estes times."
            )
        else:
            st.caption("Modelo atual: força de ataque e defesa dos times nos jogos que já caíram na Loteca.")
        if analise:
            st.caption(AVISO_MODELO_TEMPORADA)
            renderizar_analise_de_confronto(jogo["casa"], jogo["fora"], analise)
        else:
            st.caption("Modelo da temporada indisponível: os dois times precisam estar na mesma série do Brasileirão coletada pela CBF.")


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

    st.subheader("Posição na tabela, rodada a rodada")
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

    st.subheader("Pontos acumulados x média da série")
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

    st.subheader("Aproveitamento: temporada e últimos jogos")
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

    st.subheader("Saldo de gols acumulado")
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

evolucao, jogos_time, aviso_divergencia, quantidade_times, partidas_liga = [], [], None, 0, []
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

aba_visao, aba_evolucao, aba_jogos, aba_ataque, aba_liga, aba_proximo, aba_loteca = st.tabs(
    ["Visão geral", "Evolução na competição", "Jogo a jogo", "Ataque, defesa e mando", "Comparação com a liga",
     "Próximo jogo e resultados possíveis", "Na Loteca"]
)
nomes = nomes_dos_times(conexao)
nomes_participantes = {p["id"]: p["nome"] for p in participantes}

with aba_visao:
    st.header("Visão geral")
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
            "Os números abaixo e as demais informações da aba 'Na Loteca' vêm apenas dos jogos que caíram na grade."
        )
        jogos_loteca = jogos_da_loteca(conexao, participante_id)
        for frase in frases_da_loteca(jogos_loteca, frequencia_participante(conexao, participante_id), frequencia_global(conexao)):
            st.write("- " + frase)
    renderizar_classificacao_oficial(conexao, participante_id, classif)

with aba_evolucao:
    st.header("Evolução na competição")
    if evolucao:
        renderizar_evolucao(evolucao, jogos_time, quantidade_times, aviso_divergencia)
    else:
        st.info("A evolução rodada a rodada só existe para clubes das Séries A e B, cujos jogos vêm da CBF.")

with aba_jogos:
    st.header("Jogo a jogo")
    if jogos_time:
        renderizar_jogo_a_jogo(jogos_time, nomes)
    else:
        jogos_loteca = jogos_da_loteca(conexao, participante_id)
        if jogos_loteca:
            st.info("Ficha reduzida: aqui estão só os jogos deste participante na grade da Loteca, não a temporada completa.")
            renderizar_jogo_a_jogo(jogos_loteca, nomes_participantes, rotulo="Concurso", recorte="deste participante na Loteca")
        else:
            st.info("Nenhum jogo apurado deste participante na Loteca ainda.")

with aba_ataque:
    st.header("Ataque, defesa e mando")
    if jogos_time:
        renderizar_ataque_defesa_mando(jogos_time, partidas_liga, nomes)
    else:
        st.info("Ataque, defesa e mando por temporada existem para clubes das Séries A e B. Para os demais, veja a aba 'Na Loteca'.")

with aba_liga:
    st.header("Comparação com a liga")
    if jogos_time:
        renderizar_comparacao_liga(
            comparar_com_liga(partidas_liga, cod_time, disciplina_da_liga(conexao, serie_time, ano_time)),
            forca_do_calendario(partidas_liga, cod_time),
        )
    else:
        st.info("A comparação com a série existe para clubes das Séries A e B. Para os demais, veja a aba 'Na Loteca'.")

with aba_proximo:
    st.header("Próximo jogo e resultados possíveis")
    renderizar_proximo_jogo(conexao, participante_id, cod_time, classif, partidas_liga, nomes)

with aba_loteca:
    st.header("Na Loteca")
    renderizar_aba_loteca(conexao, participante_id)

conexao.close()
