"""Painel comparativo de times e seleções (Fase Q5; plano v2 aprovado em
29/09/2026 -- docs/plano-dashboard-q5.md). Só apresentação: as contas estão em
stats/painel.py e stats/competicao.py."""
import html
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import plotly.graph_objects as go
import streamlit as st
from paleta import CINZA, CINZA_CLARO, COR_RESULTADO, CORES_LINHAS, MARCADORES_LINHAS, TRACOS_LINHAS
from util import mostrar_aviso_responsabilidade, obter_conexao

import config
from stats.cbf import nomes_dos_times
from stats.concursos import concurso_a_jogar
from stats.contexto import NOMES_ZONA
from stats.painel import (
    dados_da_temporada,
    erro_da_projecao_entre_temporadas,
    frase_amostra_pequena,
    frase_de_projecao,
    frases_da_loteca,
    frases_da_temporada,
    jogos_loteca,
    nomes_da_temporada,
    participantes_com_minimo,
    participantes_do_concurso,
    resumo_loteca,
    reta_anual,
    tabela_comparativa,
    temporadas_atuais,
    temporadas_disponiveis,
    tendencia_anual_loteca,
    tendencia_do_aproveitamento,
)

NOME_SERIE = {"serie-a": "Série A", "serie-b": "Série B"}
FAIXA_ZONA = {
    "libertadores_grupos": "rgba(26,79,160,0.10)",
    "libertadores_preliminar": "rgba(26,79,160,0.06)",
    "sul_americana": "rgba(30,107,64,0.08)",
    "acesso_direto": "rgba(26,79,160,0.10)",
    "playoff_acesso": "rgba(30,107,64,0.08)",
    "rebaixamento": "rgba(179,0,16,0.08)",
}

st.title("Painel comparativo")
mostrar_aviso_responsabilidade()
st.caption(
    "Compara vários times e seleções ao mesmo tempo. As duas abas usam fontes diferentes e nunca se misturam num "
    "número só: a temporada da CBF (campeonato inteiro) e o histórico nos jogos que caíram na Loteca. Aproveitamento "
    "aqui é sempre por pontos (vitória 3, empate 1), a mesma conta da CBF."
)


# --- formatação ---------------------------------------------------------------

def _pct(valor: float | None) -> str:
    return "-" if valor is None else f"{valor:.0f}%"


def _dec(valor: float | None) -> str:
    return "-" if valor is None else f"{valor:.1f}".replace(".", ",")


def _estilo(indice: int) -> dict:
    i = indice % len(CORES_LINHAS)
    return {"cor": CORES_LINHAS[i], "traco": TRACOS_LINHAS[i], "marcador": MARCADORES_LINHAS[i]}


def _tabela_html(legenda: str, cabecalho: list[str], linhas: list[list[str]]) -> None:
    """Tabela acessível (caption e th scope) que rola dentro do próprio espaço
    em tela estreita, em vez de ser cortada. Todo texto já vem escapado."""
    ths = "".join(f"<th scope='col'>{c}</th>" for c in cabecalho)
    corpo = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in linha) + "</tr>" for linha in linhas)
    st.markdown(
        f"<div style='overflow-x:auto'><table style='min-width:640px'>"
        f"<caption style='text-align:left;font-weight:600'>{legenda}</caption>"
        f"<thead><tr>{ths}</tr></thead><tbody>{corpo}</tbody></table></div>",
        unsafe_allow_html=True,
    )


def _layout(figura: go.Figure, titulo: str, eixo_x: str, eixo_y: str, altura: int = 360) -> go.Figure:
    figura.update_layout(
        title=titulo, height=altura, margin=dict(l=10, r=10, t=50, b=10), xaxis_title=eixo_x, yaxis_title=eixo_y,
        legend=dict(orientation="h", yanchor="top", y=-0.2),
    )
    return figura


# --- aba 1: temporada (CBF) ------------------------------------------------------

