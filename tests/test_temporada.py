import sqlite3

import db
from stats.temporada import desempenho_no_ano, resumo_curto


def _conexao_com_dado():
    conexao = sqlite3.connect(":memory:")
    conexao.row_factory = sqlite3.Row
    conexao.executescript(db.SCHEMA)
    time_a = db.obter_ou_criar_participante(conexao, "TIME A", "clube", "SP")
    time_b = db.obter_ou_criar_participante(conexao, "TIME B", "clube", "RJ")
    conexao.execute("INSERT INTO concursos (numero) VALUES (1)")
    conexao.execute(
        "INSERT INTO jogos (concurso_numero, num_jogo, casa_id, fora_id, gols_casa, gols_fora, resultado, data_jogo) "
        "VALUES (1, 1, ?, ?, 2, 0, '1', '2026-03-01')",
        (time_a, time_b),
    )
    conexao.execute(
        "INSERT INTO jogos (concurso_numero, num_jogo, casa_id, fora_id, gols_casa, gols_fora, resultado, data_jogo) "
        "VALUES (1, 2, ?, ?, 1, 1, 'X', '2024-03-01')",
        (time_b, time_a),
    )
    return conexao, time_a


def test_filtra_so_o_ano_pedido():
    conexao, time_a = _conexao_com_dado()
    desempenho = desempenho_no_ano(conexao, time_a, ano=2026)
    assert desempenho["jogos"] == 1
    assert desempenho["vitorias"] == 1
    assert desempenho["empates"] == 0


def test_ano_sem_jogo_retorna_zero():
    conexao, time_a = _conexao_com_dado()
    desempenho = desempenho_no_ano(conexao, time_a, ano=2020)
    assert desempenho["jogos"] == 0
    assert "sem jogos" in resumo_curto(desempenho)


def test_resumo_curto_formata_v_e_d():
    conexao, time_a = _conexao_com_dado()
    desempenho = desempenho_no_ano(conexao, time_a, ano=2026)
    assert resumo_curto(desempenho) == "2026: 1V 0E 0D"
