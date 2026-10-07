"""Retrato imutável do bilhete (item A1 do plano v2, 07/10/2026)."""
import datetime as dt
import sqlite3

import pytest

import config
import db
from stats.bilhetes_salvos import conferir_bilhete, salvar_bilhete
from stats.retrato import gravar_retrato, retrato_do_bilhete, retrato_do_jogo, retrato_geral, versao_do_app

CALCULO = {
    "original": {"1": 50.0, "X": 30.0, "2": 20.0},
    "historico": {"1": 48.0, "X": 30.0, "2": 22.0},
    "final": {"1": 45.0, "X": 31.0, "2": 24.0},
    "deslocamento": -3.0,
    "calibracao": {"origem": "poisson", "aplicada": True, "expoente": 0.6, "mistura": 0.95, "motivo": None},
}
COBERTURA = {"nivel": "parcial", "nome_nivel": "Parcial", "faltas": ["ALFA: sem dados da CBF"], "alta_incerteza": True}


@pytest.fixture()
def conexao():
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    c.executescript(db.SCHEMA)
    alfa = db.obter_ou_criar_participante(c, "ALFA", "clube", "SP")
    beta = db.obter_ou_criar_participante(c, "BETA", "clube", "RJ")
    c.execute("INSERT INTO concursos (numero) VALUES (9001)")
    c.execute("INSERT INTO jogos (concurso_numero, num_jogo, casa_id, fora_id, gols_casa, gols_fora, resultado)"
              " VALUES (9001, 1, ?, ?, 2, 0, '1')", (alfa, beta))
    return c


def _jogo(c):
    linha = c.execute("SELECT id, casa_id, fora_id FROM jogos").fetchone()
    return {"id": linha["id"], "num_jogo": 1, "casa": "ALFA", "casa_id": linha["casa_id"], "fora": "BETA",
            "fora_id": linha["fora_id"]}


def _salvar_com_retrato(c):
    jogo = _jogo(c)
    bilhete = salvar_bilhete(c, 9001, {jogo["id"]: ["1", "X"]}, {jogo["id"]: CALCULO["final"]})
    ajustes = {jogo["casa_id"]: {"ajuste": -3.0, "resumo": "lesao_titular (-3.0)", "coletado_em": "2026-10-08T08:00:00",
                                 "evidencias": [{"manchete": "Alfa perde atacante", "url": "https://x.test/1"}]}}
    retrato = retrato_do_jogo(jogo, CALCULO, ajustes, COBERTURA, {"nivel": "alta", "motivos": []},
                              "1º na Série A", None, ["1"], ["1", "X"])
    gravar_retrato(c, bilhete, retrato_geral(dt.datetime(2026, 10, 9, 10, 0)), {jogo["id"]: retrato})
    return bilhete


def test_retrato_guarda_o_que_estava_na_tela(conexao):
    bilhete = _salvar_com_retrato(conexao)
    retrato = retrato_do_bilhete(conexao, bilhete)
    jogo = retrato["jogos"][0]
    assert jogo["percentual"]["modelo"] == CALCULO["original"] and jogo["percentual"]["final"] == CALCULO["final"]
    assert jogo["origem"] == "poisson" and jogo["calibracao"]["expoente"] == 0.6
    assert jogo["noticias"]["casa"]["evidencias"][0]["manchete"] == "Alfa perde atacante"
    assert jogo["noticias"]["fora"] is None and jogo["noticias"]["deslocamento"] == -3.0
    assert jogo["cobertura"]["alta_incerteza"] and jogo["sugestao_do_app"] == ["1"] and jogo["marcacao"] == ["1", "X"]
    assert retrato["geral"]["salvo_em"] == "2026-10-09T10:00:00"
    assert retrato["geral"]["versao_regras_noticias"] == config.VARREDURA_VERSAO_REGRAS


def test_retrato_nao_pode_ser_alterado_nem_excluido(conexao):
    _salvar_com_retrato(conexao)
    with pytest.raises(sqlite3.IntegrityError, match="não pode ser alterado"):
        conexao.execute("UPDATE retratos_bilhete SET conteudo = '{}'")
    with pytest.raises(sqlite3.IntegrityError, match="não pode ser excluído"):
        conexao.execute("DELETE FROM retratos_bilhete")


def test_conferir_o_bilhete_nao_muda_o_retrato(conexao):
    bilhete = _salvar_com_retrato(conexao)
    antes = retrato_do_bilhete(conexao, bilhete)
    conferir_bilhete(conexao, bilhete)
    assert retrato_do_bilhete(conexao, bilhete) == antes


def test_bilhete_antigo_sem_retrato_devolve_none(conexao):
    jogo = _jogo(conexao)
    bilhete = salvar_bilhete(conexao, 9001, {jogo["id"]: ["1"]}, {jogo["id"]: CALCULO["final"]})
    assert retrato_do_bilhete(conexao, bilhete) is None


def test_versao_do_app_le_o_commit(tmp_path, monkeypatch):
    git = tmp_path / ".git"
    (git / "refs" / "heads").mkdir(parents=True)
    (git / "HEAD").write_text("ref: refs/heads/master\n", encoding="utf-8")
    (git / "refs" / "heads" / "master").write_text("0123456789abcdef0123\n", encoding="utf-8")
    monkeypatch.setattr(config, "BASE_DIR", tmp_path)
    assert versao_do_app() == "0123456789ab"
    (git / "refs" / "heads" / "master").unlink()
    (git / "packed-refs").write_text("fedcba9876543210ffff refs/heads/master\n", encoding="utf-8")
    assert versao_do_app() == "fedcba987654"
    monkeypatch.setattr(config, "BASE_DIR", tmp_path / "sem_git")
    assert versao_do_app() == "desconhecida"
