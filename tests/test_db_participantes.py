import sqlite3

import config
import db


def _memoria():
    conexao = sqlite3.connect(":memory:")
    conexao.row_factory = sqlite3.Row
    conexao.executescript(db.SCHEMA)
    return conexao


def test_homonimos_de_estados_diferentes_sao_participantes_distintos():
    conexao = _memoria()
    mg = db.obter_ou_criar_participante(conexao, "ATLETICO", "clube", "MG")
    go = db.obter_ou_criar_participante(conexao, "ATLETICO", "clube", "GO")
    assert mg != go
    assert db.obter_ou_criar_participante(conexao, "ATLETICO", "clube", "MG") == mg


SCHEMA_ANTIGO = """
CREATE TABLE concursos (numero INTEGER PRIMARY KEY, data_apuracao TEXT, data_limite_aposta TEXT,
    data_proximo TEXT, tipo TEXT NOT NULL DEFAULT 'regular', acumulado INTEGER, valor_estimado_proximo REAL);
CREATE TABLE participantes (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT NOT NULL,
    tipo TEXT NOT NULL, pais_ou_uf TEXT, UNIQUE(nome, tipo));
CREATE TABLE jogos (id INTEGER PRIMARY KEY AUTOINCREMENT, concurso_numero INTEGER NOT NULL,
    num_jogo INTEGER NOT NULL, casa_id INTEGER NOT NULL, fora_id INTEGER NOT NULL);
"""


def test_migracao_recria_participantes_com_backup(tmp_path, monkeypatch):
    caminho = tmp_path / "antigo.db"
    monkeypatch.setattr(config, "DB_PATH", caminho)
    antigo = sqlite3.connect(caminho)
    antigo.executescript(SCHEMA_ANTIGO)
    antigo.execute("INSERT INTO concursos (numero) VALUES (1)")
    antigo.execute("INSERT INTO participantes (nome, tipo, pais_ou_uf) VALUES ('ATLETICO', 'clube', 'MG')")
    antigo.commit()
    antigo.close()

    db.inicializar_schema()

    assert list(tmp_path.glob("antigo.db.bak-*")), "deveria ter criado backup antes de migrar"
    with db.sessao() as conexao:
        assert conexao.execute("SELECT COUNT(*) FROM participantes").fetchone()[0] == 0
        assert conexao.execute("SELECT COUNT(*) FROM concursos").fetchone()[0] == 1  # concursos preservados
        mg = db.obter_ou_criar_participante(conexao, "ATLETICO", "clube", "MG")
        go = db.obter_ou_criar_participante(conexao, "ATLETICO", "clube", "GO")
        assert mg != go


def test_banco_ja_migrado_nao_gera_novo_backup(tmp_path, monkeypatch):
    caminho = tmp_path / "novo.db"
    monkeypatch.setattr(config, "DB_PATH", caminho)
    db.inicializar_schema()
    db.inicializar_schema()
    assert not list(tmp_path.glob("novo.db.bak-*"))
