"""Revisão pós-jogo e diagnóstico do concurso (itens D2 e D4 do plano v2, 07/10/2026)."""
import math

import pytest

from stats.revisao import diagnostico_do_concurso, frase_do_diagnostico, leitura_do_jogo, revisao_do_bilhete, surpresa

PCT = {"1": 60.0, "X": 25.0, "2": 15.0}


def test_surpresa_e_menos_log_da_chance_do_resultado():
    assert surpresa(PCT, "1") == pytest.approx(-math.log(0.60))
    assert surpresa(PCT, "2") > surpresa(PCT, "1")


@pytest.mark.parametrize("marcacoes, resultado, chave", [
    (["1"], "1", "acerto"),
    (["1"], "X", "erro"),
    (["1"], "2", "zebra"),  # 15% < limiar de zebra (25%)
    (["1", "X"], "X", "multiplo_util"),
    (["1", "X"], "1", "multiplo_dispensavel"),
    (["1", "X"], "2", "multiplo_nao_bastou"),
])
def test_leitura_de_cada_jogo(marcacoes, resultado, chave):
    assert leitura_do_jogo(PCT, marcacoes, resultado) == chave


def test_revisao_compara_o_app_com_a_frequencia_simples():
    jogos = [{"num_jogo": 1, "pct": PCT, "marcacoes": ["1"], "resultado": "1", "sugestao": ["1"]},
             {"num_jogo": 2, "pct": PCT, "marcacoes": ["1", "X"], "resultado": "2", "sugestao": ["1", "X", "2"]}]
    r = revisao_do_bilhete(jogos, {"1": 47.0, "X": 26.0, "2": 27.0})
    assert [l["leitura"] for l in r["jogos"]] == ["acerto", "multiplo_nao_bastou"]
    assert [l["sugestao_acertou"] for l in r["jogos"]] == [True, True]
    assert r["perda_log_app"] == pytest.approx((-math.log(0.60) - math.log(0.15)) / 2)
    assert r["perda_log_referencia"] == pytest.approx((-math.log(0.47) - math.log(0.27)) / 2)
    assert r["zebras"] == 1


def _c(numero, ano, ganhadores, por_milhao):
    return {"numero": numero, "ano": ano, "ganhadores_14": ganhadores, "ganhadores_por_milhao": por_milhao}


CONCURSOS = ([_c(n, 2025, 0, 0.0) for n in range(1, 5)] + [_c(n, 2025, 1, float(n)) for n in range(5, 11)]
             + [_c(11, 2026, 0, 0.0), _c(12, 2026, 3, 2.0), _c(13, 2026, 257, 96.3)])


def test_diagnostico_por_posicao_entre_os_concursos_com_ganhador():
    facil = diagnostico_do_concurso(CONCURSOS, 13)
    assert facil["classe"] == "fácil" and facil["maior_do_ano"] and facil["concursos_no_ano"] == 3
    assert diagnostico_do_concurso(CONCURSOS, 12)["classe"] == "difícil"  # 2,0 por milhão: abaixo do 1º tercil
    assert diagnostico_do_concurso(CONCURSOS, 11)["classe"] == "acumulou"
    assert diagnostico_do_concurso(CONCURSOS, 999) is None


def test_frase_do_concurso_facil_explica_que_erro_nao_e_azar_e_nao_recalibra():
    frase = frase_do_diagnostico(diagnostico_do_concurso(CONCURSOS, 13))
    assert frase.startswith("Concurso fácil: 96,3 ganhadores de 14 por milhão arrecadado (257 ganhadores), o maior do ano.")
    assert "não azar" in frase and "só com todos os concursos" in frase
    assert "ninguém fez 14" in frase_do_diagnostico(diagnostico_do_concurso(CONCURSOS, 11))
