"""Apresentação dos estudos estatísticos (fatores do desempenho, modelos de 1/X/2 e anti-manada).
Só formata e desenha: as contas estão em stats/associacao.py, stats/backtest_competicao.py e
stats/anti_manada.py. Funções puras, para poderem ser testadas sem o Streamlit."""
import html

import plotly.graph_objects as go
from paleta import AZUL, CINZA, VERMELHO

from stats import backtest_competicao as b2


def num(valor: float | None, casas: int = 2, sinal: bool = False) -> str:
    if valor is None:
        return "—"
    if round(valor, casas) == 0:
        return f"{0:.{casas}f}".replace(".", ",")  # zero não leva sinal (evita "-0,00")
    return (f"{valor:+.{casas}f}" if sinal else f"{valor:.{casas}f}").replace(".", ",")


def inteiro(valor: int) -> str:
    """Inteiro com ponto de milhar, como no resto do app (formatado à parte para não mexer nas vírgulas do texto)."""
    return f"{valor:,}".replace(",", ".")


def texto_p(valor: float | None) -> str:
    if valor is None:
        return "—"
    return "<0,001" if valor < 0.001 else f"{valor:.3f}".replace(".", ",")


def _lista(nomes: list[str]) -> str:
    return nomes[0] if len(nomes) == 1 else ", ".join(nomes[:-1]) + " e " + nomes[-1]


# ---------------------------------------------------------------- fatores do desempenho (P3)

def frase_fatores(resultados: list[dict]) -> str:
    avaliados = [r for r in resultados if r["avaliado"]]
    if not avaliados:
        return "Nenhum fator tem jogos suficientes para ser testado."
    melhoram = [r["descricao"].lower() for r in avaliados if r["conclusao"].startswith("melhora")]
    insuficientes = [r["descricao"].lower() for r in resultados if not r["avaliado"]]
    if melhoram:
        frase = (
            f"Dos {len(avaliados)} fatores testados, {len(melhoram)} melhora(m) a previsão do resultado além do que o retrospecto "
            f"do time e do adversário já informam: {_lista(melhoram)}. Os demais não acrescentam nada com esta amostra."
        )
    else:
        frase = (
            f"Nenhum dos {len(avaliados)} fatores testados melhora a previsão do resultado além do que o retrospecto do time e "
            "do adversário já informam."
        )
    if insuficientes:
        frase += f" Sem jogos suficientes para testar: {_lista(insuficientes)}."
    return frase


def linhas_fatores(resultados: list[dict]) -> list[list[str]]:
    linhas = []
    for r in resultados:
        if r["avaliado"]:
            ganho = f"{num(100 * r['ganho_relativo'], 2, True)}%"
            coef = f"{num(r['coeficiente'], 2, True)} ({num(r['coef_ic_inferior'], 2, True)} a {num(r['coef_ic_superior'], 2, True)})"
        else:
            ganho = coef = "—"
        linhas.append([
            html.escape(r["descricao"]), str(r["n_exposto"]), str(r["n_referencia"]), ganho, coef,
            texto_p(r["q"]), html.escape(r["conclusao"]),
        ])
    return linhas


CABECALHOS_FATORES = [
    "Fator", "Jogos com o fator", "Jogos sem o fator", "Ganho de previsão", "Efeito em pontos por jogo (IC 95%)", "q", "Conclusão",
]


# Rótulos curtos para o eixo do gráfico (cabem no celular); o nome completo fica na tabela e ao passar o mouse.
ROTULO_CURTO_FATOR = {
    "mando_casa": "Jogar em casa", "forma_boa": "Forma boa", "forma_ruim": "Forma ruim", "seq_vitorias": "Sequência de vitórias",
    "seq_sem_vencer": "Sequência sem vencer", "zona_topo": "Entre os primeiros", "zona_fundo": "Entre os últimos",
    "saf": "SAF no nome", "descanso_curto": "Pouco descanso", "reta_final": "Reta final",
}


