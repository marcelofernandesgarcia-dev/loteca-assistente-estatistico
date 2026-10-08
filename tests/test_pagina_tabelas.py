"""Executa a página 'Tabelas da Loteca' (Streamlit AppTest) sobre um banco SINTÉTICO (08/10/2026)."""
import sys
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

import config
import db

RAIZ = Path(__file__).resolve().parent.parent
PAGINA = RAIZ / "app" / "pages" / "10_Tabelas_da_Loteca.py"


@pytest.fixture()
def banco(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DB_PATH", tmp_path / "sintetico.db")
    for pasta in (str(RAIZ), str(RAIZ / "app")):
        if pasta not in sys.path:
            sys.path.insert(0, pasta)
    db.inicializar_schema()
    return True


def _abrir() -> AppTest:
    at = AppTest.from_file(str(PAGINA), default_timeout=90).run()
    assert not at.exception, [e.value for e in at.exception]
    return at


def _com_concurso_aberto():
    with db.sessao() as c:
        alfa = db.obter_ou_criar_participante(c, "ALFA", "clube", "SP")
        beta = db.obter_ou_criar_participante(c, "BETA", "clube", "RJ")
        c.execute("INSERT INTO concursos (numero, data_limite_aposta) VALUES (9002, '2099-01-01')")
        for num in range(1, 15):
            c.execute("INSERT INTO jogos (concurso_numero, num_jogo, casa_id, fora_id, data_jogo) VALUES (9002, ?, ?, ?, '2099-01-02')",
                      (num, alfa, beta))


def test_tabelas_de_valores_e_chances_sem_concurso_aberto(banco):
    at = _abrir()
    textos = " ".join(m.value for m in at.markdown)
    assert "Sem triplo ou com 1 triplo" in textos and "Com 2 triplos ou mais" in textos
    assert "<td>5</td><td>3</td><td>864</td><td>R$ 1.728,00</td>" in textos  # aposta máxima
    assert "<td>1 / 0</td><td>2 (R$ 4,00)</td><td>1 em 2.391.485</td><td>1 em 85.410</td>" in textos
    assert "percentuais do" not in textos  # sem concurso aberto, sem a leitura pelos percentuais
    assert any("Preço vigente: R$ 2,00 por aposta" in c.value for c in at.caption)


def test_analisar_combinacao_do_exemplo_e_combinacao_invalida(banco):
    at = _abrir()
    at.number_input(key="tabela_duplos").set_value(1)
    at.number_input(key="tabela_triplos").set_value(3).run()
    assert not at.exception, [e.value for e in at.exception]
    assert "**1 duplo(s) e 3 triplo(s): 54 apostas, R$ 108,00.**" in [m.value for m in at.markdown]
    metricas = {m.label: m.value for m in at.metric}
    assert metricas["14 pontos (método da CAIXA)"] == "1 em 88.574"
    assert metricas["13 pontos (tabela da CAIXA)"] == "1 em 3.163"
    assert metricas["Bilhete premiar (CAIXA)"] == "1 em 4.120"
    at.number_input(key="tabela_duplos").set_value(6).run()
    assert any("máximo oficial de 864" in w.value for w in at.warning)


def test_com_concurso_aberto_entra_a_leitura_pelos_percentuais(banco):
    _com_concurso_aberto()
    at = _abrir()
    textos = " ".join(m.value for m in at.markdown)
    assert "14 (percentuais do 9002)" in textos and "13 ou mais (percentuais do 9002)" in textos
    assert "Pelos percentuais do concurso 9002" in textos
    assert any(c.value.startswith("Onde a regra do app poria os múltiplos: jogo") for c in at.caption)
    assert "Chances deste bilhete" in textos  # o detalhe reaproveita o quadro de chances do volante
