"""Calibração aplicada no app (E4, Fase 2): parâmetros no banco, correção do percentual do jogo, interruptor,
recalibração em `atualizar_tudo` e apresentação. Banco sintético, sem rede."""
import sqlite3
import sys
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

import config
import db
import scripts.atualizar_tudo as atualizar_tudo
from externo.percentual_final import percentuais_do_jogo
from externo.varredura import recalcular_percentuais_gravados
from stats import calibracao as cal

RAIZ = Path(__file__).resolve().parent.parent
PAGINA = RAIZ / "app" / "pages" / "1_Concurso_atual.py"
PARAMETROS = {"expoente": 0.6, "mistura": 0.9, "jogos": 1000}


@pytest.fixture()
def conexao():
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    c.executescript(db.SCHEMA)
    return c


def _jogos_de_historico(conexao):
    """Dois clubes sem jogos suficientes (origem: frequência simples) e resultados para a frequência global."""
    alfa = db.obter_ou_criar_participante(conexao, "ALFA", "clube", "SP")
    beta = db.obter_ou_criar_participante(conexao, "BETA", "clube", "RJ")
    conexao.execute("INSERT INTO concursos (numero, data_apuracao) VALUES (1, '2026-01-01')")
    for i, (gc, gf, res) in enumerate([(2, 0, "1"), (1, 1, "X"), (0, 1, "2"), (3, 1, "1")], start=1):
        conexao.execute(
            "INSERT INTO jogos (concurso_numero, num_jogo, casa_id, fora_id, gols_casa, gols_fora, resultado, data_jogo)"
            " VALUES (1, ?, ?, ?, ?, ?, ?, '2026-01-01')", (i, alfa, beta, gc, gf, res),
        )
    return alfa, beta


def test_carregar_parametros_sem_tabela_ou_vazia_devolve_vazio():
    sem_tabela = sqlite3.connect(":memory:")
    sem_tabela.row_factory = sqlite3.Row
    assert cal.carregar_parametros(sem_tabela) == {}
    vazio = sqlite3.connect(":memory:")
    vazio.row_factory = sqlite3.Row
    vazio.executescript(db.SCHEMA)
    assert cal.carregar_parametros(vazio) == {}


def test_gravar_e_carregar_parametros_substitui_a_linha_da_origem(conexao):
    cal.gravar_parametros(conexao, {"poisson": PARAMETROS}, ate_concurso=10)
    cal.gravar_parametros(conexao, {"poisson": {**PARAMETROS, "expoente": 0.7}, "frequencia_global": PARAMETROS}, ate_concurso=12)
    p = cal.carregar_parametros(conexao)
    assert set(p) == {"poisson", "frequencia_global"} and p["poisson"]["expoente"] == 0.7 and p["poisson"]["ate_concurso"] == 12


def test_precisa_recalibrar_sem_parametros_e_quando_entra_concurso_novo(conexao):
    alfa, beta = _jogos_de_historico(conexao)
    assert cal.precisa_recalibrar(conexao) is True  # sem parâmetros
    cal.gravar_parametros(conexao, {"poisson": PARAMETROS}, ate_concurso=1)
    assert cal.precisa_recalibrar(conexao) is False  # em dia com o concurso 1
    conexao.execute("INSERT INTO concursos (numero) VALUES (2)")
    conexao.execute("INSERT INTO jogos (concurso_numero, num_jogo, casa_id, fora_id, gols_casa, gols_fora, resultado) VALUES (2, 1, ?, ?, 1, 0, '1')", (alfa, beta))
    assert cal.precisa_recalibrar(conexao) is True  # entrou o concurso 2


def test_corrigir_percentual_achata_e_soma_100():
    original = {"1": 70.0, "X": 20.0, "2": 10.0}
    frequencia = {"1": 0.46, "X": 0.27, "2": 0.27}
    corrigido = cal.corrigir_percentual(original, "poisson", frequencia, {"expoente": 0.6, "mistura": 0.9})
    assert sum(corrigido.values()) == pytest.approx(100.0)
    assert corrigido["1"] < 70.0 and corrigido["2"] > 10.0  # achatou
    assert max(corrigido, key=corrigido.get) == "1"  # sem trocar o favorito
    sem_correcao = cal.corrigir_percentual(original, "poisson", frequencia, {"expoente": 1.0, "mistura": 1.0})
    assert sem_correcao == pytest.approx(original)


