"""externo.varredura.concurso_alvo_da_semana: janela de 0 a N dias antes do
prazo, sem repetir concurso já varrido. Sem rede, banco em memória."""
import datetime as dt
import sqlite3

import pytest

import config
import db
from externo.varredura import concurso_alvo_da_semana


@pytest.fixture()
def conexao():
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    c.executescript(db.SCHEMA)
    return c


def _concurso(conexao, numero, dias_ate_o_prazo):
    prazo = (dt.date.today() + dt.timedelta(days=dias_ate_o_prazo)).isoformat()
    conexao.execute("INSERT INTO concursos (numero, data_limite_aposta) VALUES (?, ?)", (numero, prazo))


def test_dispara_exatamente_na_distancia_configurada(conexao):
    _concurso(conexao, 1273, config.VARREDURA_DIAS_ANTES_DO_PRAZO)
    assert concurso_alvo_da_semana(conexao)["numero"] == 1273


def test_recupera_o_dia_perdido_um_dia_depois_e_no_dia_do_prazo(conexao):
    _concurso(conexao, 1273, 1)
    assert concurso_alvo_da_semana(conexao)["numero"] == 1273
    conexao.execute("UPDATE concursos SET data_limite_aposta = ?", (dt.date.today().isoformat(),))
    assert concurso_alvo_da_semana(conexao)["numero"] == 1273


def test_fora_da_janela_nao_dispara(conexao):
    _concurso(conexao, 1273, config.VARREDURA_DIAS_ANTES_DO_PRAZO + 1)
    _concurso(conexao, 1272, -1)  # prazo vencido
    assert concurso_alvo_da_semana(conexao) is None


def test_concurso_ja_varrido_nao_repete(conexao):
    _concurso(conexao, 1273, 1)
    conexao.execute(
        "INSERT INTO fatores_externos (participante_id, concurso_numero, coletado_em) VALUES (1, 1273, '2026-10-01T09:00:00')"
    )
    assert concurso_alvo_da_semana(conexao) is None


def test_data_invalida_e_ignorada_sem_derrubar_a_varredura(conexao, caplog):
    conexao.execute("INSERT INTO concursos (numero, data_limite_aposta) VALUES (1300, '0-invalida')")  # ordena antes das datas ISO
    _concurso(conexao, 1273, 1)
    with caplog.at_level("WARNING"):
        assert concurso_alvo_da_semana(conexao)["numero"] == 1273
    assert "1300" in caplog.text


def test_sem_data_de_prazo_retorna_none(conexao):
    conexao.execute("INSERT INTO concursos (numero) VALUES (1273)")
    assert concurso_alvo_da_semana(conexao) is None
