"""Conexão e schema do banco SQLite local. Um arquivo só, sem servidor."""
import sqlite3
from contextlib import contextmanager

import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS concursos (
    numero INTEGER PRIMARY KEY,
    data_apuracao TEXT,
    data_limite_aposta TEXT,
    data_proximo TEXT,
    tipo TEXT NOT NULL DEFAULT 'regular',
    acumulado INTEGER,
    valor_estimado_proximo REAL
);

CREATE TABLE IF NOT EXISTS participantes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL,
    tipo TEXT NOT NULL CHECK (tipo IN ('clube', 'selecao')),
    pais_ou_uf TEXT,
    UNIQUE(nome, tipo)
);

CREATE TABLE IF NOT EXISTS jogos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    concurso_numero INTEGER NOT NULL REFERENCES concursos(numero),
    num_jogo INTEGER NOT NULL,
    casa_id INTEGER NOT NULL REFERENCES participantes(id),
    fora_id INTEGER NOT NULL REFERENCES participantes(id),
    gols_casa INTEGER,
    gols_fora INTEGER,
    resultado TEXT CHECK (resultado IN ('1', 'X', '2')),
    campeonato TEXT,
    data_jogo TEXT,
    situacao TEXT NOT NULL DEFAULT 'normal' CHECK (situacao IN ('normal', 'suspenso', 'sorteio')),
    UNIQUE(concurso_numero, num_jogo)
);

CREATE TABLE IF NOT EXISTS premiacoes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    concurso_numero INTEGER NOT NULL REFERENCES concursos(numero),
    faixa INTEGER NOT NULL,
    pontos INTEGER,
    ganhadores INTEGER,
    valor_premio REAL,
    UNIQUE(concurso_numero, faixa)
);

CREATE TABLE IF NOT EXISTS percentuais (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    jogo_id INTEGER NOT NULL REFERENCES jogos(id),
    participante_id INTEGER NOT NULL REFERENCES participantes(id),
    percentual_historico REAL NOT NULL,
    ajuste_externo REAL NOT NULL DEFAULT 0,
    percentual_final REAL NOT NULL,
    calculado_em TEXT NOT NULL,
    UNIQUE(jogo_id, participante_id)
);

CREATE TABLE IF NOT EXISTS fatores_externos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    participante_id INTEGER NOT NULL REFERENCES participantes(id),
    concurso_numero INTEGER NOT NULL REFERENCES concursos(numero),
    coletado_em TEXT NOT NULL,
    resumo TEXT,
    fontes TEXT,
    ajuste_aplicado REAL NOT NULL DEFAULT 0,
    sinal TEXT
);

-- Bootstrap: histórico agregado 1/X/2 do dataset aberto ValorFinal (sem nome de time).
-- Serve só para a frequência global até o importador da CAIXA preencher `jogos`.
CREATE TABLE IF NOT EXISTS historico_valorfinal (
    concurso INTEGER NOT NULL,
    num_jogo INTEGER NOT NULL,
    resultado TEXT NOT NULL CHECK (resultado IN ('1', 'X', '2')),
    PRIMARY KEY (concurso, num_jogo)
);
"""


def conectar() -> sqlite3.Connection:
    conexao = sqlite3.connect(config.DB_PATH)
    conexao.row_factory = sqlite3.Row
    conexao.execute("PRAGMA foreign_keys = ON")
    return conexao


def inicializar_schema() -> None:
    with conectar() as conexao:
        conexao.executescript(SCHEMA)


@contextmanager
def sessao():
    conexao = conectar()
    try:
        yield conexao
        conexao.commit()
    finally:
        conexao.close()


def obter_ou_criar_participante(conexao: sqlite3.Connection, nome: str, tipo: str, pais_ou_uf: str | None = None) -> int:
    linha = conexao.execute(
        "SELECT id FROM participantes WHERE nome = ? AND tipo = ?", (nome, tipo)
    ).fetchone()
    if linha:
        return linha["id"]
    cursor = conexao.execute(
        "INSERT INTO participantes (nome, tipo, pais_ou_uf) VALUES (?, ?, ?)",
        (nome, tipo, pais_ou_uf),
    )
    return cursor.lastrowid
