"""Testes do backtest walk-forward. O mais importante é `test_nao_ve_o_futuro`:
prova, com um jogo fabricado que só faria sentido em amostra pequena, que a
previsão de um concurso não muda quando o futuro muda -- ou seja, não há
vazamento temporal (o risco 'Crítica' apontado no parecer de 28/09/2026)."""
import pytest

from stats.backtest import (
    ModeloHistorico,
    acertos_por_concurso,
    brier,
    calibracao,
    comparar_pareado,
    escolha,
    metricas,
    prever_walk_forward,
)


def _jogo(id_jogo, concurso, num, casa, fora, gc, gf):
    resultado = "1" if gc > gf else "2" if gc < gf else "X"
    return {"id": id_jogo, "concurso_numero": concurso, "num_jogo": num, "casa_id": casa, "fora_id": fora,
            "gols_casa": gc, "gols_fora": gf, "resultado": resultado}


def test_nao_ve_o_futuro_jogo_de_concurso_anterior_nao_muda_com_o_que_vem_depois():
    base = [_jogo(i, c, 1, 1, 2, 1, 0) for i, c in enumerate(range(1, 6), start=1)]
    previsoes_sem_futuro = prever_walk_forward(base, aquecimento_concursos=2)
    futuro = base + [_jogo(100, 6, 1, 1, 2, 0, 5)]  # resultado oposto, concurso seguinte
    previsoes_com_futuro = prever_walk_forward(futuro, aquecimento_concursos=2)
    for id_jogo in previsoes_sem_futuro:
        assert previsoes_com_futuro[id_jogo]["atual"] == previsoes_sem_futuro[id_jogo]["atual"], id_jogo


def test_aquecimento_deixa_de_fora_os_primeiros_concursos():
    jogos = [_jogo(i, c, 1, 1, 2, 1, 0) for i, c in enumerate(range(1, 5), start=1)]
    previsoes = prever_walk_forward(jogos, aquecimento_concursos=2)
    assert sorted(p["concurso"] for p in previsoes.values()) == [3, 4]


def test_modelo_historico_cai_na_frequencia_global_com_amostra_pequena():
    modelo = ModeloHistorico()
    for i in range(3):
        modelo.aprender(_jogo(i, i, 1, 1, 2, 1, 0))
    previsao = modelo.prever(1, 2)
    assert previsao["origem"] == "frequencia_global"
    assert previsao["percentuais"]["1"] == pytest.approx(100.0)


def test_modelo_historico_usa_poisson_com_amostra_suficiente():
    modelo = ModeloHistorico()
    for i in range(6):
        modelo.aprender(_jogo(i, i, 1, 1, 2, 2, 0))
        modelo.aprender(_jogo(100 + i, i, 2, 2, 1, 0, 2))
    previsao = modelo.prever(1, 2)
    assert previsao["origem"] == "poisson" and previsao["percentuais"]["1"] > 50


def test_escolha_desempata_pela_ordem_1_x_2():
    assert escolha({"1": 40.0, "X": 40.0, "2": 20.0}) == "1"
    assert escolha({"1": 10.0, "X": 10.0, "2": 80.0}) == "2"


def test_brier_zero_quando_acerta_com_certeza_absoluta():
    assert brier({"1": 100.0, "X": 0.0, "2": 0.0}, "1") == pytest.approx(0.0)
    assert brier({"1": 0.0, "X": 0.0, "2": 100.0}, "1") == pytest.approx(2.0)


def test_metricas_com_lista_vazia_nao_quebra():
    assert metricas([]) == {"n": 0}


def test_comparar_pareado_detecta_modelo_pior_com_significancia():
    pior = [({"1": 10.0, "X": 10.0, "2": 80.0}, "1")] * 200
    melhor = [({"1": 80.0, "X": 10.0, "2": 10.0}, "1")] * 200
    resultado = comparar_pareado(pior, melhor)
    assert resultado["veredito"] == "pior que a referência" and resultado["diferenca"] > 0


def test_comparar_pareado_sem_diferenca_quando_os_modelos_sao_iguais():
    pares = [({"1": 50.0, "X": 30.0, "2": 20.0}, "1")] * 10
    assert comparar_pareado(pares, pares)["veredito"] == "sem diferença perceptível"


def test_calibracao_perfeita_quando_previsto_igual_observado():
    pares = [({"1": 100.0, "X": 0.0, "2": 0.0}, "1")] * 5 + [({"1": 0.0, "X": 100.0, "2": 0.0}, "2")] * 5
    faixas = {f["faixa"]: f for f in calibracao(pares)}
    alta = faixas["90% a 100%"]
    assert alta["n"] == 10 and alta["previsto"] == pytest.approx(100.0)


def test_acertos_por_concurso_so_conta_concurso_com_os_14_jogos():
    jogos = {i: {"num_jogo": (i % 14) + 1, "resultado": "1"} for i in range(28)}
    previsoes = {i: {"concurso": 1 if i < 14 else 2, "atual": {"1": 90.0, "X": 5.0, "2": 5.0}} for i in range(28)}
    resultado = acertos_por_concurso(jogos, previsoes)
    assert resultado["concursos"] == 2 and resultado["media"]["sempre_mandante"] == pytest.approx(14.0)
