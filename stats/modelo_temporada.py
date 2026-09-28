"""Modelo EXPERIMENTAL de gols para uma série, com os jogos da temporada.

Cada time recebe uma força de ataque e uma de defesa, estimadas em conjunto
(a força de quem enfrentou adversários fracos ou fortes é corrigida) e
puxadas para a média da série com peso `config.MODELO_TEMPORADA_PESO_PRIOR`
(em "jogos de um time médio"), para times com poucos jogos não terem força
extrema. Gols esperados:

    casa  = media_gols_mandante x ataque_casa  x defesa_visitante
    fora  = media_gols_visitante x ataque_fora x defesa_mandante

e os placares seguem distribuições de Poisson independentes. É uma estimativa
para análise, NÃO uma previsão nem garantia: ainda não foi testada contra
resultados passados (etapa B3) e o peso do prior é um parâmetro a calibrar.
"""
import math
from collections import defaultdict

import config

MAX_GOLS = 8
ITERACOES = 200


def forcas_da_serie(partidas: list[dict], peso_prior: float | None = None) -> dict | None:
    """{'media_casa', 'media_fora', 'ataque': {time: x}, 'defesa': {time: x}, 'jogos': {time: n}}.
    `defesa` maior = sofre mais gols. None se não houver jogos."""
    if not partidas:
        return None
    peso = config.MODELO_TEMPORADA_PESO_PRIOR if peso_prior is None else peso_prior
    n = len(partidas)
    media_casa = sum(p["gols_mandante"] for p in partidas) / n
    media_fora = sum(p["gols_visitante"] for p in partidas) / n
    media_time = (media_casa + media_fora) / 2

    gols_pro, gols_contra, jogos = defaultdict(int), defaultdict(int), defaultdict(int)
    for p in partidas:
        gols_pro[p["mandante_id"]] += p["gols_mandante"]
        gols_contra[p["mandante_id"]] += p["gols_visitante"]
        gols_pro[p["visitante_id"]] += p["gols_visitante"]
        gols_contra[p["visitante_id"]] += p["gols_mandante"]
        jogos[p["mandante_id"]] += 1
        jogos[p["visitante_id"]] += 1

    times = list(jogos)
    ataque = {t: 1.0 for t in times}
    defesa = {t: 1.0 for t in times}
    for _ in range(ITERACOES):
        esperado_pro, esperado_contra = defaultdict(float), defaultdict(float)
        for p in partidas:
            m, v = p["mandante_id"], p["visitante_id"]
            esperado_pro[m] += media_casa * defesa[v]
            esperado_contra[v] += media_casa * ataque[m]
            esperado_pro[v] += media_fora * defesa[m]
            esperado_contra[m] += media_fora * ataque[v]
        novo_ataque = {t: (gols_pro[t] + peso * media_time) / (esperado_pro[t] + peso * media_time) for t in times}
        novo_defesa = {t: (gols_contra[t] + peso * media_time) / (esperado_contra[t] + peso * media_time) for t in times}
        media_ataque = sum(novo_ataque.values()) / len(times)
        media_defesa = sum(novo_defesa.values()) / len(times)
        ataque = {t: v / media_ataque for t, v in novo_ataque.items()}
        defesa = {t: v / media_defesa for t, v in novo_defesa.items()}
    return {"media_casa": media_casa, "media_fora": media_fora, "ataque": ataque, "defesa": defesa, "jogos": dict(jogos)}


def gols_esperados(forcas: dict, casa: int, fora: int) -> tuple[float, float] | None:
    if casa not in forcas["ataque"] or fora not in forcas["ataque"] or casa == fora:
        return None
    return (
        forcas["media_casa"] * forcas["ataque"][casa] * forcas["defesa"][fora],
        forcas["media_fora"] * forcas["ataque"][fora] * forcas["defesa"][casa],
    )


def _poisson(k: int, lam: float) -> float:
    return math.exp(-lam) * lam**k / math.factorial(k) if lam > 0 else (1.0 if k == 0 else 0.0)


def matriz_de_placares(lambda_casa: float, lambda_fora: float, max_gols: int = MAX_GOLS) -> list[list[float]]:
    """matriz[gols_casa][gols_fora] = probabilidade (soma 1, após normalizar a cauda)."""
    matriz = [[_poisson(c, lambda_casa) * _poisson(f, lambda_fora) for f in range(max_gols + 1)] for c in range(max_gols + 1)]
    total = sum(sum(linha) for linha in matriz)
    return [[x / total for x in linha] for linha in matriz]


def resumo_da_matriz(matriz: list[list[float]], top: int = 5) -> dict:
    n = len(matriz)
    casa = sum(matriz[c][f] for c in range(n) for f in range(n) if c > f)
    empate = sum(matriz[i][i] for i in range(n))
    fora = 1.0 - casa - empate
    placares = sorted(((c, f, matriz[c][f]) for c in range(n) for f in range(n)), key=lambda x: -x[2])[:top]
    return {
        "p_casa": casa,
        "p_empate": empate,
        "p_fora": fora,
        "p_casa_marca": 1.0 - sum(matriz[0]),
        "p_fora_marca": 1.0 - sum(matriz[c][0] for c in range(n)),
        "p_ambos_marcam": sum(matriz[c][f] for c in range(1, n) for f in range(1, n)),
        "p_3_ou_mais_gols": sum(matriz[c][f] for c in range(n) for f in range(n) if c + f >= 3),
        "placares_mais_provaveis": [{"gols_casa": c, "gols_fora": f, "probabilidade": p} for c, f, p in placares],
    }


def analisar_confronto(forcas: dict, casa: int, fora: int) -> dict | None:
    esperados = gols_esperados(forcas, casa, fora)
    if esperados is None:
        return None
    matriz = matriz_de_placares(*esperados)
    return {
        "gols_esperados_casa": esperados[0],
        "gols_esperados_fora": esperados[1],
        "jogos_casa": forcas["jogos"][casa],
        "jogos_fora": forcas["jogos"][fora],
        "matriz": matriz,
        **resumo_da_matriz(matriz),
    }
