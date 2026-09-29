"""Executa a página 'Meus bilhetes' (Streamlit AppTest) sobre um banco
SINTÉTICO: vazia, com bilhete não apurado e com bilhete pronto para conferir."""
import sys
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

import config
import db
from stats.bilhetes_salvos import salvar_bilhete

RAIZ = Path(__file__).resolve().parent.parent
PAGINA = RAIZ / "app" / "pages" / "6_Meus_bilhetes.py"


@pytest.fixture()
def conexao_pronta(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DB_PATH", tmp_path / "sintetico.db")
    for pasta in (str(RAIZ), str(RAIZ / "app")):
        if pasta not in sys.path:
            sys.path.insert(0, pasta)
    db.inicializar_schema()
    with db.sessao() as c:
        alfa = db.obter_ou_criar_participante(c, "ALFA", "clube", "SP")
        beta = db.obter_ou_criar_participante(c, "BETA", "clube", "RJ")
        c.execute("INSERT INTO concursos (numero) VALUES (9001)")
        c.execute(
            "INSERT INTO jogos (concurso_numero, num_jogo, casa_id, fora_id, gols_casa, gols_fora, resultado)"
            " VALUES (9001, 1, ?, ?, 2, 0, '1')", (alfa, beta),
        )
        jogo_id = c.execute("SELECT id FROM jogos").fetchone()["id"]
        salvar_bilhete(c, 9001, {jogo_id: ["1"]}, {jogo_id: {"1": 50.0, "X": 30.0, "2": 20.0}})
    return True


def test_sem_bilhete_nenhum_mostra_instrucao(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DB_PATH", tmp_path / "vazio.db")
    for pasta in (str(RAIZ), str(RAIZ / "app")):
        if pasta not in sys.path:
            sys.path.insert(0, pasta)
    db.inicializar_schema()
    at = AppTest.from_file(str(PAGINA), default_timeout=60).run()
    assert not at.exception
    assert any("Nenhum bilhete salvo" in i.value for i in at.info)


def test_bilhete_apurado_pode_ser_conferido_e_mostra_acerto(conexao_pronta):
    at = AppTest.from_file(str(PAGINA), default_timeout=60).run()
    assert not at.exception, [e.value for e in at.exception]
    assert any("1" in m.value for m in at.metric)  # "Bilhetes salvos": 1
    at.button[0].click().run()  # "Conferir"
    assert not at.exception, [e.value for e in at.exception]
    assert any("1 de 1 acertos" in w.value for w in at.markdown)


def test_historico_aparece_so_depois_de_conferir_e_bilhete_mostra_o_que_ensina(conexao_pronta):
    at = AppTest.from_file(str(PAGINA), default_timeout=60).run()
    assert any("Aparece depois do primeiro bilhete conferido" in i.value for i in at.info)
    at.button[0].click().run()  # "Conferir"
    assert not at.exception, [e.value for e in at.exception]
    textos = " ".join(m.value for m in at.markdown)
    assert "O que este bilhete ensina" in textos
    assert "o app esperava cerca de 0,5 acertos; você fez 1." in textos
    assert "aguardando amostra (1 de 30)" in textos
    assert any(m.label == "Seus acertos por bilhete (média)" for m in at.metric)
