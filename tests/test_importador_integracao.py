"""Teste de integração leve -- bate contra a API real da CAIXA. Pula
sozinho se não houver rede (ex.: rodando num ambiente isolado), em vez de
falhar o teste por um motivo que não é bug do código.
"""
import sqlite3

import pytest

import db
from importer.caixa_client import ErroImportacaoLoteca, importar_concurso


@pytest.fixture()
def conexao_em_memoria():
    conexao = sqlite3.connect(":memory:")
    conexao.row_factory = sqlite3.Row
    conexao.executescript(db.SCHEMA)
    yield conexao
    conexao.close()


def test_importa_concurso_1271_conhecido(conexao_em_memoria):
    try:
        numero = importar_concurso(1271, conexao_em_memoria)
    except ErroImportacaoLoteca as erro:
        pytest.skip(f"API da CAIXA indisponível neste ambiente: {erro}")
    assert numero == 1271

    jogo_flamengo = conexao_em_memoria.execute(
        """
        SELECT j.gols_casa, j.gols_fora, j.resultado
        FROM jogos j JOIN participantes pc ON pc.id = j.casa_id
        WHERE j.concurso_numero = 1271 AND pc.nome = 'FLAMENGO'
        """
    ).fetchone()
    assert jogo_flamengo is not None
    assert (jogo_flamengo["gols_casa"], jogo_flamengo["gols_fora"]) == (2, 1)
    assert jogo_flamengo["resultado"] == "1"
