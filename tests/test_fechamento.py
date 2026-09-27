import csv

import pytest

import config
from stats.fechamento import calcular, consultar


def test_formula_bate_linha_a_linha_com_a_tabela_oficial():
    with open(config.BOLOES_OFICIAL_CSV_PATH, encoding="utf-8") as arquivo:
        leitor = csv.DictReader(arquivo, delimiter=";")
        for linha in leitor:
            triplos, duplos = int(linha["triplos"]), int(linha["duplos"])
            resultado = calcular(triplos, duplos)
            assert resultado["apostas"] == int(linha["apostas"]), linha
            assert resultado["valor_reais"] == pytest.approx(float(linha["valor_reais"]), abs=0.01)


def test_maximo_oficial_e_864_apostas():
    assert calcular(3, 5)["apostas"] == 864


def test_consultar_combinacao_conhecida():
    linha = consultar(3, 5)
    assert linha is not None
    assert linha["apostas"] == 864
    assert linha["valor_min_cota_reais"] == 34.56


def test_consultar_combinacao_fora_da_tabela_retorna_none():
    assert consultar(6, 6) is None
