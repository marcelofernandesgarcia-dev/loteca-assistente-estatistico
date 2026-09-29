import sqlite3

import pytest

import db
from importer.unificar_participantes import candidatos_a_duplicidade, unificar
from stats import resultado
from stats.resultado import carregar_apelidos, identidade_participante, limpar_nome


@pytest.fixture()
def conexao():
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    c.executescript(db.SCHEMA)
    return c


@pytest.fixture()
def apelidos(tmp_path, monkeypatch):
    arquivo = tmp_path / "apelidos.csv"
    arquivo.write_text(
        "# comentário\nvariante;uf;canonico;justificativa\nS. FICTICIO;SP;FICTICIO;abreviação antiga do mesmo clube\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(resultado.config, "APELIDOS_PARTICIPANTES_CSV", arquivo)
    carregar_apelidos.cache_clear()
    yield
    carregar_apelidos.cache_clear()


def test_limpar_nome_junta_espacos_repetidos():
    assert limpar_nome("SAO  CAETANO") == "SAO CAETANO"
    assert limpar_nome("  SERVIA/SER ") == "SERVIA"


def test_apelido_vale_so_para_a_uf_indicada(apelidos):
    assert identidade_participante("S. FICTICIO", "SP")["nome"] == "FICTICIO"
    assert identidade_participante("S. FICTICIO", "RJ")["nome"] == "S. FICTICIO"
    assert identidade_participante("S. FICTICIO", None)["nome"] == "S. FICTICIO"


def _jogo(c, concurso, num, casa, fora, gc=1, gf=0):
    c.execute("INSERT OR IGNORE INTO concursos (numero) VALUES (?)", (concurso,))
    c.execute(
        "INSERT INTO jogos (concurso_numero, num_jogo, casa_id, fora_id, gols_casa, gols_fora, resultado)"
        " VALUES (?, ?, ?, ?, ?, ?, '1')", (concurso, num, casa, fora, gc, gf),
    )


def test_unificar_junta_variantes_move_jogos_e_e_idempotente(conexao, apelidos):
    novo = db.obter_ou_criar_participante(conexao, "FICTICIO", "clube", "SP")
    antigo = db.obter_ou_criar_participante(conexao, "S. FICTICIO", "clube", "SP")
    espaco = db.obter_ou_criar_participante(conexao, "TIME  DOIS", "clube", "RJ")
    outro = db.obter_ou_criar_participante(conexao, "OUTRO", "clube", "MG")
    _jogo(conexao, 1, 1, novo, outro)
    _jogo(conexao, 2, 1, antigo, outro)
    _jogo(conexao, 3, 1, outro, antigo)
    _jogo(conexao, 4, 1, espaco, outro)

    relatorio = unificar(conexao)
    nomes = sorted(r["nome"] for r in conexao.execute("SELECT nome FROM participantes"))
    assert nomes == ["FICTICIO", "OUTRO", "TIME DOIS"]
    assert conexao.execute("SELECT COUNT(*) FROM jogos WHERE casa_id = ? OR fora_id = ?", (novo, novo)).fetchone()[0] == 3
    assert [r["canonico"] for r in relatorio] == ["FICTICIO"] and relatorio[0]["jogos_afetados"] == 2
    assert unificar(conexao) == []  # segunda passada não muda nada


def test_unificar_nao_junta_mesmo_nome_de_ufs_diferentes(conexao):
    a = db.obter_ou_criar_participante(conexao, "ATLETICO", "clube", "MG")
    b = db.obter_ou_criar_participante(conexao, "ATLETICO", "clube", "GO")
    assert unificar(conexao) == []
    assert conexao.execute("SELECT COUNT(*) FROM participantes").fetchone()[0] == 2 and a != b


def test_unificar_preserva_o_pareamento_com_a_cbf(conexao, apelidos):
    novo = db.obter_ou_criar_participante(conexao, "FICTICIO", "clube", "SP")
    antigo = db.obter_ou_criar_participante(conexao, "S. FICTICIO", "clube", "SP")
    conexao.execute("INSERT INTO cbf_times (cod_time, nome) VALUES (10, 'Ficticio FC')")
    conexao.execute("INSERT INTO mapa_cbf_participante (participante_id, cod_time, metodo) VALUES (?, 10, 'teste')", (antigo,))
    unificar(conexao)
    mapa = conexao.execute("SELECT participante_id FROM mapa_cbf_participante").fetchall()
    assert [m["participante_id"] for m in mapa] == [novo]


def test_candidatos_listam_nomes_parecidos_da_mesma_uf_que_nunca_jogam_juntos(conexao):
    a = db.obter_ou_criar_participante(conexao, "ATHLETICO", "clube", "PR")
    b = db.obter_ou_criar_participante(conexao, "ATLETICO", "clube", "PR")
    c = db.obter_ou_criar_participante(conexao, "PARANA", "clube", "PR")
    d = db.obter_ou_criar_participante(conexao, "PARANAENSE", "clube", "PR")
    x = db.obter_ou_criar_participante(conexao, "XAVANTE", "clube", "SP")
    _jogo(conexao, 1, 1, a, x)
    _jogo(conexao, 2, 1, b, x)
    _jogo(conexao, 3, 1, c, d)  # jogam juntos: são times diferentes
    pares = {(p["a"], p["b"]) for p in candidatos_a_duplicidade(conexao)}
    assert ("ATHLETICO", "ATLETICO") in pares
    assert ("PARANA", "PARANAENSE") not in pares