def figura_coeficientes(resultados: list[dict]) -> go.Figure | None:
    avaliados = [r for r in resultados if r["avaliado"]]
    if not avaliados:
        return None
    avaliados = avaliados[::-1]  # o primeiro fator da tabela fica no alto do gráfico
    figura = go.Figure(go.Scatter(
        x=[r["coeficiente"] for r in avaliados], y=[ROTULO_CURTO_FATOR.get(r["fator"], r["descricao"]) for r in avaliados],
        customdata=[r["descricao"] for r in avaliados], mode="markers",
        marker=dict(size=9, symbol="diamond", color=[AZUL if r["conclusao"].startswith("melhora") else CINZA for r in avaliados]),
        error_x=dict(
            type="data", symmetric=False, color=CINZA,
            array=[r["coef_ic_superior"] - r["coeficiente"] for r in avaliados],
            arrayminus=[r["coeficiente"] - r["coef_ic_inferior"] for r in avaliados],
        ),
        hovertemplate="%{customdata}<br>%{x:+.2f} ponto por jogo<extra></extra>", name="Efeito estimado",
    ))
    figura.add_vline(x=0, line=dict(color=VERMELHO, dash="dash", width=1))
    figura.update_layout(
        height=90 + 46 * len(avaliados), margin=dict(l=10, r=10, t=10, b=40),
        xaxis=dict(title="Pontos por jogo", tickangle=0, nticks=5), yaxis=dict(automargin=True), showlegend=False, separators=",.",
    )
    return figura


# ---------------------------------------------------------------- modelos de 1/X/2 (B2)

def frase_b2(resumo: dict) -> str:
    por_par = {(c["modelo"], c["contra"]): c for c in resumo["comparacoes"]}
    melhores = [b2.DESCRICAO[m].lower() for m in ("retrospecto", "poisson") if por_par[(m, "referencia")]["conclusao"] == "melhor"]
    piores = [b2.DESCRICAO[m].lower() for m in ("retrospecto", "poisson") if por_par[(m, "referencia")]["conclusao"] == "pior"]
    ref = resumo["metricas"]["referencia"]["perda_log"]
    partes = []
    if melhores:
        partes.append(f"Fora da amostra, {_lista(melhores)} dá mais probabilidade ao que de fato aconteceu do que a frequência simples de 1/X/2")
    if piores:
        partes.append(f"{_lista(piores)} fica pior que a frequência simples")
    if not melhores and not piores:
        partes.append("Nenhum dos modelos testados se distingue da frequência simples de 1/X/2")
    frase = "; ".join(partes) + f" (perda logarítmica da frequência simples: {num(ref, 3)}; menor é melhor)."
    entre = por_par[("poisson", "retrospecto")]
    if entre["conclusao"] == "sem diferença perceptível":
        frase += " Entre os dois modelos não há diferença perceptível."
    elif entre["conclusao"] == "melhor":
        frase += " O Poisson da temporada é melhor que o retrospecto."
    else:
        frase += " O retrospecto é melhor que o Poisson da temporada."
    return frase + " O ganho é pequeno e vale só para jogos das Séries A e B."


CABECALHOS_B2 = ["Modelo", "Jogos", "Acerto do favorito", "Brier", "Perda logarítmica"]
CABECALHOS_B2_COMPARACAO = ["Comparação", "Ganho em perda logarítmica (IC 95%)", "q", "Conclusão"]


def linhas_b2(resumo: dict) -> list[list[str]]:
    linhas = []
    for modelo in b2.MODELOS:
        m = resumo["metricas"][modelo]
        linhas.append([html.escape(b2.DESCRICAO[modelo]), str(m["n"]), f"{num(m['acuracia'], 1)}%", num(m["brier"], 4), num(m["perda_log"], 4)])
    return linhas


def _rotulo_comparacao(c: dict) -> str:
    contra = b2.DESCRICAO[c["contra"]]
    return f"{b2.DESCRICAO[c['modelo']]} contra {contra[0].lower() + contra[1:]}"


def linhas_b2_comparacoes(resumo: dict) -> list[list[str]]:
    linhas = []
    for c in resumo["comparacoes"]:
        pl = c["perda_log"]
        linhas.append([
            html.escape(_rotulo_comparacao(c)),
            f"{num(pl['media'], 4, True)} ({num(pl['ic_inferior'], 4, True)} a {num(pl['ic_superior'], 4, True)})",
            texto_p(c["q"]), html.escape(c["conclusao"]),
        ])
    return linhas


ROTULO_CURTO_COMPARACAO = {
    ("retrospecto", "referencia"): "Retrospecto × frequência", ("poisson", "referencia"): "Poisson × frequência",
    ("poisson", "retrospecto"): "Poisson × retrospecto",
}


