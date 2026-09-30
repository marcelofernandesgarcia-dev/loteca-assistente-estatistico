"""Estudo de sugestões para jogos complexos (pedido do usuário, 30/09/2026; E1 a
E3 aqui, o teste E4 em stats/estudo_sugestoes.py). Funções puras sobre os
percentuais de cada jogo ({'1','X','2'} em %). Nada disto aparece na tela antes
de o usuário ver o resultado do teste (decisão do usuário).

Chance do bilhete = produto das chances cobertas de cada jogo, supondo jogos
independentes e percentuais corretos -- a mesma suposição de
stats.analise_palpite.chance_do_bilhete. Se os percentuais forem fracos (o teste
B3 mostrou isso para os clubes), otimizar em cima deles pode só amplificar ruído:
é por isso que o E4 mede com resultados reais antes de qualquer uso.

Mesmo custo = mesmos números de duplos e triplos: 2^d x 3^t só se repete com o
mesmo par (d, t).
"""
import math

import config
from stats.bilhete import PRECO_APOSTA

COLUNAS = ("1", "X", "2")
NOME_TIPO = {1: "seco", 2: "duplo", 3: "triplo"}


def _ordenadas(pct: dict) -> list[str]:
    return sorted(COLUNAS, key=lambda c: (-pct[c], COLUNAS.index(c)))


def cobertura(pct: dict, colunas) -> float:
    return sum(pct[c] for c in colunas)


def chance_de_todos(pcts: list[dict], marcacoes: list[list[str]]) -> float:
    """Probabilidade (0 a 1) de acertar todos os jogos."""
    chance = 1.0
    for pct, colunas in zip(pcts, marcacoes):
        chance *= min(cobertura(pct, colunas), 100.0) / 100.0
    return chance


# ---------------------------------------------------------------------------
# E1 -- complexidade do jogo, por regra e com o número que a sustenta
# ---------------------------------------------------------------------------

def complexidade_do_jogo(pct: dict, sem_base_propria: bool = False, melhor_no_ano: str | None = None) -> dict:
    """Por que um jogo é difícil de marcar. `melhor_no_ano`: 'casa' ou 'fora' (quem vai
    melhor no ano em curso, stats.ano_em_curso.diferenca_no_ano), para apontar quando o
    favorito do percentual e o ano em curso discordam. Nível: 'alta' com 2 motivos ou
    mais, 'media' com 1, 'baixa' sem motivo."""
    ordem = _ordenadas(pct)
    favorito, segundo = ordem[0], ordem[1]
    margem = pct[favorito] - pct[segundo]
    motivos = []
    if pct[favorito] < config.ANALISE_LIMIAR_EQUILIBRADO:
        motivos.append(f"favorito com só {pct[favorito]:.0f}% (abaixo de {config.ANALISE_LIMIAR_EQUILIBRADO:.0f}%)")
    if margem < config.OTIMIZACAO_MARGEM_APERTADA_PP:
        motivos.append(f"1º e 2º resultado separados por {margem:.0f} pontos")
    if sem_base_propria:
        motivos.append("pouco histórico dos dois times: percentual é a média geral")
    lado_do_favorito = {"1": "casa", "2": "fora"}.get(favorito)
    if melhor_no_ano and lado_do_favorito and melhor_no_ano != lado_do_favorito:
        motivos.append("o favorito do percentual vai pior no ano em curso")
    nivel = "alta" if len(motivos) >= 2 else "media" if motivos else "baixa"
    return {"nivel": nivel, "motivos": motivos, "favorito": favorito, "pct_favorito": pct[favorito], "margem": margem}


# ---------------------------------------------------------------------------
# E2 -- melhor distribuição dos duplos e triplos pelo mesmo custo (cálculo exato)
# ---------------------------------------------------------------------------

def melhor_distribuicao(pcts: list[dict], duplos: int, triplos: int) -> dict:
    """Onde pôr exatamente `duplos` duplos e `triplos` triplos para a maior chance de acertar
    todos, cobrindo em cada jogo as colunas de maior percentual. Exato (programação dinâmica
    sobre quantos duplos e triplos já foram usados); ValueError se não cabem nos jogos."""
    n = len(pcts)
    if duplos < 0 or triplos < 0 or duplos + triplos > n:
        raise ValueError("Quantidade de duplos e triplos não cabe no número de jogos.")
    ordens = [_ordenadas(p) for p in pcts]

    def valor(i, k):
        return math.log(max(cobertura(pcts[i], ordens[i][:k]), 1e-9) / 100.0)

    # melhor[(d, t)] = (soma dos logs, escolhas) depois de cada jogo.
    melhor = {(0, 0): (0.0, [])}
    for i in range(n):
        novo = {}
        for (d, t), (soma, escolhas) in melhor.items():
            for k, dd, tt in ((1, 0, 0), (2, 1, 0), (3, 0, 1)):
                chave = (d + dd, t + tt)
                if chave[0] > duplos or chave[1] > triplos:
                    continue
                candidato = soma + valor(i, k)
                if chave not in novo or candidato > novo[chave][0]:
                    novo[chave] = (candidato, escolhas + [k])
        melhor = novo
    soma, escolhas = melhor[(duplos, triplos)]
    marcacoes = [sorted(ordens[i][:k], key=COLUNAS.index) for i, k in enumerate(escolhas)]
    return {"marcacoes": marcacoes, "chance_todos": math.exp(soma), "apostas": 2**duplos * 3**triplos}


