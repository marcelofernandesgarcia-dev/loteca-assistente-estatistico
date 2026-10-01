"""Teste (B2) de modelos de 1/X/2 para os jogos de uma competição, andando no tempo.

Pergunta do roteiro: um modelo que use os jogos da temporada (CBF) prevê melhor o resultado do que a
frequência simples de vitória da casa, empate e vitória do visitante? Só se a resposta for sim vale
pensar em trocar o percentual exibido -- esta etapa NÃO troca nada, só mede.

Modelos, todos com a mesma amostra de jogos:
- referência: frequência de 1, X e 2 nos anos anteriores ao testado;
- retrospecto: regressão logística multinomial sobre os pontos por jogo de cada time até o jogo,
  treinada nos anos anteriores;
- Poisson da temporada: `modelo_temporada` (ataque e defesa de cada time, com prior), refeito a cada
  rodada só com os jogos já conhecidos.

Sem olhar o futuro: para cada rodada, "jogo conhecido" é o de rodada anterior E data anterior ao primeiro
jogo da rodada (um jogo adiado, de rodada antiga mas disputado depois, não conta). Treino só com anos
anteriores ao testado. Comparação pareada, jogo a jogo, com intervalo e valor p por reamostragem de
rodadas (os jogos de uma mesma rodada compartilham o contexto), valor q de Benjamini-Hochberg.
"""
import numpy as np

import config
from stats import backtest, competicao, modelo_temporada
from stats.associacao import ajustar_benjamini_hochberg

MODELOS = ("referencia", "retrospecto", "poisson")
DESCRICAO = {
    "referencia": "Frequência simples de 1/X/2",
    "retrospecto": "Retrospecto dos dois times (logística)",
    "poisson": "Poisson da temporada (modelo_temporada)",
}
COMPARACOES = (("retrospecto", "referencia"), ("poisson", "referencia"), ("poisson", "retrospecto"))


def _resultado(partida: dict) -> str:
    gm, gv = partida["gols_mandante"], partida["gols_visitante"]
    return "1" if gm > gv else "X" if gm == gv else "2"


def amostra_da_temporada(partidas: list[dict], serie: str, ano: int, com_poisson: bool = True) -> list[dict]:
    """Um registro por jogo elegível, com o retrospecto dos dois times e, se pedido, a previsão do
    Poisson da temporada. `partidas` vem de `competicao.carregar_partidas`."""
    minimo = config.B2_JOGOS_ANTERIORES_MINIMOS
    por_rodada: dict[int, list[dict]] = {}
    for p in partidas:
        por_rodada.setdefault(p["rodada"], []).append(p)
    amostra = []
    for rodada in sorted(por_rodada):
        jogos_da_rodada = por_rodada[rodada]
        datas = [p["data_jogo"] for p in jogos_da_rodada if p["data_jogo"]]
        if not datas:
            continue
        corte = min(datas)
        conhecidas = [p for p in partidas if p["rodada"] < rodada and p["data_jogo"] and p["data_jogo"] < corte]
        pontos, jogos = {}, {}
        for p in conhecidas:
            for time, pro, contra in ((p["mandante_id"], p["gols_mandante"], p["gols_visitante"]),
                                      (p["visitante_id"], p["gols_visitante"], p["gols_mandante"])):
                pontos[time] = pontos.get(time, 0) + (3 if pro > contra else 1 if pro == contra else 0)
                jogos[time] = jogos.get(time, 0) + 1
        elegiveis = [
            p for p in jogos_da_rodada
            if jogos.get(p["mandante_id"], 0) >= minimo and jogos.get(p["visitante_id"], 0) >= minimo
        ]
        if not elegiveis:
            continue
        forcas = modelo_temporada.forcas_da_serie(conhecidas) if com_poisson else None
        for p in elegiveis:
            registro = {
                "temporada": f"{serie}-{ano}", "serie": serie, "ano": ano, "cluster": f"{serie}-{ano}-{rodada}",
                "retro_casa": pontos[p["mandante_id"]] / jogos[p["mandante_id"]],
                "retro_fora": pontos[p["visitante_id"]] / jogos[p["visitante_id"]],
                "resultado": _resultado(p), "poisson": None,
            }
            analise = modelo_temporada.analisar_confronto(forcas, p["mandante_id"], p["visitante_id"]) if forcas else None
            if analise:
                registro["poisson"] = (analise["p_casa"], analise["p_empate"], analise["p_fora"])
            amostra.append(registro)
    return amostra


def carregar_amostra(conexao) -> list[dict]:
    """Amostra de todas as temporadas coletadas. Só lê o banco."""
    amostra = []
    for t in conexao.execute("SELECT DISTINCT serie, ano FROM cbf_partidas ORDER BY ano, serie").fetchall():
        amostra += amostra_da_temporada(competicao.carregar_partidas(conexao, t["serie"], t["ano"]), t["serie"], t["ano"])
    return amostra


def ajustar_logistica(X: np.ndarray, y: np.ndarray, iteracoes: int = 30, ridge: float = 1e-4) -> np.ndarray:
    """Logística multinomial (classe 0 = vitória da casa como referência) por Newton-Raphson.
    `y` em {0, 1, 2}. Devolve W (colunas x 2), para `probabilidades_logistica`."""
    n, d = X.shape
    Y = np.eye(3)[y][:, 1:]
    W = np.zeros((d, 2))
    for _ in range(iteracoes):
        exp = np.exp(X @ W)
        P = exp / (1.0 + exp.sum(axis=1, keepdims=True))
        gradiente = np.concatenate([X.T @ (P - Y)[:, k] + ridge * W[:, k] for k in range(2)])
        H = np.zeros((2 * d, 2 * d))
        for k in range(2):
            for m in range(2):
                peso = P[:, k] * ((1.0 if k == m else 0.0) - P[:, m])
                H[k * d:(k + 1) * d, m * d:(m + 1) * d] = X.T @ (X * peso[:, None])
        H += ridge * np.eye(2 * d)
        W = W - np.linalg.solve(H, gradiente).reshape(2, d).T
    return W


