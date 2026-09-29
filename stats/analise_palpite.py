"""Análise do palpite do usuário (item 20 da rastreabilidade, aprovado em
29/09/2026 -- ver docs/estudo-analise-do-palpite.md).

Tudo por regra sobre os percentuais que o app já mostra; sem IA e sem fonte
nova. A análise nunca diz "certo" ou "errado": diz se a marcação acompanha o
favorito dos dados, vai contra ele ou é zebra, se o jogo é equilibrado, e
quanto cada duplo ou triplo rende em chance. Os percentuais do app são uma
estimativa fraca (o backtest B3 mostrou que o modelo perde da frequência
histórica simples) -- a página diz isso junto com a análise.

Primeira entrega (aprovada): coerência, zebras, rendimento de duplos e
triplos, chance do bilhete, jogos sem base própria e, depois do resultado, o
que aconteceu em cada tipo de marcação, acumulado para aprendizado.
"""
import config
from stats.bilhete import montar_bilhete

COLUNAS = ("1", "X", "2")

A_FAVOR = "a_favor"
CONTRA_O_FAVORITO = "contra_o_favorito"
ZEBRA = "zebra"
EQUILIBRADO = "equilibrado"
COBERTURA_TOTAL = "cobertura_total"

NOME_CATEGORIA = {
    A_FAVOR: "A favor dos dados",
    CONTRA_O_FAVORITO: "Contra o favorito",
    ZEBRA: "Zebra",
    EQUILIBRADO: "Jogo equilibrado",
    COBERTURA_TOTAL: "Triplo (cobre os 3 resultados)",
}

SALVOU = "salvou"
NAO_FEZ_DIFERENCA = "nao_fez_diferenca"
NAO_BASTOU = "nao_bastou"


def classificar_jogo(pct: dict, marcacoes: list[str]) -> dict:
    """Lê uma marcação contra os percentuais do jogo ({'1': %, 'X': %, '2': %}).

    Ordem das regras: triplo cobre tudo; favorito abaixo de
    `ANALISE_LIMIAR_EQUILIBRADO` = jogo equilibrado (nenhuma marcação tem
    apoio forte); favorito marcado = a favor dos dados; todas as colunas
    marcadas abaixo de `ANALISE_LIMIAR_ZEBRA` = zebra; o resto = contra o
    favorito (resultado possível, mas não o mais provável)."""
    marcadas = [c for c in COLUNAS if c in set(marcacoes)]
    if not marcadas:
        raise ValueError("Jogo sem marcação não pode ser analisado.")
    favorito = max(COLUNAS, key=lambda c: pct[c])
    chance = sum(pct[c] for c in marcadas)
    if len(marcadas) == 3:
        categoria = COBERTURA_TOTAL
    elif pct[favorito] < config.ANALISE_LIMIAR_EQUILIBRADO:
        categoria = EQUILIBRADO
    elif favorito in marcadas:
        categoria = A_FAVOR
    elif all(pct[c] < config.ANALISE_LIMIAR_ZEBRA for c in marcadas):
        categoria = ZEBRA
    else:
        categoria = CONTRA_O_FAVORITO
    zebras = [] if categoria == COBERTURA_TOTAL else [c for c in marcadas if pct[c] < config.ANALISE_LIMIAR_ZEBRA]
    melhor_marcada = max(marcadas, key=lambda c: pct[c])
    return {
        "marcacoes": marcadas,
        "favorito": favorito,
        "pct_favorito": pct[favorito],
        "chance_coberta": chance,
        "categoria": categoria,
        "zebras": zebras,
        "melhor_marcada": melhor_marcada,
        "ganho_do_multiplo": chance - pct[melhor_marcada] if len(marcadas) > 1 else None,
        "multiplicador": len(marcadas),
    }


