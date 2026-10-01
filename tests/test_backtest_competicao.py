"""stats/backtest_competicao.py: teste B2 dos modelos de 1/X/2. Dados sintéticos, sem rede."""
import numpy as np
import pytest

import config
from stats import backtest_competicao as b2
from tests.test_associacao import _partida, _temporada_sintetica


def test_logistica_recupera_as_probabilidades_verdadeiras():
    rng = np.random.default_rng(1)
    n = 20000
    X = np.column_stack([np.ones(n), rng.uniform(0, 3, n), rng.uniform(0, 3, n)])
    W_verdadeiro = np.array([[0.2, -0.1], [-0.4, 0.5], [0.3, -0.6]])
    P = b2.probabilidades_logistica(X, W_verdadeiro)
    y = np.array([rng.choice(3, p=linha) for linha in P])
    W = b2.ajustar_logistica(X, y)
    P_estimado = b2.probabilidades_logistica(X, W)
    assert np.allclose(P_estimado.sum(axis=1), 1.0)
    assert np.abs(P_estimado - P).mean() < 0.01


def test_logistica_com_uma_so_classe_nao_quebra():
    X = np.column_stack([np.ones(50), np.linspace(0, 3, 50), np.linspace(3, 0, 50)])
    P = b2.probabilidades_logistica(X, b2.ajustar_logistica(X, np.zeros(50, dtype=int)))
    assert np.isfinite(P).all() and P[:, 0].min() > 0.9  # sem erro numérico, e a classe única domina


def _liga_pequena():
    """4 times, 10 rodadas; time 1 vence sempre. Jogo da rodada 3 (3 x 4) é disputado só depois da rodada 8."""
    partidas, rodada = [], 0
    pares = [(1, 2, 3, 4), (3, 4, 1, 2)]
    for r in range(1, 11):
        a, b, c, d = pares[r % 2]
        partidas.append(_partida(r, a, b, 2, 0) | {"data_jogo": f"2026-02-{r:02d}"})
        partidas.append(_partida(r, c, d, 1, 1) | {"data_jogo": f"2026-02-{r:02d}"})
    return partidas


def test_jogo_so_entra_quando_os_dois_times_tem_o_minimo_de_jogos_conhecidos():
    amostra = b2.amostra_da_temporada(_liga_pequena(), "serie-a", 2026, com_poisson=False)
    assert amostra and min(int(o["cluster"].split("-")[-1]) for o in amostra) == 6  # 5 jogos conhecidos antes


def test_jogo_adiado_nao_entra_no_conhecimento_antes_de_ser_disputado():
    partidas = _liga_pequena()
    # o jogo 1 x 2 da rodada 2 (vitória de 1) é disputado só depois do início da rodada 9
    adiado = next(p for p in partidas if p["rodada"] == 2 and p["mandante_id"] in (1, 2))
    adiado["data_jogo"] = "2026-02-20"
    com_adiado = {o["cluster"]: o for o in b2.amostra_da_temporada(partidas, "serie-a", 2026, com_poisson=False)}
    sem_adiado = {o["cluster"]: o for o in b2.amostra_da_temporada(_liga_pequena(), "serie-a", 2026, com_poisson=False)}
    # na rodada 9 o jogo adiado ainda não aconteceu: o retrospecto do time 1 não pode contá-lo
    assert com_adiado["serie-a-2026-9"]["retro_casa"] != sem_adiado["serie-a-2026-9"]["retro_casa"] or \
        com_adiado["serie-a-2026-9"]["retro_fora"] != sem_adiado["serie-a-2026-9"]["retro_fora"]


def test_amostra_vazia_ou_sem_data_nao_gera_registro():
    assert b2.amostra_da_temporada([], "serie-a", 2026) == []
    sem_data = [p | {"data_jogo": None} for p in _liga_pequena()]
    assert b2.amostra_da_temporada(sem_data, "serie-a", 2026, com_poisson=False) == []