def grafico_posicao(dados: dict, cods: list[int], nomes: dict[int, str]) -> go.Figure:
    figura = go.Figure()
    for nome_zona, intervalo in (config.ZONAS_CBF.get((dados["serie"], dados["ano"])) or {}).items():
        figura.add_hrect(
            y0=intervalo.start - 0.5, y1=intervalo.stop - 0.5, fillcolor=FAIXA_ZONA.get(nome_zona, "rgba(0,0,0,0.04)"),
            line_width=0, annotation_text=NOMES_ZONA[nome_zona], annotation_position="top left", annotation_font_size=10,
        )
    for i, cod in enumerate(cods):
        estilo, evolucao = _estilo(i), dados["evolucao"][cod]
        figura.add_trace(
            go.Scatter(
                x=[e["rodada"] for e in evolucao], y=[e["posicao"] for e in evolucao], name=nomes.get(cod, str(cod)),
                mode="lines+markers", line=dict(color=estilo["cor"], dash=estilo["traco"]),
                marker=dict(symbol=estilo["marcador"], size=6),
            )
        )
        projecao = (dados["projecao"] or {}).get(cod)
        if projecao and projecao["restantes"] and evolucao:
            figura.add_trace(
                go.Scatter(
                    x=[evolucao[-1]["rodada"], dados["rodada_final"]],
                    y=[evolucao[-1]["posicao"], projecao["posicao_proj_temporada"]],
                    mode="lines+markers", showlegend=False, hoverinfo="skip",
                    line=dict(color=estilo["cor"], dash="dot", width=1),
                    marker=dict(symbol=f"{estilo['marcador']}-open", size=9),
                )
            )
    figura.update_yaxes(autorange="reversed", dtick=1)
    return _layout(figura, "Posição rodada a rodada (1º no topo) e posição projetada no fim", "Rodada", "Posição", 460)


def grafico_pontos(dados: dict, cods: list[int], nomes: dict[int, str], altura: int = 380) -> go.Figure:
    figura = go.Figure()
    for i, cod in enumerate(cods):
        estilo, evolucao = _estilo(i), dados["evolucao"][cod]
        figura.add_trace(
            go.Scatter(
                x=[e["rodada"] for e in evolucao], y=[e["pontos"] for e in evolucao], name=nomes.get(cod, str(cod)),
                mode="lines+markers", line=dict(color=estilo["cor"], dash=estilo["traco"]),
                marker=dict(symbol=estilo["marcador"], size=5),
            )
        )
        projecao = (dados["projecao"] or {}).get(cod)
        if projecao and projecao["restantes"] and evolucao:
            ultimo = evolucao[-1]
            for chave, rotulo in (("pontos_proj_temporada", "ritmo da temporada"), ("pontos_proj_cautelosa", "projeção cautelosa")):
                figura.add_trace(
                    go.Scatter(
                        x=[ultimo["rodada"], dados["rodada_final"]], y=[ultimo["pontos"], projecao[chave]],
                        mode="lines", showlegend=False, line=dict(color=estilo["cor"], dash="dot", width=1),
                        hovertemplate=f"{nomes.get(cod, cod)}, {rotulo}: %{{y:.0f}} pontos<extra></extra>",
                    )
                )
    if cods:
        media = dados["evolucao"][cods[0]]
        figura.add_trace(
            go.Scatter(
                x=[e["rodada"] for e in media], y=[e["pontos_media_serie"] for e in media], name="Média da série",
                mode="lines", line=dict(color=CINZA, dash="dash"),
            )
        )
    return _layout(figura, "Pontos acumulados e projeção até o fim (linhas pontilhadas)", "Rodada", "Pontos", altura)


def grafico_aproveitamento(dados: dict, cods: list[int], nomes: dict[int, str]) -> go.Figure:
    figura = go.Figure()
    for i, cod in enumerate(cods):
        estilo, movel = _estilo(i), dados["movel"][cod]
        if not movel:
            continue
        figura.add_trace(
            go.Scatter(
                x=[m["rodada"] for m in movel], y=[m["aproveitamento_movel"] for m in movel], name=nomes.get(cod, str(cod)),
                mode="lines+markers", line=dict(color=estilo["cor"], dash=estilo["traco"]),
                marker=dict(symbol=estilo["marcador"], size=5),
            )
        )
        reta = tendencia_do_aproveitamento(movel, dados["rodada_final"])
        if reta:
            figura.add_trace(
                go.Scatter(
                    x=[p["rodada"] for p in reta], y=[p["valor"] for p in reta], mode="lines", showlegend=False,
                    line=dict(color=estilo["cor"], dash="dot", width=1), hoverinfo="skip",
                )
            )
    figura.update_yaxes(range=[0, 100])
    return _layout(
        figura, f"Aproveitamento nos últimos {config.COMPETICAO_JANELA_MOVEL} jogos e reta de tendência até o fim",
        "Rodada", "Aproveitamento (%)",
    )


