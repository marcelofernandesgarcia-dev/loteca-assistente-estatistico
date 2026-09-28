import config
from stats.bilhete import montar_bilhete
from stats.fechamento import calcular


def _grade(n=14, favorito=(50.0, 25.0, 25.0)):
    return [dict(zip(("1", "X", "2"), favorito)) for _ in range(n)]


def test_bilhete_minimo_tem_um_duplo_mesmo_com_orcamento_menor_que_4():
    resultado = montar_bilhete(_grade(), orcamento=2.0)
    assert resultado["duplos"] == 1 and resultado["triplos"] == 0
    assert resultado["apostas"] == 2 and resultado["custo"] == 4.0


def test_nunca_passa_do_maximo_oficial_sem_orcamento():
    resultado = montar_bilhete(_grade(favorito=(34.0, 33.0, 33.0)))
    assert resultado["apostas"] <= config.BILHETE_MAX_APOSTAS
    assert resultado["apostas"] == calcular(resultado["triplos"], resultado["duplos"])["apostas"]


def test_respeita_o_orcamento():
    for orcamento in (4.0, 16.0, 64.0, 200.0, 1000.0):
        resultado = montar_bilhete(_grade(favorito=(40.0, 30.0, 30.0)), orcamento=orcamento)
        assert resultado["custo"] <= max(orcamento, 4.0)


def test_duplos_vao_para_os_jogos_mais_incertos():
    grade = _grade(favorito=(80.0, 12.0, 8.0))
    grade[5] = {"1": 36.0, "X": 33.0, "2": 31.0}
    resultado = montar_bilhete(grade, orcamento=4.0)
    assert len(resultado["marcacoes"][5]) == 2
    assert all(len(m) == 1 for i, m in enumerate(resultado["marcacoes"]) if i != 5)


def test_marca_as_colunas_de_maior_percentual():
    grade = _grade(favorito=(20.0, 30.0, 50.0))
    resultado = montar_bilhete(grade, orcamento=4.0)
    marcada = next(m for m in resultado["marcacoes"] if len(m) == 2)
    assert marcada == ["2", "X"]


def test_mais_orcamento_nunca_reduz_a_probabilidade_de_cobertura():
    grade = _grade(favorito=(45.0, 30.0, 25.0))
    anterior = 0.0
    for orcamento in (4.0, 8.0, 32.0, 128.0, 512.0, 1728.0):
        prob = montar_bilhete(grade, orcamento=orcamento)["prob_todos_acertos"]
        assert prob >= anterior
        anterior = prob
