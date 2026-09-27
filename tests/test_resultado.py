import pytest

from stats.resultado import calcular_resultado, classificar_participante


def test_mandante_vence():
    assert calcular_resultado(2, 1) == "1"


def test_visitante_vence():
    assert calcular_resultado(0, 3) == "2"


def test_empate():
    assert calcular_resultado(1, 1) == "X"


def test_placar_incompleto_levanta_erro():
    with pytest.raises(ValueError):
        calcular_resultado(None, 1)


def test_clube_brasileiro_tem_uf():
    assert classificar_participante("FLAMENGO", "RJ") == "clube"


def test_selecao_nacional_sem_uf_na_lista():
    assert classificar_participante("ALEMANHA", "") == "selecao"
    assert classificar_participante("Inglaterra", None) == "selecao"


def test_clube_estrangeiro_sem_uf_fora_da_lista():
    assert classificar_participante("BARCELONA", "") == "clube"
    assert classificar_participante("REAL MADRID", None) == "clube"
