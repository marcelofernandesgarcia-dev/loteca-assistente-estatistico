"""stats/backtest_loteca.py: teste B2 nos jogos da Loteca. Banco em memória sintético, sem rede."""
import sqlite3

import numpy as np
import pytest

import db
from stats import backtest_competicao as b2
from stats import backtest_loteca as bl
from tests.test_associacao import _temporada_sintetica

PREVISAO = {"1": 40.0, "X": 30.0, "2": 30.0}


@pytest.fixture()
def conexao():
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    c.executescript(db.SCHEMA)
    return c


def _inserir_temporada(conexao, partidas, serie, ano, deslocamento=0, primeiro_id=1):
    for i, p in enumerate(partidas, start=primeiro_id):
        conexao.execute(
            "INSERT INTO cbf_partidas (id_jogo, serie, ano, rodada, data_jogo, mandante_id, visitante_id, gols_mandante, gols_visitante, coletado_em)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'x')",
            (i + ano * 1000 + (0 if serie == "serie-a" else 500), serie, ano, p["rodada"], p["data_jogo"],
             p["mandante_id"] + deslocamento, p["visitante_id"] + deslocamento, p["gols_mandante"], p["gols_visitante"]),
        )


def _data_da_rodada(partidas, rodada):
    return next(p["data_jogo"] for p in partidas if p["rodada"] == rodada)


def _jogo(conexao, numero, casa, fora, data, resultado="1"):
    gols = {"1": (2, 0), "X": (1, 1), "2": (0, 2)}[resultado]
    conexao.execute(
        "INSERT INTO jogos (concurso_numero, num_jogo, casa_id, fora_id, gols_casa, gols_fora, resultado, data_jogo, situacao)"
        " VALUES (?, 1, ?, ?, ?, ?, ?, ?, 'normal')", (numero, casa, fora, gols[0], gols[1], resultado, data),
    )
    return conexao.execute("SELECT last_insert_rowid()").fetchone()[0]


@pytest.fixture()
def cenario(conexao):
    rng = np.random.default_rng(5)
    a2019, a2020, b2020 = _temporada_sintetica(rng, 2019, 8), _temporada_sintetica(rng, 2020, 8), _temporada_sintetica(rng, 2020, 4)
    _inserir_temporada(conexao, a2019, "serie-a", 2019)
    _inserir_temporada(conexao, a2020, "serie-a", 2020)
    _inserir_temporada(conexao, b2020, "serie-b", 2020, deslocamento=100)
    for participante, cod in [(i, i - 1) for i in range(1, 9)] + [(9, 100)]:
        conexao.execute("INSERT INTO mapa_cbf_participante (participante_id, cod_time, metodo) VALUES (?, ?, 'uf+nome')", (participante, cod))
    ids = {
        "valido_1": _jogo(conexao, 1, 1, 2, _data_da_rodada(a2020, 10)),
        "valido_2": _jogo(conexao, 2, 3, 4, _data_da_rodada(a2020, 12), "X"),
        "cedo": _jogo(conexao, 3, 1, 2, _data_da_rodada(a2020, 2)),
        "outra_serie": _jogo(conexao, 4, 1, 9, _data_da_rodada(a2020, 10)),
        "sem_pareamento": _jogo(conexao, 5, 99, 2, _data_da_rodada(a2020, 10)),
        "sem_data": _jogo(conexao, 6, 1, 2, None),
        "ano_sem_treino": _jogo(conexao, 7, 1, 2, _data_da_rodada(a2019, 10)),
        "sem_modelo_atual": _jogo(conexao, 8, 5, 6, _data_da_rodada(a2020, 10)),
    }
    atual = {ids[k]: {"atual": PREVISAO, "referencia": PREVISAO, "concurso": 0} for k in ("valido_1", "valido_2")}
    pesos = bl.pesos_por_ano(b2.carregar_amostra(conexao))
    return conexao, ids, atual, pesos, a2020


def test_temporada_por_data_conta_so_jogos_estritamente_antes_do_dia():
    partidas = [
        {"data_jogo": "2026-03-01", "mandante_id": 1, "visitante_id": 2, "gols_mandante": 2, "gols_visitante": 0},
        {"data_jogo": "2026-03-08", "mandante_id": 2, "visitante_id": 1, "gols_mandante": 1, "gols_visitante": 1},
        {"data_jogo": "2026-03-15", "mandante_id": 1, "visitante_id": 3, "gols_mandante": 0, "gols_visitante": 5},
    ]
    t = bl.TemporadaPorData(partidas)
    assert t.retrospecto(1, "2026-03-01") == (0, 0)  # o jogo do próprio dia não conta
    assert t.retrospecto(1, "2026-03-02") == (3, 1)
    assert t.retrospecto(1, "2026-03-15") == (4, 2)
    assert t.retrospecto(1, "2026-12-31") == (4, 3)
    assert t.retrospecto(99, "2026-12-31") == (0, 0)  # time desconhecido
    assert [p["data_jogo"] for p in t.conhecidas("2026-03-09")] == ["2026-03-01", "2026-03-08"]
    assert bl.TemporadaPorData([]).conhecidas("2026-01-01") == []
    assert bl.TemporadaPorData([{**partidas[0], "data_jogo": None}]).partidas == []  # sem data não entra