def grafico_ved(rotulos: list[str], vitorias: list[int], empates: list[int], derrotas: list[int], titulo: str) -> go.Figure:
    """Barras em % (cada participante soma 100%), com o número de jogos escrito
    na barra: compara participantes com amostras muito diferentes sem esconder
    o tamanho de cada uma."""
    figura = go.Figure()
    for nome, valores, cor in (("Vitórias", vitorias, COR_RESULTADO["V"]), ("Empates", empates, COR_RESULTADO["E"]),
                               ("Derrotas", derrotas, COR_RESULTADO["D"])):
        figura.add_trace(
            go.Bar(y=rotulos, x=valores, name=nome, orientation="h", marker_color=cor, text=valores, textposition="inside",
                   insidetextfont=dict(color="#ffffff"), hovertemplate=f"%{{y}}: %{{text}} {nome.lower()} (%{{x:.0f}}%)<extra></extra>")
        )
    figura.update_layout(barmode="stack", barnorm="percent")
    figura.update_yaxes(autorange="reversed")
    return _layout(figura, titulo, "% dos jogos (número de jogos escrito na barra)", "", 60 + 32 * len(rotulos))


def grafico_ataque_defesa(dados: dict, cods: list[int], nomes: dict[int, str]) -> go.Figure:
    metricas = dados["metricas"]
    figura = go.Figure()
    fundo = [c for c in metricas if c not in cods]
    figura.add_trace(
        go.Scatter(
            x=[metricas[c]["ataque"] for c in fundo], y=[metricas[c]["defesa"] for c in fundo], mode="markers",
            name="Demais times da série", marker=dict(color=CINZA_CLARO, size=8),
            text=[nomes.get(c, str(c)) for c in fundo], hovertemplate="%{text}<extra></extra>",
        )
    )
    for i, cod in enumerate(cods):
        if cod not in metricas:
            continue
        estilo = _estilo(i)
        figura.add_trace(
            go.Scatter(
                x=[metricas[cod]["ataque"]], y=[metricas[cod]["defesa"]], mode="markers+text", name=nomes.get(cod, str(cod)),
                text=[nomes.get(cod, str(cod))], textposition="top center",
                marker=dict(color=estilo["cor"], symbol=estilo["marcador"], size=12),
            )
        )
    todos = list(metricas.values())
    if todos:
        figura.add_vline(x=sum(m["ataque"] for m in todos) / len(todos), line_dash="dash", line_color=CINZA)
        figura.add_hline(y=sum(m["defesa"] for m in todos) / len(todos), line_dash="dash", line_color=CINZA)
    figura.update_yaxes(autorange="reversed")
    return _layout(
        figura, "Ataque x defesa (gols por jogo; defesa melhor para cima; tracejado = média da série)",
        "Gols marcados por jogo", "Gols sofridos por jogo", 440,
    )


def mapa_de_calor(dados: dict, nomes: dict[int, str]) -> go.Figure:
    tabelas = dados["tabelas"]
    rodadas = sorted(tabelas)
    ultima = tabelas[rodadas[-1]]
    ordem = [linha["cod_time"] for linha in ultima]
    posicoes = {r: {linha["cod_time"]: linha["posicao"] for linha in tabelas[r]} for r in rodadas}
    z = [[posicoes[r].get(cod) for r in rodadas] for cod in ordem]
    figura = go.Figure(
        go.Heatmap(
            z=z, x=rodadas, y=[nomes.get(cod, str(cod)) for cod in ordem], text=z, texttemplate="%{text}",
            colorscale="Blues", reversescale=True, showscale=False,
            hovertemplate="%{y}, rodada %{x}: %{z}º<extra></extra>",
        )
    )
    figura.update_yaxes(autorange="reversed")
    return _layout(
        figura, "Todos os times da série: posição em cada rodada (número na célula; mais escuro = mais perto do topo)",
        "Rodada", "", 80 + 26 * len(ordem),
    )


@st.cache_data(show_spinner=False)
def _erro_entre_temporadas(_conexao, versao_dos_jogos: int):
    """O erro da projeção medido em todas as temporadas completas leva alguns segundos;
    fica em cache e é refeito quando entram jogos novos (`versao_dos_jogos`)."""
    return erro_da_projecao_entre_temporadas(_conexao)


def _versao_dos_jogos(conexao) -> int:
    return conexao.execute("SELECT COUNT(*) FROM cbf_partidas WHERE gols_mandante IS NOT NULL").fetchone()[0]


