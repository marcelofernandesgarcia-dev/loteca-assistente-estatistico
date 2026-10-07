"""Item A3 do plano v2 (07/10/2026): cada manchete lida fica registrada com a decisão do filtro --
aplicada, informativa, descartada (com o motivo) ou sem sinal. Manchetes fictícias, no formato das reais."""
import sqlite3

import pytest

import config
import db
from externo import varredura
from externo.analise import MOTIVOS_DE_DESCARTE, classificar_noticias, extrair_sinais

CONCURSO = ["TIME ALFA", "TIME BETA", "TIME GAMA", "TIME DELTA"]


def _uma(titulo, participante="TIME ALFA", adversario="TIME BETA", tipo="clube"):
    return classificar_noticias([{"titulo": titulo, "url": ""}], participante, adversario, tipo, CONCURSO)[0]


def test_lesao_do_proprio_time_e_aplicada():
    item = _uma("Atacante do Time Alfa sofre lesão e desfalca o time")
    assert item["situacao"] == "aplicada" and item["aceitos"] and not item["descartes"]


@pytest.mark.parametrize("titulo, participante, adversario, tipo, motivo", [
    ("Time Gama perde atacante por lesão", "TIME ALFA", "TIME BETA", "clube", "nao_menciona"),
    ("Atacante do Time Alfa é liberado após lesão", "TIME ALFA", "TIME BETA", "clube", "negacao"),
    ("Time Alfa feminino tem desfalques", "TIME ALFA", "TIME BETA", "clube", "outra_equipe"),
    ("Time Gama tem lesão e Time Alfa observa", "TIME ALFA", "TIME BETA", "clube", "sujeito_outro_time"),
    ("Time Alfa tem desfalques contra o Time Delta", "TIME ALFA", "TIME BETA", "clube", "outro_jogo"),
    ("Time Alfa contrata atacante", "TIME ALFA", "TIME BETA", "selecao", "selecao_nao_contrata"),
])
def test_descarte_registra_o_motivo(titulo, participante, adversario, tipo, motivo):
    item = _uma(titulo, participante, adversario, tipo)
    assert item["situacao"] == "descartada" and not item["aceitos"]
    assert motivo in {d["motivo"] for d in item["descartes"]}
    assert motivo in MOTIVOS_DE_DESCARTE


def test_manchete_sem_palavra_chave_fica_sem_sinal():
    assert _uma("Time Alfa divulga programação da semana")["situacao"] == "sem_sinal"


def test_classificacao_e_extracao_concordam():
    noticias = [{"titulo": t, "url": ""} for t in (
        "Atacante do Time Alfa sofre lesão", "Time Gama perde atacante por lesão", "Time Alfa contrata zagueiro",
    )]
    aceitos = [s for item in classificar_noticias(noticias, "TIME ALFA", "TIME BETA", "clube", CONCURSO)
               for s in item["aceitos"]]
    assert sorted(aceitos) == sorted(s["sinal"] for s in extrair_sinais(noticias, "TIME ALFA", "TIME BETA", "clube", CONCURSO))


@pytest.fixture()
def banco():
    conexao = sqlite3.connect(":memory:")
    conexao.row_factory = sqlite3.Row
    conexao.executescript(db.SCHEMA)
    casa = db.obter_ou_criar_participante(conexao, "TIME A", "clube", "SP")
    fora = db.obter_ou_criar_participante(conexao, "TIME B", "clube", "RJ")
    conexao.execute("INSERT INTO concursos (numero) VALUES (7)")
    conexao.execute("INSERT INTO jogos (concurso_numero, num_jogo, casa_id, fora_id) VALUES (7, 1, ?, ?)", (casa, fora))
    return conexao, casa, fora


def test_varredura_grava_todas_as_manchetes_com_a_decisao_e_a_versao(banco, monkeypatch):
    conexao, casa, fora = banco
    noticias = {
        "TIME A": [
            {"titulo": "Atacante do Time A está lesionado", "fonte": "Veículo X", "url": "http://x/1"},
            {"titulo": "Time A divulga programação", "fonte": "Veículo Y", "url": "http://y/2"},
        ],
        "TIME B": [],
    }
    monkeypatch.setattr(varredura, "buscar_noticias", lambda nome, **kw: noticias[nome])
    varredura.executar_para_concurso(conexao, 7)
    lidas = varredura.noticias_lidas_do_concurso(conexao, 7)
    assert [(n["titulo"], n["situacao"]) for n in lidas] == [
        ("Atacante do Time A está lesionado", "aplicada"), ("Time A divulga programação", "sem_sinal"),
    ]
    assert {n["versao_regras"] for n in lidas} == {config.VARREDURA_VERSAO_REGRAS}
    assert lidas[0]["url"] == "http://x/1" and lidas[0]["participante"] == "TIME A"


def test_so_a_leitura_mais_recente_vale_por_padrao(banco):
    conexao, casa, _ = banco
    item = {"noticia": {"titulo": "Manchete", "url": ""}, "aceitos": [], "descartes": [], "situacao": "sem_sinal"}
    varredura.gravar_noticias_lidas(conexao, 7, casa, "2026-10-08T08:00:00", [item])
    varredura.gravar_noticias_lidas(conexao, 7, casa, "2026-10-10T08:00:00", [item, item])
    assert len(varredura.noticias_lidas_do_concurso(conexao, 7)) == 2
    assert len(varredura.noticias_lidas_do_concurso(conexao, 7, so_ultima_leitura=False)) == 3
