"""Testes da leitura da CBF com páginas SINTÉTICAS montadas aqui (nomes
fictícios) -- nenhum conteúdo do site da CBF é guardado no repositório."""
import json
import sqlite3

import pytest

import db
from importer.cbf_client import (
    ErroColetaCBF,
    data_iso,
    gravar_classificacao,
    gravar_pagina_time,
    parse_classificacao,
    parse_pagina_time,
)
from importer.cbf_mapeamento import parear, tokens
from stats.cbf import classificacao_do_participante, partidas_do_participante, resumo_curto_cbf


def _html(texto_fluxo: str) -> str:
    escapado = json.dumps(texto_fluxo)[1:-1]
    return f'<html><script>self.__next_f.push([1,"{escapado}"])</script></html>'


CLASSIFICACAO = [
    {"cod_time": "100", "uf_time": "SP", "time": "Time Alfa SAF", "posicao": "1", "pontos": "54", "jogos": "30",
     "vitorias": "16", "empates": "6", "derrotas": "8", "gols_pro": "43", "gols_contra": "31", "gols_saldo": "+12",
     "cartoes_vermelho": "8", "cartoes_amarelo": "77", "aproveitamento": "60", "rodada": "30",
     "ultimos_jogos": ["E", "V", "V"], "proximo_jogo": {"id": "200", "time": "Time Beta"}},
    {"cod_time": "200", "uf_time": "RJ", "time": "Time Beta", "posicao": "2", "pontos": "50", "jogos": "30",
     "vitorias": "15", "empates": "5", "derrotas": "10", "gols_pro": "40", "gols_contra": "35", "gols_saldo": "5",
     "cartoes_vermelho": "2", "cartoes_amarelo": "60", "aproveitamento": "55", "rodada": "30",
     "ultimos_jogos": ["D", "V", "E"], "proximo_jogo": {"id": "100", "time": "Time Alfa SAF"}},
]

ESTATISTICAS = {"gols_feitos": "43", "gols_sofridos": "31", "jogos_sem_sofrer_gol": "11",
                "jogos_disputados": "30", "vitorias": "16", "derrotas": "8", "empates": "6",
                "cartoes_amarelos": "77", "cartoes_vermelhos": "8"}

# formato já interpretado por parse_pagina_time (estatisticas = dict)
PAGINA_TIME = {
    "estatisticas": ESTATISTICAS,
    "jogos": [
        {"id_jogo": "1", "rodada": "29", "mandante": {"id": "100", "nome": "Time Alfa SAF", "gols": "1", "panaltis": "0"},
         "visitante": {"id": "200", "nome": "Time Beta", "gols": "0", "panaltis": "0"},
         "local": "Estádio Teste - Cidade - SP", "data": " 20/09/2026", "hora": "16:00"},
        {"id_jogo": "2", "rodada": "31", "mandante": {"id": "200", "nome": "Time Beta", "gols": "", "panaltis": ""},
         "visitante": {"id": "100", "nome": "Time Alfa SAF", "gols": "", "panaltis": ""},
         "local": "Outro Estádio - RJ", "data": " 04/10/2026", "hora": "19:00"},
    ],
}


@pytest.fixture()
def conexao():
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    c.executescript(db.SCHEMA)
    return c


def test_parse_classificacao_le_a_tabela_embutida():
    html = _html("prefixo," + '"data":' + json.dumps(CLASSIFICACAO) + ",sufixo")
    linhas = parse_classificacao(html)
    assert [x["time"] for x in linhas] == ["Time Alfa SAF", "Time Beta"]


def test_parse_classificacao_sem_tabela_levanta_erro_claro():
    with pytest.raises(ErroColetaCBF):
        parse_classificacao(_html("página sem tabela"))


def test_pagina_sem_fluxo_levanta_erro_claro():
    with pytest.raises(ErroColetaCBF, match="site pode ter mudado"):
        parse_pagina_time("<html>nada</html>")


def test_parse_pagina_time_le_estatisticas_e_jogos():
    html = _html('"estatisticas":' + json.dumps([ESTATISTICAS]) + ',"jogos":' + json.dumps(PAGINA_TIME["jogos"]))
    dados = parse_pagina_time(html)
    assert dados["estatisticas"]["jogos_sem_sofrer_gol"] == "11"
    assert len(dados["jogos"]) == 2


def test_data_iso():
    assert data_iso(" 25/09/2026") == "2026-09-25"
    assert data_iso("") is None
    assert data_iso("lixo") is None