def mostrar_temporada(
    dados: dict, cods: list[int], nomes: dict[int, str], chave: str, erro_entre: dict | None = None
) -> None:
    """Tabela, leituras, gráficos e mapa de calor de uma série, para os times pedidos."""
    linhas = tabela_comparativa(dados, cods)
    cods = [linha["cod_time"] for linha in linhas]
    if not cods:
        st.info("Nenhum dos times escolhidos tem jogos coletados nesta série.")
        return

    for frase in frases_da_temporada(dados, cods, nomes, erro_entre):
        st.markdown(f"- {frase}")
    if dados["projecao"] is None and dados.get("encerrada"):
        st.caption("Temporada encerrada: todos os jogos foram disputados, não há o que projetar.")
    elif dados["projecao"] is None:
        st.info(
            "Sem projeção para esta série: o número de jogos da temporada não está cadastrado a partir do "
            "regulamento (config.TEMPORADA_JOGOS_POR_TIME). O app não supõe o tamanho da temporada."
        )
    else:
        with st.expander("Projeção: se o desempenho persistir", expanded=True):
            st.caption(
                "É um cenário, não uma previsão: supõe que cada time mantém o ritmo e não considera os adversários "
                "que faltam (o calendário futuro não é coletado), lesões, suspensões, troca de técnico ou outras "
                "competições. Todos os times da série são projetados para calcular a posição. Dois cenários: o "
                "**ritmo da temporada** (o que o time fez até aqui se repete) e a **projeção cautelosa**, que mistura "
                "esse ritmo com a média da liga, mais quanto menos jogos o time já disputou. Em 13 temporadas "
                "completas a cautelosa errou menos (números acima)."
            )
            for linha in linhas:
                frase = frase_de_projecao(html.escape(nomes.get(linha["cod_time"], "")), linha["projecao"], NOMES_ZONA)
                if frase:
                    st.markdown(f"- {frase}")

    tabela = []
    for linha in linhas:
        projecao = linha["projecao"]
        faixa = "-"
        if projecao and projecao["restantes"]:
            valores = [projecao["pontos_proj_temporada"], projecao["pontos_proj_cautelosa"]]
            faixa = f"{min(valores):.0f} a {max(valores):.0f}"
        cartoes = linha["cartoes_por_jogo"]
        tabela.append(
            [
                f"{linha['posicao']}º", html.escape(nomes.get(linha["cod_time"], "")),
                html.escape(NOMES_ZONA.get(linha["zona"], "-")) if linha["zona"] else "-",
                str(linha["pontos"]), str(linha["jogos"]), str(linha["vitorias"]), str(linha["empates"]),
                str(linha["derrotas"]), str(linha["gols_pro"]), str(linha["gols_contra"]), str(linha["saldo"]),
                _pct(linha["aproveitamento"]), _pct(linha["aproveitamento_casa"]), _pct(linha["aproveitamento_fora"]),
                html.escape(linha["sequencia"] or "-"), _dec(cartoes), faixa,
            ]
        )
    _tabela_html(
        "Comparação na temporada (posição e pontos: classificação oficial da CBF)",
        ["Pos.", "Time", "Zona", "Pts", "J", "V", "E", "D", "GP", "GC", "Saldo", "Aprov.", "Casa", "Fora",
         "Sequência", "Cartões/jogo", "Pontos no fim (projeção)"],
        tabela,
    )

    if len(cods) <= config.PAINEL_LINHAS_SOBREPOSTAS_MAX:
        st.plotly_chart(grafico_posicao(dados, cods, nomes), width="stretch", key=f"{chave}_posicao")
        st.plotly_chart(grafico_pontos(dados, cods, nomes), width="stretch", key=f"{chave}_pontos")
        st.plotly_chart(grafico_aproveitamento(dados, cods, nomes), width="stretch", key=f"{chave}_aprov")
        st.caption(
            "A reta pontilhada só mostra a direção da média dos últimos jogos. Ela não foi medida como previsão: "
            "essa média, em 13 temporadas, foi pior guia do que o ritmo da temporada inteira. A projeção que foi "
            "medida é a de pontos, acima."
        )
    else:
        st.caption(
            f"Com mais de {config.PAINEL_LINHAS_SOBREPOSTAS_MAX} times, cada um ganha o seu gráfico de pontos e projeção "
            "(mesma escala). A posição de todos está no mapa de calor abaixo."
        )
        # Mesmos eixos em todos os mini-gráficos, para a comparação visual não enganar.
        teto = max(
            [linha["pontos"] for linha in linhas]
            + [v for linha in linhas if linha["projecao"] for v in (linha["projecao"]["pontos_proj_temporada"],
                                                                     linha["projecao"]["pontos_proj_cautelosa"])]
        )
        ultima_rodada = dados["rodada_final"] or max(dados["tabelas"])
        with st.container(horizontal=True, wrap=True, gap="small"):
            for cod in cods:
                with st.container(width=340):
                    figura = grafico_pontos(dados, [cod], nomes, altura=260)
                    figura.update_layout(title=nomes.get(cod, str(cod)), showlegend=False)
                    figura.update_yaxes(range=[0, teto * 1.05])
                    figura.update_xaxes(range=[0, ultima_rodada + 1])
                    st.plotly_chart(figura, width="stretch", key=f"{chave}_mini_{cod}")
    st.plotly_chart(
        grafico_ved(
            [nomes.get(l["cod_time"], "") for l in linhas], [l["vitorias"] for l in linhas],
            [l["empates"] for l in linhas], [l["derrotas"] for l in linhas], "Vitórias, empates e derrotas na temporada",
        ),
        width="stretch", key=f"{chave}_ved",
    )
    st.plotly_chart(grafico_ataque_defesa(dados, cods, nomes), width="stretch", key=f"{chave}_ataque")
    with st.expander("Mapa de calor: todos os times da série, rodada a rodada"):
        st.plotly_chart(mapa_de_calor(dados, nomes), width="stretch", key=f"{chave}_mapa")


