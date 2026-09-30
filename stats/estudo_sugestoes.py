"""E4 -- teste das sugestões para jogos complexos contra resultados reais, sem olhar
o futuro (cada concurso usa só percentuais calculados com os concursos anteriores,
stats.backtest.prever_walk_forward). Pedido do usuário, 30/09/2026: estudar e testar
antes de mostrar qualquer sugestão na tela.

Perguntas respondidas:
1. Com o mesmo custo, o cálculo exato (E2) acerta mais que a regra simples que o app já
   usa? E mais que pôr os duplos e triplos ao acaso?
2. A "chance de acertar todos" que o app mostra é realista? (previsto x ocorrido)
3. Aplicar a melhor troca de um passo (E2) num bilhete montado sem critério aumenta os
   acertos reais?
"""
import math
import random
from collections import defaultdict

from stats.analise_palpite import chance_do_bilhete
from stats.otimizacao_bilhete import (
    COLUNAS,
    _ordenadas,
    distribuicao_por_regra,
    melhor_distribuicao,
    trocas_de_um_passo,
)


def concursos_completos(jogos: list[dict], previsoes: dict[int, dict], chave: str = "atual") -> list[list[tuple[dict, str]]]:
    """[(percentuais, resultado real)] de cada concurso com os 14 jogos avaliáveis."""
    por_concurso = defaultdict(list)
    por_id = {j["id"]: j for j in jogos}
    for id_jogo, previsao in previsoes.items():
        por_concurso[previsao["concurso"]].append((por_id[id_jogo]["num_jogo"], previsao[chave], por_id[id_jogo]["resultado"]))
    return [[(p, r) for _, p, r in sorted(itens, key=lambda x: x[0])]
            for _, itens in sorted(por_concurso.items()) if len(itens) == 14]


def acertos(marcacoes: list[list[str]], reais: list[str]) -> int:
    return sum(1 for m, r in zip(marcacoes, reais) if r in m)


def distribuicao_aleatoria(pcts: list[dict], duplos: int, triplos: int, sorteio: random.Random) -> list[list[str]]:
    """Duplos e triplos em jogos sorteados, cobrindo as colunas de maior percentual."""
    jogos = sorteio.sample(range(len(pcts)), duplos + triplos)
    quantos = [1] * len(pcts)
    for i in jogos[:triplos]:
        quantos[i] = 3
    for i in jogos[triplos:]:
        quantos[i] = 2
    return [sorted(_ordenadas(p)[:k], key=COLUNAS.index) for p, k in zip(pcts, quantos)]


def _media_e_erro(valores: list[float]) -> tuple[float, float]:
    n = len(valores)
    media = sum(valores) / n
    if n < 2:
        return media, float("nan")
    variancia = sum((v - media) ** 2 for v in valores) / (n - 1)
    return media, math.sqrt(variancia / n)


def _veredito(media: float, erro: float) -> str:
    if math.isnan(erro):
        return "amostra insuficiente"
    if media - 1.96 * erro > 0:
        return "acerta mais"
    if media + 1.96 * erro < 0:
        return "acerta menos"
    return "sem diferença perceptível"


def avaliar_orcamento(concursos: list[list[tuple[dict, str]]], duplos: int, triplos: int, semente: int = 2026) -> dict:
    """Pergunta 1 e 2 para um custo (duplos, triplos)."""
    sorteio = random.Random(semente)
    linhas = []
    for concurso in concursos:
        pcts, reais = [p for p, _ in concurso], [r for _, r in concurso]
        exato = melhor_distribuicao(pcts, duplos, triplos)["marcacoes"]
        regra = distribuicao_por_regra(pcts, duplos, triplos)
        aleatorio = distribuicao_aleatoria(pcts, duplos, triplos, sorteio)
        chance = chance_do_bilhete([sum(p[c] for c in m) for p, m in zip(pcts, exato)])
        linhas.append({
            "exato": acertos(exato, reais), "regra": acertos(regra, reais), "aleatorio": acertos(aleatorio, reais),
            "iguais": exato == regra,
            "previsto_14": chance["chance_todos"], "previsto_13": chance["chance_todos_menos_um_ou_mais"],
        })
    n = len(linhas)
    resumo = {"duplos": duplos, "triplos": triplos, "apostas": 2**duplos * 3**triplos, "concursos": n}
    for estrategia in ("exato", "regra", "aleatorio"):
        resumo[estrategia] = {
            "acertos_medios": sum(l[estrategia] for l in linhas) / n,
            "fez_14": sum(1 for l in linhas if l[estrategia] == 14),
            "fez_13_ou_mais": sum(1 for l in linhas if l[estrategia] >= 13),
            "fez_12_ou_mais": sum(1 for l in linhas if l[estrategia] >= 12),
        }
    for nome, outra in (("exato_menos_regra", "regra"), ("exato_menos_aleatorio", "aleatorio")):
        media, erro = _media_e_erro([l["exato"] - l[outra] for l in linhas])
        resumo[nome] = {"media": media, "erro_padrao": erro, "veredito": _veredito(media, erro)}
    resumo["exato_igual_a_regra"] = sum(1 for l in linhas if l["iguais"])
    resumo["previsto_14_soma"] = sum(l["previsto_14"] for l in linhas)
    resumo["previsto_13_soma"] = sum(l["previsto_13"] for l in linhas)
    return resumo


def avaliar_trocas(concursos: list[list[tuple[dict, str]]], duplos: int, triplos: int,
                   chance_contraria: float = 0.25, semente: int = 2026) -> dict:
    """Pergunta 3: parte de um bilhete sem critério (duplos e triplos em jogos sorteados e,
    em cada seco, `chance_contraria` de marcar outra coluna que não a de maior percentual) e
    aplica a melhor troca de um passo, quando há. Compara os acertos reais antes e depois."""
    sorteio = random.Random(semente)
    diferencas, aplicadas = [], 0
    for concurso in concursos:
        pcts, reais = [p for p, _ in concurso], [r for _, r in concurso]
        partida = distribuicao_aleatoria(pcts, duplos, triplos, sorteio)
        for i, colunas in enumerate(partida):
            if len(colunas) == 1 and sorteio.random() < chance_contraria:
                partida[i] = [sorteio.choice([c for c in COLUNAS if c != colunas[0]])]
        trocas = trocas_de_um_passo(pcts, partida)
        if not trocas:
            continue
        aplicadas += 1
        diferencas.append(acertos(trocas[0]["marcacoes"], reais) - acertos(partida, reais))
    if not diferencas:
        return {"concursos": len(concursos), "com_sugestao": 0}
    media, erro = _media_e_erro(diferencas)
    return {
        "concursos": len(concursos), "com_sugestao": aplicadas,
        "ganhou": sum(1 for d in diferencas if d > 0), "perdeu": sum(1 for d in diferencas if d < 0),
        "igual": sum(1 for d in diferencas if d == 0),
        "diferenca_media": media, "erro_padrao": erro, "veredito": _veredito(media, erro),
    }
