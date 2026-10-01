"""stats/chances_bilhete.py: chance de um bilhete e de um conjunto de bilhetes. Conferido contra força bruta em
jogos pequenos e contra a conta Poisson-binomial já usada no app."""
import itertools
import math
import time

import numpy as np
import pytest

import config
from stats import chances_bilhete as cb
from stats.analise_palpite import chance_do_bilhete

COLUNAS = ("1", "X", "2")


def _pcts(n, semente=1):
    rng = np.random.default_rng(semente)
    saida = []
    for _ in range(n):
        p = rng.dirichlet([3, 2, 2]) * 100
        saida.append({"1": float(p[0]), "X": float(p[1]), "2": float(p[2])})
    return saida


def _forca_bruta(pcts, bilhetes):
    """Percorre cada resultado possível e conta, por bilhete, os acertos e as apostas que premiam (13+ no concurso de
    14, ou n-1 nos jogos de teste)."""
    n = len(pcts)
    minimo = n - 1
    total = {"qualquer_13": 0.0, "qualquer_14": 0.0, "dois_ou_mais_13": 0.0, "apostas_premiadas": [0.0] * len(bilhetes)}
    por_bilhete = [{"13": 0.0, "14": 0.0} for _ in bilhetes]
    for resultado in itertools.product(COLUNAS, repeat=n):
        prob = math.prod(pcts[i][r] / 100.0 for i, r in enumerate(resultado))
        faz13 = []
        for k, marcacoes in enumerate(bilhetes):
            acertos = sum(1 for m, r in zip(marcacoes, resultado) if r in m)
            faz13.append(acertos >= minimo)
            por_bilhete[k]["13"] += prob * (acertos >= minimo)
            por_bilhete[k]["14"] += prob * (acertos == n)
            premiadas = sum(1 for aposta in itertools.product(*marcacoes) if sum(a == r for a, r in zip(aposta, resultado)) >= minimo)
            total["apostas_premiadas"][k] += prob * premiadas
        total["qualquer_13"] += prob * any(faz13)
        total["qualquer_14"] += prob * any(sum(1 for m, r in zip(b, resultado) if r in m) == n for b in bilhetes)
        total["dois_ou_mais_13"] += prob * (sum(faz13) >= 2)
    return total, por_bilhete


MARCACOES_A = [["1"], ["1", "X"], ["2"], ["1", "X", "2"], ["X"]]
MARCACOES_B = [["1", "2"], ["1", "X"], ["X"], ["1"], ["X", "2"]]


def test_medidas_do_bilhete_batem_com_forca_bruta_e_com_a_conta_do_app():
    pcts = _pcts(5)
    m = cb.medidas_do_bilhete(pcts, MARCACOES_A)
    bruto, por = _forca_bruta(pcts, [MARCACOES_A])
    assert m["chance_14"] == pytest.approx(por[0]["14"])
    assert m["chance_13_ou_mais"] == pytest.approx(por[0]["13"])
    assert m["apostas_premiadas"]["esperadas"] == pytest.approx(bruto["apostas_premiadas"][0])
    assert m["apostas"] == 6 and m["custo"] == 12.0 and (m["duplos"], m["triplos"]) == (1, 1)
    assert sum(m["distribuicao"].values()) == pytest.approx(1.0)
    # mesma conta que o app já usa (Poisson-binomial), com as chances cobertas em %
    app = chance_do_bilhete([100 * c for c in m["cobertas"]])
    assert m["chance_14"] == pytest.approx(app["chance_todos"]) and m["chance_13_ou_mais"] == pytest.approx(app["chance_todos_menos_um_ou_mais"])


def test_apostas_que_premiam_em_cada_caso():
    m = cb.medidas_do_bilhete(_pcts(5), MARCACOES_A)  # tamanhos 1, 2, 1, 3, 1
    assert m["apostas_premiadas"]["se_acertar_todos"] == {"com_14": 1, "com_13": 1 + 2}  # (2-1) + (3-1)
    assert m["apostas_premiadas"]["se_errar_exatamente_um"] == {"minimo": 1, "maximo": 3}


def test_bilhete_so_de_simples_nao_tem_aposta_extra():
    m = cb.medidas_do_bilhete(_pcts(5), [["1"]] * 5)
    assert m["apostas"] == 1 and m["apostas_premiadas"]["se_acertar_todos"] == {"com_14": 1, "com_13": 0}