def _resumo_lado_cbf(nome: str, cod: int | None, dados_por_cod: dict, nomes_cbf: dict[int, str]) -> str:
    if not cod or cod not in dados_por_cod:
        return f"**{html.escape(nome)}**: sem dados da CBF (seleção ou time fora das Séries A e B). Veja a aba 'Histórico na Loteca'."
    dados = dados_por_cod[cod]
    linha = tabela_comparativa(dados, [cod])[0]
    zona = f", {NOMES_ZONA[linha['zona']]}" if linha["zona"] else ""
    texto = (
        f"**{html.escape(nome)}** ({NOME_SERIE.get(dados['serie'], dados['serie'])}): {linha['posicao']}º{zona} · "
        f"{linha['pontos']} pts em {linha['jogos']} jogos · aproveitamento {_pct(linha['aproveitamento'])}"
    )
    if linha["sequencia"]:
        texto += f" · {html.escape(linha['sequencia'])}"
    frase = frase_de_projecao("Projeção", linha["projecao"], NOMES_ZONA)
    return texto + (f"  \n{frase}" if frase else "")


def aba_temporada(conexao, jogos_concurso: list[dict], numero_concurso: int | None) -> None:
    temporadas = temporadas_disponiveis(conexao)
    if not temporadas:
        st.info(
            "Sem dados da CBF no banco. Colete pela página inicial ('Atualizar tudo') ou rode "
            "`scripts/coleta_cbf.py`. A aba 'Histórico na Loteca' funciona sem eles."
        )
        return
    nomes = nomes_dos_times(conexao)
    # O modo "todos do concurso" usa só a temporada mais recente (a de agora). As passadas
    # (coleta histórica) só entram no modo livre, para comparar; calculadas quando escolhidas.
    dados_series = {t: dados_da_temporada(conexao, *t) for t in temporadas_atuais(temporadas)}
    dados_por_cod = {cod: d for d in dados_series.values() if d for cod in d["times"]}
    erro_entre = _erro_entre_temporadas(conexao, _versao_dos_jogos(conexao))
    modo = st.radio(
        "Quais times analisar", ["Todos os times do concurso a jogar", "Escolher livremente"], horizontal=True,
        key="modo_temporada",
    )
    if modo.startswith("Todos"):
        if not jogos_concurso:
            st.info("Nenhum concurso a jogar encontrado. Use 'Escolher livremente'.")
            return
        cods_concurso = {cod for j in jogos_concurso for cod in (j["casa_cod"], j["fora_cod"]) if cod}
        st.caption(
            f"Concurso {numero_concurso}: {len(cods_concurso)} dos {2 * len(jogos_concurso)} participantes têm dados "
            "da CBF (Séries A e B). Seleções e times de outras divisões aparecem na aba 'Histórico na Loteca'."
        )
        for (serie, ano), dados in dados_series.items():
            if not dados:
                continue
            cods = [c for c in dados["times"] if c in cods_concurso]
            if cods:
                st.subheader(f"{NOME_SERIE.get(serie, serie)} {ano}")
                mostrar_temporada(dados, cods, nomes, f"concurso_{serie}_{ano}", erro_entre)
        st.subheader("Jogo a jogo do concurso")
        for jogo in jogos_concurso:
            if not (jogo["casa_cod"] in dados_por_cod or jogo["fora_cod"] in dados_por_cod):
                continue
            with st.container(border=True):
                st.markdown(f"**{jogo['num_jogo']}. {html.escape(jogo['casa'])} x {html.escape(jogo['fora'])}**")
                st.markdown(_resumo_lado_cbf(jogo["casa"], jogo["casa_cod"], dados_por_cod, nomes))
                st.markdown(_resumo_lado_cbf(jogo["fora"], jogo["fora_cod"], dados_por_cod, nomes))
                lados = [c for c in (jogo["casa_cod"], jogo["fora_cod"]) if c in dados_por_cod]
                if lados:
                    figura = go.Figure()
                    for i, cod in enumerate(lados):
                        dados, estilo = dados_por_cod[cod], _estilo(i)
                        movel = dados["movel"][cod]
                        figura.add_trace(
                            go.Scatter(
                                x=[m["rodada"] for m in movel], y=[m["aproveitamento_movel"] for m in movel],
                                name=nomes.get(cod, str(cod)), mode="lines+markers",
                                line=dict(color=estilo["cor"], dash=estilo["traco"]),
                                marker=dict(symbol=estilo["marcador"], size=5),
                            )
                        )
                        reta = tendencia_do_aproveitamento(movel, dados["rodada_final"])
                        if reta:
                            figura.add_trace(
                                go.Scatter(x=[p["rodada"] for p in reta], y=[p["valor"] for p in reta], mode="lines",
                                           showlegend=False, hoverinfo="skip",
                                           line=dict(color=estilo["cor"], dash="dot", width=1))
                            )
                    figura.update_yaxes(range=[0, 100])
                    st.plotly_chart(
                        _layout(figura, f"Aproveitamento nos últimos {config.COMPETICAO_JANELA_MOVEL} jogos e tendência",
                                "Rodada", "%", 280),
                        width="stretch", key=f"jogo_cbf_{jogo['num_jogo']}",
                    )
    else:
        rotulos = {t: f"{NOME_SERIE.get(t[0], t[0])} {t[1]}" for t in temporadas}
        rotulo_escolhido = st.selectbox("Série e ano", list(rotulos.values()), key="serie_livre")
        escolhida = next(t for t, rotulo in rotulos.items() if rotulo == rotulo_escolhido)
        dados = dados_series.get(escolhida) or dados_da_temporada(conexao, *escolhida)
        if not dados:
            st.info("Sem jogos com placar nesta série.")
            return
        # Nome do time naquela temporada (ex.: "Coritiba" em 2019, "Coritiba SAF" em 2026).
        nomes_da_serie = nomes_da_temporada(conexao, *escolhida)
        if escolhida not in dados_series:
            st.caption(
                f"Temporada passada ({rotulos[escolhida]}): a tabela mostra o resultado final e o nome que cada time tinha "
                "naquele ano. Sem zonas nem projeção, porque não há mais jogos a disputar."
            )
        cods_concurso = {cod for j in jogos_concurso for cod in (j["casa_cod"], j["fora_cod"]) if cod}
        padrao = [c for c in dados["times"] if c in cods_concurso] or [
            l["cod_time"] for l in dados["tabelas"][max(dados["tabelas"])][:4]
        ]
        escolhidos = st.multiselect(
            "Times", options=dados["times"], default=padrao, format_func=lambda c: nomes_da_serie.get(c, str(c)),
            key=f"times_livre_{escolhida[0]}_{escolhida[1]}",
        )
        if not escolhidos:
            st.info("Escolha ao menos um time para comparar.")
            return
        mostrar_temporada(dados, escolhidos, nomes_da_serie, f"livre_{escolhida[0]}_{escolhida[1]}", erro_entre)