def test_calibrar_jogo_aplica_so_nas_origens_corrigidas_e_explica_o_motivo(conexao, monkeypatch):
    alfa, beta = _jogos_de_historico(conexao)
    cal.gravar_parametros(conexao, {"frequencia_global": PARAMETROS, "poisson": PARAMETROS, "elo_selecoes": PARAMETROS}, ate_concurso=1)
    original = {"1": 60.0, "X": 25.0, "2": 15.0}

    aplicado = cal.calibrar_jogo(conexao, alfa, beta, original)
    assert aplicado["origem"] == "frequencia_global" and aplicado["aplicada"] and aplicado["calibrado"] != original
    assert sum(aplicado["calibrado"].values()) == pytest.approx(100.0)

    monkeypatch.setattr("stats.percentual.origem_do_percentual", lambda c, a, b: {"metodo": "elo_selecoes"})
    elo = cal.calibrar_jogo(conexao, alfa, beta, original)
    assert not elo["aplicada"] and elo["calibrado"] == original and elo["motivo"] == "origem não corrigida"


def test_calibrar_jogo_sem_parametros_ou_com_interruptor_desligado_mantem_o_original(conexao, monkeypatch):
    alfa, beta = _jogos_de_historico(conexao)
    original = {"1": 60.0, "X": 25.0, "2": 15.0}
    sem_parametros = cal.calibrar_jogo(conexao, alfa, beta, original)
    assert not sem_parametros["aplicada"] and sem_parametros["motivo"] == "sem parâmetros gravados" and sem_parametros["calibrado"] == original

    cal.gravar_parametros(conexao, {"frequencia_global": PARAMETROS}, ate_concurso=1)
    monkeypatch.setattr(config, "CALIBRACAO_ATIVA", False)
    desligada = cal.calibrar_jogo(conexao, alfa, beta, original)
    assert not desligada["aplicada"] and desligada["motivo"] == "interruptor desligado" and desligada["calibrado"] == original


def test_calibrar_jogo_sem_nenhum_resultado_para_a_frequencia_nao_corrige(conexao):
    alfa = db.obter_ou_criar_participante(conexao, "ALFA", "clube", "SP")
    beta = db.obter_ou_criar_participante(conexao, "BETA", "clube", "RJ")
    cal.gravar_parametros(conexao, {"frequencia_global": PARAMETROS}, ate_concurso=1)
    r = cal.calibrar_jogo(conexao, alfa, beta, {"1": 50.0, "X": 30.0, "2": 20.0})
    assert not r["aplicada"] and r["motivo"] == "sem frequência de referência"


def test_percentuais_do_jogo_aplica_a_correcao_antes_das_noticias(conexao):
    alfa, beta = _jogos_de_historico(conexao)
    sem = percentuais_do_jogo(conexao, alfa, beta, {})
    assert sem["historico"] == sem["original"] and not sem["calibracao"]["aplicada"]

    cal.gravar_parametros(conexao, {"frequencia_global": PARAMETROS}, ate_concurso=1)
    com = percentuais_do_jogo(conexao, alfa, beta, {})
    assert com["calibracao"]["aplicada"] and com["historico"] != com["original"] and com["original"] == sem["original"]
    assert sum(com["final"].values()) == pytest.approx(100.0)

    com_noticia = percentuais_do_jogo(conexao, alfa, beta, {alfa: {"ajuste": -5.0}})
    assert com_noticia["calibracao"]["calibrado"] == com["historico"]  # a base é a corrigida
    assert com_noticia["ajustado"] and com_noticia["final"]["1"] < com["historico"]["1"]  # o ajuste entra por cima


def test_recalcular_percentuais_gravados_refaz_so_concursos_com_varredura(conexao):
    alfa, beta = _jogos_de_historico(conexao)
    conexao.execute("INSERT INTO concursos (numero, data_limite_aposta) VALUES (2, '2099-01-01')")
    conexao.execute("INSERT INTO jogos (concurso_numero, num_jogo, casa_id, fora_id, data_jogo) VALUES (2, 1, ?, ?, '2099-01-02')", (alfa, beta))
    assert recalcular_percentuais_gravados(conexao) == 0  # nenhuma varredura ainda
    conexao.execute(
        "INSERT INTO fatores_externos (participante_id, concurso_numero, coletado_em, ajuste_aplicado) VALUES (?, 2, '2026-10-01T09:00:00', -3.0)", (alfa,)
    )
    cal.gravar_parametros(conexao, {"frequencia_global": PARAMETROS}, ate_concurso=1)
    assert recalcular_percentuais_gravados(conexao) == 1
    linhas = conexao.execute("SELECT participante_id, percentual_historico, percentual_final FROM percentuais").fetchall()
    assert {l["participante_id"] for l in linhas} == {alfa, beta}
    mandante = next(l for l in linhas if l["participante_id"] == alfa)
    esperado = percentuais_do_jogo(conexao, alfa, beta, {alfa: {"ajuste": -3.0}})
    assert mandante["percentual_historico"] == pytest.approx(esperado["historico"]["1"])  # grava a base corrigida


