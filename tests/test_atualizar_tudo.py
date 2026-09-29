"""scripts/atualizar_tudo.py: cada fonte é isolada -- a falha de uma não deve
impedir as outras nem derrubar o script. Sem rede (tudo com monkeypatch)."""
import sqlite3

import pytest

import db
import scripts.atualizar_tudo as atualizar_tudo


@pytest.fixture()
def conexao():
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    c.executescript(db.SCHEMA)
    return c


def test_todas_as_fontes_com_sucesso_registram_execucao(conexao, monkeypatch):
    monkeypatch.setattr(atualizar_tudo, "importar_programacao", lambda conexao: [1272])
    monkeypatch.setattr(atualizar_tudo, "importar_concurso", lambda numero, conexao: 1271)
    monkeypatch.setattr(atualizar_tudo, "coletar_todas", lambda conexao: [{"serie": "serie-a", "times": 20}, {"serie": "serie-b", "times": 20}])
    monkeypatch.setattr(atualizar_tudo, "concurso_alvo_da_semana", lambda conexao: None)

    falhas = 0
    for nome, funcao in (
        ("caixa", atualizar_tudo._atualizar_caixa),
        ("cbf", atualizar_tudo._atualizar_cbf),
        ("noticias", atualizar_tudo._atualizar_noticias),
    ):
        funcao(conexao)

    execucoes = db.ultima_execucao_por_fonte(conexao)
    assert execucoes["caixa"]["sucesso"] == 1 and execucoes["caixa"]["quantidade"] == 2
    assert execucoes["cbf"]["sucesso"] == 1 and execucoes["cbf"]["quantidade"] == 40
    assert "noticias" not in execucoes  # sem concurso na janela -- nada registrado, não é falha


def test_falha_de_uma_fonte_nao_impede_as_outras(conexao, monkeypatch):
    def caixa_com_erro(conexao):
        raise ConnectionError("CAIXA fora do ar")

    monkeypatch.setattr(atualizar_tudo, "_atualizar_caixa", caixa_com_erro)
    monkeypatch.setattr(atualizar_tudo, "_atualizar_cbf", lambda conexao: db.registrar_execucao(conexao, "cbf", True, 40))
    monkeypatch.setattr(atualizar_tudo, "_atualizar_noticias", lambda conexao: db.registrar_execucao(conexao, "noticias", True, 5))

    falhas = 0
    for nome, funcao in (
        ("caixa", atualizar_tudo._atualizar_caixa),
        ("cbf", atualizar_tudo._atualizar_cbf),
        ("noticias", atualizar_tudo._atualizar_noticias),
    ):
        try:
            funcao(conexao)
        except Exception as erro:
            falhas += 1
            db.registrar_execucao(conexao, nome, sucesso=False, erro=str(erro))

    assert falhas == 1
    execucoes = db.ultima_execucao_por_fonte(conexao)
    assert execucoes["caixa"]["sucesso"] == 0 and "CAIXA fora do ar" in execucoes["caixa"]["erro"]
    assert execucoes["cbf"]["sucesso"] == 1 and execucoes["noticias"]["sucesso"] == 1


def test_registrar_e_ultima_execucao_por_fonte(conexao):
    db.registrar_execucao(conexao, "caixa", sucesso=True, quantidade=3)
    db.registrar_execucao(conexao, "caixa", sucesso=False, erro="timeout")  # execução mais recente da fonte
    ultimas = db.ultima_execucao_por_fonte(conexao)
    assert ultimas["caixa"]["sucesso"] == 0 and ultimas["caixa"]["erro"] == "timeout"


def test_sem_nenhuma_execucao_ultima_execucao_por_fonte_e_vazio(conexao):
    assert db.ultima_execucao_por_fonte(conexao) == {}
