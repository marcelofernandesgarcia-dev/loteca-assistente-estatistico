"""Modelo da temporada da CBF em produção (itens B1 e B2 do plano v2, 07/10/2026). Banco SINTÉTICO: três
temporadas de uma "Série A" de 6 times fictícios, com placares sorteados por semente fixa."""
import datetime as dt
import random
import sqlite3

import pytest

import config
import db
from externo.percentual_final import percentuais_do_jogo
from stats import backtest_competicao as b2
from stats import backtest_loteca as bl
from stats import modelo_cbf

TIMES = [101, 102, 103, 104, 105, 106]


def _temporada(conexao, ano: int, sorteio: random.Random, serie: str = "serie-a") -> None:
    """Turno e returno; rodada r no dia 7*r a partir de 1º de março."""
    rodada, inicio = 0, dt.date(ano, 3, 1)
    confrontos = [(a, b) for a in TIMES for b in TIMES if a != b]
    sorteio.shuffle(confrontos)
    for i in range(0, len(confrontos), 3):
        rodada += 1
        for mandante, visitante in confrontos[i:i + 3]:
            conexao.execute(
                "INSERT INTO cbf_partidas (id_jogo, serie, ano, rodada, data_jogo, mandante_id, visitante_id, gols_mandante,"
                " gols_visitante, coletado_em) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'x')",
                (ano * 1000 + i + confrontos[i:i + 3].index((mandante, visitante)), serie, ano, rodada,
                 (inicio + dt.timedelta(days=7 * rodada)).isoformat(), mandante, visitante,
                 sorteio.choice([0, 1, 1, 2, 3]), sorteio.choice([0, 0, 1, 1, 2])),
            )


@pytest.fixture()
def conexao():
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    c.executescript(db.SCHEMA)
    sorteio = random.Random(20261007)
    for ano in (2024, 2025, 2026):
        _temporada(c, ano, sorteio)
    participantes = {}
    for cod in TIMES:
        c.execute("INSERT INTO cbf_times (cod_time, nome, uf) VALUES (?, ?, 'SP')", (cod, f"Time {cod}"))
        participantes[cod] = db.obter_ou_criar_participante(c, f"TIME {cod}", "clube", "SP")
        c.execute("INSERT INTO mapa_cbf_participante (participante_id, cod_time, metodo) VALUES (?, ?, 'uf+nome')",
                  (participantes[cod], cod))
    c.execute("INSERT INTO concursos (numero) VALUES (500)")
    # Jogo da Loteca em julho de 2026, já apurado (para o estudo poder conferi-lo).
    c.execute("INSERT INTO jogos (concurso_numero, num_jogo, casa_id, fora_id, gols_casa, gols_fora, resultado, data_jogo)"
              " VALUES (500, 1, ?, ?, 1, 0, '1', '2026-07-20')", (participantes[101], participantes[102]))
    return c


def test_paridade_com_o_estudo_b2(conexao):
    """A função da tela dá o mesmo número que o estudo para o mesmo jogo (item B1)."""
    jogo = conexao.execute("SELECT id, casa_id, fora_id, data_jogo FROM jogos").fetchone()
    amostra = b2.carregar_amostra(conexao)
    pesos = bl.pesos_por_ano(amostra)
    falso_atual = {jogo["id"]: {"referencia": {"1": 45.0, "X": 28.0, "2": 27.0}, "atual": {"1": 45.0, "X": 28.0, "2": 27.0}}}
    jogos_estudo, _ = bl.montar_jogos(conexao, falso_atual, pesos)
    assert len(jogos_estudo) == 1
    estudo = jogos_estudo[0]["previsoes"]["retrospecto"]
    producao = modelo_cbf.prever(conexao, jogo["casa_id"], jogo["fora_id"], jogo["data_jogo"])
    assert producao == pytest.approx(estudo, abs=1e-9)
    assert sum(producao.values()) == pytest.approx(100.0)


