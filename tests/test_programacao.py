import datetime as dt
import sqlite3

import pytest

import config
import db
import importer.caixa_client as caixa
from stats.prazo import formatar_restante, situacao_do_prazo
from stats.resultado import identidade_participante, limpar_nome


@pytest.fixture()
def conexao():
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    c.executescript(db.SCHEMA)
    return c


def _jogo(seq, um, dois, uf1="", uf2="", pais1="", pais2="", data="26/09/2026 00:00:00", sorteio=0, gols=(0, 0)):
    return {
        "nuSequencial": seq, "nomeEquipeUm": um, "nomeEquipeDois": dois,
        "siglaUFUm": uf1, "siglaUFDois": uf2, "siglaPaisUm": pais1, "siglaPaisDois": pais2,
        "dtJogo": data, "nomeCampeonato": "", "icSorteioResultado": sorteio,
        "nuGolEquipeUm": gols[0], "nuGolEquipeDois": gols[1],
    }


PROGRAMACAO = [
    {
        "nuConcurso": 1272, "dataFimApostas": "26/09/2026", "horarioFimApostas": "15",
        "dataProximoConcurso": "26/09/2026", "valorEstimadoProximoConcurso": 1500000.0,
        "listaJogos": [
            _jogo(1, "INGLATERRA", "SERVIA/SER"),
            _jogo(2, "OPERARIO", "CEARA", uf1="PR", uf2="CE"),
        ],
    }
]


def test_limpar_nome_tira_codigo_de_pais():
    assert limpar_nome("SERVIA/SER") == "SERVIA"
    assert limpar_nome("ESCOCIA/SCT") == "ESCOCIA"
    assert limpar_nome("FLAMENGO") == "FLAMENGO"


def test_identidade_de_selecao_ignora_codigo_de_pais_e_clube_usa_uf():
    assert identidade_participante("SERVIA/SER", "") == {"nome": "SERVIA", "tipo": "selecao", "uf": None}
    assert identidade_participante("BARCELONA", "") == {"nome": "BARCELONA", "tipo": "clube", "uf": None}
    assert identidade_participante("CEARA", "ce") == {"nome": "CEARA", "tipo": "clube", "uf": "CE"}


def test_importar_programacao_grava_prazo_exato_e_jogos_sem_placar(conexao, monkeypatch):
    monkeypatch.setattr(caixa, "_buscar_json", lambda sufixo="": PROGRAMACAO)
    assert caixa.importar_programacao(conexao) == [1272]

    concurso = conexao.execute("SELECT * FROM concursos WHERE numero = 1272").fetchone()
    assert concurso["data_limite_aposta"] == "2026-09-26" and concurso["horario_fim_apostas"] == 15
    jogos = conexao.execute("SELECT * FROM jogos WHERE concurso_numero = 1272 ORDER BY num_jogo").fetchall()
    assert len(jogos) == 2
    assert all(j["gols_casa"] is None and j["resultado"] is None for j in jogos)
    tipos = {r["nome"]: r["tipo"] for r in conexao.execute("SELECT nome, tipo FROM participantes")}
    assert tipos["SERVIA"] == "selecao" and tipos["INGLATERRA"] == "selecao" and tipos["OPERARIO"] == "clube"


def test_importar_programacao_e_idempotente_e_nao_apaga_placar_existente(conexao, monkeypatch):
    monkeypatch.setattr(caixa, "_buscar_json", lambda sufixo="": PROGRAMACAO)
    caixa.importar_programacao(conexao)
    conexao.execute("UPDATE jogos SET gols_casa = 2, gols_fora = 1, resultado = '1' WHERE num_jogo = 2")
    caixa.importar_programacao(conexao)
    assert conexao.execute("SELECT COUNT(*) FROM jogos").fetchone()[0] == 2
    jogo = conexao.execute("SELECT * FROM jogos WHERE num_jogo = 2").fetchone()
    assert (jogo["gols_casa"], jogo["gols_fora"], jogo["resultado"]) == (2, 1, "1")


def test_mesma_selecao_no_historico_e_na_programacao_e_um_participante_so(conexao, monkeypatch):
    historico = {
        "numero": 1270, "dataApuracao": "14/09/2026", "acumulado": False,
        "listaResultadoEquipeEsportiva": [_jogo(1, "INGLATERRA", "ESPANHA", pais1="ING", pais2="ESP", gols=(1, 0))],
    }
    monkeypatch.setattr(caixa, "_buscar_json", lambda sufixo="": historico)
    caixa.importar_concurso(1270, conexao)
    monkeypatch.setattr(caixa, "_buscar_json", lambda sufixo="": PROGRAMACAO)
    caixa.importar_programacao(conexao)
    assert conexao.execute("SELECT COUNT(*) FROM participantes WHERE nome = 'INGLATERRA'").fetchone()[0] == 1


def test_icSorteioResultado_marca_o_jogo_como_sorteio(conexao, monkeypatch):
    corpo = {
        "numero": 1000, "dataApuracao": "01/01/2020", "acumulado": False,
        "listaResultadoEquipeEsportiva": [_jogo(1, "TIME A", "TIME B", uf1="SP", uf2="RJ", sorteio=1, gols=(1, 0))],
    }
    monkeypatch.setattr(caixa, "_buscar_json", lambda sufixo="": corpo)
    caixa.importar_concurso(1000, conexao)
    assert conexao.execute("SELECT situacao FROM jogos").fetchone()[0] == "sorteio"


def test_programacao_em_formato_inesperado_levanta_erro_claro(conexao, monkeypatch):
    monkeypatch.setattr(caixa, "_buscar_json", lambda sufixo="": {"message": "x"})
    with pytest.raises(caixa.ErroImportacaoLoteca):
        caixa.importar_programacao(conexao)


def test_prazo_exato_aberto_e_encerrado():
    antes = dt.datetime(2026, 9, 26, 12, 0)
    depois = dt.datetime(2026, 9, 26, 15, 30)
    aberto = situacao_do_prazo("2026-09-26", 15, antes)
    fechado = situacao_do_prazo("2026-09-26", 15, depois)
    assert aberto["exato"] and aberto["aberto"] and formatar_restante(aberto["restante"]) == "faltam 3 h 0 min"
    assert fechado["aberto"] is False and formatar_restante(fechado["restante"]) == "encerradas"


def test_prazo_aproximado_vale_ate_o_fim_do_dia():
    resultado = situacao_do_prazo("2026-09-26", None, dt.datetime(2026, 9, 26, 20, 0))
    assert resultado["exato"] is False and resultado["aberto"] is True
    assert situacao_do_prazo(None, None)["aberto"] is None


def test_banco_antigo_sem_coluna_de_horario_ganha_a_coluna(tmp_path, monkeypatch):
    caminho = tmp_path / "velho.db"
    monkeypatch.setattr(config, "DB_PATH", caminho)
    velho = sqlite3.connect(caminho)
    velho.executescript(
        "CREATE TABLE concursos (numero INTEGER PRIMARY KEY, data_apuracao TEXT, data_limite_aposta TEXT,"
        " data_proximo TEXT, tipo TEXT NOT NULL DEFAULT 'regular', acumulado INTEGER, valor_estimado_proximo REAL);"
        "INSERT INTO concursos (numero) VALUES (7);"
    )
    velho.commit()
    velho.close()
    db.inicializar_schema()
    with db.sessao() as conexao:
        colunas = {r["name"] for r in conexao.execute("PRAGMA table_info(concursos)")}
        assert "horario_fim_apostas" in colunas
        assert conexao.execute("SELECT COUNT(*) FROM concursos").fetchone()[0] == 1