# ---------------------------------------------------------------- atualizar_tudo


def test_atualizar_calibracao_recalibra_registra_a_execucao_e_nao_repete_em_dia(conexao, monkeypatch):
    _jogos_de_historico(conexao)
    chamadas = []
    monkeypatch.setattr(cal, "recalibrar", lambda c: chamadas.append(1) or {"poisson": PARAMETROS})
    monkeypatch.setattr(atualizar_tudo, "recalcular_percentuais_gravados", lambda c: 0)
    atualizar_tudo._atualizar_calibracao(conexao)
    assert chamadas == [1]
    assert db.ultima_execucao_por_fonte(conexao)["calibracao"]["sucesso"] == 1
    cal.gravar_parametros(conexao, {"poisson": PARAMETROS}, ate_concurso=1)
    atualizar_tudo._atualizar_calibracao(conexao)
    assert chamadas == [1]  # em dia: não refaz


def test_atualizar_calibracao_desligada_nao_faz_nada_e_sem_jogos_falha_com_mensagem(conexao, monkeypatch):
    monkeypatch.setattr(config, "CALIBRACAO_ATIVA", False)
    atualizar_tudo._atualizar_calibracao(conexao)
    assert "calibracao" not in db.ultima_execucao_por_fonte(conexao)
    monkeypatch.setattr(config, "CALIBRACAO_ATIVA", True)
    monkeypatch.setattr(cal, "recalibrar", lambda c: None)
    with pytest.raises(RuntimeError, match="sem jogos apurados suficientes"):
        atualizar_tudo._atualizar_calibracao(conexao)


def test_falha_na_calibracao_nao_impede_as_outras_fontes(conexao, monkeypatch):
    monkeypatch.setattr(atualizar_tudo, "_atualizar_caixa", lambda c: None)
    monkeypatch.setattr(atualizar_tudo, "_atualizar_cbf", lambda c: None)
    monkeypatch.setattr(atualizar_tudo, "_atualizar_noticias", lambda c: db.registrar_execucao(c, "noticias", True, 5))

    def quebra(_):
        raise RuntimeError("falha de teste")

    monkeypatch.setattr(atualizar_tudo, "_atualizar_calibracao", quebra)
    class SemFechar:  # o main() fecha a conexão ao terminar; o teste ainda precisa ler o banco depois
        def __getattr__(self, nome):
            return getattr(conexao, nome)

        def close(self):
            pass

    monkeypatch.setattr(atualizar_tudo.db, "inicializar_schema", lambda: None)
    monkeypatch.setattr(atualizar_tudo.db, "conectar", lambda: SemFechar())
    assert atualizar_tudo.main() == 1  # uma falha
    execucoes = db.ultima_execucao_por_fonte(conexao)
    assert execucoes["calibracao"]["sucesso"] == 0 and "falha de teste" in execucoes["calibracao"]["erro"]
    assert execucoes["noticias"]["sucesso"] == 1  # as outras seguiram


# ---------------------------------------------------------------- apresentação


def _calculo(aplicada, motivo=None, origem="poisson"):
    return {
        "original": {"1": 70.0, "X": 20.0, "2": 10.0}, "historico": {"1": 62.0, "X": 24.0, "2": 14.0}, "final": {"1": 60.0, "X": 25.0, "2": 15.0},
        "calibracao": {"aplicada": aplicada, "motivo": motivo, "origem": origem, "expoente": 0.6, "mistura": 0.95},
    }