def chance_do_bilhete(chances_pct: list[float]) -> dict:
    """Probabilidade de acertar todos os jogos e de errar no máximo um, e o
    número esperado de acertos, supondo jogos independentes e percentuais
    corretos (Poisson-binomial exata). `chances_pct`: chance coberta de cada
    jogo, em %."""
    probabilidades = [min(max(c / 100.0, 0.0), 1.0) for c in chances_pct]
    distribuicao = [1.0]
    for p in probabilidades:
        nova = [0.0] * (len(distribuicao) + 1)
        for acertos, prob in enumerate(distribuicao):
            nova[acertos] += prob * (1 - p)
            nova[acertos + 1] += prob * p
        distribuicao = nova
    n = len(probabilidades)
    todos = distribuicao[n]
    return {
        "jogos": n,
        "chance_todos": todos,
        "chance_todos_menos_um_ou_mais": todos + (distribuicao[n - 1] if n >= 1 else 0.0),
        "acertos_esperados": sum(probabilidades),
    }


def formatar_uma_em(probabilidade: float) -> str:
    """0,00077 -> '1 em 1.297'; chances altas viram porcentagem."""
    if probabilidade <= 0:
        return "praticamente nula"
    if probabilidade >= 0.1:
        return f"{probabilidade * 100:.0f}%".replace(".", ",")
    return "1 em " + f"{round(1 / probabilidade):,}".replace(",", ".")


def _melhor_coluna_livre(pct: dict, marcacoes: list[str]) -> tuple[str, float] | None:
    livres = [c for c in COLUNAS if c not in marcacoes]
    if not livres:
        return None
    coluna = max(livres, key=lambda c: pct[c])
    return coluna, pct[coluna]


def analisar_palpite(jogos: list[dict]) -> dict:
    """`jogos`: na ordem do concurso, cada um com `num_jogo`, `casa`, `fora`,
    `pct` ({'1','X','2'} em %), `marcacoes` (não vazia) e, opcionalmente,
    `sem_base_propria` (percentual caiu na média geral) e `jogo_id`."""
    analisados = []
    for jogo in jogos:
        leitura = classificar_jogo(jogo["pct"], jogo["marcacoes"])
        analisados.append(
            {
                "jogo_id": jogo.get("jogo_id"),
                "num_jogo": jogo["num_jogo"],
                "casa": jogo["casa"],
                "fora": jogo["fora"],
                "pct": jogo["pct"],
                "sem_base_propria": bool(jogo.get("sem_base_propria")),
                **leitura,
            }
        )

    resumo = {categoria: 0 for categoria in NOME_CATEGORIA}
    for jogo in analisados:
        resumo[jogo["categoria"]] += 1

    zebras = [
        {"num_jogo": j["num_jogo"], "coluna": c, "pct": j["pct"][c], "casa": j["casa"], "fora": j["fora"]}
        for j in analisados
        for c in j["zebras"]
    ]
    multiplos = [
        {
            "num_jogo": j["num_jogo"],
            "tipo": "triplo" if j["multiplicador"] == 3 else "duplo",
            "chance_antes": j["pct"][j["melhor_marcada"]],
            "chance_depois": j["chance_coberta"],
            "ganho": j["ganho_do_multiplo"],
        }
        for j in analisados
        if j["multiplicador"] > 1
    ]

    candidatos = []
    for j in analisados:
        if j["multiplicador"] != 1:
            continue
        livre = _melhor_coluna_livre(j["pct"], j["marcacoes"])
        if livre:
            candidatos.append({"num_jogo": j["num_jogo"], "coluna_extra": livre[0], "ganho": livre[1]})
    candidatos.sort(key=lambda c: (-c["ganho"], c["num_jogo"]))

    trocas = []
    usados = set()
    for duplo in sorted((m for m in multiplos if m["tipo"] == "duplo"), key=lambda m: m["ganho"]):
        alvo = next((c for c in candidatos if c["num_jogo"] not in usados), None)
        if alvo and alvo["ganho"] - duplo["ganho"] >= config.ANALISE_DIFERENCA_PARA_TROCA_PP:
            usados.add(alvo["num_jogo"])
            trocas.append(
                {
                    "de": duplo["num_jogo"], "ganho_atual": duplo["ganho"],
                    "para": alvo["num_jogo"], "coluna_extra": alvo["coluna_extra"], "ganho_novo": alvo["ganho"],
                }
            )

    chance = chance_do_bilhete([j["chance_coberta"] for j in analisados])
    sem_base = [j["num_jogo"] for j in analisados if j["sem_base_propria"]]
    analise = {
        "jogos": analisados,
        "resumo_categorias": resumo,
        "zebras": zebras,
        "multiplos": multiplos,
        "melhores_duplos": candidatos[: config.ANALISE_QUANTOS_MELHORES_DUPLOS],
        "trocas": trocas,
        "chance": chance,
        "sem_base_propria": sem_base,
    }
    analise["frases"] = frases_da_analise(analise)
    return analise


