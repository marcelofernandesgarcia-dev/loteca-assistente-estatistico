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


def _medicao_exemplo():
    grupo = {"n": 100, "perda_log": 1.02, "perda_log_frequencia": 1.07, "rps": 0.21, "rps_frequencia": 0.22,
             "brier": 0.62, "acerto": 49.0, "acerto_frequencia": 45.0, "ganho": 0.05, "ic_inferior": 0.03,
             "ic_superior": 0.07, "p": 0.001}
    return {"calculado_em": "2026-10-08T06:00:00", "desde_ano": 2020, "jogos_apurados": 100, "ultimo_concurso": 9,
            "total": grupo, "por_tipo": {"Séries A e B": grupo}, "por_ano": {"2026": grupo},
            "calibracao": [{"faixa": "40% a 50%", "n": 30, "previsto": 45.0, "observado": 46.0}],
            "elo_clubes_ativo": True, "modelo_clubes": "retrospecto_cbf"}


def test_sem_medicao_do_app_de_hoje_orienta_e_com_medicao_mostra_o_veredito(banco_vazio):
    # Sugestão S1 (08/10/2026): o topo mede o app de hoje; o modelo anterior vira histórico.
    from stats import confiabilidade

    at = AppTest.from_file(str(PAGINA), default_timeout=60).run()
    assert not at.exception, [e.value for e in at.exception]
    assert any("Ainda não há medição gravada" in i.value for i in at.info)
    with db.sessao() as c:
        confiabilidade.gravar(c, _medicao_exemplo())
    at = AppTest.from_file(str(PAGINA), default_timeout=60).run()
    assert not at.exception, [e.value for e in at.exception]
    assert any("o app de hoje é **melhor que a frequência simples**" in s.value for s in at.success)
    textos = " ".join(m.value for m in at.markdown)
    assert "| Séries A e B | 100 | 1,0200 | 1,0700 |" in textos
    assert any(h.value == "Histórico: o modelo anterior" for h in at.header)


def test_precisa_medir_quando_entra_concurso_novo(banco_vazio):
    from stats import confiabilidade

    with db.sessao() as c:
        alfa = db.obter_ou_criar_participante(c, "ALFA", "clube", "SP")
        beta = db.obter_ou_criar_participante(c, "BETA", "clube", "RJ")
        c.execute("INSERT INTO concursos (numero) VALUES (9)")
        c.execute("INSERT INTO jogos (concurso_numero, num_jogo, casa_id, fora_id, gols_casa, gols_fora, resultado)"
                  " VALUES (9, 1, ?, ?, 1, 0, '1')", (alfa, beta))
        assert confiabilidade.precisa_medir(c)
        confiabilidade.gravar(c, _medicao_exemplo())
        assert not confiabilidade.precisa_medir(c)
        assert confiabilidade.ultima(c)["total"]["n"] == 100


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
