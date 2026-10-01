"""Página 'Estudos estatísticos' (Streamlit AppTest) sobre banco SINTÉTICO. Os cálculos pesados são
trocados por resultados prontos onde o que interessa é a página; o estudo anti-manada roda de verdade."""
import sys
from pathlib import Path

import pytest
import streamlit as st
from streamlit.testing.v1 import AppTest

import config
import db
from stats import associacao
from stats import backtest_competicao as b2
from tests.test_anti_manada import _concurso, _normais
from tests.test_backtest_competicao import _jogos_com_previsoes

RAIZ = Path(__file__).resolve().parent.parent
PAGINA = RAIZ / "app" / "pages" / "9_Estudos_estatisticos.py"


@pytest.fixture(autouse=True)
def _limpar_cache():
    st.cache_data.clear()
    yield
    st.cache_data.clear()


@pytest.fixture()
def banco_vazio(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DB_PATH", tmp_path / "sintetico.db")
    for pasta in (str(RAIZ), str(RAIZ / "app")):
        if pasta not in sys.path:
            sys.path.insert(0, pasta)
    db.inicializar_schema()
    return tmp_path


def _inserir_partida_cbf():
    with db.sessao() as c:
        c.execute(
            "INSERT INTO cbf_partidas (id_jogo, serie, ano, rodada, data_jogo, mandante_id, visitante_id, gols_mandante, gols_visitante, coletado_em)"
            " VALUES (1, 'serie-a', 2025, 1, '2025-04-01', 1, 2, 1, 0, '2026-10-01T09:00:00')"
        )


def _resultado(chave, descricao, conclusao, avaliado=True, q=0.5, coef=0.01):
    base = {"fator": chave, "descricao": descricao, "conclusao": conclusao, "avaliado": avaliado, "n_exposto": 300, "n_referencia": 900, "p": q, "q": q}
    if avaliado:
        base |= {"ganho": 0.01, "ganho_relativo": 0.05, "ganho_ic_inferior": 0.0, "ganho_ic_superior": 0.02,
                 "coeficiente": coef, "coef_ic_inferior": coef - 0.1, "coef_ic_superior": coef + 0.1}
    else:
        base |= {"p": None, "q": None, "n_exposto": 3}
    return base


def _textos(at):
    return " ".join(m.value for m in at.markdown) + " " + " ".join(c.value for c in at.caption)


def test_sem_nenhum_dado_cada_aba_orienta_em_vez_de_quebrar(banco_vazio):
    at = AppTest.from_file(str(PAGINA), default_timeout=60).run()
    assert not at.exception, [e.value for e in at.exception]
    infos = [i.value for i in at.info]
    assert sum("Nenhuma partida da CBF foi coletada ainda" in i for i in infos) == 2  # fatores e modelos
    assert any("Nenhuma premiação importada ainda" in i for i in infos)
    assert [t.label for t in at.tabs] == ["Fatores do desempenho", "Modelos de 1/X/2", "Anti-manada"]


def test_fatores_mostram_conclusao_tabela_acessivel_e_grafico(banco_vazio, monkeypatch):
    _inserir_partida_cbf()
    monkeypatch.setattr(associacao, "carregar_observacoes", lambda conexao: [])
    monkeypatch.setattr(associacao, "estudar", lambda obs: [
        _resultado("mando_casa", "Jogar em casa, comparado a jogar fora", "melhora a previsão fora da amostra", q=0.004, coef=0.65),
        _resultado("forma_boa", "Forma boa", "não melhora a previsão", coef=0.02),
        _resultado("saf", "Time com SAF no nome da CBF na temporada", "amostra insuficiente", avaliado=False),
    ])
    at = AppTest.from_file(str(PAGINA), default_timeout=60).run()
    assert not at.exception, [e.value for e in at.exception]
    textos = _textos(at)
    assert "Dos 2 fatores testados, 1 melhora(m) a previsão" in textos and "jogar em casa, comparado a jogar fora" in textos
    assert "sem jogos suficientes para testar: time com saf" in textos.lower()
    assert 'scope="col"' in textos and "Fatores testados" in textos  # tabela com cabeçalho associado
    assert "Descrição do gráfico" in textos  # alternativa em texto para o gráfico
    assert "+0,65 (+0,55 a +0,75)" in textos  # números com vírgula decimal


def test_fatores_sem_nenhum_testavel_explica(banco_vazio, monkeypatch):
    _inserir_partida_cbf()
    monkeypatch.setattr(associacao, "carregar_observacoes", lambda conexao: [])
    monkeypatch.setattr(associacao, "estudar", lambda obs: [_resultado("saf", "SAF", "amostra insuficiente", avaliado=False)])
    at = AppTest.from_file(str(PAGINA), default_timeout=60).run()
    assert not at.exception, [e.value for e in at.exception]
    assert "Nenhum fator tem jogos suficientes para ser testado." in _textos(at)


def test_falha_no_calculo_mostra_mensagem_util_sem_detalhe_tecnico(banco_vazio, monkeypatch):
    _inserir_partida_cbf()
    monkeypatch.setattr(associacao, "carregar_observacoes", lambda conexao: [])

    def quebra(_):
        raise ValueError("detalhe interno que não pode aparecer")

    monkeypatch.setattr(associacao, "estudar", quebra)
    at = AppTest.from_file(str(PAGINA), default_timeout=60).run()
    assert not at.exception, [e.value for e in at.exception]
    erros = [e.value for e in at.error]
    assert any("Não foi possível calcular os fatores do desempenho agora" in e for e in erros)
    assert not any("detalhe interno" in e for e in erros)
    assert any(b.label == "Tentar de novo" for b in at.button)


def test_modelos_pedem_confirmacao_e_depois_mostram_o_teste(banco_vazio, monkeypatch):
    _inserir_partida_cbf()
    monkeypatch.setattr(b2, "carregar_amostra", lambda conexao: [])
    jogos = [o | {"ano": 2021} for o in _jogos_com_previsoes([0.7, 0.2, 0.1], [1 / 3, 1 / 3, 1 / 3])]
    monkeypatch.setattr(b2, "prever", lambda amostra: jogos)
    at = AppTest.from_file(str(PAGINA), default_timeout=90).run()
    assert any("leva cerca de 10 segundos" in i.value for i in at.info)
    at.button(key="rodar_teste_modelos").click().run()
    assert not at.exception, [e.value for e in at.exception]
    textos = _textos(at)
    assert "Comparações pareadas" in textos and "Desempenho de cada modelo (400 jogos, de 2021 a 2021)" in textos
    assert "Retrospecto dos dois times (logística) contra frequência simples de 1/X/2" in textos


def test_modelos_sem_jogos_suficientes_orientam(banco_vazio, monkeypatch):
    _inserir_partida_cbf()
    monkeypatch.setattr(b2, "carregar_amostra", lambda conexao: [])
    monkeypatch.setattr(b2, "prever", lambda amostra: [])
    at = AppTest.from_file(str(PAGINA), default_timeout=60).run()
    at.button(key="rodar_teste_modelos").click().run()
    assert not at.exception, [e.value for e in at.exception]
    assert any("Ainda não há jogos suficientes para o teste" in i.value for i in at.info)


def test_anti_manada_roda_de_verdade_sobre_o_banco_sintetico(banco_vazio, monkeypatch):
    monkeypatch.setattr(config, "Q7_PERMUTACOES", 200)
    monkeypatch.setattr(config, "Q7_REPETICOES_BOOTSTRAP", 100)
    with db.sessao() as c:
        db.obter_ou_criar_participante(c, "ALFA", "clube", "SP")  # ids 1 e 2, usados pelos jogos sintéticos
        db.obter_ou_criar_participante(c, "BETA", "clube", "RJ")
        for n in range(60):
            fora = n % 15
            _concurso(c, 100 + n, _normais(*(["1"] * (14 - fora) + ["X"] * fora)), ganhadores=max(0, 40 - 3 * fora + n % 3),
                      data="2023-06-01" if n < 30 else "2024-06-01")
    at = AppTest.from_file(str(PAGINA), default_timeout=60).run()
    assert not at.exception, [e.value for e in at.exception]
    textos = _textos(at)
    assert "Em 60 concursos de 2023 a 2024" in textos and "menos ganhadores de 14 acertos por milhão arrecadado" in textos
    assert "Não recomenda marcar resultados improváveis" in textos.replace("**", "")
    assert "Por faixa de jogos fora da coluna 1" in textos


def test_anti_manada_sem_concursos_uteis_orienta(banco_vazio):
    with db.sessao() as c:
        c.execute("INSERT INTO concursos (numero, data_apuracao) VALUES (9001, '2025-01-01')")
        c.execute("INSERT INTO premiacoes (concurso_numero, faixa, pontos, ganhadores, valor_premio) VALUES (9001, 1, 14, 2, 100.0)")
    at = AppTest.from_file(str(PAGINA), default_timeout=60).run()
    assert not at.exception, [e.value for e in at.exception]
    assert any("Ainda não há concursos com arrecadação e ganhadores de 14 informados" in i.value for i in at.info)
