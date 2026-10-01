"""stats/calibracao.py: calibração dos percentuais (E4). Dados sintéticos, sem rede e sem o banco real."""
import random

import numpy as np
import pytest

import config
from stats import calibracao as cal


def _probs_verdadeiras(rng, n):
    """Favorito entre 60% e 90%, o resto dividido ao acaso; coluna do favorito sorteada."""
    T = np.zeros((n, 3))
    for i in range(n):
        fav = rng.uniform(0.6, 0.9)
        resto = rng.uniform(0.3, 0.7) * (1 - fav)
        linha = [fav, resto, 1 - fav - resto]
        rng.shuffle(linha)
        T[i] = linha
    return T


def _afiar(T, potencia):
    A = T ** potencia
    return A / A.sum(axis=1, keepdims=True)


def _pct(linha):
    return {c: 100.0 * float(v) for c, v in zip(cal.COLUNAS, linha)}


def _registros(T, P, rng, origem="poisson", jogos_por_concurso=14):
    """Resultados sorteados pela verdade T; o 'app' informa P; frequência = média de T."""
    y = np.array([rng.choice(3, p=t) for t in T])
    freq = _pct(T.mean(axis=0))
    return [
        {"id": i, "concurso": 1 + i // jogos_por_concurso, "num_jogo": 1 + i % jogos_por_concurso,
         "resultado": cal.COLUNAS[y[i]], "origem": origem, "p": _pct(P[i]), "f": freq}
        for i in range(len(T))
    ]


def test_aplicar_sem_correcao_e_identidade_e_expoente_zero_iguala_as_colunas():
    P = np.array([[0.7, 0.2, 0.1], [0.5, 0.3, 0.2]])
    F = np.array([[0.45, 0.28, 0.27]] * 2)
    assert np.allclose(cal.aplicar(P, F, 1.0, 1.0), P)
    assert np.allclose(cal.aplicar(P, F, 0.0, 1.0), 1 / 3)
    assert np.allclose(cal.aplicar(P, F, 1.0, 0.0), F)
    assert np.allclose(cal.aplicar(P, F, 0.5, 0.6).sum(axis=1), 1.0)


def test_ajuste_reconhece_percentuais_confiantes_demais():
    rng = np.random.default_rng(1)
    T = _probs_verdadeiras(rng, 8000)
    P = _afiar(T, 2.0)  # o "app" eleva ao quadrado: confiante demais
    y = np.array([rng.choice(3, p=t) for t in T])
    expoente, mistura = cal.ajustar(P, np.tile(T.mean(axis=0), (len(T), 1)), y, "temperatura")
    assert mistura == 1.0 and 0.4 <= expoente <= 0.6  # o inverso do quadrado


def test_ajuste_nao_mexe_em_percentuais_ja_calibrados():
    rng = np.random.default_rng(2)
    T = _probs_verdadeiras(rng, 8000)
    y = np.array([rng.choice(3, p=t) for t in T])
    expoente, mistura = cal.ajustar(T, np.tile(T.mean(axis=0), (len(T), 1)), y, "temperatura_e_mistura")
    assert 0.9 <= expoente <= 1.1 and mistura >= 0.9


def test_ajuste_com_percentual_sem_informacao_vai_para_a_frequencia():
    rng = np.random.default_rng(3)
    n = 6000
    F = np.tile([0.47, 0.27, 0.26], (n, 1))
    y = rng.choice(3, size=n, p=F[0])
    ruido = rng.dirichlet([1, 1, 1], size=n)  # percentual que não tem relação com o resultado
    _, mistura = cal.ajustar(ruido, F, y, "mistura")
    assert mistura <= 0.15


def test_ajuste_sem_dados_ou_metodo_desconhecido():
    vazio = np.zeros((0, 3))
    assert cal.ajustar(vazio, vazio, np.zeros(0, dtype=int), "temperatura_e_mistura") == (1.0, 1.0)
    with pytest.raises(ValueError):
        cal.ajustar(np.ones((1, 3)) / 3, np.ones((1, 3)) / 3, np.array([0]), "inventado")


def test_calibracao_andando_no_tempo_nao_olha_o_futuro_e_respeita_o_minimo(monkeypatch):
    monkeypatch.setattr(config, "CALIBRACAO_MINIMO_JOGOS", {"poisson": 300})
    monkeypatch.setattr(config, "CALIBRACAO_REAJUSTE_A_CADA", 25)
    rng = np.random.default_rng(4)
    T = _probs_verdadeiras(rng, 14 * 100)
    registros = _registros(T, _afiar(T, 2.0), rng)
    Q, com_treino = cal.calibrar_andando_no_tempo(registros, "temperatura_e_mistura")
    concursos = np.array([r["concurso"] for r in registros])
    assert not com_treino[concursos <= 25].any()  # primeiro bloco: sem passado para treinar
    assert com_treino[concursos > 25].all()  # depois: 350+ jogos de treino
    assert np.allclose(Q[concursos <= 25], cal.como_matriz([r["p"] for r in registros])[concursos <= 25])
    # mudar resultados do futuro (concursos 76 em diante) não muda a correção dos concursos até 75
    alterados = [r | {"resultado": "2"} if r["concurso"] > 75 else r for r in registros]
    Q2, _ = cal.calibrar_andando_no_tempo(alterados, "temperatura_e_mistura")
    assert np.allclose(Q[concursos <= 75], Q2[concursos <= 75])


