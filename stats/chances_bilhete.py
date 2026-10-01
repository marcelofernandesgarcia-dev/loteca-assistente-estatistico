"""Chances matemáticas de um bilhete e de um conjunto de bilhetes do mesmo concurso (pedido do usuário, 01/10/2026).

Entrada: o percentual de cada jogo (os números do app, já calibrados) e as colunas marcadas em cada jogo.
Premiam 14 e 13 acertos (Manual de Produtos v21): um bilhete "faz 13 ou mais" quando as colunas marcadas cobrem
o resultado em pelo menos 13 jogos, porque aí alguma de suas apostas acerta 13 ou 14.

Suposição: os jogos são independentes. O estudo de calibração conferiu isso (acertos previstos e observados por
concurso batem). A chance é tão boa quanto os percentuais: com os percentuais já corrigidos pela calibração, bateu
com o que aconteceu nos concursos passados; sem a correção, era cerca de 7 vezes otimista.

Não calcula prêmio em reais: o valor depende de quantas outras apostas acertaram, o que o app não sabe.
"""
import itertools
import math

import numpy as np

import config
from stats.bilhete import PRECO_APOSTA
from stats.calibracao import COLUNAS, distribuicao_de_acertos
from stats.otimizacao_bilhete import distribuicao_por_regra

LIMITE_JOGOS = 14  # 3^14 resultados cabem na memória; o concurso tem 14 jogos
LIMITE_BILHETES_NO_CONJUNTO = 12  # a repetição de apostas usa inclusão-exclusão (2^k termos)


def _apostas(marcacoes: list[list[str]]) -> int:
    return math.prod(len(m) for m in marcacoes)


def probabilidades_cobertas(pcts: list[dict], marcacoes: list[list[str]]) -> list[float]:
    """Chance, em fração, de o resultado de cada jogo cair numa das colunas marcadas. O percentual de cada jogo é
    normalizado para somar 1 (os números do app somam 100 com arredondamento)."""
    cobertas = []
    for pct, marcadas in zip(pcts, marcacoes):
        total = sum(pct[c] for c in COLUNAS)
        cobertas.append(sum(pct[c] for c in marcadas) / total if total > 0 else 0.0)
    return cobertas


def _validar(pcts: list[dict], marcacoes: list[list[str]]) -> None:
    if len(pcts) != len(marcacoes):
        raise ValueError("Cada jogo precisa de um percentual e de uma marcação.")
    if not pcts:
        raise ValueError("Sem jogos.")
    if len(pcts) > LIMITE_JOGOS:
        raise ValueError(f"No máximo {LIMITE_JOGOS} jogos.")
    for m in marcacoes:
        if not m or any(c not in COLUNAS for c in m) or len(set(m)) != len(m):
            raise ValueError("Marcação inválida: use 1, X e 2 sem repetir, ao menos uma coluna por jogo.")


def medidas_do_bilhete(pcts: list[dict], marcacoes: list[list[str]]) -> dict:
    """Medidas de um bilhete: chances de 14, 13 ou mais e 12 ou mais, distribuição de acertos, acertos esperados,
    apostas, custo e o que as apostas do bilhete rendem em cada caso."""
    _validar(pcts, marcacoes)
    n = len(pcts)
    cobertas = probabilidades_cobertas(pcts, marcacoes)
    dist = distribuicao_de_acertos(cobertas)
    tamanhos = [len(m) for m in marcacoes]
    apostas = _apostas(marcacoes)

    extras_13_se_14 = sum(t - 1 for t in tamanhos)
    prob_todos = float(dist[n])
    esperadas = prob_todos * (1 + extras_13_se_14)
    for g in range(n):  # exatamente o jogo g descoberto: as t_g apostas que acertam os outros 13 fazem 13
        so_g_descoberto = (1.0 - cobertas[g]) * math.prod(c for i, c in enumerate(cobertas) if i != g)
        esperadas += so_g_descoberto * tamanhos[g]

    return {
        "jogos": n, "duplos": sum(1 for t in tamanhos if t == 2), "triplos": sum(1 for t in tamanhos if t == 3),
        "apostas": apostas, "custo": apostas * PRECO_APOSTA,
        "cobertas": cobertas,
        "chance_14": prob_todos,
        "chance_13_ou_mais": float(dist[n - 1:].sum()),
        "chance_12_ou_mais": float(dist[n - 2:].sum()),
        "acertos_esperados": float(sum(cobertas)),
        "distribuicao": {k: float(dist[k]) for k in range(n, -1, -1)},
        "apostas_premiadas": {
            "se_acertar_todos": {"com_14": 1, "com_13": extras_13_se_14},
            "se_errar_exatamente_um": {"minimo": min(tamanhos), "maximo": max(tamanhos)},
            "esperadas": esperadas,
        },
    }