# --- aba 2: histórico na Loteca --------------------------------------------------

def _rotulo_participante(p: dict) -> str:
    uf = f" ({p['pais_ou_uf']})" if p.get("pais_ou_uf") else ""
    tipo = "seleção" if p.get("tipo") == "selecao" else "clube"
    return f"{p['nome']}{uf} · {tipo} · {p['jogos']} jogos"


def grafico_anual(series: list[tuple[str, dict]], altura: int = 380) -> go.Figure:
    """`series`: [(nome, tendencia_anual_loteca)]. Marcador cresce com o número
    de jogos do ano; ano com poucos jogos aparece vazado (sinal fraco)."""
    figura = go.Figure()
    for i, (nome, tendencia) in enumerate(series):
        estilo, anos = _estilo(i), tendencia["anos"]
        if not anos:
            continue
        figura.add_trace(
            go.Scatter(
                x=[a["ano"] for a in anos], y=[a["aproveitamento"] for a in anos], name=nome, mode="lines+markers",
                line=dict(color=estilo["cor"], dash=estilo["traco"], width=1.5),
                marker=dict(
                    symbol=[estilo["marcador"] + ("-open" if a["fraco"] else "") for a in anos],
                    size=[min(6 + 2 * a["jogos"], 22) for a in anos], color=estilo["cor"],
                ),
                customdata=[a["jogos"] for a in anos],
                hovertemplate=f"{nome}, %{{x}}: %{{y:.0f}}% em %{{customdata}} jogo(s)<extra></extra>",
            )
        )
        reta = reta_anual(anos)
        if reta:
            figura.add_trace(
                go.Scatter(x=[p["ano"] for p in reta], y=[p["valor"] for p in reta], mode="lines", showlegend=False,
                           hoverinfo="skip", line=dict(color=estilo["cor"], dash="dot", width=1))
            )
    figura.update_yaxes(range=[0, 100])
    return _layout(figura, "Aproveitamento por ano na Loteca", "Ano", "Aproveitamento (%)", altura)


