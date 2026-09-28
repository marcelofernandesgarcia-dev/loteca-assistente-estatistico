import sqlite3

import db
from stats.concursos import concurso_a_jogar, ultimo_encerrado


def _conexao():
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    c.executescript(db.SCHEMA)
    a = db.obter_ou_criar_participante(c, "A", "clube", "SP")
    b = db.obter_ou_criar_participante(c, "B", "clube", "RJ")
    return c, a, b


def _jogo(c, concurso, casa, fora, resultado):
    c.execute("INSERT OR IGNORE INTO concursos (numero, data_limite_aposta, horario_fim_apostas) VALUES (?, '2026-09-26', 15)", (concurso,))
    c.execute(
        "INSERT INTO jogos (concurso_numero, num_jogo, casa_id, fora_id, resultado) VALUES (?, 1, ?, ?, ?)",
        (concurso, casa, fora, resultado),
    )


def test_a_jogar_e_o_maior_concurso_com_jogo_sem_resultado():
    c, a, b = _conexao()
    _jogo(c, 1271, a, b, "1")
    _jogo(c, 1272, a, b, None)
    assert concurso_a_jogar(c)["numero"] == 1272
    assert concurso_a_jogar(c)["horario_fim_apostas"] == 15
    assert ultimo_encerrado(c) == 1271


def test_sem_concurso_aberto_devolve_none():
    c, a, b = _conexao()
    _jogo(c, 1271, a, b, "X")
    assert concurso_a_jogar(c) is None


def test_banco_vazio():
    c, _, _ = _conexao()
    assert concurso_a_jogar(c) is None and ultimo_encerrado(c) is None
