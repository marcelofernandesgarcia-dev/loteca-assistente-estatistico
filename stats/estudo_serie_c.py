"""Estudo da Série C (itens B3 e C2 do plano v2, aprovado em 07/10/2026). Só mede; não muda percentual.

B3 -- o modelo da temporada (retrospecto da CBF) é melhor que o modelo anterior também na Série C?
Mesmo método do estudo das Séries A e B: logística treinada só em temporadas ANTERIORES da própria Série C,
jogos testados sem olhar o futuro, nos jogos da CBF e nos jogos da Loteca entre dois clubes da Série C.
Critério fixado antes do resultado (regra do usuário): só vale se a perda logarítmica fora da amostra for
menor que a do modelo anterior nos jogos da Loteca, com valor q < config.ASSOCIACAO_NIVEL_SIGNIFICANCIA.

C2 -- a fase decisiva (2ª fase em diante) empata mais que a 1ª fase? Descritivo (taxa de empate por fase,
com intervalo de 95%) e, como critério, se acrescentar "fase decisiva" ao retrospecto melhora a perda
logarítmica fora da amostra, ano a ano. Sem melhora comprovada, a fase fica só como contexto na tela.
"""
import math

import numpy as np

import config
from stats import backtest, backtest_competicao as b2, backtest_loteca as bl
from stats.associacao import ajustar_benjamini_hochberg

SERIE = ("serie-c",)
INDICE = {"1": 0, "X": 1, "2": 2}


def _wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    centro = (p + z * z / (2 * n)) / (1 + z * z / n)
    meia = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return centro - meia, centro + meia


def cobertura(conexao) -> list[dict]:
    """Por temporada: jogos, jogos com placar, fases distintas e jogos sem fase."""
    return [dict(l) for l in conexao.execute(
        """
        SELECT ano, COUNT(*) AS jogos, SUM(gols_mandante IS NOT NULL) AS com_placar,
               COUNT(DISTINCT fase) AS fases, SUM(fase IS NULL) AS sem_fase
        FROM cbf_partidas WHERE serie = 'serie-c' GROUP BY ano ORDER BY ano
        """
    )]


def _decisiva(fase: str | None, rodada: int | None, rodada_fase: int | None) -> bool | None:
    """Fase decisiva = qualquer fase depois da primeira, pela POSIÇÃO: há rodadas antes dela na temporada
    (rodada em sequência maior que a rodada da fase). O nome não serve: a CBF chama a 1ª fase de "1a Fase",
    "1ª Fase" ou "TURNO" (2023). Sem fase gravada -> None (fica fora do C2)."""
    if not fase or rodada is None or rodada_fase is None:
        return None
    return rodada > rodada_fase


def fase_por_jogo(conexao) -> dict[int, bool | None]:
    """{id_jogo: é fase decisiva?} dos jogos da Série C."""
    return {
        l["id_jogo"]: _decisiva(l["fase"], l["rodada"], l["rodada_fase"])
        for l in conexao.execute("SELECT id_jogo, fase, rodada, rodada_fase FROM cbf_partidas WHERE serie = 'serie-c'")
    }


def empates_por_fase(conexao) -> dict:
    """Taxa de empate na 1ª fase e nas decisivas, com intervalo de Wilson de 95%, e a diferença."""
    contagem = {False: [0, 0], True: [0, 0]}
    for l in conexao.execute(
        "SELECT fase, rodada, rodada_fase, gols_mandante, gols_visitante FROM cbf_partidas"
        " WHERE serie = 'serie-c' AND gols_mandante IS NOT NULL"
    ):
        decisiva = _decisiva(l["fase"], l["rodada"], l["rodada_fase"])
        if decisiva is None:
            continue
        contagem[decisiva][0] += int(l["gols_mandante"] == l["gols_visitante"])
        contagem[decisiva][1] += 1
    saida = {}
    for chave, nome in ((False, "primeira_fase"), (True, "decisivas")):
        k, n = contagem[chave]
        saida[nome] = {"empates": k, "jogos": n, "taxa": k / n if n else None, "ic95": _wilson(k, n)}
    a, b = saida["decisivas"], saida["primeira_fase"]
    if a["jogos"] and b["jogos"]:
        dif = a["taxa"] - b["taxa"]
        ep = math.sqrt(a["taxa"] * (1 - a["taxa"]) / a["jogos"] + b["taxa"] * (1 - b["taxa"]) / b["jogos"])
        saida["diferenca"] = {"pontos": dif, "ic95": (dif - 1.96 * ep, dif + 1.96 * ep)}
    return saida


def teste_fase_decisiva(amostra: list[dict], decisivas: dict[int, bool | None]) -> dict | None:
    """Retrospecto com e sem o indicador de fase decisiva, treinado em temporadas anteriores e testado ano a
    ano. Ganho positivo = o indicador melhora a previsão. None sem ao menos dois anos com fase.
    `decisivas`: de `fase_por_jogo`."""
    dados = [o | {"decisiva": decisivas.get(o["id_jogo"])} for o in amostra]
    dados = [o for o in dados if o["decisiva"] is not None]
    anos = sorted({o["ano"] for o in dados})
    if len(anos) < 2:
        return None
    ganhos, clusters = [], []
    for ano in anos[1:]:
        treino = [o for o in dados if o["ano"] < ano]
        teste = [o for o in dados if o["ano"] == ano]
        if not treino or not teste or not any(o["decisiva"] for o in treino):
            continue
        y = np.array([INDICE[o["resultado"]] for o in treino])
        base = lambda lista: np.column_stack([np.ones(len(lista)), [o["retro_casa"] for o in lista], [o["retro_fora"] for o in lista]])  # noqa: E731
        com_fase = lambda lista: np.column_stack([base(lista), [float(o["decisiva"]) for o in lista]])  # noqa: E731
        p_base = b2.probabilidades_logistica(base(teste), b2.ajustar_logistica(base(treino), y))
        p_fase = b2.probabilidades_logistica(com_fase(teste), b2.ajustar_logistica(com_fase(treino), y))
        for o, pb, pf in zip(teste, p_base, p_fase):
            i = INDICE[o["resultado"]]
            ganhos.append(-math.log(max(pb[i], 1e-12)) + math.log(max(pf[i], 1e-12)))
            clusters.append(o["cluster"])
    if not ganhos:
        return None
    resultado = b2._bootstrap_por_cluster(np.array(ganhos), np.array(clusters), config.B2_REPETICOES_BOOTSTRAP,
                                          config.B2_SEMENTE + 300)
    return {"n": len(ganhos), **resultado}


def estudar(conexao) -> dict:
    """Tudo o que o relatório precisa. Só lê o banco; demora cerca de 1 a 2 minutos no banco real."""
    amostra = b2.carregar_amostra(conexao, SERIE)
    cbf = b2.prever(amostra)
    resumo_cbf = b2.resumir(cbf) if cbf else None
    pesos = bl.pesos_por_ano(amostra)
    jogos, funil = bl.montar_jogos(conexao, backtest.prever_walk_forward(backtest.carregar_jogos(conexao)), pesos, SERIE)
    fase = teste_fase_decisiva(amostra, fase_por_jogo(conexao))
    if fase:
        fase["q"] = ajustar_benjamini_hochberg([fase["p"]])[0]
    return {
        "cobertura": cobertura(conexao),
        "cbf": resumo_cbf,
        "loteca": bl.resumir(jogos),
        "funil": funil,
        "empates": empates_por_fase(conexao),
        "fase_decisiva": fase,
    }