LEGENDA_ANUAL = (
    f"No gráfico por ano: marcador maior = mais jogos no ano; marcador vazado = menos de {config.PAINEL_MIN_JOGOS_ANO} "
    f"jogos (sinal fraco); linha pontilhada = tendência até o ano seguinte, desenhada só com pelo menos "
    f"{config.PAINEL_ANOS_MINIMOS_RETA} anos de base."
)


def mostrar_loteca(
    conexao, participantes: list[dict], periodo: tuple[int | None, int | None], chave: str, graficos_individuais: bool = True
) -> None:
    """`participantes`: [{'id', 'nome'}]. `graficos_individuais=False` no modo
    concurso, em que os blocos por jogo já trazem o gráfico de cada par."""
    ano_inicial, ano_final = periodo
    dados = []
    for p in participantes:
        jogos = jogos_loteca(conexao, p["id"])
        if ano_inicial is not None:
            jogos_periodo = [j for j in jogos if j["ano"] is not None and ano_inicial <= j["ano"] <= ano_final]
        else:
            jogos_periodo = jogos
        dados.append((p, resumo_loteca(jogos, ano_inicial, ano_final), tendencia_anual_loteca(jogos_periodo)))

    pequena = frase_amostra_pequena([html.escape(p["nome"]) for p, r, _ in dados if r["amostra_pequena"] and r["jogos"]])
    if pequena:
        st.markdown(f"- {pequena}")
    for p, resumo, _ in dados:
        for frase in frases_da_loteca(html.escape(p["nome"]), resumo):
            st.markdown(f"- {frase}")
    sem_data = max((r["sem_data_excluidos"] for _, r, _ in dados), default=0)
    if sem_data:
        st.caption("Com período escolhido, jogos sem data no banco ficam de fora (não dá para saber o ano).")

    linhas = [
        [
            html.escape(p["nome"]), str(r["jogos"]), f"{r['vitorias']} ({_pct(r['pct_vitorias'])})",
            f"{r['empates']} ({_pct(r['pct_empates'])})", f"{r['derrotas']} ({_pct(r['pct_derrotas'])})",
            _pct(r["aproveitamento"]), _pct(r["aproveitamento_recente"]), _dec(r["gols_pro_por_jogo"]),
            _dec(r["gols_contra_por_jogo"]), _pct(r["aproveitamento_casa"]), _pct(r["aproveitamento_fora"]),
            "amostra pequena" if r["amostra_pequena"] else "ok",
        ]
        for p, r, _ in dados
    ]
    _tabela_html(
        "Desempenho nos jogos que caíram na Loteca",
        ["Participante", "J", "V", "E", "D", "Aprov.", f"Últimos {config.PAINEL_JANELA_RECENTE_LOTECA}",
         "Gols pró/jogo", "Gols contra/jogo", "Casa", "Fora", "Amostra"],
        linhas,
    )
    series = [(p["nome"], t) for p, _, t in dados]
    st.caption(LEGENDA_ANUAL)
    if graficos_individuais and len(series) <= config.PAINEL_LINHAS_SOBREPOSTAS_MAX:
        st.plotly_chart(grafico_anual(series), width="stretch", key=f"{chave}_anual")
    elif graficos_individuais:
        st.caption(f"Com mais de {config.PAINEL_LINHAS_SOBREPOSTAS_MAX} participantes, cada um ganha o seu gráfico (mesma escala).")
        anos = [a["ano"] for _, t in series for a in t["anos"]]
        with st.container(horizontal=True, wrap=True, gap="small"):
            for i, (nome, tendencia) in enumerate(series):
                with st.container(width=340):
                    figura = grafico_anual([(nome, tendencia)], altura=260)
                    figura.update_layout(title=nome, showlegend=False)
                    if anos:  # mesmo eixo de anos em todos (o de % já é 0-100)
                        figura.update_xaxes(range=[min(anos) - 0.5, max(anos) + 1.5])
                    st.plotly_chart(figura, width="stretch", key=f"{chave}_mini_{i}")
    st.plotly_chart(
        grafico_ved(
            [p["nome"] for p, _, _ in dados], [r["vitorias"] for _, r, _ in dados], [r["empates"] for _, r, _ in dados],
            [r["derrotas"] for _, r, _ in dados], "Vitórias, empates e derrotas nos jogos da Loteca",
        ),
        width="stretch", key=f"{chave}_ved",
    )


