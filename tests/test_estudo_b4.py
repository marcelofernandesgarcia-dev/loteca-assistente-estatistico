"""Item B4 do plano v2: regras para o único duplo ou triplo."""
import pytest

from stats.estudo_b4 import acertos, escolher, estudar


def _j(pfav, cobertura, resultado="1"):
    resto = (100.0 - pfav) / 2
    return {"p": {"1": pfav, "X": resto, "2": resto}, "cobertura": cobertura, "resultado": resultado}


JOGOS = [_j(70, "completa"), _j(40, "completa"), _j(48, "parcial"), _j(55, "baixa"), _j(65, "selecoes")]


def test_regras_escolhem_o_jogo_certo():
    assert escolher(JOGOS, "atual") == 1  # 40%: o mais incerto
    assert escolher(JOGOS, "cobertura") == 2  # o mais incerto entre parcial e baixa
    assert escolher(JOGOS, "mista") == 2  # entre os 3 mais incertos (40, 48, 55), o de pouca cobertura mais incerto
    so_completos = [_j(60, "completa"), _j(45, "completa")]
    assert escolher(so_completos, "cobertura") == escolher(so_completos, "atual") == 1


def test_acertos_com_duplo_e_triplo():
    terceiro = {"p": {"1": 50.0, "X": 20.0, "2": 30.0}, "cobertura": "parcial", "resultado": "2"}
    jogos = [_j(40, "completa", resultado="X"), _j(70, "completa", resultado="1"), terceiro]
    assert acertos(jogos, 0) == 2  # 40% < 45%: triplo no jogo 0 acerta; jogo 1 acerta; jogo 2 (seco no 1) erra
    assert acertos(jogos, 2) == 2  # duplo 1-2 no jogo 2 acerta; jogo 0 (seco no 1) erra; jogo 1 acerta


def test_estudo_compara_com_a_regra_atual():
    concursos = [{"numero": n, "ano": 2020, "jogos": JOGOS} for n in range(20)]
    r = estudar(concursos)
    assert r["concursos"] == 20 and r["outro_jogo"]["atual"] == 0 and r["outro_jogo"]["cobertura"] == 20
    assert {c["regra"] for c in r["comparacoes"]} == {"cobertura", "mista"}
    assert r["media"]["atual"] == pytest.approx(5.0)  # todos os resultados são "1": acerta tudo
    assert estudar([]) is None