def test_prever_usa_so_anos_anteriores_e_o_primeiro_ano_so_treina():
    rng = np.random.default_rng(3)
    amostra = []
    for ano in (2019, 2020, 2021):
        amostra += b2.amostra_da_temporada(_temporada_sintetica(rng, ano, n_times=8), "serie-a", ano)
    previstos = b2.prever(amostra)
    assert previstos and {o["ano"] for o in previstos} == {2020, 2021}
    um = previstos[0]["previsoes"]
    for modelo in b2.MODELOS:
        assert sum(um[modelo].values()) == pytest.approx(100.0)
    # a referência de 2020 vem só de 2019: não muda se o resultado de 2021 mudar
    alterada = [o | {"resultado": "2"} if o["ano"] == 2021 else o for o in amostra]
    previstos_2 = b2.prever(alterada)
    ref_2020 = [o["previsoes"]["referencia"] for o in previstos if o["ano"] == 2020]
    ref_2020_alterada = [o["previsoes"]["referencia"] for o in previstos_2 if o["ano"] == 2020]
    assert ref_2020 == ref_2020_alterada


def test_prever_com_um_ano_ou_vazio_devolve_vazio():
    assert b2.prever([]) == []
    rng = np.random.default_rng(4)
    um_ano = b2.amostra_da_temporada(_temporada_sintetica(rng, 2019, n_times=8), "serie-a", 2019)
    assert b2.prever(um_ano) == []


def _jogos_com_previsoes(prob_a, prob_b, n=400, semente=1):
    """Resultados sorteados pelas probabilidades de A (modelo 'retrospecto'); B = 'referencia' uniforme."""
    rng = np.random.default_rng(semente)
    jogos = []
    for i in range(n):
        resultado = ["1", "X", "2"][rng.choice(3, p=prob_a)]
        jogos.append({
            "resultado": resultado, "cluster": f"r{i // 5}",
            "previsoes": {
                "retrospecto": dict(zip("1X2", (100 * np.array(prob_a)))),
                "referencia": dict(zip("1X2", (100 * np.array(prob_b)))),
                "poisson": dict(zip("1X2", (100 * np.array(prob_b)))),
            },
        })
    return jogos


def test_modelo_melhor_que_a_referencia_e_reconhecido():
    resumo = b2.resumir(_jogos_com_previsoes([0.7, 0.2, 0.1], [1 / 3, 1 / 3, 1 / 3]))
    comparacao = next(c for c in resumo["comparacoes"] if c["modelo"] == "retrospecto" and c["contra"] == "referencia")
    assert comparacao["conclusao"] == "melhor" and comparacao["perda_log"]["ic_inferior"] > 0 and comparacao["q"] < 0.05
    assert resumo["metricas"]["retrospecto"]["perda_log"] < resumo["metricas"]["referencia"]["perda_log"]


def test_modelos_iguais_nao_mostram_diferenca():
    resumo = b2.resumir(_jogos_com_previsoes([0.5, 0.3, 0.2], [0.5, 0.3, 0.2]))
    comparacao = next(c for c in resumo["comparacoes"] if c["modelo"] == "retrospecto" and c["contra"] == "referencia")
    assert comparacao["conclusao"] == "sem diferença perceptível" and comparacao["perda_log"]["media"] == pytest.approx(0.0, abs=1e-9)


def test_modelo_pior_e_reconhecido():
    # A = distribuição enganosa (aposta na casa); B = a verdadeira
    jogos = _jogos_com_previsoes([0.1, 0.2, 0.7], [0.1, 0.2, 0.7], n=400)
    for o in jogos:
        o["previsoes"]["retrospecto"] = {"1": 90.0, "X": 5.0, "2": 5.0}
    resumo = b2.resumir(jogos)
    comparacao = next(c for c in resumo["comparacoes"] if c["modelo"] == "retrospecto" and c["contra"] == "referencia")
    assert comparacao["conclusao"] == "pior"


def test_parametros_de_config_existem():
    assert config.B2_JOGOS_ANTERIORES_MINIMOS >= 1 and config.B2_REPETICOES_BOOTSTRAP >= 100
