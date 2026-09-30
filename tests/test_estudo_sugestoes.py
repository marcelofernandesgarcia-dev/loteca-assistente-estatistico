import random

from stats.estudo_sugestoes import (
    _veredito,
    acertos,
    avaliar_orcamento,
    avaliar_trocas,
    concursos_completos,
    distribuicao_aleatoria,
)

FAVORITO_CASA = {"1": 60.0, "X": 25.0, "2": 15.0}
EQUILIBRADO = {"1": 34.0, "X": 33.0, "2": 33.0}


def _concurso(resultados):
    pcts = [EQUILIBRADO] + [FAVORITO_CASA] * 13
    return list(zip(pcts, resultados))


def test_concursos_completos_so_com_14_jogos_na_ordem():
    jogos = [{"id": i, "num_jogo": 15 - i, "resultado": "1"} for i in range(1, 15)] + [{"id": 99, "num_jogo": 1, "resultado": "X"}]
    previsoes = {i: {"concurso": 10, "atual": {"1": float(i), "X": 0.0, "2": 0.0}} for i in range(1, 15)}
    previsoes[99] = {"concurso": 11, "atual": FAVORITO_CASA}
    completos = concursos_completos(jogos, previsoes)
    assert len(completos) == 1 and completos[0][0][0]["1"] == 14.0  # num_jogo 1 é o id 14


def test_acertos_e_aleatorio_respeita_o_orcamento():
    assert acertos([["1"], ["X", "2"]], ["1", "2"]) == 2
    marc = distribuicao_aleatoria([FAVORITO_CASA] * 14, 2, 1, random.Random(1))
    assert sorted(len(m) for m in marc)[-3:] == [2, 2, 3]


def test_orcamento_com_favoritos_certos_e_empate_no_jogo_equilibrado():
    concursos = [_concurso(["X"] + ["1"] * 13) for _ in range(5)]
    resumo = avaliar_orcamento(concursos, 0, 1)
    assert resumo["exato"]["fez_14"] == 5 and resumo["regra"]["fez_14"] == 5  # o triplo vai no jogo equilibrado
    assert resumo["exato_menos_regra"]["media"] == 0 and resumo["exato_igual_a_regra"] == 5


def test_trocas_recuperam_acertos_de_um_bilhete_sem_criterio():
    concursos = [_concurso(["X"] + ["1"] * 13) for _ in range(40)]
    resumo = avaliar_trocas(concursos, 1, 0, chance_contraria=0.5)
    assert resumo["com_sugestao"] > 0 and resumo["diferenca_media"] > 0 and resumo["perdeu"] == 0


def test_veredito():
    assert _veredito(0.5, 0.1) == "acerta mais"
    assert _veredito(-0.5, 0.1) == "acerta menos"
    assert _veredito(0.1, 0.1) == "sem diferença perceptível"
    assert _veredito(1.0, float("nan")) == "amostra insuficiente"