def test_funil_mostra_onde_cada_jogo_ficou_de_fora(cenario):
    conexao, _, atual, pesos, _ = cenario
    jogos, funil = bl.montar_jogos(conexao, atual, pesos)
    assert funil == {
        "apurados": 8, "com_data_em_ano_testavel": 6, "dois_clubes_pareados": 5,
        "mesma_serie": 4, "jogos_conhecidos": 3, "com_modelo_atual": 2,
    }
    assert sorted(j["concurso"] for j in jogos) == [1, 2]
    for j in jogos:
        for modelo in bl.MODELOS:
            assert sum(j["previsoes"][modelo].values()) == pytest.approx(100.0)
        assert j["serie"] == "serie-a" and j["ano"] == 2020


def test_resultado_dos_jogos_do_dia_e_depois_nao_altera_as_previsoes(cenario):
    conexao, ids, atual, pesos, a2020 = cenario
    antes = {j["id"]: j["previsoes"] for j in bl.montar_jogos(conexao, atual, pesos)[0]}
    data = _data_da_rodada(a2020, 10)
    conexao.execute("UPDATE cbf_partidas SET gols_mandante = 9, gols_visitante = 0 WHERE ano = 2020 AND data_jogo >= ?", (data,))
    depois = {j["id"]: j["previsoes"] for j in bl.montar_jogos(conexao, atual, pesos)[0]}
    assert depois[ids["valido_1"]]["retrospecto"] == antes[ids["valido_1"]]["retrospecto"]
    assert depois[ids["valido_1"]]["poisson"] == antes[ids["valido_1"]]["poisson"]


def test_sem_jogos_da_cbf_nada_e_testavel(conexao):
    jogos, funil = bl.montar_jogos(conexao, {}, {})
    assert jogos == [] and funil["apurados"] == 0
    assert bl.pesos_por_ano([]) == {}


def _jogos_previstos(n=600, semente=1):
    rng = np.random.default_rng(semente)
    verdadeira = {"1": 70.0, "X": 20.0, "2": 10.0}
    uniforme = {"1": 100 / 3, "X": 100 / 3, "2": 100 / 3}
    jogos = []
    for i in range(n):
        resultado = ["1", "X", "2"][rng.choice(3, p=[0.7, 0.2, 0.1])]
        jogos.append({
            "resultado": resultado, "cluster": f"concurso-{i // 5}", "ano": 2021 + i % 2,
            "previsoes": {"referencia": uniforme, "atual": uniforme, "retrospecto": verdadeira, "poisson": verdadeira},
        })
    return jogos


def test_resumir_reconhece_modelo_melhor_e_modelos_iguais():
    resumo = bl.resumir(_jogos_previstos())
    por_par = {(c["modelo"], c["contra"]): c for c in resumo["comparacoes"]}
    assert len(resumo["comparacoes"]) == len(bl.COMPARACOES) == 6
    assert por_par[("retrospecto", "referencia")]["conclusao"] == "melhor" and por_par[("poisson", "atual")]["conclusao"] == "melhor"
    assert por_par[("atual", "referencia")]["conclusao"] == "sem diferença perceptível"
    assert por_par[("poisson", "retrospecto")]["conclusao"] == "sem diferença perceptível"
    assert resumo["n"] == 600 and set(resumo["por_ano"]) == {2021, 2022}
    assert resumo["metricas"]["retrospecto"]["perda_log"] < resumo["metricas"]["referencia"]["perda_log"]


def test_resumir_reconhece_modelo_pior():
    jogos = _jogos_previstos()
    for o in jogos:
        o["previsoes"]["atual"] = {"1": 5.0, "X": 5.0, "2": 90.0}  # aposta errada com convicção
    por_par = {(c["modelo"], c["contra"]): c for c in bl.resumir(jogos)["comparacoes"]}
    assert por_par[("atual", "referencia")]["conclusao"] == "pior"


def test_resumir_sem_jogos_devolve_none():
    assert bl.resumir([]) is None
