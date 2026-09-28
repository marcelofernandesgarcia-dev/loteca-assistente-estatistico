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


def test_origem_do_percentual_diz_quando_cai_na_frequencia_global():
    import sqlite3

    import db
    from stats.percentual import origem_do_percentual

    conexao = sqlite3.connect(":memory:")
    conexao.row_factory = sqlite3.Row
    conexao.executescript(db.SCHEMA)
    a = db.obter_ou_criar_participante(conexao, "TIME A", "clube", "SP")
    b = db.obter_ou_criar_participante(conexao, "TIME B", "clube", "RJ")
    conexao.execute("INSERT INTO concursos (numero) VALUES (1)")
    origem = origem_do_percentual(conexao, a, b)
    assert origem["metodo"] == "frequencia_global" and origem["menor_amostra"] == 0
    for n in range(1, 7):
        for casa, fora in ((a, b), (b, a)):
            conexao.execute(
                "INSERT INTO jogos (concurso_numero, num_jogo, casa_id, fora_id, gols_casa, gols_fora, resultado)"
                " VALUES (1, ?, ?, ?, 1, 0, '1')", (n * 10 + (casa == a), casa, fora),
            )
    assert origem_do_percentual(conexao, a, b)["metodo"] == "poisson"


def _base_loteca():
    import sqlite3

    import db

    conexao = sqlite3.connect(":memory:")
    conexao.row_factory = sqlite3.Row
    conexao.executescript(db.SCHEMA)
    a = db.obter_ou_criar_participante(conexao, "TIME A", "clube", "SP")
    b = db.obter_ou_criar_participante(conexao, "TIME B", "clube", "RJ")
    conexao.execute("INSERT INTO concursos (numero) VALUES (1)")
    return conexao, a, b


def test_jogos_da_loteca_ordena_e_marca_mando_e_resultado():
    from stats.desempenho import jogos_da_loteca

    conexao, a, b = _base_loteca()
    linhas = [(1, a, b, 2, 0, "2026-03-02", "normal"), (2, b, a, 1, 1, "2026-03-01", "normal"),
              (3, b, a, 3, 0, "2026-03-09", "sorteio"), (4, a, b, None, None, "2026-03-20", "normal")]
    for num, casa, fora, gc, gf, data, situacao in linhas:
        conexao.execute(
            "INSERT INTO jogos (concurso_numero, num_jogo, casa_id, fora_id, gols_casa, gols_fora, data_jogo, situacao)"
            " VALUES (1, ?, ?, ?, ?, ?, ?, ?)", (num, casa, fora, gc, gf, data, situacao),
        )
    jogos = jogos_da_loteca(conexao, a)
    assert [(j["data"], j["mando"], j["resultado"]) for j in jogos] == [
        ("2026-03-01", "fora", "E"), ("2026-03-02", "casa", "V"), ("2026-03-09", "fora", "D")]
    assert jogos[2]["sorteio"] is True and jogos[0]["adversario_id"] == b


def test_frases_da_loteca_sinalizam_amostra_pequena_e_comparam_com_a_media():
    from stats.desempenho import frases_da_loteca

    jogos = [{"resultado": "V", "pontos": 3, "gols_pro": 2, "gols_contra": 0}] * 3
    por_mando = {"mandante": {"1": 3, "X": 0, "2": 0, "total": 3}, "visitante": {"1": 0, "X": 0, "2": 0, "total": 0}}
    frases = frases_da_loteca(jogos, por_mando, {"1": 0.47, "X": 0.26, "2": 0.27})
    texto = " ".join(frases)
    assert "3 jogos, 3V 0E 0D, 6 gols marcados e 0 sofridos" in texto
    assert "Amostra pequena" in texto and "3 vitórias seguidas" in texto
    assert "Como mandante" not in texto  # menos de 5 jogos: sem comparação
    grande = {"mandante": {"1": 6, "X": 2, "2": 2, "total": 10}, "visitante": {"1": 0, "X": 0, "2": 0, "total": 0}}
    assert "Como mandante, a vitória saiu em 60% dos 10 jogos, contra 47%" in " ".join(
        frases_da_loteca(jogos, grande, {"1": 0.47, "X": 0.26, "2": 0.27}))


def test_frases_da_loteca_sem_jogos_nao_inventam_nada():
    from stats.desempenho import frases_da_loteca

    assert frases_da_loteca([], {}, {}) == []
