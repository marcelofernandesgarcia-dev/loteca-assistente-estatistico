"""Página 'Premiações' e o bloco de valores do concurso (Streamlit AppTest) sobre banco SINTÉTICO."""
import sys
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

import config
import db

RAIZ = Path(__file__).resolve().parent.parent
PAGINA = RAIZ / "app" / "pages" / "8_Premiacoes.py"
PAGINA_ATUAL = RAIZ / "app" / "pages" / "1_Concurso_atual.py"


def _preparar(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DB_PATH", tmp_path / "sintetico.db")
    for pasta in (str(RAIZ), str(RAIZ / "app")):
        if pasta not in sys.path:
            sys.path.insert(0, pasta)
    db.inicializar_schema()


@pytest.fixture()
def banco(tmp_path, monkeypatch):
    _preparar(tmp_path, monkeypatch)
    with db.sessao() as c:
        alfa = db.obter_ou_criar_participante(c, "ALFA", "clube", "SP")
        beta = db.obter_ou_criar_participante(c, "BETA", "clube", "RJ")
        dados = [  # numero, arrecadado, g14, premio14, g13, premio13
            (9001, 2500000.0, 1, 1294441.38, 13, 7613.49),
            (9002, 2000000.0, 0, 0.0, 30, 3000.0),
            (9003, None, 2, 400000.0, 40, 2000.0),
        ]
        for numero, arrecadado, g14, p14, g13, p13 in dados:
            c.execute(
                "INSERT INTO concursos (numero, data_apuracao, valor_arrecadado, valor_acumulado_final_0_5, valor_acumulado_especial,"
                " valor_estimado_proximo) VALUES (?, '2026-03-05', ?, 298574.51, 630726.95, 600000.0)", (numero, arrecadado))
            c.execute("INSERT INTO premiacoes (concurso_numero, faixa, pontos, ganhadores, valor_premio) VALUES (?, 1, 14, ?, ?)", (numero, g14, p14))
            c.execute("INSERT INTO premiacoes (concurso_numero, faixa, pontos, ganhadores, valor_premio) VALUES (?, 2, 13, ?, ?)", (numero, g13, p13))
            c.execute(
                "INSERT INTO jogos (concurso_numero, num_jogo, casa_id, fora_id, gols_casa, gols_fora, resultado, data_jogo)"
                " VALUES (?, 1, ?, ?, 2, 0, '1', '2026-03-02')", (numero, alfa, beta))
    return True


def _textos(at):
    return " ".join(m.value for m in at.markdown) + " " + " ".join(c.value for c in at.caption)


def test_pagina_sem_premiacao_nenhuma_orienta(tmp_path, monkeypatch):
    _preparar(tmp_path, monkeypatch)
    at = AppTest.from_file(str(PAGINA), default_timeout=60).run()
    assert not at.exception, [e.value for e in at.exception]
    assert any("Nenhuma premiação importada ainda" in i.value for i in at.info)


def test_pagina_mostra_resumo_tabela_e_detalhe_do_concurso(banco):
    at = AppTest.from_file(str(PAGINA), default_timeout=90).run()
    assert not at.exception, [e.value for e in at.exception]
    rotulos = {m.label: m.value for m in at.metric}
    assert rotulos["Concursos apurados"] == "3"
    assert rotulos["Sem ganhador de 14 acertos"].startswith("1 (33%)")
    assert rotulos["Maior prêmio de 14 acertos"] == "R$ 1.294.441,38"
    assert rotulos["Arrecadação mediana"] == "R$ 2.250.000,00"
    textos = _textos(at)
    assert "Arrecadação registrada em 2 de 3 concursos" in textos  # o 9003 não tem arrecadação
    assert "ninguém" in textos and "sem dado" in textos  # 9002 sem ganhador de 14; 9003 sem arrecadação
    assert "Concursos 9001 a 9003" in textos
    # Detalhe do concurso mais recente (9003): sem arrecadação, mas com as faixas.
    assert "R$ 800.000,00" in textos  # 2 x 400.000 na 1ª faixa


def test_detalhe_de_concurso_sem_ganhador_avisa_que_acumulou(banco):
    at = AppTest.from_file(str(PAGINA), default_timeout=90).run()
    at.selectbox(key="concurso_detalhe_premiacao").select(9002).run()
    assert not at.exception, [e.value for e in at.exception]
    assert any("Ninguém acertou os 14 jogos neste concurso" in i.value for i in at.info)
    assert "ninguém acertou" in _textos(at)
    assert "R$ 90.000,00" in _textos(at)  # 30 x 3.000 na 2ª faixa = total pago
    assert any(m.label == "Arrecadação total" and m.value == "R$ 2.000.000,00" for m in at.metric)
    assert "Regra oficial de distribuição e o que os números mostram" in [e.label for e in at.expander]
    assert "não calcula valores por essa regra" in _textos(at)


def test_concurso_atual_mostra_os_valores_do_ultimo_apurado(banco):
    with db.sessao() as c:
        c.execute("INSERT INTO concursos (numero, data_limite_aposta, horario_fim_apostas) VALUES (9004, '2099-01-01', 15)")
        alfa = c.execute("SELECT id FROM participantes WHERE nome = 'ALFA'").fetchone()[0]
        beta = c.execute("SELECT id FROM participantes WHERE nome = 'BETA'").fetchone()[0]
        c.execute("INSERT INTO jogos (concurso_numero, num_jogo, casa_id, fora_id, data_jogo) VALUES (9004, 1, ?, ?, '2099-01-02')", (alfa, beta))
    at = AppTest.from_file(str(PAGINA_ATUAL), default_timeout=90).run()
    assert not at.exception, [e.value for e in at.exception]
    assert any("Valores do concurso 9003" in e.label for e in at.expander)
    textos = _textos(at)
    assert "Premiação do último concurso apurado" in textos and "Acumulado para a Loteca Especial" in textos
    assert "R$ 630.726,95" in textos