def _lista(numeros: list[int]) -> str:
    textos = [str(n) for n in numeros]
    return textos[0] if len(textos) == 1 else ", ".join(textos[:-1]) + " e " + textos[-1]


def frases_da_analise(analise: dict) -> list[str]:
    """Leituras por regra, cada uma com o número que a sustenta."""
    resumo, total = analise["resumo_categorias"], len(analise["jogos"])
    frases = [
        f"{resumo[A_FAVOR]} de {total} marcações acompanham o favorito dos dados; "
        f"{resumo[CONTRA_O_FAVORITO]} vão contra o favorito; {resumo[ZEBRA]} são zebra "
        f"(abaixo de {config.ANALISE_LIMIAR_ZEBRA:.0f}%); {resumo[EQUILIBRADO]} estão em jogo equilibrado "
        f"(favorito abaixo de {config.ANALISE_LIMIAR_EQUILIBRADO:.0f}%)"
        + (f"; {resumo[COBERTURA_TOTAL]} com triplo (cobre os 3 resultados)." if resumo[COBERTURA_TOTAL] else ".")
    ]
    chance = analise["chance"]
    n = chance["jogos"]
    esperado = f"{chance['acertos_esperados']:.1f}".replace(".", ",")
    frases.append(
        f"Pelos percentuais do app, a chance de {n} acertos é de {formatar_uma_em(chance['chance_todos'])} e a de "
        f"{n - 1} ou mais, {formatar_uma_em(chance['chance_todos_menos_um_ou_mais'])}. "
        f"O esperado é em torno de {esperado} acertos."
    )
    if analise["zebras"]:
        frases.append(
            "Zebra tem chance menor. Nos concursos passados, os que tiveram mais zebras tiveram menos ganhadores "
            "na faixa principal (relação fraca): quando acerta, o prêmio tende a ser menos dividido."
        )
    for troca in analise["trocas"]:
        frases.append(
            f"O duplo do jogo {troca['de']} soma {troca['ganho_atual']:.0f} pontos de chance. No jogo {troca['para']}, "
            f"o mesmo duplo (coluna {troca['coluna_extra']}) somaria {troca['ganho_novo']:.0f} pontos, pelo mesmo custo."
        )
    if analise["sem_base_propria"]:
        frases.append(
            f"Nos jogos {_lista(analise['sem_base_propria'])}, os times têm pouco histórico e o percentual é a média "
            "geral de todos os jogos: ali nenhuma marcação tem apoio forte nos dados."
        )
    return frases


def avaliar_depois_do_resultado(jogos: list[dict]) -> dict:
    """Depois do resultado: o que aconteceu em cada tipo de marcação e se os
    duplos e triplos fizeram diferença. `jogos`: cada um com `pct`,
    `marcacoes`, `resultado` ('1','X','2') e, se já gravada, `categoria`."""
    por_categoria = {categoria: {"marcacoes": 0, "acertos": 0} for categoria in NOME_CATEGORIA}
    multiplos = {SALVOU: 0, NAO_FEZ_DIFERENCA: 0, NAO_BASTOU: 0}
    zebras_que_aconteceram = []
    esperado = 0.0
    acertos = 0
    for jogo in jogos:
        leitura = classificar_jogo(jogo["pct"], jogo["marcacoes"])
        categoria = jogo.get("categoria") or leitura["categoria"]
        acertou = jogo["resultado"] in leitura["marcacoes"]
        por_categoria[categoria]["marcacoes"] += 1
        por_categoria[categoria]["acertos"] += int(acertou)
        acertos += int(acertou)
        esperado += leitura["chance_coberta"] / 100.0
        if leitura["multiplicador"] > 1:
            if not acertou:
                multiplos[NAO_BASTOU] += 1
            elif jogo["resultado"] == leitura["melhor_marcada"]:
                multiplos[NAO_FEZ_DIFERENCA] += 1
            else:
                multiplos[SALVOU] += 1
        if jogo["pct"][jogo["resultado"]] < config.ANALISE_LIMIAR_ZEBRA:
            zebras_que_aconteceram.append({"num_jogo": jogo.get("num_jogo"), "marcou": acertou})
    return {
        "acertos": acertos,
        "acertos_esperados": esperado,
        "por_categoria": por_categoria,
        "multiplos": multiplos,
        "zebras_que_aconteceram": zebras_que_aconteceram,
    }