def test_ganho_de_cada_multiplo_remove_a_coluna_de_menor_percentual_e_mostra_o_custo():
    pcts = [{"1": 60.0, "X": 25.0, "2": 15.0}] * 4
    ganhos = cb.ganho_de_cada_multiplo(pcts, [["1", "X"], ["1"], ["1", "X", "2"], ["2"]])
    assert [g["indice"] for g in ganhos] == [0, 2]
    duplo, triplo = ganhos
    assert duplo["coluna_acrescentada"] == "X" and (duplo["de"], duplo["para"]) == (2, 1)
    assert triplo["coluna_acrescentada"] == "2" and (triplo["de"], triplo["para"]) == (3, 2)
    assert duplo["ganho_13"] > 0 and triplo["ganho_13"] > 0
    assert duplo["custo_extra"] == pytest.approx(2.0 * (6 - 3))  # 6 apostas com o duplo, 3 sem: R$ 6,00 a mais
    assert duplo["ganho_13_por_real"] == pytest.approx(duplo["ganho_13"] / duplo["custo_extra"])
    assert cb.ganho_de_cada_multiplo(pcts, [["1"]] * 4) == []


def test_conjunto_bate_com_forca_bruta_em_todas_as_medidas():
    pcts = _pcts(5, 2)
    conjunto = [{"id": "a", "marcacoes": MARCACOES_A}, {"id": "b", "marcacoes": MARCACOES_B}]
    m = cb.medidas_do_conjunto(pcts, conjunto)
    bruto, por = _forca_bruta(pcts, [MARCACOES_A, MARCACOES_B])
    assert m["chance_13_ou_mais"] == pytest.approx(bruto["qualquer_13"])
    assert m["chance_14"] == pytest.approx(bruto["qualquer_14"])
    assert m["chance_dois_ou_mais_bilhetes_13"] == pytest.approx(bruto["dois_ou_mais_13"])
    for lido, esperado in zip(m["por_bilhete"], por):
        assert lido["chance_13_ou_mais"] == pytest.approx(esperado["13"]) and lido["chance_14"] == pytest.approx(esperado["14"])
    assert m["apostas"] == 6 + 8 and m["custo"] == 28.0


def test_conjunto_de_um_bilhete_e_igual_a_medida_do_bilhete():
    pcts = _pcts(5, 3)
    um = cb.medidas_do_conjunto(pcts, [{"id": 1, "marcacoes": MARCACOES_A}])
    sozinho = cb.medidas_do_bilhete(pcts, MARCACOES_A)
    assert um["chance_13_ou_mais"] == pytest.approx(sozinho["chance_13_ou_mais"]) and um["chance_14"] == pytest.approx(sozinho["chance_14"])
    assert um["por_bilhete"][0]["acrescenta_13"] == pytest.approx(sozinho["chance_13_ou_mais"])
    assert um["pares"] == [] and um["apostas_repetidas"] == 0


def test_bilhetes_iguais_repetem_todas_as_apostas_e_nao_acrescentam_nada():
    pcts = _pcts(5, 4)
    m = cb.medidas_do_conjunto(pcts, [{"id": 1, "marcacoes": MARCACOES_A}, {"id": 2, "marcacoes": MARCACOES_A}])
    sozinho = cb.medidas_do_bilhete(pcts, MARCACOES_A)
    assert m["chance_13_ou_mais"] == pytest.approx(sozinho["chance_13_ou_mais"])  # o segundo não acrescenta chance
    assert m["apostas_repetidas"] == 6 and m["custo_repetido"] == 12.0
    assert m["por_bilhete"][1]["acrescenta_13"] == pytest.approx(0.0, abs=1e-12)
    assert m["pares"][0]["apostas_em_comum"] == 6 and m["pares"][0]["sobreposicao_13"] == pytest.approx(1.0)


def test_apostas_distintas_batem_com_a_uniao_enumerada():
    a = [["1", "X"], ["1"], ["2", "X"], ["1"]]
    b = [["1"], ["1", "X"], ["2"], ["1", "2"]]
    c = [["X"], ["1"], ["2", "X"], ["1", "X"]]
    uniao = set(itertools.product(*a)) | set(itertools.product(*b)) | set(itertools.product(*c))
    assert cb._apostas_distintas([a, b, c]) == len(uniao)
    assert cb._apostas_em_comum(a, b) == len(set(itertools.product(*a)) & set(itertools.product(*b)))


def test_dois_bilhetes_que_dividem_a_mesma_cobertura_nao_ganham_chance_sobre_um_so():
    """Os dois bilhetes de 2 apostas cobrem juntos o mesmo que um bilhete de 4 apostas com dois duplos."""
    pcts = _pcts(5, 5)
    quatro = [["1", "X"], ["1", "2"], ["X"], ["1"], ["2"]]
    b1 = [["1", "X"], ["1"], ["X"], ["1"], ["2"]]
    b2 = [["1", "X"], ["2"], ["X"], ["1"], ["2"]]
    conjunto = cb.medidas_do_conjunto(pcts, [{"id": 1, "marcacoes": b1}, {"id": 2, "marcacoes": b2}])
    unico = cb.medidas_do_bilhete(pcts, quatro)
    assert conjunto["apostas_repetidas"] == 0
    # mesmo conjunto de resultados cobertos que o bilhete de 4 apostas, mas "faz 13" por caminhos diferentes:
    # o bilhete de 4 apostas nunca é pior
    assert unico["chance_13_ou_mais"] >= conjunto["chance_13_ou_mais"] - 1e-12


