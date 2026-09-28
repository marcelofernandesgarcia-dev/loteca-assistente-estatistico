import pytest

import config
from stats.bilhete import montar_bilhete


def _grade(n=14, favorito=(60.0, 25.0, 15.0)):
    return [dict(zip(("1", "X", "2"), favorito)) for _ in range(n)]


def test_so_um_jogo_tem_mais_de_uma_coluna():
    grade = _grade()
    grade[4] = {"1": 42.0, "X": 30.0, "2": 28.0}
    resultado = montar_bilhete(grade)
    multiplos = [i for i, m in enumerate(resultado["marcacoes"]) if len(m) > 1]
    assert multiplos == [4] == [resultado["jogo_multiplo"]]


def test_favorito_abaixo_do_limiar_vira_triplo():
    grade = _grade()
    grade[2] = {"1": 36.0, "X": 33.0, "2": 31.0}
    resultado = montar_bilhete(grade)
    assert resultado["marcacoes"][2] == ["1", "2", "X"]
    assert (resultado["duplos"], resultado["triplos"], resultado["apostas"], resultado["custo"]) == (0, 1, 3, 6.0)


def test_favorito_acima_do_limiar_vira_duplo_com_as_duas_maiores_colunas():
    grade = _grade(favorito=(70.0, 20.0, 10.0))
    grade[7] = {"1": 20.0, "X": 30.0, "2": 50.0}
    resultado = montar_bilhete(grade)
    assert resultado["marcacoes"][7] == ["2", "X"]
    assert (resultado["duplos"], resultado["triplos"], resultado["apostas"], resultado["custo"]) == (1, 0, 2, 4.0)


def test_limiar_exato_e_duplo(monkeypatch):
    monkeypatch.setattr(config, "SUGESTAO_LIMIAR_DUPLO", 45.0)
    grade = _grade()
    grade[0] = {"1": 45.0, "X": 30.0, "2": 25.0}
    assert len(montar_bilhete(grade)["marcacoes"][0]) == 2


def test_probabilidade_de_cobertura_e_o_produto_das_coberturas():
    grade = _grade(n=14, favorito=(50.0, 30.0, 20.0))
    resultado = montar_bilhete(grade)
    esperado = (0.5**13) * 0.8
    assert resultado["prob_todos_acertos"] == pytest.approx(esperado)
