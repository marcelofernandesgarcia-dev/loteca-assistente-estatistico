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


# --- validar_volante (card 3 com 3 quadrados por jogo) ---
from stats.bilhete import validar_volante


def test_volante_completo_com_um_duplo_pode_salvar():
    marcacoes = [["1"]] * 13 + [["1", "X"]]
    r = validar_volante(marcacoes)
    assert r["pode_salvar"] and r["problemas"] == []
    assert (r["marcados"], r["duplos"], r["triplos"], r["apostas"], r["custo"]) == (14, 1, 0, 2, 4.0)


def test_jogo_em_branco_bloqueia_e_nao_vira_coluna_1():
    marcacoes = [["1"]] * 12 + [[], ["1", "X", "2"]]
    r = validar_volante(marcacoes)
    assert not r["pode_salvar"]
    assert r["jogos_sem_marcacao"] == [13]
    assert "Falta marcar o(s) jogo(s) 13." in r["problemas"]
    assert r["marcados"] == 13 and r["apostas"] == 3  # jogo em branco não conta como coluna


def test_volante_todo_simples_exige_um_duplo_ou_triplo():
    r = validar_volante([["2"]] * 14)
    assert not r["pode_salvar"] and "ao menos um duplo ou triplo" in r["problemas"][0]


def test_volante_acima_do_maximo_oficial_e_bloqueado():
    marcacoes = [["1", "X"]] * 5 + [["1", "X", "2"]] * 4 + [["1"]] * 5  # 32 x 81 = 2.592
    r = validar_volante(marcacoes)
    assert r["apostas"] == 2592 and not r["pode_salvar"]
    assert any("864" in p for p in r["problemas"])


def test_volante_no_limite_exato_de_864_pode_salvar():
    marcacoes = [["1", "X"]] * 5 + [["1", "X", "2"]] * 3 + [["1"]] * 6
    r = validar_volante(marcacoes)
    assert r["apostas"] == 864 and r["pode_salvar"]


def test_volante_vazio_lista_todos_os_jogos():
    r = validar_volante([[] for _ in range(14)])
    assert r["jogos_sem_marcacao"] == list(range(1, 15)) and r["marcados"] == 0