def test_distribuicao_de_acertos_valores_conhecidos():
    assert np.allclose(cal.distribuicao_de_acertos([0.5, 0.5]), [0.25, 0.5, 0.25])
    assert np.allclose(cal.distribuicao_de_acertos([1.0, 0.0]), [0.0, 1.0, 0.0])
    assert np.allclose(cal.distribuicao_de_acertos([]), [1.0])
    d = cal.distribuicao_de_acertos(np.linspace(0.3, 0.9, 14))
    assert len(d) == 15 and d.sum() == pytest.approx(1.0)


def test_marcar_bilhete_sorteado_respeita_duplos_e_triplos_e_e_reprodutivel():
    pcts = [{"1": 50.0, "X": 30.0, "2": 20.0}] * 14
    marcas = cal.marcar_bilhete(pcts, 3, 2, "sorteada", random.Random(9))
    tamanhos = sorted(len(m) for m in marcas)
    assert tamanhos.count(3) == 2 and tamanhos.count(2) == 3 and tamanhos.count(1) == 9
    assert marcas == cal.marcar_bilhete(pcts, 3, 2, "sorteada", random.Random(9))
    assert cal.marcar_bilhete(pcts, 1, 0, "regra", random.Random(1)).count(["1", "X"]) == 1
    with pytest.raises(ValueError):
        cal.marcar_bilhete(pcts, 1, 0, "inventado", random.Random(1))


def test_curva_de_calibracao_de_previsao_perfeita():
    Q = np.array([[1.0, 0.0, 0.0]] * 10)
    curva = cal.curva_de_calibracao(Q, np.zeros(10, dtype=int))
    assert {(round(c["previsto"], 2), round(c["observado"], 2)) for c in curva} == {(0.0, 0.0), (1.0, 1.0)}


def test_montar_registros_usa_elo_nas_selecoes_e_mantem_a_origem_do_resto():
    jogos = [{"id": 1, "num_jogo": 2, "resultado": "1"}, {"id": 2, "num_jogo": 1, "resultado": "X"}]
    b3 = {1: {"concurso": 10, "atual": {"1": 50.0, "X": 30.0, "2": 20.0}, "referencia": {"1": 45.0, "X": 28.0, "2": 27.0}, "origem": "poisson"},
          2: {"concurso": 10, "atual": {"1": 45.0, "X": 28.0, "2": 27.0}, "referencia": {"1": 45.0, "X": 28.0, "2": 27.0}, "origem": "frequencia_global"}}
    elo = {1: {"1": 70.0, "X": 20.0, "2": 10.0}}
    registros = cal.montar_registros(jogos, b3, elo)
    assert [r["id"] for r in registros] == [2, 1]  # ordem de concurso e número do jogo
    assert registros[1]["origem"] == "elo_selecoes" and registros[1]["p"]["1"] == 70.0
    assert registros[0]["origem"] == "frequencia_global"


def test_estudo_completo_aproxima_o_previsto_do_ocorrido_nos_bilhetes(monkeypatch):
    monkeypatch.setattr(config, "CALIBRACAO_MINIMO_JOGOS", {"poisson": 500})
    monkeypatch.setattr(config, "CALIBRACAO_REAJUSTE_A_CADA", 25)
    monkeypatch.setattr(config, "CALIBRACAO_REPETICOES_BOOTSTRAP", 200)
    rng = np.random.default_rng(5)
    T = _probs_verdadeiras(rng, 14 * 400)
    estudo = cal.estudar(_registros(T, _afiar(T, 2.0), rng))
    principal = next(c for c in estudo["comparacoes"] if c["metodo"] == cal.METODO_PRINCIPAL)
    assert principal["conclusao"] == "melhor que sem correção"
    assert estudo["metricas"][cal.METODO_PRINCIPAL]["perda_log"] < estudo["metricas"]["original"]["perda_log"]
    bilhete = next(b for b in estudo["bilhetes"] if (b["duplos"], b["triplos"], b["modo"]) == (1, 0, "regra"))
    erro_original = abs(bilhete["previsto_13_original"] - bilhete["feito_13"])
    erro_corrigido = abs(bilhete["previsto_13_corrigida"] - bilhete["feito_13"])
    assert bilhete["previsto_13_original"] > bilhete["feito_13"]  # a conta direta superestima
    assert erro_corrigido < erro_original / 2
    assert 0.4 <= estudo["parametros_finais"]["poisson"]["expoente"] <= 0.7


def test_estudo_com_percentuais_certos_nao_inventa_melhora(monkeypatch):
    monkeypatch.setattr(config, "CALIBRACAO_MINIMO_JOGOS", {"poisson": 500})
    monkeypatch.setattr(config, "CALIBRACAO_REPETICOES_BOOTSTRAP", 200)
    rng = np.random.default_rng(6)
    T = _probs_verdadeiras(rng, 14 * 300)
    estudo = cal.estudar(_registros(T, T, rng))
    principal = next(c for c in estudo["comparacoes"] if c["metodo"] == cal.METODO_PRINCIPAL)
    assert principal["conclusao"] != "melhor que sem correção"


def test_estudo_sem_registros_devolve_none():
    assert cal.estudar([]) is None