def aba_loteca(conexao, jogos_concurso: list[dict], numero_concurso: int | None) -> None:
    st.info("Desempenho nos jogos que caíram na grade da Loteca. Não é classificação de campeonato.")
    anos = conexao.execute(
        "SELECT MIN(CAST(substr(data_jogo, 1, 4) AS INTEGER)), MAX(CAST(substr(data_jogo, 1, 4) AS INTEGER)) FROM jogos "
        "WHERE data_jogo IS NOT NULL AND resultado IS NOT NULL"
    ).fetchone()
    if not anos or anos[0] is None:
        st.info("Ainda não há jogos apurados no banco.")
        return
    primeiro, ultimo = int(anos[0]), int(anos[1])
    escolha = st.slider("Período", min_value=primeiro, max_value=ultimo, value=(primeiro, ultimo), key="periodo_loteca")
    periodo = (None, None) if escolha == (primeiro, ultimo) else escolha
    modo = st.radio(
        "Quem analisar", ["Todos os participantes do concurso a jogar", "Escolher livremente"], horizontal=True,
        key="modo_loteca",
    )
    if modo.startswith("Todos"):
        if not jogos_concurso:
            st.info("Nenhum concurso a jogar encontrado. Use 'Escolher livremente'.")
            return
        st.caption(
            f"Concurso {numero_concurso}: todos os {2 * len(jogos_concurso)} participantes, inclusive os com menos de "
            f"{config.PAINEL_MIN_JOGOS_LOTECA} jogos (marcados como amostra pequena)."
        )
        todos = [
            {"id": j[f"{lado}_id"], "nome": j[lado]} for j in jogos_concurso for lado in ("casa", "fora")
        ]
        mostrar_loteca(conexao, todos, periodo, "loteca_concurso", graficos_individuais=False)
        st.subheader("Jogo a jogo do concurso")
        for jogo in jogos_concurso:
            with st.container(border=True):
                st.markdown(f"**{jogo['num_jogo']}. {html.escape(jogo['casa'])} x {html.escape(jogo['fora'])}**")
                series = []
                for lado in ("casa", "fora"):
                    jogos = jogos_loteca(conexao, jogo[f"{lado}_id"])
                    resumo = resumo_loteca(jogos, *periodo)
                    st.markdown(
                        f"**{html.escape(jogo[lado])}**: {resumo['jogos']} jogos · {resumo['vitorias']}V "
                        f"{resumo['empates']}E {resumo['derrotas']}D · aproveitamento {_pct(resumo['aproveitamento'])}"
                        f" · últimos {config.PAINEL_JANELA_RECENTE_LOTECA}: {_pct(resumo['aproveitamento_recente'])}"
                        + (" · amostra pequena" if resumo["amostra_pequena"] else "")
                    )
                    if periodo[0] is not None:
                        jogos = [j for j in jogos if j["ano"] is not None and periodo[0] <= j["ano"] <= periodo[1]]
                    series.append((jogo[lado], tendencia_anual_loteca(jogos)))
                st.plotly_chart(grafico_anual(series, altura=280), width="stretch", key=f"jogo_loteca_{jogo['num_jogo']}")
    else:
        c1, c2 = st.columns(2)
        tipo = c1.radio("Tipo", ["Todos", "Clubes", "Seleções"], horizontal=True, key="tipo_loteca")
        minimo = c2.number_input(
            "Mínimo de jogos na Loteca", min_value=1, value=config.PAINEL_MIN_JOGOS_LOTECA, step=1, key="minimo_loteca",
            help="Padrão 10. Pode aumentar se mais informação favorecer a análise.",
        )
        filtro = {"Todos": None, "Clubes": "clube", "Seleções": "selecao"}[tipo]
        opcoes = participantes_com_minimo(conexao, int(minimo), filtro)
        rotulos = {p["id"]: _rotulo_participante(p) for p in opcoes}
        nomes = {p["id"]: p["nome"] for p in opcoes}
        escolhidos = st.multiselect(
            f"Participantes ({len(opcoes)} com {int(minimo)} jogos ou mais)", options=list(rotulos),
            format_func=rotulos.get, key="participantes_loteca",
        )
        if not escolhidos:
            st.info("Escolha ao menos um participante para comparar.")
            return
        mostrar_loteca(conexao, [{"id": pid, "nome": nomes[pid]} for pid in escolhidos], periodo, "loteca_livre")


conexao = obter_conexao()
a_jogar = concurso_a_jogar(conexao)
numero = a_jogar["numero"] if a_jogar else None
jogos_do_concurso = participantes_do_concurso(conexao, numero) if numero else []

aba_cbf, aba_hist = st.tabs(["Temporada (CBF)", "Histórico na Loteca"])
with aba_cbf:
    aba_temporada(conexao, jogos_do_concurso, numero)
with aba_hist:
    aba_loteca(conexao, jogos_do_concurso, numero)

conexao.close()