def probabilidades_logistica(X: np.ndarray, W: np.ndarray) -> np.ndarray:
    """Matriz n x 3 com as probabilidades de 1, X e 2."""
    exp = np.exp(X @ W)
    denominador = 1.0 + exp.sum(axis=1, keepdims=True)
    return np.column_stack([1.0 / denominador, exp / denominador])


def _como_percentuais(p: tuple[float, float, float] | np.ndarray) -> dict:
    return {r: 100.0 * float(v) for r, v in zip(backtest.RESULTADOS, p)}


def prever(amostra: list[dict]) -> list[dict]:
    """Acrescenta a cada jogo, com `ano` a partir do segundo, as probabilidades dos três modelos
    (`previsoes[modelo]` em percentual). Jogos do primeiro ano só servem de treino."""
    anos = sorted({o["ano"] for o in amostra})
    indice = {"1": 0, "X": 1, "2": 2}
    saida = []
    for ano in anos[1:]:
        treino = [o for o in amostra if o["ano"] < ano]
        teste = [o for o in amostra if o["ano"] == ano and o["poisson"] is not None]
        if not treino or not teste:
            continue
        y_treino = np.array([indice[o["resultado"]] for o in treino])
        frequencias = np.bincount(y_treino, minlength=3) / len(y_treino)
        X_treino = np.column_stack([np.ones(len(treino)), [o["retro_casa"] for o in treino], [o["retro_fora"] for o in treino]])
        W = ajustar_logistica(X_treino, y_treino)
        X_teste = np.column_stack([np.ones(len(teste)), [o["retro_casa"] for o in teste], [o["retro_fora"] for o in teste]])
        probabilidades = probabilidades_logistica(X_teste, W)
        for o, p_logistica in zip(teste, probabilidades):
            saida.append(
                o | {"previsoes": {
                    "referencia": _como_percentuais(frequencias),
                    "retrospecto": _como_percentuais(p_logistica),
                    "poisson": _como_percentuais(o["poisson"]),
                }}
            )
    return saida


def _bootstrap_por_cluster(valores: np.ndarray, clusters: np.ndarray, repeticoes: int, semente: int) -> dict:
    """Média, intervalo de 95% e valor p unilateral (a média é maior que zero?) reamostrando clusters."""
    _, cl = np.unique(clusters, return_inverse=True)
    k = cl.max() + 1
    soma = np.bincount(cl, weights=valores, minlength=k)
    cont = np.bincount(cl, minlength=k).astype(float)
    sorteio = np.random.default_rng(semente).integers(0, k, size=(repeticoes, k))
    medias = soma[sorteio].sum(axis=1) / cont[sorteio].sum(axis=1)
    ic = np.percentile(medias, [2.5, 97.5])
    return {
        "media": float(valores.mean()), "ic_inferior": float(ic[0]), "ic_superior": float(ic[1]),
        "p": (1 + int((medias <= 0).sum())) / (1 + repeticoes),
    }


def resumir(jogos_previstos: list[dict]) -> dict:
    """Métricas por modelo e comparações pareadas (ganho em perda logarítmica e em Brier; positivo =
    o primeiro modelo da comparação é melhor), com valor q entre as comparações."""
    metricas = {
        m: backtest.metricas([(o["previsoes"][m], o["resultado"]) for o in jogos_previstos]) for m in MODELOS
    }
    clusters = np.array([o["cluster"] for o in jogos_previstos])
    comparacoes = []
    for indice, (a, b) in enumerate(COMPARACOES):
        ganho_log = np.array([
            backtest.perda_log(o["previsoes"][b], o["resultado"]) - backtest.perda_log(o["previsoes"][a], o["resultado"])
            for o in jogos_previstos
        ])
        ganho_brier = np.array([
            backtest.brier(o["previsoes"][b], o["resultado"]) - backtest.brier(o["previsoes"][a], o["resultado"])
            for o in jogos_previstos
        ])
        comparacoes.append({
            "modelo": a, "contra": b,
            "perda_log": _bootstrap_por_cluster(ganho_log, clusters, config.B2_REPETICOES_BOOTSTRAP, config.B2_SEMENTE + indice),
            "brier": _bootstrap_por_cluster(ganho_brier, clusters, config.B2_REPETICOES_BOOTSTRAP, config.B2_SEMENTE + 10 + indice),
        })
    for c, q in zip(comparacoes, ajustar_benjamini_hochberg([c["perda_log"]["p"] for c in comparacoes])):
        c["q"] = q
        if q < config.ASSOCIACAO_NIVEL_SIGNIFICANCIA:
            c["conclusao"] = "melhor"
        elif _bootstrap_inverso_significativo(c):
            c["conclusao"] = "pior"
        else:
            c["conclusao"] = "sem diferença perceptível"
    return {"n": len(jogos_previstos), "metricas": metricas, "comparacoes": comparacoes}


def _bootstrap_inverso_significativo(comparacao: dict) -> bool:
    """O intervalo de 95% da perda logarítmica fica inteiro abaixo de zero: o modelo é pior."""
    return comparacao["perda_log"]["ic_superior"] < 0
