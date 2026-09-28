"""Conexão e schema do banco SQLite local. Um arquivo só, sem servidor."""
import datetime as dt
import shutil
import sqlite3
from contextlib import contextmanager

import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS concursos (
    numero INTEGER PRIMARY KEY,
    data_apuracao TEXT,
    data_limite_aposta TEXT,
    horario_fim_apostas INTEGER,
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
    UNIQUE(nome, tipo, pais_ou_uf)
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
    sinal TEXT,
    evidencias TEXT
);

-- Dados lidos das páginas públicas da CBF (ver docs/cbf-fonte-de-dados.md).
-- Ficam só neste banco local (loteca.db não vai para o GitHub).
CREATE TABLE IF NOT EXISTS cbf_times (
    cod_time INTEGER PRIMARY KEY,
    nome TEXT NOT NULL,
    uf TEXT
);

CREATE TABLE IF NOT EXISTS cbf_classificacao (
    serie TEXT NOT NULL,
    ano INTEGER NOT NULL,
    cod_time INTEGER NOT NULL REFERENCES cbf_times(cod_time),
    rodada INTEGER NOT NULL,
    posicao INTEGER,
    pontos INTEGER,
    jogos INTEGER,
    vitorias INTEGER,
    empates INTEGER,
    derrotas INTEGER,
    gols_pro INTEGER,
    gols_contra INTEGER,
    saldo INTEGER,
    cartoes_amarelo INTEGER,
    cartoes_vermelho INTEGER,
    aproveitamento REAL,
    ultimos_jogos TEXT,
    proximo_adversario TEXT,
    proximo_adversario_id INTEGER,
    coletado_em TEXT NOT NULL,
    PRIMARY KEY (serie, ano, cod_time, rodada)
);

CREATE TABLE IF NOT EXISTS cbf_estatisticas_time (
    serie TEXT NOT NULL,
    ano INTEGER NOT NULL,
    cod_time INTEGER NOT NULL REFERENCES cbf_times(cod_time),
    jogos_disputados INTEGER,
    gols_feitos INTEGER,
    gols_sofridos INTEGER,
    jogos_sem_sofrer_gol INTEGER,
    cartoes_amarelos INTEGER,
    cartoes_vermelhos INTEGER,
    coletado_em TEXT NOT NULL,
    PRIMARY KEY (serie, ano, cod_time)
);

CREATE TABLE IF NOT EXISTS cbf_partidas (
    id_jogo INTEGER PRIMARY KEY,
    serie TEXT NOT NULL,
    ano INTEGER NOT NULL,
    rodada INTEGER,
    data_jogo TEXT,
    hora TEXT,
    local TEXT,
    mandante_id INTEGER NOT NULL,
    visitante_id INTEGER NOT NULL,
    gols_mandante INTEGER,
    gols_visitante INTEGER,
    penaltis_mandante INTEGER,
    penaltis_visitante INTEGER,
    coletado_em TEXT NOT NULL
);

-- Pareamento entre participante da Loteca e time da CBF (só clubes brasileiros).
CREATE TABLE IF NOT EXISTS mapa_cbf_participante (
    participante_id INTEGER PRIMARY KEY REFERENCES participantes(id),
    cod_time INTEGER NOT NULL REFERENCES cbf_times(cod_time),
    metodo TEXT NOT NULL
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


def _precisa_migrar_participantes(conexao: sqlite3.Connection) -> bool:
    linha = conexao.execute(
        "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 'participantes'"
    ).fetchone()
    return bool(linha) and "UNIQUE(nome, tipo, pais_ou_uf)" not in linha["sql"]


def _migrar_participantes(conexao: sqlite3.Connection) -> None:
    """Versões antigas tratavam 'ATLETICO' (MG) e 'ATLETICO' (GO) como o mesmo
    participante, misturando estatísticas. Recria as tabelas que dependem de
    participante; os jogos são reimportados da CAIXA (o banco é cache
    regenerável). `concursos` e `premiacoes` ficam."""
    for tabela in ("percentuais", "fatores_externos", "mapa_cbf_participante", "jogos", "participantes"):
        conexao.execute(f"DROP TABLE IF EXISTS {tabela}")


def _garantir_colunas(conexao: sqlite3.Connection) -> None:
    """Bancos criados antes de uma coluna existir ganham a coluna sem perder dado."""
    novas = {
        "concursos": [("horario_fim_apostas", "INTEGER")],
        "cbf_classificacao": [("proximo_adversario_id", "INTEGER")],
        "fatores_externos": [("evidencias", "TEXT")],
    }
    for tabela, colunas in novas.items():
        existentes = {linha["name"] for linha in conexao.execute(f"PRAGMA table_info({tabela})")}
        for nome, tipo in colunas:
            if nome not in existentes:
                conexao.execute(f"ALTER TABLE {tabela} ADD COLUMN {nome} {tipo}")


def limpar_participantes_orfaos(conexao: sqlite3.Connection) -> int:
    """Remove participantes que nenhum jogo, pareamento CBF ou bilhete usa
    mais (sobras de mudança na identidade/normalização de nomes)."""
    cursor = conexao.execute(
        """
        DELETE FROM participantes
        WHERE id NOT IN (SELECT casa_id FROM jogos UNION SELECT fora_id FROM jogos)
          AND id NOT IN (SELECT participante_id FROM mapa_cbf_participante)
          AND id NOT IN (SELECT participante_id FROM fatores_externos)
          AND id NOT IN (SELECT participante_id FROM percentuais)
        """
    )
    return cursor.rowcount


def inicializar_schema() -> None:
    conexao = conectar()
    try:
        if _precisa_migrar_participantes(conexao):
            conexao.close()
            copia = config.DB_PATH.with_name(
                f"{config.DB_PATH.name}.bak-{dt.datetime.now().strftime('%Y%m%d-%H%M%S')}"
            )
            shutil.copy2(config.DB_PATH, copia)
            conexao = conectar()
            _migrar_participantes(conexao)
        conexao.executescript(SCHEMA)
        _garantir_colunas(conexao)
        conexao.commit()
    finally:
        conexao.close()


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
        "SELECT id FROM participantes WHERE nome = ? AND tipo = ? AND pais_ou_uf IS ?",
        (nome, tipo, pais_ou_uf),
    ).fetchone()
    if linha:
        return linha["id"]
    cursor = conexao.execute(
        "INSERT INTO participantes (nome, tipo, pais_ou_uf) VALUES (?, ?, ?)",
        (nome, tipo, pais_ou_uf),
    )
    return cursor.lastrowid
