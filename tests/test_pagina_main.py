"""Executa a página inicial (Streamlit AppTest), incluindo o painel 'Status
dos dados' (etapa D1), sobre um banco SINTÉTICO."""
import sys
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

import config
import db

RAIZ = Path(__file__).resolve().parent.parent
PAGINA = RAIZ / "app" / "main.py"


@pytest.fixture()
def banco(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DB_PATH", tmp_path / "sintetico.db")
    for pasta in (str(RAIZ), str(RAIZ / "app")):
        if pasta not in sys.path:
            sys.path.insert(0, pasta)
    db.inicializar_schema()
    return True


def test_sem_nenhuma_execucao_mostra_nunca_rodou(banco):
    at = AppTest.from_file(str(PAGINA), default_timeout=60).run()
    assert not at.exception, [e.value for e in at.exception]
    assert sum(1 for c in at.caption if "Nunca rodou" in c.value) == 5  # CAIXA, CBF, calibração, notícias e medição


def test_execucao_recente_com_sucesso_mostra_ok(banco):
    with db.sessao() as c:
        db.registrar_execucao(c, "caixa", sucesso=True, quantidade=2)
    at = AppTest.from_file(str(PAGINA), default_timeout=60).run()
    assert not at.exception
    assert any("OK em" in s.value and "2 registro" in s.value for s in at.success)


def test_execucao_com_falha_mostra_erro(banco):
    with db.sessao() as c:
        db.registrar_execucao(c, "cbf", sucesso=False, erro="HTTP 500")
    at = AppTest.from_file(str(PAGINA), default_timeout=60).run()
    assert not at.exception
    assert any("Falhou em" in e.value and "HTTP 500" in e.value for e in at.error)


def test_sem_concurso_a_jogar_o_ano_em_curso_orienta(banco):
    at = AppTest.from_file(str(PAGINA), default_timeout=60).run()
    assert not at.exception
    assert any(h.value.startswith("Ano em curso") for h in at.header)
    assert any("Nenhum concurso a jogar" in i.value for i in at.info)


def test_ano_em_curso_aparece_primeiro_com_o_concurso_e_o_jogo_a_jogo(banco):
    import datetime as dt

    ano = dt.date.today().year
    with db.sessao() as c:
        alfa = db.obter_ou_criar_participante(c, "ALFA", "clube", "SP")
        beta = db.obter_ou_criar_participante(c, "BETA", "clube", "RJ")
        c.execute("INSERT INTO concursos (numero) VALUES (9001)")
        c.execute("INSERT INTO concursos (numero, data_limite_aposta, horario_fim_apostas) VALUES (9002, '2099-01-01', 15)")
        c.execute("INSERT INTO jogos (concurso_numero, num_jogo, casa_id, fora_id, gols_casa, gols_fora, resultado, data_jogo)"
                  " VALUES (9001, 1, ?, ?, 2, 0, '1', ?)", (alfa, beta, f"{ano}-03-01"))
        c.execute("INSERT INTO jogos (concurso_numero, num_jogo, casa_id, fora_id) VALUES (9002, 1, ?, ?)", (alfa, beta))
    at = AppTest.from_file(str(PAGINA), default_timeout=60).run()
    assert not at.exception, [e.value for e in at.exception]
    assert at.header[0].value == f"Ano em curso ({ano})"
    assert at.metric[0].value == "9002"
    assert any(m.value == "2 de 2" for m in at.metric)  # os dois têm jogo do ano na grade da Loteca
    tabela = " ".join(m.value for m in at.markdown)
    assert f"Jogo a jogo em {ano}" in tabela and "Alfa +100 p.p." in tabela and "amostra pequena" in tabela


def test_execucao_antiga_com_sucesso_mostra_aviso_de_desatualizado(banco):
    import datetime as dt

    antiga = (dt.datetime.now() - dt.timedelta(days=10)).isoformat(timespec="seconds")
    with db.sessao() as c:
        c.execute(
            "INSERT INTO execucoes (fonte, iniciado_em, concluido_em, sucesso, quantidade) VALUES ('caixa', ?, ?, 1, 1)",
            (antiga, antiga),
        )
    at = AppTest.from_file(str(PAGINA), default_timeout=60).run()
    assert not at.exception
    assert any("pode estar desatualizado" in w.value for w in at.warning)
