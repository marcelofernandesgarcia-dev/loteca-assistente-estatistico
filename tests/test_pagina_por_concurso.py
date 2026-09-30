"""Executa a página 'Por concurso' (Streamlit AppTest) sobre um banco SINTÉTICO."""
import sys
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

import config
import db

RAIZ = Path(__file__).resolve().parent.parent
PAGINA = RAIZ / "app" / "pages" / "2_Por_concurso.py"


@pytest.fixture()
def banco(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DB_PATH", tmp_path / "sintetico.db")
    for pasta in (str(RAIZ), str(RAIZ / "app")):
        if pasta not in sys.path:
            sys.path.insert(0, pasta)
    db.inicializar_schema()
    with db.sessao() as c:
        alfa = db.obter_ou_criar_participante(c, "ALFA", "clube", "SP")
        beta = db.obter_ou_criar_participante(c, "BETA", "clube", "RJ")
        c.execute(
            "INSERT INTO concursos (numero, data_apuracao, data_limite_aposta, horario_fim_apostas, acumulado)"
            " VALUES (9001, '2026-03-05', '2026-03-01', 15, 1)"
        )
        c.execute(
            "INSERT INTO jogos (concurso_numero, num_jogo, casa_id, fora_id, gols_casa, gols_fora, resultado, data_jogo)"
            " VALUES (9001, 1, ?, ?, 2, 0, '1', '2026-03-02')", (alfa, beta),
        )
        c.execute(
            "INSERT INTO premiacoes (concurso_numero, faixa, pontos, ganhadores, valor_premio) VALUES (9001, 1, 14, 3, 50000.0)"
        )
    return True


def test_pagina_sem_concurso_nenhum_nao_quebra(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DB_PATH", tmp_path / "vazio.db")
    for pasta in (str(RAIZ), str(RAIZ / "app")):
        if pasta not in sys.path:
            sys.path.insert(0, pasta)
    db.inicializar_schema()
    at = AppTest.from_file(str(PAGINA), default_timeout=60).run()
    assert not at.exception
    assert any("Nenhum concurso importado" in i.value for i in at.info)


def test_pagina_mostra_prazo_exato_jogos_e_premiacao(banco):
    at = AppTest.from_file(str(PAGINA), default_timeout=60).run()
    assert not at.exception, [e.value for e in at.exception]
    legenda = " ".join(c.value for c in at.caption)
    assert "Prazo de aposta: 01/03/2026 às 15h" in legenda
    assert "Acumulou: sim" in legenda
    assert [h.value for h in at.subheader] == ["Premiação"]
    textos = " ".join(m.value for m in at.markdown)
    assert "1ª faixa (14 acertos)" in textos and "R$ 50.000,00" in textos and "R$ 150.000,00" in textos  # 3 x 50.000
    assert any(m.label == "Arrecadação total" and m.value == "sem dado" for m in at.metric)  # o banco sintético não tem