def test_gravar_e_consultar(conexao):
    participante = db.obter_ou_criar_participante(conexao, "TIME ALFA", "clube", "SP")
    gravar_classificacao(conexao, "serie-b", 2026, CLASSIFICACAO, "2026-09-27T10:00:00")
    gravar_pagina_time(conexao, "serie-b", 2026, 100, PAGINA_TIME, "2026-09-27T10:00:00")
    resultado = parear(conexao)
    assert resultado["pareados"] == 1

    classif = classificacao_do_participante(conexao, participante)
    assert classif["posicao"] == 1 and classif["pontos"] == 54 and classif["saldo"] == 12
    assert classif["ultimos_jogos"] == "E,V,V"
    assert resumo_curto_cbf(classif) == "CBF: 1º · 60% aprov. · E V V"

    partidas = partidas_do_participante(conexao, participante)
    assert [p["rodada"] for p in partidas] == [31, 29]  # mais recente primeiro
    futura, passada = partidas
    assert futura["realizada"] is False and futura["gols_feitos"] is None
    assert passada["mando"] == "casa" and (passada["gols_feitos"], passada["gols_sofridos"]) == (1, 0)


def test_gravar_duas_vezes_nao_duplica(conexao):
    for _ in range(2):
        gravar_classificacao(conexao, "serie-b", 2026, CLASSIFICACAO, "2026-09-27T10:00:00")
        gravar_pagina_time(conexao, "serie-b", 2026, 100, PAGINA_TIME, "2026-09-27T10:00:00")
    assert conexao.execute("SELECT COUNT(*) FROM cbf_classificacao").fetchone()[0] == 2
    assert conexao.execute("SELECT COUNT(*) FROM cbf_partidas").fetchone()[0] == 2


def test_tokens_ignoram_acento_e_saf():
    assert tokens("Atlético Goianiense Saf") == frozenset({"ATLETICO", "GOIANIENSE"})
    assert tokens("VASCO DA GAMA") == frozenset({"VASCO", "GAMA"})


def _cbf(conexao, cod, nome, uf):
    conexao.execute("INSERT INTO cbf_times (cod_time, nome, uf) VALUES (?, ?, ?)", (cod, nome, uf))


def test_pareamento_usa_uf_para_separar_homonimos(conexao):
    _cbf(conexao, 1, "Botafogo", "RJ")
    _cbf(conexao, 2, "Botafogo", "SP")
    rj = db.obter_ou_criar_participante(conexao, "BOTAFOGO", "clube", "RJ")
    sp = db.obter_ou_criar_participante(conexao, "BOTAFOGO", "clube", "SP")
    parear(conexao)
    mapa = {r["participante_id"]: r["cod_time"] for r in conexao.execute("SELECT * FROM mapa_cbf_participante")}
    assert mapa == {rj: 1, sp: 2}


def test_pareamento_nomes_diferentes_da_cbf(conexao):
    _cbf(conexao, 1, "Red Bull Bragantino", "SP")
    _cbf(conexao, 2, "Athletic SAF", "MG")
    _cbf(conexao, 3, "Atlético Mineiro", "MG")
    bragantino = db.obter_ou_criar_participante(conexao, "BRAGANTINO", "clube", "SP")
    athletic = db.obter_ou_criar_participante(conexao, "ATHLETIC CLUB", "clube", "MG")
    atletico = db.obter_ou_criar_participante(conexao, "ATLETICO", "clube", "MG")
    parear(conexao)
    mapa = {r["participante_id"]: r["cod_time"] for r in conexao.execute("SELECT * FROM mapa_cbf_participante")}
    assert mapa == {bragantino: 1, athletic: 2, atletico: 3}


def test_pareamento_ambiguo_nao_adivinha(conexao):
    _cbf(conexao, 1, "Time Alfa Norte", "SP")
    _cbf(conexao, 2, "Time Alfa Sul", "SP")
    db.obter_ou_criar_participante(conexao, "TIME ALFA", "clube", "SP")
    resultado = parear(conexao)
    assert resultado["pareados"] == 0
    assert len(resultado["ambiguos"]) == 1
    assert conexao.execute("SELECT COUNT(*) FROM mapa_cbf_participante").fetchone()[0] == 0


def test_estrangeiro_e_selecao_nao_pareiam(conexao):
    _cbf(conexao, 1, "Barcelona", "SP")
    db.obter_ou_criar_participante(conexao, "BARCELONA", "clube", "ESP")
    db.obter_ou_criar_participante(conexao, "ALEMANHA", "selecao", "GER")
    assert parear(conexao)["pareados"] == 0


def test_classificacao_guarda_o_codigo_do_proximo_adversario(conexao):
    gravar_classificacao(conexao, "serie-a", 2026, CLASSIFICACAO, "2026-09-27T10:00:00")
    linha = conexao.execute(
        "SELECT proximo_adversario, proximo_adversario_id FROM cbf_classificacao WHERE cod_time = 100"
    ).fetchone()
    assert (linha["proximo_adversario"], linha["proximo_adversario_id"]) == ("Time Beta", 200)