def ganho_de_cada_multiplo(pcts: list[dict], marcacoes: list[list[str]]) -> list[dict]:
    """Para cada jogo com duplo ou triplo: o que mudaria sem a coluna de menor percentual (triplo vira duplo, duplo
    vira simples). Mostra quanto de chance aquela coluna acrescenta e quanto ela custa. Hipótese de cálculo: o bilhete
    sem ela pode ficar abaixo do mínimo oficial de um duplo, o que só vale como comparação."""
    _validar(pcts, marcacoes)
    n = len(pcts)
    com = medidas_do_bilhete(pcts, marcacoes)
    saida = []
    for i, marcadas in enumerate(marcacoes):
        if len(marcadas) < 2:
            continue
        removida = min(marcadas, key=lambda c: pcts[i][c])
        sem_marcacoes = [list(m) for m in marcacoes]
        sem_marcacoes[i] = [c for c in marcadas if c != removida]
        sem = medidas_do_bilhete(pcts, sem_marcacoes)
        custo_extra = com["custo"] - sem["custo"]
        saida.append(
            {
                "indice": i, "de": len(marcadas), "para": len(marcadas) - 1, "coluna_acrescentada": removida,
                "chance_13_com": com["chance_13_ou_mais"], "chance_13_sem": sem["chance_13_ou_mais"],
                "ganho_13": com["chance_13_ou_mais"] - sem["chance_13_ou_mais"],
                "ganho_14": com["chance_14"] - sem["chance_14"],
                "custo_extra": custo_extra,
                "ganho_13_por_real": (com["chance_13_ou_mais"] - sem["chance_13_ou_mais"]) / custo_extra if custo_extra else None,
            }
        )
    return saida


def _apostas_em_comum(a: list[list[str]], b: list[list[str]]) -> int:
    """Apostas completas (uma coluna por jogo) que os dois bilhetes têm em comum."""
    return math.prod(len(set(ma) & set(mb)) for ma, mb in zip(a, b))


def _apostas_distintas(bilhetes: list[list[list[str]]]) -> int:
    """Tamanho da união das apostas de todos os bilhetes, por inclusão-exclusão: a interseção de vários bilhetes é o
    produto, jogo a jogo, das colunas que todos marcaram."""
    total = 0
    for k in range(1, len(bilhetes) + 1):
        for grupo in itertools.combinations(bilhetes, k):
            comum = math.prod(len(set.intersection(*(set(b[i]) for b in grupo))) for i in range(len(grupo[0])))
            total += (-1) ** (k + 1) * comum
    return total