def test_frases_da_correcao_cobrem_todos_os_casos():
    sys.path.insert(0, str(RAIZ / "app"))
    import calibracao_ui as ui

    assert ui.frase_da_correcao({"aplicada": True, "expoente": 0.6, "mistura": 0.95, "motivo": None}) == "corrigido (expoente 0,60, mistura 0,95)"
    assert "Elo das seleções já está calibrado" in ui.frase_da_correcao({"aplicada": False, "motivo": "origem não corrigida"})
    assert "LOTECA_CALIBRACAO=0" in ui.frase_da_correcao({"aplicada": False, "motivo": "interruptor desligado"})
    assert "ainda não calculados" in ui.frase_da_correcao({"aplicada": False, "motivo": "sem parâmetros gravados"})
    assert ui.frase_da_correcao({"aplicada": False, "motivo": "outro"}) == "sem correção"


def test_linhas_do_quadro_escapam_html_e_trazem_as_tres_camadas():
    sys.path.insert(0, str(RAIZ / "app"))
    import calibracao_ui as ui

    jogos = [{"id": 1, "num_jogo": 3, "casa": "<b>ALFA</b>", "fora": "BETA & Cia"}]
    linhas = ui.linhas_calibracao(jogos, {1: _calculo(True)})
    assert len(linhas[0]) == len(ui.CABECALHOS)
    assert "&lt;b&gt;ALFA&lt;/b&gt;" in linhas[0][0] and "BETA &amp; Cia" in linhas[0][0]
    assert linhas[0][1:5] == ["Histórico dos clubes", "70 / 20 / 10", "62 / 24 / 14", "60 / 25 / 15"]


def test_resumo_do_concurso_nos_tres_casos(monkeypatch):
    sys.path.insert(0, str(RAIZ / "app"))
    import calibracao_ui as ui

    assert "2 de 3 jogos tiveram o percentual corrigido" in ui.resumo_do_concurso({1: _calculo(True), 2: _calculo(True), 3: _calculo(False, "origem não corrigida")})
    assert "Nenhum jogo deste concurso foi corrigido" in ui.resumo_do_concurso({1: _calculo(False, "sem parâmetros gravados")})
    monkeypatch.setattr(config, "CALIBRACAO_ATIVA", False)
    assert "calibração está desligada" in ui.resumo_do_concurso({1: _calculo(False, "interruptor desligado")})


def test_pagina_concurso_atual_mostra_a_calibracao(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DB_PATH", tmp_path / "sintetico.db")
    for pasta in (str(RAIZ), str(RAIZ / "app")):
        if pasta not in sys.path:
            sys.path.insert(0, pasta)
    db.inicializar_schema()
    with db.sessao() as c:
        alfa = db.obter_ou_criar_participante(c, "ALFA", "clube", "SP")
        beta = db.obter_ou_criar_participante(c, "BETA", "clube", "RJ")
        c.execute("INSERT INTO concursos (numero, data_apuracao, data_limite_aposta) VALUES (9001, '2026-03-05', '2026-03-01')")
        c.execute("INSERT INTO concursos (numero, data_limite_aposta, horario_fim_apostas) VALUES (9002, '2099-01-01', 15)")
        for num, casa, fora, gc, gf, res in [(1, alfa, beta, 2, 0, "1"), (2, beta, alfa, 1, 1, "X"), (3, alfa, beta, 0, 1, "2")]:
            c.execute("INSERT INTO jogos (concurso_numero, num_jogo, casa_id, fora_id, gols_casa, gols_fora, resultado, data_jogo)"
                      " VALUES (9001, ?, ?, ?, ?, ?, ?, '2026-03-02')", (num, casa, fora, gc, gf, res))
        c.execute("INSERT INTO jogos (concurso_numero, num_jogo, casa_id, fora_id, data_jogo) VALUES (9002, 1, ?, ?, '2099-01-02')", (alfa, beta))
        cal.gravar_parametros(c, {"frequencia_global": PARAMETROS}, ate_concurso=9001)

    at = AppTest.from_file(str(PAGINA), default_timeout=90).run()
    assert not at.exception, [e.value for e in at.exception]
    legendas = " ".join(c.value for c in at.caption)
    assert "1 de 1 jogos tiveram o percentual corrigido pela calibração" in legendas
    expansor = next(e for e in at.expander if "Ver como cada percentual foi corrigido" in e.label)
    texto = " ".join(m.value for m in expansor.markdown)
    assert "Frequência simples (poucos jogos)" in texto and "corrigido (expoente 0,60, mistura 0,90)" in texto

    monkeypatch.setattr(config, "CALIBRACAO_ATIVA", False)
    at = AppTest.from_file(str(PAGINA), default_timeout=90).run()
    assert not at.exception, [e.value for e in at.exception]
    assert "A calibração está desligada" in " ".join(c.value for c in at.caption)