def test_bilhete_unico_com_o_mesmo_dinheiro():
    pcts = _pcts(14, 6)
    u = cb.bilhete_unico_com_o_mesmo_dinheiro(pcts, 24.0)
    assert u["apostas"] == 12 and u["sobra"] == pytest.approx(0.0) and (u["duplos"], u["triplos"]) == (2, 1)
    assert cb.bilhete_unico_com_o_mesmo_dinheiro(pcts, 28.0)["sobra"] == pytest.approx(4.0)  # 14 apostas: cabe 12
    assert cb.bilhete_unico_com_o_mesmo_dinheiro(pcts, 3.0) is None  # abaixo do mínimo oficial (R$ 4,00)
    grande = cb.bilhete_unico_com_o_mesmo_dinheiro(pcts, 5000.0)
    assert grande["apostas"] <= config.BILHETE_MAX_APOSTAS  # respeita o máximo oficial


def test_conjunto_dos_14_jogos_roda_rapido_e_bate_com_a_conta_exata_de_cada_bilhete():
    pcts = _pcts(14, 7)
    marcas = [
        [["1"]] * 12 + [["1", "X"], ["2", "X"]],
        [["1", "X"]] + [["1"]] * 12 + [["X"]],
        [["X", "2"]] + [["1"]] * 11 + [["1", "2", "X"], ["2"]],
    ]
    inicio = time.perf_counter()
    m = cb.medidas_do_conjunto(pcts, [{"id": i, "marcacoes": mm} for i, mm in enumerate(marcas)])
    assert time.perf_counter() - inicio < 30  # 3^14 = 4,78 milhões de resultados
    for lido, mm in zip(m["por_bilhete"], marcas):
        exato = cb.medidas_do_bilhete(pcts, mm)
        assert lido["chance_13_ou_mais"] == pytest.approx(exato["chance_13_ou_mais"], abs=1e-9)
        assert lido["chance_14"] == pytest.approx(exato["chance_14"], abs=1e-9)
    assert max(p["chance_13_ou_mais"] for p in m["por_bilhete"]) <= m["chance_13_ou_mais"] <= sum(p["chance_13_ou_mais"] for p in m["por_bilhete"]) + 1e-12


def test_entradas_invalidas_dao_erro_claro():
    pcts = _pcts(5)
    with pytest.raises(ValueError, match="Cada jogo"):
        cb.medidas_do_bilhete(pcts, [["1"]] * 4)
    with pytest.raises(ValueError, match="Marcação inválida"):
        cb.medidas_do_bilhete(pcts, [["1"], ["Z"], ["1"], ["1"], ["1"]])
    with pytest.raises(ValueError, match="Marcação inválida"):
        cb.medidas_do_bilhete(pcts, [["1"], [], ["1"], ["1"], ["1"]])
    with pytest.raises(ValueError, match="Marcação inválida"):
        cb.medidas_do_bilhete(pcts, [["1", "1"], ["1"], ["1"], ["1"], ["1"]])
    with pytest.raises(ValueError, match="Sem jogos"):
        cb.medidas_do_bilhete([], [])
    with pytest.raises(ValueError, match="No máximo 14 jogos"):
        cb.medidas_do_bilhete(_pcts(15), [["1"]] * 15)
    with pytest.raises(ValueError, match="Sem bilhetes"):
        cb.medidas_do_conjunto(pcts, [])
    with pytest.raises(ValueError, match="No máximo 12 bilhetes"):
        cb.medidas_do_conjunto(pcts, [{"id": i, "marcacoes": [["1"]] * 5} for i in range(13)])


def test_percentual_que_nao_soma_100_e_normalizado_e_zero_nao_quebra():
    pcts = [{"1": 50.0, "X": 25.0, "2": 24.0}] * 5  # soma 99 por arredondamento
    m = cb.medidas_do_bilhete(pcts, [["1", "X", "2"]] * 5)
    assert m["chance_14"] == pytest.approx(1.0)  # cobrir as três colunas é certeza
    zerado = cb.medidas_do_bilhete([{"1": 0.0, "X": 0.0, "2": 0.0}] * 5, [["1"]] * 5)
    assert zerado["chance_14"] == 0.0