def figura_comparacoes_b2(resumo: dict) -> go.Figure:
    comparacoes = resumo["comparacoes"][::-1]
    figura = go.Figure(go.Scatter(
        x=[c["perda_log"]["media"] for c in comparacoes],
        y=[ROTULO_CURTO_COMPARACAO.get((c["modelo"], c["contra"]), _rotulo_comparacao(c)) for c in comparacoes],
        customdata=[_rotulo_comparacao(c) for c in comparacoes], mode="markers",
        marker=dict(size=9, symbol="diamond", color=[AZUL if c["conclusao"] == "melhor" else CINZA for c in comparacoes]),
        error_x=dict(
            type="data", symmetric=False, color=CINZA,
            array=[c["perda_log"]["ic_superior"] - c["perda_log"]["media"] for c in comparacoes],
            arrayminus=[c["perda_log"]["media"] - c["perda_log"]["ic_inferior"] for c in comparacoes],
        ),
        hovertemplate="%{customdata}<br>ganho %{x:+.4f}<extra></extra>", name="Ganho",
    ))
    figura.add_vline(x=0, line=dict(color=VERMELHO, dash="dash", width=1))
    figura.update_layout(
        height=90 + 60 * len(comparacoes), margin=dict(l=10, r=10, t=10, b=40),
        xaxis=dict(title="Ganho por jogo", tickangle=0, nticks=5), yaxis=dict(automargin=True), showlegend=False, separators=",.",
    )
    return figura


# ---------------------------------------------------------------- anti-manada (Q7)

def frase_q7(resultados: list[dict], n_concursos: int, anos: tuple[int, int]) -> str:
    principal = next(r for r in resultados if r["exposicao"] == "fora_da_coluna_1")
    if principal["rho"] is None:
        return "Não há concursos suficientes para a análise."
    base = f"Em {n_concursos} concursos de {anos[0]} a {anos[1]}, "
    ic = f"{num(principal['ic_inferior'], 2, True)} a {num(principal['ic_superior'], 2, True)}"
    if principal["conclusao"].startswith("associação detectada"):
        sentido = "menos" if principal["rho"] < 0 else "mais"
        return (
            base + f"quanto mais jogos terminaram fora da coluna 1, {sentido} ganhadores de 14 acertos por milhão arrecadado, comparando "
            f"concursos do mesmo ano (correlação de postos {num(principal['rho'], 2, True)}; IC 95%: {ic}). É associação do passado: "
            "não indica o que vai acontecer em um concurso futuro."
        )
    return base + f"não houve relação perceptível entre jogos fora da coluna 1 e ganhadores de 14 por milhão arrecadado (correlação {num(principal['rho'], 2, True)}; IC 95%: {ic})."


CABECALHOS_Q7 = ["Exposição", "Concursos", "Correlação de postos", "IC 95%", "q", "Conclusão"]
CABECALHOS_Q7_FAIXAS = ["Jogos fora da coluna 1", "Concursos", "Ganhadores de 14 por milhão arrecadado (média)", "Sem ganhador de 14", "Prêmio mediano de 14 (onde houve)"]


def linhas_q7(resultados: list[dict]) -> list[list[str]]:
    return [
        [
            html.escape(r["descricao"]), str(r["n"]), num(r["rho"], 2, True),
            "—" if r["rho"] is None else f"{num(r['ic_inferior'], 2, True)} a {num(r['ic_superior'], 2, True)}",
            texto_p(r["q"]), html.escape(r["conclusao"]),
        ]
        for r in resultados
    ]


def linhas_q7_faixas(faixas: list[dict], formatar_reais) -> list[list[str]]:
    return [
        [
            html.escape(f["faixa"]), str(f["concursos"]), num(f["ganhadores_por_milhao"], 1), f"{num(f['sem_ganhador_14'], 0)}%",
            "—" if f["premio_mediano"] is None else formatar_reais(f["premio_mediano"]),
        ]
        for f in faixas
    ]


def figura_faixas_q7(faixas: list[dict]) -> go.Figure:
    figura = go.Figure(go.Bar(
        x=[f["faixa"] for f in faixas], y=[f["sem_ganhador_14"] for f in faixas], marker=dict(color=AZUL),
        text=[f"{f['sem_ganhador_14']:.0f}%".replace(".", ",") for f in faixas], textposition="outside",
        hovertemplate="%{x} jogos fora da coluna 1: %{y:.0f}% dos concursos sem ganhador de 14<extra></extra>",
    ))
    figura.update_layout(
        height=300, margin=dict(l=10, r=10, t=10, b=40),
        xaxis=dict(title="Jogos fora da coluna 1"), yaxis=dict(title="% dos concursos", range=[0, 100]),
        showlegend=False, separators=",.",
    )
    return figura


TITULO_FIGURA_FATORES = "Efeito de cada fator, em pontos por jogo (barras: intervalo de 95%)"
TITULO_FIGURA_B2 = "Ganho em perda logarítmica (à direita de zero, o primeiro modelo é melhor)"
TITULO_FIGURA_Q7 = "Concursos sem ganhador de 14 acertos, por jogos fora da coluna 1"
