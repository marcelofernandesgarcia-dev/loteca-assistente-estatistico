"""Tabelas da Loteca (pedido do usuário, 08/10/2026): valores e combinações de apostas, e as chances de cada
combinação de duplos e triplos em três leituras. Funções puras; o banco só entra pelas funções que recebem dados.

Valores: 2^duplos x 3^triplos apostas, ao preço vigente (config.PRECO_APOSTA_LOTECA). As combinações válidas vão de 1
duplo (2 apostas, a mínima) até config.BILHETE_MAX_APOSTAS (864 = 5 duplos e 3 triplos), Manual de Produtos v21,
item 6.3.3.2. O formato das tabelas segue o CAIXA Informa de 2019 (docs/fontes-oficiais/), cujos preços não valem mais.

Chances, três leituras (decisão do usuário: todas):
1. **Método da CAIXA**, cada resultado com 1 em 3 nos 3^14 resultados possíveis. Reproduz as chances da aposta
   mínima publicadas no item 6.3.6 do Manual v21 (14 pontos: 1 em 2.391.485; 13 pontos: 1 em 85.410):
   - 14 pontos: casos = apostas (uma aposta acerta tudo em cada resultado coberto);
   - 13 pontos, como na tabela da CAIXA: soma, aposta por aposta, dos resultados em que ela faz exatamente 13
     (2 x 14 por aposta). Conta duas vezes o resultado em que duas apostas do bilhete fazem 13;
   - o bilhete premiar (13 ou 14): cada resultado conta uma vez. Casos = apostas + soma, jogo a jogo, das colunas
     que o bilhete não cobre naquele jogo vezes as apostas que cobrem os outros 13.
   A tabela "aposta máxima" do item 6.3.6 repete os números da aposta mínima (aparente erro de cópia do manual); aqui
   cada combinação tem o seu número calculado.
2. **Pelos percentuais do concurso atual:** os duplos e triplos postos pela regra do app (jogos de favorito mais
   fraco, stats.otimizacao_bilhete.distribuicao_por_regra), com o cálculo exato de stats.chances_bilhete. Otimista:
   os percentuais são mais confiantes que a realidade.
3. **O que aconteceu de fato:** a mesma regra nos concursos passados (stats.calibracao_bilhete.frequencia_por_custo).
"""
from fractions import Fraction

import config
from stats.chances_bilhete import medidas_do_bilhete
from stats.otimizacao_bilhete import distribuicao_por_regra

COLUNAS = ("1", "X", "2")


def _apostas(duplos: int, triplos: int) -> int:
    return 2**duplos * 3**triplos


def motivo_invalida(duplos: int, triplos: int, jogos: int = config.JOGOS_POR_CONCURSO) -> str | None:
    """Por que a combinação não pode ser jogada, ou None se pode."""
    if duplos < 0 or triplos < 0:
        return "a quantidade de duplos e de triplos não pode ser negativa"
    if duplos + triplos > jogos:
        return f"o concurso tem {jogos} jogos: não cabem {duplos + triplos} duplos e triplos"
    if duplos + triplos == 0:
        return "o volante exige ao menos um duplo ou triplo (aposta mínima de 1 duplo, 2 apostas)"
    if _apostas(duplos, triplos) > config.BILHETE_MAX_APOSTAS:
        return (f"{_apostas(duplos, triplos)} apostas passam do máximo oficial de {config.BILHETE_MAX_APOSTAS} "
                "(5 duplos e 3 triplos)")
    return None


def combinacoes_validas(jogos: int = config.JOGOS_POR_CONCURSO) -> list[tuple[int, int]]:
    """(duplos, triplos) válidos, por triplos e depois por duplos, como nas tabelas da CAIXA."""
    return [(d, t) for t in range(jogos + 1) for d in range(jogos + 1 - t) if motivo_invalida(d, t, jogos) is None]


def valor(duplos: int, triplos: int) -> dict:
    apostas = _apostas(duplos, triplos)
    return {"duplos": duplos, "triplos": triplos, "apostas": apostas, "valor": apostas * config.PRECO_APOSTA_LOTECA}


def tabela_de_valores() -> list[dict]:
    """As combinações válidas com apostas e valor, em dois grupos como no CAIXA Informa: 'ate_1_triplo' e
    '2_ou_mais_triplos'."""
    return [{**valor(d, t), "grupo": "ate_1_triplo" if t <= 1 else "2_ou_mais_triplos"} for d, t in combinacoes_validas()]


def uma_em(total: int, casos: int) -> str:
    """'1 em 2.391.485' com arredondamento para cima na metade, como nas tabelas da CAIXA (4.782.969 / 2)."""
    if casos <= 0:
        return "impossível"
    inteiro = int(Fraction(total, casos) + Fraction(1, 2))
    return "1 em " + f"{inteiro:,}".replace(",", ".")


def chances_metodo_caixa(duplos: int, triplos: int, jogos: int = config.JOGOS_POR_CONCURSO) -> dict:
    """Contagem exata, com cada resultado valendo 1 em 3 (ver o docstring do módulo)."""
    motivo = motivo_invalida(duplos, triplos, jogos)
    if motivo:
        raise ValueError(motivo)
    apostas = _apostas(duplos, triplos)
    tamanhos = [2] * duplos + [3] * triplos + [1] * (jogos - duplos - triplos)
    casos_premiar = apostas + sum((3 - k) * (apostas // k) for k in tamanhos)
    total = 3**jogos
    return {
        "duplos": duplos, "triplos": triplos, "apostas": apostas, "total_resultados": total,
        "casos_14": apostas, "casos_13_caixa": apostas * 2 * jogos, "casos_premiar": casos_premiar,
        "chance_14": apostas / total, "chance_13_caixa": apostas * 2 * jogos / total, "chance_premiar": casos_premiar / total,
    }


def chances_pelos_percentuais(pcts: list[dict], duplos: int, triplos: int) -> dict:
    """Os duplos e triplos postos pela regra do app sobre os percentuais do concurso; medidas exatas do bilhete."""
    motivo = motivo_invalida(duplos, triplos, len(pcts))
    if motivo:
        raise ValueError(motivo)
    marcacoes = distribuicao_por_regra(pcts, duplos, triplos)
    return {"marcacoes": marcacoes, **medidas_do_bilhete(pcts, marcacoes)}


def tabela_de_chances(pcts: list[dict] | None, historico: dict[tuple[int, int], dict | None] | None) -> list[dict]:
    """Uma linha por combinação válida com as três leituras. `pcts`: percentuais dos 14 jogos do concurso atual
    (None se não houver concurso completo); `historico`: {(duplos, triplos): frequencia_por_custo(...)}."""
    linhas = []
    for d, t in combinacoes_validas():
        linha = {**valor(d, t), "caixa": chances_metodo_caixa(d, t), "percentuais": None, "historico": None}
        if pcts and len(pcts) == config.JOGOS_POR_CONCURSO:
            linha["percentuais"] = chances_pelos_percentuais(pcts, d, t)
        if historico:
            linha["historico"] = historico.get((d, t))
        linhas.append(linha)
    return linhas