def distribuicao_por_regra(pcts: list[dict], duplos: int, triplos: int) -> list[list[str]]:
    """A regra simples que o app já usa, estendida para vários duplos e triplos: os triplos
    nos jogos de favorito mais fraco, os duplos nos seguintes (stats.bilhete.montar_bilhete
    é o caso de um só)."""
    ordens = [_ordenadas(p) for p in pcts]
    por_incerteza = sorted(range(len(pcts)), key=lambda i: (pcts[i][ordens[i][0]], i))
    quantos = [1] * len(pcts)
    for i in por_incerteza[:triplos]:
        quantos[i] = 3
    for i in por_incerteza[triplos:triplos + duplos]:
        quantos[i] = 2
    return [sorted(ordens[i][:k], key=COLUNAS.index) for i, k in enumerate(quantos)]


def _tipo(colunas) -> str:
    return NOME_TIPO.get(len(colunas), "vazio")


def trocas_de_um_passo(pcts: list[dict], marcacoes: list[list[str]], num_jogos: list[int] | None = None) -> list[dict]:
    """Alterações simples que mantêm o custo, ordenadas pela chance de acertar todos:
    (a) trocar uma coluna marcada por outra do mesmo jogo; (b) trocar o duplo/triplo de um
    jogo com o seco de outro (cada um passa a cobrir as colunas de maior percentual). Só entra
    o que aumenta a chance em `config.OTIMIZACAO_GANHO_MINIMO_RELATIVO` ou mais."""
    num_jogos = num_jogos or list(range(1, len(pcts) + 1))
    base = chance_de_todos(pcts, marcacoes)
    ordens = [_ordenadas(p) for p in pcts]
    trocas = []

    def registrar(nova, descricao, jogos):
        chance = chance_de_todos(pcts, nova)
        if base > 0 and chance / base - 1 >= config.OTIMIZACAO_GANHO_MINIMO_RELATIVO:
            trocas.append({"descricao": descricao, "jogos": jogos, "chance_antes": base, "chance_depois": chance,
                           "ganho_relativo": chance / base - 1, "marcacoes": nova})

    for i, colunas in enumerate(marcacoes):
        if len(colunas) == 3:
            continue
        melhores = sorted(ordens[i][:len(colunas)], key=COLUNAS.index)
        if melhores != sorted(colunas, key=COLUNAS.index):
            nova = [list(m) for m in marcacoes]
            nova[i] = melhores
            registrar(nova, f"jogo {num_jogos[i]}: trocar {''.join(colunas)} por {''.join(melhores)} "
                            f"(mesmo {_tipo(colunas)})", [num_jogos[i]])
    for i, colunas_i in enumerate(marcacoes):
        if len(colunas_i) < 2:
            continue
        for j, colunas_j in enumerate(marcacoes):
            if len(colunas_j) != 1 or i == j:
                continue
            nova = [list(m) for m in marcacoes]
            nova[i] = [ordens[i][0]]
            nova[j] = sorted(ordens[j][:len(colunas_i)], key=COLUNAS.index)
            registrar(nova, f"levar o {_tipo(colunas_i)} do jogo {num_jogos[i]} para o jogo {num_jogos[j]} "
                            f"({''.join(nova[j])}); o jogo {num_jogos[i]} fica em {nova[i][0]}",
                      [num_jogos[i], num_jogos[j]])
    trocas.sort(key=lambda t: -t["chance_depois"])
    return trocas


# ---------------------------------------------------------------------------
# E3 -- economia: qual duplo ou triplo custa mais caro pelo que rende
# ---------------------------------------------------------------------------

def economias(pcts: list[dict], marcacoes: list[list[str]], num_jogos: list[int] | None = None) -> list[dict]:
    """Para cada duplo ou triplo, tirar a coluna de menor percentual: quanto o bilhete
    economiza e quanto da chance de acertar todos se perde. Ordenado pela menor perda por
    real economizado. Não sugere tirar o último duplo/triplo (o volante exige ao menos um)."""
    num_jogos = num_jogos or list(range(1, len(pcts) + 1))
    multiplos = [i for i, m in enumerate(marcacoes) if len(m) > 1]
    if len(multiplos) <= 1 and all(len(marcacoes[i]) == 2 for i in multiplos):
        return []
    apostas = 1
    for m in marcacoes:
        apostas *= len(m)
    base = chance_de_todos(pcts, marcacoes)
    saida = []
    for i in multiplos:
        if len(multiplos) == 1 and len(marcacoes[i]) == 2:
            continue
        pior = min(marcacoes[i], key=lambda c: (pcts[i][c], -COLUNAS.index(c)))
        nova = [list(m) for m in marcacoes]
        nova[i] = [c for c in marcacoes[i] if c != pior]
        novas_apostas = apostas // len(marcacoes[i]) * len(nova[i])
        economia = (apostas - novas_apostas) * PRECO_APOSTA
        chance = chance_de_todos(pcts, nova)
        saida.append({
            "jogo": num_jogos[i], "tirar": pior, "de": marcacoes[i], "para": nova[i],
            "economia_reais": economia, "chance_antes": base, "chance_depois": chance,
            "perda_relativa": 1 - chance / base if base else 0.0,
            "perda_por_real": (1 - chance / base) / economia if base and economia else 0.0,
        })
    saida.sort(key=lambda e: e["perda_por_real"])
    return saida