def bilhete_unico_com_o_mesmo_dinheiro(pcts: list[dict], custo_total: float) -> dict | None:
    """O melhor bilhete único, montado pela regra do app, que cabe no mesmo dinheiro (e no máximo oficial de apostas):
    o de mais apostas; no empate, o de maior chance de 13 ou mais. None se o dinheiro não chega ao mínimo (R$ 4,00)."""
    n = len(pcts)
    limite = min(int(custo_total // PRECO_APOSTA), config.BILHETE_MAX_APOSTAS)
    melhor = None
    for triplos in range(0, n + 1):
        for duplos in range(0, n - triplos + 1):
            apostas = 2**duplos * 3**triplos
            if apostas < 2 or apostas > limite:
                continue
            marcacoes = distribuicao_por_regra(pcts, duplos, triplos)
            m = medidas_do_bilhete(pcts, marcacoes)
            chave = (apostas, m["chance_13_ou_mais"])
            if melhor is None or chave > melhor[0]:
                melhor = (chave, marcacoes, m)
    if melhor is None:
        return None
    _, marcacoes, m = melhor
    return {"marcacoes": marcacoes, **m, "sobra": custo_total - m["custo"]}


def medidas_do_conjunto(pcts: list[dict], bilhetes: list[dict]) -> dict:
    """Medidas de vários bilhetes jogados juntos no mesmo concurso. `bilhetes`: [{'id', 'marcacoes'}].

    Os bilhetes disputam os mesmos jogos, então as chances não se somam: o cálculo percorre os 3^n resultados
    possíveis (com a probabilidade de cada um, jogos independentes) e vê, em cada um, quais bilhetes acertam."""
    if not bilhetes:
        raise ValueError("Sem bilhetes.")
    if len(bilhetes) > LIMITE_BILHETES_NO_CONJUNTO:
        raise ValueError(f"No máximo {LIMITE_BILHETES_NO_CONJUNTO} bilhetes por conjunto.")
    n = len(pcts)
    for b in bilhetes:
        _validar(pcts, b["marcacoes"])

    P = np.array([[pct[c] for c in COLUNAS] for pct in pcts], dtype=float)
    P = P / P.sum(axis=1, keepdims=True)
    prob = np.ones(1)
    acertos = [np.zeros(1, dtype=np.uint8) for _ in bilhetes]
    for i in range(n):
        prob = (prob[:, None] * P[i][None, :]).ravel()
        for k, b in enumerate(bilhetes):
            cobre = np.array([1 if c in b["marcacoes"][i] else 0 for c in COLUNAS], dtype=np.uint8)
            acertos[k] = (acertos[k][:, None] + cobre[None, :]).ravel()

    minimo = n - 1
    faz_13 = [a >= minimo for a in acertos]
    faz_14 = [a == n for a in acertos]
    qualquer_13 = np.logical_or.reduce(faz_13)
    qualquer_14 = np.logical_or.reduce(faz_14)
    quantos_13 = np.sum(faz_13, axis=0)

    por_bilhete = []
    for k, b in enumerate(bilhetes):
        outros = [f for j, f in enumerate(faz_13) if j != k]
        outros_14 = [f for j, f in enumerate(faz_14) if j != k]
        sem_13 = float(prob[np.logical_or.reduce(outros)].sum()) if outros else 0.0
        sem_14 = float(prob[np.logical_or.reduce(outros_14)].sum()) if outros_14 else 0.0
        apostas = _apostas(b["marcacoes"])
        por_bilhete.append(
            {
                "id": b["id"], "apostas": apostas, "custo": apostas * PRECO_APOSTA,
                "chance_13_ou_mais": float(prob[faz_13[k]].sum()), "chance_14": float(prob[faz_14[k]].sum()),
                "acrescenta_13": float(prob[qualquer_13].sum()) - sem_13,
                "acrescenta_14": float(prob[qualquer_14].sum()) - sem_14,
            }
        )

    pares = []
    for (i, a), (j, b) in itertools.combinations(enumerate(bilhetes), 2):
        os_dois = float(prob[faz_13[i] & faz_13[j]].sum())
        algum = float(prob[faz_13[i] | faz_13[j]].sum())
        pares.append(
            {
                "ids": (a["id"], b["id"]), "apostas_em_comum": _apostas_em_comum(a["marcacoes"], b["marcacoes"]),
                "sobreposicao_13": os_dois / algum if algum > 0 else 0.0,
            }
        )

    apostas_total = sum(p["apostas"] for p in por_bilhete)
    distintas = _apostas_distintas([b["marcacoes"] for b in bilhetes])
    custo_total = apostas_total * PRECO_APOSTA
    unico = bilhete_unico_com_o_mesmo_dinheiro(pcts, custo_total)
    chance_13 = float(prob[qualquer_13].sum())
    return {
        "jogos": n, "bilhetes": len(bilhetes), "apostas": apostas_total, "custo": custo_total,
        "chance_14": float(prob[qualquer_14].sum()),
        "chance_13_ou_mais": chance_13,
        "chance_dois_ou_mais_bilhetes_13": float(prob[quantos_13 >= 2].sum()),
        "por_bilhete": por_bilhete, "pares": pares,
        "apostas_distintas": distintas, "apostas_repetidas": apostas_total - distintas,
        "custo_repetido": (apostas_total - distintas) * PRECO_APOSTA,
        "chance_13_por_100_reais": chance_13 / custo_total * 100.0 if custo_total else None,
        "bilhete_unico": unico,
    }