def _taxa(acertos: int, total: int) -> float | None:
    """Taxa só aparece com amostra mínima -- abaixo disso, é ruído."""
    return 100.0 * acertos / total if total >= config.ANALISE_AMOSTRA_MINIMA else None


def agregar_historico(bilhetes: list[list[dict]]) -> dict:
    """Aprendizado acumulado dos bilhetes já conferidos. `bilhetes`: lista de
    bilhetes, cada um a lista dos seus jogos (na ordem do concurso) com `pct`,
    `marcacoes`, `resultado`, `categoria` (pode faltar em bilhete antigo) e
    `motivos` (lista, pode ser vazia). Compara também com a sugestão do app
    calculada sobre o MESMO percentual salvo, nos jogos em que você divergiu."""
    categorias = {c: {"marcacoes": 0, "acertos": 0} for c in NOME_CATEGORIA}
    motivos: dict[str, dict] = {}
    multiplos = {SALVOU: 0, NAO_FEZ_DIFERENCA: 0, NAO_BASTOU: 0}
    divergencias = {"jogos": 0, "voce_acertou": 0, "app_acertou": 0}
    acertos_total = esperado_total = 0.0

    for jogos in bilhetes:
        avaliacao = avaliar_depois_do_resultado(jogos)
        acertos_total += avaliacao["acertos"]
        esperado_total += avaliacao["acertos_esperados"]
        for categoria, contagem in avaliacao["por_categoria"].items():
            categorias[categoria]["marcacoes"] += contagem["marcacoes"]
            categorias[categoria]["acertos"] += contagem["acertos"]
        for chave, valor in avaliacao["multiplos"].items():
            multiplos[chave] += valor

        sugestao = montar_bilhete([j["pct"] for j in jogos])["marcacoes"]
        for jogo, do_app in zip(jogos, sugestao):
            acertou = jogo["resultado"] in jogo["marcacoes"]
            for motivo in jogo.get("motivos") or []:
                registro = motivos.setdefault(motivo, {"marcacoes": 0, "acertos": 0})
                registro["marcacoes"] += 1
                registro["acertos"] += int(acertou)
            if sorted(jogo["marcacoes"]) != sorted(do_app):
                divergencias["jogos"] += 1
                divergencias["voce_acertou"] += int(acertou)
                divergencias["app_acertou"] += int(jogo["resultado"] in do_app)

    def com_taxa(contagens: dict) -> dict:
        return {chave: {**v, "taxa": _taxa(v["acertos"], v["marcacoes"])} for chave, v in contagens.items()}

    n = len(bilhetes)
    return {
        "bilhetes": n,
        "acertos_medios": acertos_total / n if n else None,
        "acertos_esperados_medios": esperado_total / n if n else None,
        "por_categoria": com_taxa(categorias),
        "por_motivo": com_taxa(motivos),
        "multiplos": multiplos,
        "divergencias": {
            **divergencias,
            "taxa_voce": _taxa(divergencias["voce_acertou"], divergencias["jogos"]),
            "taxa_app": _taxa(divergencias["app_acertou"], divergencias["jogos"]),
        },
        "amostra_minima": config.ANALISE_AMOSTRA_MINIMA,
    }