def test_fora_do_alcance_devolve_none(conexao):
    jogo = conexao.execute("SELECT casa_id, fora_id FROM jogos").fetchone()
    assert modelo_cbf.prever(conexao, jogo["casa_id"], jogo["fora_id"], None) is None  # sem data
    assert modelo_cbf.prever(conexao, jogo["casa_id"], jogo["fora_id"], "2026-03-02") is None  # nenhum jogo antes do dia
    assert modelo_cbf.prever(conexao, jogo["casa_id"], jogo["fora_id"], "2024-07-20") is None  # sem ano anterior de treino
    selecao = db.obter_ou_criar_participante(conexao, "ALEMANHA", "selecao", "GER")
    assert modelo_cbf.prever(conexao, jogo["casa_id"], selecao, "2026-07-20") is None  # sem par na CBF


def test_time_de_outra_serie_fica_com_o_modelo_anterior(conexao):
    conexao.execute("INSERT INTO cbf_times (cod_time, nome, uf) VALUES (201, 'Time B', 'RJ')")
    conexao.execute("INSERT INTO cbf_partidas (id_jogo, serie, ano, rodada, data_jogo, mandante_id, visitante_id,"
                    " gols_mandante, gols_visitante, coletado_em) VALUES (9, 'serie-b', 2026, 1, '2026-03-08', 201, 101, 1, 1, 'x')")
    outro = db.obter_ou_criar_participante(conexao, "TIME B", "clube", "RJ")
    conexao.execute("INSERT INTO mapa_cbf_participante (participante_id, cod_time, metodo) VALUES (?, 201, 'uf+nome')", (outro,))
    casa = conexao.execute("SELECT casa_id FROM jogos").fetchone()[0]
    assert modelo_cbf.prever(conexao, casa, outro, "2026-07-20") is None


def test_interruptor_volta_ao_modelo_anterior(conexao, monkeypatch):
    jogo = conexao.execute("SELECT casa_id, fora_id, data_jogo FROM jogos").fetchone()
    novo = percentuais_do_jogo(conexao, jogo["casa_id"], jogo["fora_id"], {}, jogo["data_jogo"])
    assert novo["origem"] == "retrospecto_cbf" and novo["anterior"] is not None
    assert novo["original"] == novo["historico"]  # sem calibração no modelo novo
    assert not novo["calibracao"]["aplicada"] and novo["calibracao"]["motivo"] == "origem não corrigida"
    monkeypatch.setattr(config, "MODELO_CLUBES", "historico")
    antigo = percentuais_do_jogo(conexao, jogo["casa_id"], jogo["fora_id"], {}, jogo["data_jogo"])
    assert antigo["origem"] != "retrospecto_cbf" and antigo["anterior"] is None
    assert antigo["historico"] == pytest.approx(novo["anterior"])


def test_perda_por_serie_separa_as_competicoes():
    certo = {"1": 80.0, "X": 10.0, "2": 10.0}
    errado = {"1": 10.0, "X": 10.0, "2": 80.0}
    jogos = [
        {"serie": "serie-a", "resultado": "1", "previsoes": {m: certo for m in bl.MODELOS}},
        {"serie": "serie-b", "resultado": "1", "previsoes": {m: errado for m in bl.MODELOS}},
    ]
    por_serie = bl.perda_por_serie(jogos)
    assert por_serie["serie-a"]["n"] == 1 and por_serie["serie-b"]["n"] == 1
    assert por_serie["serie-a"]["retrospecto"] < por_serie["serie-b"]["retrospecto"]


def test_noticias_entram_depois_do_modelo_novo_com_o_mesmo_teto(conexao):
    jogo = conexao.execute("SELECT casa_id, fora_id, data_jogo FROM jogos").fetchone()
    ajustes = {jogo["casa_id"]: {"ajuste": -30.0, "resumo": "x", "evidencias": [], "coletado_em": "2026-07-19T08:00:00"}}
    calculo = percentuais_do_jogo(conexao, jogo["casa_id"], jogo["fora_id"], ajustes, jogo["data_jogo"])
    assert abs(calculo["deslocamento"]) <= config.AJUSTE_EXTERNO_TETO_PONTOS + 1e-9
    assert sum(calculo["final"].values()) == pytest.approx(100.0)
