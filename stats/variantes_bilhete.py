"""Bilhetes alternativos a partir do volante do usuário (pedido de 08/10/2026, plano validado: três tipos,
"levar ao volante" e "salvar como meu bilhete", origem guardada, aviso de bilhete igual e aviso de prêmio dividido).

Três variantes, todas sobre os percentuais da tela:
- **ajuste leve:** até `config.VARIANTES_MAX_TROCAS_AJUSTE` trocas de um passo (stats.otimizacao_bilhete), uma de cada
  vez, cada uma pelo mesmo custo e com os mesmos duplos e triplos;
- **reorganizado:** os mesmos números de duplos e triplos, colocados pela regra do app (os triplos e os duplos nos jogos
  de favorito mais fraco). No estudo E4, a regra empatou com o cálculo exato e ganhou do acaso;
- **econômico:** tira `config.VARIANTES_COLUNAS_TIRADAS_ECONOMICO` coluna(s), sempre a de menor perda de chance por
  real economizado (stats.otimizacao_bilhete.economias).

Regras do usuário conferidas aqui, não só na tela: nenhuma variante aumenta o custo nem o número de duplos e triplos;
variante igual ao bilhete de partida ou a outra variante não é repetida. O efeito medido é pequeno (estudo E4: cerca de
+0,3 acerto por concurso, quase tudo de desfazer marcação contra o favorito), e a tela diz isso.

As funções de montagem são puras; as de banco recebem a conexão.
"""
import json

import config
from stats.bilhete import PRECO_APOSTA
from stats.chances_bilhete import medidas_do_bilhete
from stats.otimizacao_bilhete import distribuicao_por_regra, economias, trocas_de_um_passo
from stats.versoes_palpite import acertos, diferencas

COLUNAS = ("1", "X", "2")
ORIGEM_VOLANTE = "volante"
NOMES = {
    "ajuste_leve": "Ajuste leve",
    "reorganizado": "Reorganizado",
    "economico": "Econômico",
}
DESCRICOES = {
    "ajuste_leve": "poucas trocas no seu bilhete, pelo mesmo custo",
    "reorganizado": "os seus duplos e triplos nos jogos mais incertos, pela regra do app, pelo mesmo custo",
    "economico": "o seu bilhete sem a coluna que menos rende pelo que custa",
}
SEM_MUDANCA = {
    "ajuste_leve": "nenhuma troca pelo mesmo custo aumenta a chance de acertar todos em "
                   f"{config.OTIMIZACAO_GANHO_MINIMO_RELATIVO:.0%} ou mais, pelos percentuais do app",
    "reorganizado": "os seus duplos e triplos já estão onde a regra do app os colocaria",
    "economico": "não há coluna para tirar: o volante exige ao menos um duplo",
}


def nome_da_origem(origem: str | None) -> str:
    """Nome para a tela; bilhete antigo (sem origem gravada) é do volante."""
    return NOMES.get(origem or ORIGEM_VOLANTE, "Seu volante")


def _ordenar(colunas) -> list[str]:
    return [c for c in COLUNAS if c in set(colunas)]


def _apostas(marcacoes: list[list[str]]) -> int:
    apostas = 1
    for colunas in marcacoes:
        apostas *= len(colunas)
    return apostas


def _forma(marcacoes: list[list[str]]) -> tuple[int, int]:
    return sum(1 for m in marcacoes if len(m) == 2), sum(1 for m in marcacoes if len(m) == 3)


def favoritos_secos(pcts: list[dict], marcacoes: list[list[str]]) -> int:
    """Jogos marcados só no favorito dos percentuais: quanto mais, mais o bilhete se parece com o da maioria."""
    return sum(1 for p, m in zip(pcts, marcacoes) if len(m) == 1 and m[0] == max(COLUNAS, key=lambda c: (p[c], -COLUNAS.index(c))))


def _ajuste_leve(pcts, marcacoes, numeros) -> tuple[list[list[str]], list[str]]:
    custo, forma = _apostas(marcacoes), _forma(marcacoes)
    atual, passos = [list(m) for m in marcacoes], []
    for _ in range(config.VARIANTES_MAX_TROCAS_AJUSTE):
        trocas = [t for t in trocas_de_um_passo(pcts, atual, numeros)
                  if _apostas(t["marcacoes"]) == custo and _forma(t["marcacoes"]) == forma]
        if not trocas:
            break
        atual = [list(m) for m in trocas[0]["marcacoes"]]
        passos.append(trocas[0]["descricao"])
    return atual, passos


def _reorganizado(pcts, marcacoes, numeros) -> tuple[list[list[str]], list[str]]:
    duplos, triplos = _forma(marcacoes)
    return distribuicao_por_regra(pcts, duplos, triplos), [
        f"{duplos} duplo(s) e {triplos} triplo(s) nos jogos de favorito mais fraco, com as colunas de maior percentual"
    ]


def _economico(pcts, marcacoes, numeros) -> tuple[list[list[str]], list[str]]:
    atual, passos = [list(m) for m in marcacoes], []
    for _ in range(config.VARIANTES_COLUNAS_TIRADAS_ECONOMICO):
        opcoes = economias(pcts, atual, numeros)
        if not opcoes:
            break
        escolhida = opcoes[0]
        indice = numeros.index(escolhida["jogo"])
        atual[indice] = list(escolhida["para"])
        passos.append(
            f"jogo {escolhida['jogo']}: tirar a coluna {escolhida['tirar']} ({''.join(escolhida['de'])} vira "
            f"{''.join(escolhida['para'])}), a de menor perda de chance por real economizado"
        )
    return atual, passos


