import sqlite3

import db
from stats.desempenho import (
    aproveitamento_casa_fora,
    contagem_por_resultado,
    gerar_insight,
    kpis,
    tendencia_por_ano,
)


def _conexao():
    conexao = sqlite3.connect(":memory:")
    conexao.row_factory = sqlite3.Row
    conexao.executescript(db.SCHEMA)
    a = db.obter_ou_criar_participante(conexao, "TIME A", "clube", "SP")
    b = db.obter_ou_criar_participante(conexao, "TIME B", "clube", "RJ")
    conexao.execute("INSERT INTO concursos (numero) VALUES (1)")
    return conexao, a, b


def _jogo(conexao, num, casa, fora, gc, gf, resultado, data, campeonato="PRINCIPAL"):
    conexao.execute(
        "INSERT INTO jogos (concurso_numero, num_jogo, casa_id, fora_id, gols_casa, gols_fora, resultado, data_jogo, campeonato) "
        "VALUES (1, ?, ?, ?, ?, ?, ?, ?, ?)",
        (num, casa, fora, gc, gf, resultado, data, campeonato),
    )


def test_amostra_vazia_nao_quebra():
    conexao, a, _ = _conexao()
    assert contagem_por_resultado(conexao, a)["jogos"] == 0
    assert aproveitamento_casa_fora(conexao, a) == {"casa": 0.0, "fora": 0.0, "jogos_casa": 0, "jogos_fora": 0}
    assert tendencia_por_ano(conexao, a) == []


def test_so_vitorias():
    conexao, a, b = _conexao()
    _jogo(conexao, 1, a, b, 2, 0, "1", "2026-01-01")
    _jogo(conexao, 2, b, a, 0, 3, "2", "2026-02-01")
    contagem = contagem_por_resultado(conexao, a)
    assert contagem["vitorias"] == 2 and contagem["empates"] == 0 and contagem["derrotas"] == 0
    assert contagem["pct_vitorias"] == 100.0


def test_mix_de_resultados_e_kpis():
    conexao, a, b = _conexao()
    _jogo(conexao, 1, a, b, 2, 1, "1", "2026-01-01")   # V
    _jogo(conexao, 2, a, b, 1, 1, "X", "2026-02-01")   # E
    _jogo(conexao, 3, b, a, 3, 0, "1", "2026-03-01")   # D (A visitante perdeu)
    contagem = contagem_por_resultado(conexao, a)
    assert (contagem["vitorias"], contagem["empates"], contagem["derrotas"]) == (1, 1, 1)
    k = kpis(conexao, a)
    assert k["jogos"] == 3
    assert k["gols_marcados"] == 3  # 2 + 1 + 0
    assert k["gols_sofridos"] == 5  # 1 + 1 + 3
    assert k["saldo"] == -2


def test_aproveitamento_casa_fora_separa_corretamente():
    conexao, a, b = _conexao()
    _jogo(conexao, 1, a, b, 1, 0, "1", "2026-01-01")  # A ganha em casa
    _jogo(conexao, 2, a, b, 0, 1, "2", "2026-02-01")  # A perde em casa
    _jogo(conexao, 3, b, a, 0, 2, "2", "2026-03-01")  # A ganha fora
    resultado = aproveitamento_casa_fora(conexao, a)
    assert resultado["casa"] == 50.0
    assert resultado["fora"] == 100.0


def test_filtro_por_ano_e_campeonato():
    conexao, a, b = _conexao()
    _jogo(conexao, 1, a, b, 1, 0, "1", "2025-01-01", campeonato="COPA")
    _jogo(conexao, 2, a, b, 1, 0, "1", "2026-01-01", campeonato="PRINCIPAL")
    assert contagem_por_resultado(conexao, a, ano=2026)["jogos"] == 1
    assert contagem_por_resultado(conexao, a, campeonato="COPA")["jogos"] == 1
    assert contagem_por_resultado(conexao, a, ano=2025, campeonato="PRINCIPAL")["jogos"] == 0


def test_filtro_de_mando_separa_casa_e_fora():
    conexao, a, b = _conexao()
    _jogo(conexao, 1, a, b, 2, 0, "1", "2026-01-01")  # A em casa, vence
    _jogo(conexao, 2, b, a, 1, 0, "1", "2026-02-01")  # A fora, perde
    assert contagem_por_resultado(conexao, a, mando="casa")["vitorias"] == 1
    assert contagem_por_resultado(conexao, a, mando="casa")["derrotas"] == 0
    assert contagem_por_resultado(conexao, a, mando="fora")["derrotas"] == 1
    assert kpis(conexao, a, mando="fora")["gols_marcados"] == 0
    assert kpis(conexao, a, mando="casa")["gols_marcados"] == 2


def test_tendencia_por_ano_agrupa_por_ano_civil():
    conexao, a, b = _conexao()
    _jogo(conexao, 1, a, b, 1, 0, "1", "2025-01-01")
    _jogo(conexao, 2, a, b, 0, 1, "2", "2025-06-01")
    _jogo(conexao, 3, a, b, 2, 0, "1", "2026-01-01")
    tendencia = tendencia_por_ano(conexao, a)
    assert [t["ano"] for t in tendencia] == ["2025", "2026"]
    assert tendencia[0]["pct_aproveitamento"] == 50.0
    assert tendencia[1]["pct_aproveitamento"] == 100.0


def test_insight_diferenca_casa_fora():
    texto = gerar_insight(
        {"casa": 80.0, "fora": 20.0, "jogos_casa": 5, "jogos_fora": 5},
        {"jogos": 10, "vitorias": 5, "pct_vitorias": 50.0},
    )
    assert "em casa" in texto


def test_insight_sem_vitoria():
    texto = gerar_insight(
        {"casa": 0.0, "fora": 0.0, "jogos_casa": 3, "jogos_fora": 2},
        {"jogos": 5, "vitorias": 0, "pct_vitorias": 0.0},
    )
    assert "Nenhuma vitória" in texto


def test_insight_amostra_pequena_nao_inventa_padrao():
    texto = gerar_insight(
        {"casa": 100.0, "fora": 0.0, "jogos_casa": 1, "jogos_fora": 1},
        {"jogos": 2, "vitorias": 1, "pct_vitorias": 50.0},
    )
    assert "Sem padrão forte" in texto
