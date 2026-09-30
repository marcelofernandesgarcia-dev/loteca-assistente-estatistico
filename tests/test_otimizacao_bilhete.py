import itertools
import math

import pytest

from stats.otimizacao_bilhete import (
    chance_de_todos,
    complexidade_do_jogo,
    distribuicao_por_regra,
    economias,
    melhor_distribuicao,
    trocas_de_um_passo,
)

FACIL = {"1": 70.0, "X": 20.0, "2": 10.0}
EQUILIBRADO = {"1": 36.0, "X": 33.0, "2": 31.0}
MEDIO = {"1": 50.0, "X": 30.0, "2": 20.0}
EMPATE_FORTE = {"1": 20.0, "X": 45.0, "2": 35.0}


def test_complexidade_por_regra_com_motivos():
    assert complexidade_do_jogo(FACIL)["nivel"] == "baixa"
    alta = complexidade_do_jogo(EQUILIBRADO, sem_base_propria=True)
    assert alta["nivel"] == "alta" and len(alta["motivos"]) == 3 and alta["margem"] == 3.0
    discorda = complexidade_do_jogo(FACIL, melhor_no_ano="fora")
    assert discorda["nivel"] == "media" and "vai pior no ano em curso" in discorda["motivos"][0]
    # Favorito empate: "melhor no ano" não se aplica.
    assert "ano em curso" not in " ".join(complexidade_do_jogo(EMPATE_FORTE, melhor_no_ano="casa")["motivos"])


def _forca_bruta(pcts, duplos, triplos):
    melhor = 0.0
    for escolha in itertools.product((1, 2, 3), repeat=len(pcts)):
        if escolha.count(2) != duplos or escolha.count(3) != triplos:
            continue
        chance = 1.0
        for p, k in zip(pcts, escolha):
            chance *= sum(sorted(p.values(), reverse=True)[:k]) / 100
        melhor = max(melhor, chance)
    return melhor


@pytest.mark.parametrize("duplos,triplos", [(1, 0), (0, 1), (2, 1), (1, 2), (0, 0)])
def test_melhor_distribuicao_bate_com_a_forca_bruta(duplos, triplos):
    pcts = [FACIL, EQUILIBRADO, MEDIO, EMPATE_FORTE, {"1": 55.0, "X": 25.0, "2": 20.0}]
    resultado = melhor_distribuicao(pcts, duplos, triplos)
    assert math.isclose(resultado["chance_todos"], _forca_bruta(pcts, duplos, triplos), rel_tol=1e-9)
    assert sum(len(m) == 2 for m in resultado["marcacoes"]) == duplos
    assert sum(len(m) == 3 for m in resultado["marcacoes"]) == triplos
    assert resultado["apostas"] == 2**duplos * 3**triplos


def test_melhor_distribuicao_recusa_o_que_nao_cabe():
    with pytest.raises(ValueError):
        melhor_distribuicao([FACIL], 1, 1)


def test_regra_poe_o_triplo_no_mais_incerto_e_nunca_supera_o_exato():
    pcts = [FACIL, EQUILIBRADO, MEDIO, EMPATE_FORTE]
    regra = distribuicao_por_regra(pcts, 1, 1)
    assert regra[1] == ["1", "X", "2"] and regra[3] == ["X", "2"] and regra[0] == ["1"]
    assert chance_de_todos(pcts, regra) <= melhor_distribuicao(pcts, 1, 1)["chance_todos"] + 1e-12


def test_trocas_sugerem_levar_o_duplo_para_o_jogo_equilibrado():
    pcts = [FACIL, EQUILIBRADO]
    trocas = trocas_de_um_passo(pcts, [["1", "X"], ["1"]], [7, 8])
    assert trocas[0]["jogos"] == [7, 8] and "levar o duplo do jogo 7 para o jogo 8" in trocas[0]["descricao"]
    assert trocas[0]["chance_depois"] > trocas[0]["chance_antes"]


def test_trocas_sugerem_trocar_coluna_de_zebra_e_nada_quando_ja_e_otimo():
    trocas = trocas_de_um_passo([MEDIO, FACIL], [["2"], ["1", "X"]])
    assert any("jogo 1: trocar 2 por 1" in t["descricao"] for t in trocas)
    otimo = melhor_distribuicao([FACIL, EQUILIBRADO], 1, 0)["marcacoes"]
    assert trocas_de_um_passo([FACIL, EQUILIBRADO], otimo) == []


def test_economias_ordena_pela_menor_perda_por_real_e_respeita_o_minimo_do_volante():
    pcts = [MEDIO, EQUILIBRADO, FACIL]
    saida = economias(pcts, [["1", "X"], ["1", "X", "2"], ["1"]])
    assert [e["jogo"] for e in saida][0] in (1, 2) and all(e["economia_reais"] > 0 for e in saida)
    assert saida == sorted(saida, key=lambda e: e["perda_por_real"])
    assert economias(pcts, [["1", "X"], ["1"], ["1"]]) == []  # único duplo: o volante exige ao menos um
