"""Montagem de um bilhete VÁLIDO a partir dos percentuais.

Regras oficiais (Manual de Produtos v21, item 6.3.3): 14 jogos; aposta
mínima = 1 duplo (2 apostas, R$ 4,00); máximo de 864 apostas; cada aposta
custa R$ 2,00. A sugestão por limiar de cada jogo isolado (stats/sugestao.py)
pode somar mais duplos/triplos do que o volante aceita; este módulo escolhe
ONDE gastar duplos e triplos dentro do máximo e do orçamento.

Critério: a cada passo faz o aumento de cobertura (seco->duplo, duplo->triplo)
com maior razão ln(ganho na probabilidade de acertar o jogo) / ln(aumento de
custo). Heurística gulosa e transparente -- não promete acerto; só evita gastar
cobertura onde ela rende pouco.
"""
import math

import config

PRECO_APOSTA = 2.0


def _cobertura(percentuais: dict, colunas: list[str]) -> float:
    return sum(percentuais[c] for c in colunas) / 100.0


def montar_bilhete(jogos: list[dict], orcamento: float | None = None) -> dict:
    """`jogos`: lista de {'1': %, 'X': %, '2': %}. `orcamento` em reais (None =
    só o máximo oficial). O bilhete sempre tem ao menos 1 duplo (mínimo
    oficial), mesmo que o orçamento seja menor que R$ 4,00."""
    ordenados = [sorted(j, key=j.get, reverse=True) for j in jogos]
    marcacoes = [[colunas[0]] for colunas in ordenados]
    apostas = 1
    teto_custo = orcamento if orcamento is not None else config.BILHETE_MAX_APOSTAS * PRECO_APOSTA

    def melhor_aumento(so_de_seco: bool, apostas_atuais: int, respeitar_limites: bool):
        melhor = None
        for i, colunas in enumerate(marcacoes):
            k = len(colunas)
            if k >= 3 or (so_de_seco and k != 1):
                continue
            novas = round(apostas_atuais * (k + 1) / k)
            if respeitar_limites and (
                novas > config.BILHETE_MAX_APOSTAS or novas * PRECO_APOSTA > teto_custo
            ):
                continue
            nova_coluna = ordenados[i][k]
            atual = _cobertura(jogos[i], colunas)
            razao = math.log((atual + jogos[i][nova_coluna] / 100.0) / atual) / math.log((k + 1) / k)
            if melhor is None or razao > melhor[0]:
                melhor = (razao, i, nova_coluna, novas)
        return melhor

    # duplo obrigatório (mínimo oficial), independente do orçamento
    primeiro = melhor_aumento(so_de_seco=True, apostas_atuais=apostas, respeitar_limites=False)
    _, i, coluna, apostas = primeiro
    marcacoes[i].append(coluna)

    while (aumento := melhor_aumento(False, apostas, True)) is not None:
        _, i, coluna, apostas = aumento
        marcacoes[i].append(coluna)

    probabilidade = 1.0
    for i, colunas in enumerate(marcacoes):
        probabilidade *= _cobertura(jogos[i], colunas)
    return {
        "marcacoes": [sorted(m) for m in marcacoes],
        "apostas": apostas,
        "custo": apostas * PRECO_APOSTA,
        "duplos": sum(1 for m in marcacoes if len(m) == 2),
        "triplos": sum(1 for m in marcacoes if len(m) == 3),
        "prob_todos_acertos": probabilidade,
    }
