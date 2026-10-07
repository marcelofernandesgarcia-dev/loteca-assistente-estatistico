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
    valores = {m.label: m.value for m in at.metric}
    assert valores["Total gasto"] == "R$ 2,00" and valores["Saldo"] == "R$ -2,00"  # vírgula decimal (07/10/2026)
    at.button[0].click().run()  # "Conferir"
    assert not at.exception, [e.value for e in at.exception]
    assert any("1 de 1 acertos" in w.value for w in at.markdown)


def test_sem_versoes_orienta_e_com_versoes_mostra_como_o_bilhete_foi_montado(conexao_pronta):
    from stats.versoes_palpite import guardar_versao, ligar_ao_bilhete

    at = AppTest.from_file(str(PAGINA), default_timeout=60).run()
    assert any("Aparece quando um concurso tiver mais de uma versão" in i.value for i in at.info)
    with db.sessao() as c:
        jogo_id = c.execute("SELECT id FROM jogos").fetchone()["id"]
        bilhete_id = c.execute("SELECT id FROM bilhetes").fetchone()["id"]
        guardar_versao(c, 9001, {jogo_id: ["2"]}, {}, None)
        final = guardar_versao(c, 9001, {jogo_id: ["1"]}, {}, None)
        ligar_ao_bilhete(c, final["versao"]["id"], bilhete_id)
    at = AppTest.from_file(str(PAGINA), default_timeout=60).run()
    assert not at.exception, [e.value for e in at.exception]
    legendas = " ".join(c.value for c in at.caption)
    assert "Montado na versão 2 de 2" in legendas and "jogo 1: 2 (seco) virou 1 (seco)" in legendas
    assert "a versão 1 teria feito 0 acerto(s) e esta fez 1" in legendas
    textos = " ".join(m.value for m in at.markdown)
    assert "**ajudaram em 1**" in textos and "saldo: +1 acerto(s)" in textos
    assert "Ainda são poucos concursos" in legendas


def test_bilhete_sem_retrato_avisa_e_com_retrato_mostra_a_tabela(conexao_pronta):
    # Item A1 do plano v2 (07/10/2026).
    at = AppTest.from_file(str(PAGINA), default_timeout=60).run()
    assert any("o retrato completo do que o app mostrava não foi guardado" in c.value for c in at.caption)
    from stats.retrato import gravar_retrato, retrato_geral

    with db.sessao() as c:
        bilhete_id = c.execute("SELECT id FROM bilhetes").fetchone()["id"]
        c.execute("INSERT INTO bilhetes (concurso_numero, criado_em, apostas, custo) VALUES (9001, '2026-10-09T10:00:00', 1, 2.0)")
        novo = c.execute("SELECT MAX(id) FROM bilhetes").fetchone()[0]
        jogo_id = c.execute("SELECT id FROM jogos").fetchone()["id"]
        c.execute("INSERT INTO bilhete_jogos (bilhete_id, jogo_id, marcacoes) VALUES (?, ?, '1')", (novo, jogo_id))
        gravar_retrato(c, novo, retrato_geral(), {jogo_id: {
            "num_jogo": 1, "casa": "ALFA", "fora": "BETA", "origem": "poisson",
            "percentual": {"final": {"1": 50.0, "X": 30.0, "2": 20.0}},
            "noticias": {"casa": None, "fora": None, "deslocamento": 0.0},
            "cobertura": {"nivel": "parcial", "nome_nivel": "Parcial", "faltas": [], "alta_incerteza": True},
            "sugestao_do_app": ["1"], "marcacao": ["1"],
        }})
    at = AppTest.from_file(str(PAGINA), default_timeout=60).run()
    assert not at.exception, [e.value for e in at.exception]
    at.toggle(key=f"retrato_{novo}").set_value(True).run()
    textos = " ".join(m.value for m in at.markdown)
    assert "O que o app mostrava ao salvar" in textos and "histórico da Loteca (Poisson)" in textos
    assert "⚠ Parcial" in textos and "sem leitura" in textos
    assert bilhete_id != novo


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
