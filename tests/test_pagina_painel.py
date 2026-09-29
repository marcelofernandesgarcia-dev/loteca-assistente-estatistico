"""Executa a página 'Painel comparativo' (Streamlit AppTest) sobre um banco
SINTÉTICO: temporada da CBF com 3 times, um concurso a jogar com um clube
pareado com a CBF e uma seleção, e histórico na Loteca."""
import sys
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

import config
import db
from stats.painel import frase_amostra_pequena

RAIZ = Path(__file__).resolve().parent.parent
PAGINA = RAIZ / "app" / "pages" / "7_Painel_comparativo.py"


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
        gama = db.obter_ou_criar_participante(c, "GAMA", "selecao", None)
        c.execute("INSERT INTO concursos (numero) VALUES (9001)")
        c.execute("INSERT INTO concursos (numero, data_limite_aposta) VALUES (9002, '2099-01-01')")
        historico = [(1, alfa, beta, 2, 0, "1", "2024-03-02"), (2, beta, alfa, 1, 1, "X", "2025-03-02"),
                     (3, gama, alfa, 0, 1, "2", "2026-03-02"), (4, alfa, gama, 3, 1, "1", None)]
        for num, casa, fora, gc, gf, res, data in historico:
            c.execute(
                "INSERT INTO jogos (concurso_numero, num_jogo, casa_id, fora_id, gols_casa, gols_fora, resultado, data_jogo)"
                " VALUES (9001, ?, ?, ?, ?, ?, ?, ?)", (num, casa, fora, gc, gf, res, data),
            )
        c.execute("INSERT INTO jogos (concurso_numero, num_jogo, casa_id, fora_id) VALUES (9002, 1, ?, ?)", (alfa, beta))
        c.execute("INSERT INTO jogos (concurso_numero, num_jogo, casa_id, fora_id) VALUES (9002, 2, ?, ?)", (gama, alfa))

        for cod, nome, uf in ((1, "Alfa FC", "SP"), (2, "Beta EC", "RJ"), (3, "Outro AC", "MG")):
            c.execute("INSERT INTO cbf_times (cod_time, nome, uf) VALUES (?, ?, ?)", (cod, nome, uf))
        confrontos = [(1, 2), (2, 3), (3, 1), (2, 1), (3, 2), (1, 3)]
        placares = [(2, 0), (1, 1), (0, 2), (1, 0), (2, 2), (3, 1)]
        for rodada, ((casa, fora), (gc, gf)) in enumerate(zip(confrontos, placares), start=1):
            c.execute(
                "INSERT INTO cbf_partidas (id_jogo, serie, ano, rodada, data_jogo, mandante_id, visitante_id,"
                " gols_mandante, gols_visitante, coletado_em) VALUES (?, 'serie-a', 2026, ?, ?, ?, ?, ?, ?, '2026-09-27')",
                (rodada, rodada, f"2026-05-{rodada:02d}", casa, fora, gc, gf),
            )
        for cod, posicao, pontos in ((1, 1, 9), (2, 2, 5), (3, 3, 2)):
            c.execute(
                "INSERT INTO cbf_classificacao (serie, ano, cod_time, rodada, posicao, pontos, jogos, vitorias, empates,"
                " derrotas, gols_pro, gols_contra, saldo, coletado_em) VALUES ('serie-a', 2026, ?, 6, ?, ?, 4, 0, 0, 0,"
                " 0, 0, 0, '2026-09-27')",
                (cod, posicao, pontos),
            )
        c.execute("INSERT INTO mapa_cbf_participante (participante_id, cod_time, metodo) VALUES (?, 1, 'teste')", (alfa,))
        c.execute("INSERT INTO mapa_cbf_participante (participante_id, cod_time, metodo) VALUES (?, 2, 'teste')", (beta,))
    return True


def _abrir() -> AppTest:
    at = AppTest.from_file(str(PAGINA), default_timeout=90).run()
    assert not at.exception, [e.value for e in at.exception]
    return at


def _textos(at: AppTest) -> str:
    return " ".join(m.value for m in at.markdown) + " " + " ".join(c.value for c in at.caption)


def test_modo_concurso_mostra_as_duas_abas_com_todos_os_participantes(banco):
    at = _abrir()
    assert [t.label for t in at.tabs] == ["Temporada (CBF)", "Histórico na Loteca"]
    assert any(s.value == "Série A 2026" for s in at.subheader)
    textos = _textos(at)
    assert "Comparação na temporada" in textos and "Alfa FC" in textos and "Beta EC" in textos
    assert "2 dos 4 participantes têm dados da CBF" in textos
    assert "GAMA**: sem dados da CBF" in textos  # seleção: aponta para a outra aba
    assert "Projeção: se o desempenho persistir" in [e.label for e in at.expander]
    # Aba da Loteca: todos os 4 participantes, inclusive a seleção com pouca amostra.
    assert "todos os 4 participantes" in textos and "Amostra pequena" in textos
    assert "Desempenho nos jogos que caíram na Loteca" in textos


def test_sem_dados_da_cbf_a_aba_de_temporada_orienta_e_a_da_loteca_funciona(banco):
    with db.sessao() as c:
        c.execute("DELETE FROM cbf_partidas")
    at = _abrir()
    assert any("Sem dados da CBF no banco" in i.value for i in at.info)
    assert "Desempenho nos jogos que caíram na Loteca" in _textos(at)


def test_serie_sem_tamanho_cadastrado_avisa_que_nao_projeta(banco, monkeypatch):
    monkeypatch.setattr(config, "TEMPORADA_JOGOS_POR_TIME", {})
    at = _abrir()
    assert any("Sem projeção para esta série" in i.value for i in at.info)


def test_modo_livre_na_temporada_e_na_loteca(banco):
    at = _abrir()
    at.radio(key="modo_temporada").set_value("Escolher livremente").run()
    assert not at.exception, [e.value for e in at.exception]
    assert "Alfa FC" in _textos(at)
    at.radio(key="modo_loteca").set_value("Escolher livremente").run()
    assert any("Escolha ao menos um participante" in i.value for i in at.info)
    at.number_input(key="minimo_loteca").set_value(1).run()
    assert any(o.startswith("ALFA (SP) · clube · 4 jogos") for o in at.multiselect(key="participantes_loteca").options)
    with db.sessao() as c:
        alfa_id = c.execute("SELECT id FROM participantes WHERE nome = 'ALFA'").fetchone()[0]
    at.multiselect(key="participantes_loteca").set_value([alfa_id]).run()
    assert not at.exception, [e.value for e in at.exception]
    assert "Desempenho nos jogos que caíram na Loteca" in _textos(at)


def test_frase_de_amostra_pequena():
    assert frase_amostra_pequena([]) is None
    assert frase_amostra_pequena(["GAMA", "BETA"]).endswith("leitura fraca: GAMA, BETA.")
