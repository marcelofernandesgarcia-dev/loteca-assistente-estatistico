"""Executa a página 'Confiabilidade do modelo' (Streamlit AppTest) sobre um
banco SINTÉTICO -- pequeno demais para o aquecimento padrão do backtest, o que
já é o caso mais comum de erro (divisão por zero, lista vazia etc.)."""
import sys
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

import config
import db

RAIZ = Path(__file__).resolve().parent.parent
PAGINA = RAIZ / "app" / "pages" / "5_Confiabilidade_do_modelo.py"


@pytest.fixture()
def banco_vazio(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DB_PATH", tmp_path / "sintetico.db")
    for pasta in (str(RAIZ), str(RAIZ / "app")):
        if pasta not in sys.path:
            sys.path.insert(0, pasta)
    db.inicializar_schema()
    return True


def test_base_pequena_demais_mostra_aviso_sem_quebrar(banco_vazio):
    at = AppTest.from_file(str(PAGINA), default_timeout=60).run()
    assert not at.exception, [e.value for e in at.exception]
    assert any("Base pequena demais" in i.value for i in at.info)


def test_base_com_poucos_concursos_reais_tambem_nao_quebra(banco_vazio):
    with db.sessao() as c:
        alfa = db.obter_ou_criar_participante(c, "ALFA", "clube", "SP")
        beta = db.obter_ou_criar_participante(c, "BETA", "clube", "RJ")
        for numero in range(1, 5):
            c.execute("INSERT INTO concursos (numero) VALUES (?)", (numero,))
            c.execute(
                "INSERT INTO jogos (concurso_numero, num_jogo, casa_id, fora_id, gols_casa, gols_fora, resultado)"
                " VALUES (?, 1, ?, ?, 1, 0, '1')", (numero, alfa, beta),
            )
    at = AppTest.from_file(str(PAGINA), default_timeout=60).run()
    assert not at.exception, [e.value for e in at.exception]