MONTADORES = {"ajuste_leve": _ajuste_leve, "reorganizado": _reorganizado, "economico": _economico}


def gerar_variantes(pcts: list[dict], marcacoes: list[list[str]], numeros: list[int]) -> dict:
    """`pcts` ({'1','X','2'} em %), `marcacoes` e `numeros` (número de cada jogo) na ordem do concurso. Devolve
    {'base': medidas do bilhete de partida, 'variantes': [...], 'sem_variante': [{'tipo', 'motivo'}]}.
    ValueError se o bilhete de partida tem jogo em branco ou passa do máximo oficial de apostas."""
    if not marcacoes or any(not m for m in marcacoes) or not (len(marcacoes) == len(pcts) == len(numeros)):
        raise ValueError("Marque todos os jogos para montar as alternativas.")
    if _apostas(marcacoes) > config.BILHETE_MAX_APOSTAS:
        raise ValueError(f"O bilhete passa do máximo oficial de {config.BILHETE_MAX_APOSTAS} apostas.")
    base = [_ordenar(m) for m in marcacoes]
    custo_base, (duplos_base, triplos_base) = _apostas(base), _forma(base)
    favoritos_base = favoritos_secos(pcts, base)
    vistas = {tuple(map(tuple, base)): "o seu bilhete"}
    variantes, sem_variante = [], []
    for tipo, montar in MONTADORES.items():
        nova, passos = montar(pcts, base, numeros)
        nova = [_ordenar(m) for m in nova]
        duplos, triplos = _forma(nova)
        # Conferência das regras do usuário: nunca mais caro, nunca mais duplos e triplos.
        if _apostas(nova) > custo_base or duplos + triplos > duplos_base + triplos_base or triplos > triplos_base:
            sem_variante.append({"tipo": tipo, "motivo": "a alteração aumentaria o custo; foi descartada"})
            continue
        chave = tuple(map(tuple, nova))
        if not passos or chave in vistas:
            igual = vistas.get(chave, "o seu bilhete")
            motivo = SEM_MUDANCA[tipo] if igual == "o seu bilhete" else f"sairia igual ao bilhete {igual}"
            sem_variante.append({"tipo": tipo, "motivo": motivo})
            continue
        vistas[chave] = f"“{NOMES[tipo]}”"
        medidas = medidas_do_bilhete(pcts, nova)
        favoritos = favoritos_secos(pcts, nova)
        variantes.append({
            "tipo": tipo, "nome": NOMES[tipo], "descricao": DESCRICOES[tipo], "passos": passos,
            "marcacoes": nova, "medidas": medidas,
            "mudancas": diferencas(dict(zip(numeros, base)), dict(zip(numeros, nova))),
            "economia": (custo_base - _apostas(nova)) * PRECO_APOSTA,
            "favoritos_secos": favoritos, "mais_favoritos_que_a_base": favoritos > favoritos_base,
        })
    return {"base": {**medidas_do_bilhete(pcts, base), "favoritos_secos": favoritos_base},
            "variantes": variantes, "sem_variante": sem_variante}


# ---------------------------------------------------------------------------
# Depois do resultado: a variante salva x o volante de onde ela saiu
# ---------------------------------------------------------------------------

def comparar_com_a_base(marcacoes_base: dict, marcacoes: dict, resultados: dict[int, str | None]) -> dict | None:
    """Acertos do volante de partida e da variante ({jogo_id: colunas}); None se falta resultado."""
    da_base, da_variante = acertos(marcacoes_base, resultados), acertos(marcacoes, resultados)
    if da_base is None or da_variante is None:
        return None
    return {"acertos_base": da_base, "acertos_variante": da_variante, "saldo": da_variante - da_base}


def ler_marcacoes_base(texto: str | None) -> dict[int, list[str]] | None:
    if not texto:
        return None
    return {int(jogo): colunas for jogo, colunas in json.loads(texto).items()}


def leituras_das_variantes(conexao) -> list[dict]:
    """Uma leitura por bilhete salvo a partir de uma variante, com resultado completo: quantos acertos a variante fez
    a mais (ou a menos) que o volante de onde saiu. Formato de stats.versoes_palpite.agregar_aprendizado (`saldo`)."""
    from stats.bilhetes_salvos import SO_APOSTADOS, jogos_do_bilhete  # import local: sem dependência circular

    saida = []
    for linha in conexao.execute(
        "SELECT id, concurso_numero, origem, marcacoes_base FROM bilhetes"
        f" WHERE origem IS NOT NULL AND origem != ? AND marcacoes_base IS NOT NULL AND {SO_APOSTADOS} ORDER BY id",
        (ORIGEM_VOLANTE,),
    ).fetchall():
        jogos = jogos_do_bilhete(conexao, linha["id"])
        resultados = {j["jogo_id"]: j["resultado"] for j in jogos}
        leitura = comparar_com_a_base(ler_marcacoes_base(linha["marcacoes_base"]),
                                      {j["jogo_id"]: j["marcacoes"] for j in jogos}, resultados)
        if leitura:
            saida.append({"bilhete_id": linha["id"], "concurso_numero": linha["concurso_numero"],
                          "origem": linha["origem"], **leitura})
    return saida
