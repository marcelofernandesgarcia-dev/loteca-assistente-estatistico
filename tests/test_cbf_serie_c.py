"""Série C (Fase 2 do plano de 07/10/2026): competição com fases e grupos. Páginas SINTÉTICAS
montadas aqui, no formato conferido no site em 07/10/2026 (nomes fictícios) -- nenhum conteúdo
do site da CBF é guardado no repositório."""
import json
import sqlite3

import pytest

import config
import db
from importer import cbf_client
from importer.cbf_client import (
    calendario_de_fases,
    fases_pela_sequencia,
    gravar_classificacao,
    gravar_pagina_time,
    parse_tabela_completa,
    reatribuir_fases,
)
from stats.ano_em_curso import frase_do_lado, lado_no_ano
from stats.cbf import classificacao_do_participante, partidas_do_participante, resumo_curto_cbf
from stats.competicao import serie_do_time
from stats.painel import temporadas_disponiveis

FASE_1 = {"fase_id": "10", "fase_nome": "1ª Fase", "rodadas_qtd": "19", "partidas": "190"}
FASE_2 = {"fase_id": "11", "fase_nome": "2ª Fase", "rodadas_qtd": "6", "partidas": "12"}


def _html(texto_fluxo: str) -> str:
    escapado = json.dumps(texto_fluxo)[1:-1]
    return f'<html><script>self.__next_f.push([1,"{escapado}"])</script></html>'


def _linha(cod, uf, nome, posicao, rodada="5", proximo=None):
    return {"cod_time": str(cod), "uf_time": uf, "time": nome, "posicao": str(posicao), "pontos": "10", "jogos": "5",
            "vitorias": "3", "empates": "1", "derrotas": "1", "gols_pro": "6", "gols_contra": "3", "gols_saldo": "+3",
            "cartoes_vermelho": "0", "cartoes_amarelo": "9", "aproveitamento": "67", "rodada": rodada,
            "ultimos_jogos": ["V", "E", "V"], "proximo_jogo": proximo or ["nenhum"]}


def _pagina_tabela(grupos: dict[str, list[dict]], fases_lista: list, fase_atual: dict) -> str:
    """Formato da página de tabela: objeto `phase`, `phasesList` (a fase atual vem como referência)
    e uma tabela por grupo, cada uma com o título logo antes de "data"."""
    tabelas = ",".join(
        f'["$","div","{titulo}",{{"children":[["$","$L2e",null,{{"title":"{titulo}","data":{json.dumps(linhas)},"message":""}}]]}}]'
        for titulo, linhas in grupos.items()
    )
    return _html(
        f'1a:{{"competitionData":{{"phase":{json.dumps(fase_atual)},"phasesList":{json.dumps(fases_lista)},"year":"2026"}}}}\n'
        f'2a:[{tabelas}]'
    )


SERIE_C = _pagina_tabela(
    {"GRUPO B": [_linha(1, "PE", "Time Um", 1), _linha(2, "PR", "Time Dois", 2)],
     "GRUPO C": [_linha(3, "SP", "Time Três", 1), _linha(4, "MG", "Time Quatro", 2)]},
    [FASE_1, "$1a:5:props:competitionData:phase"], FASE_2,
)
SERIE_A = _pagina_tabela(
    {"GRUPO ÚNICO": [_linha(100, "SP", "Time Alfa", 1, rodada="28")]},
    ["$1a:5:props:competitionData:phase"], {"fase_id": "1", "fase_nome": "Fase Única", "rodadas_qtd": "38", "partidas": "380"},
)


def _jogo(id_jogo, num_jogo, rodada, grupo, mandante, visitante, gols=("1", "0"), data="06/09/2026"):
    return {"id_jogo": str(id_jogo), "num_jogo": str(num_jogo), "rodada": str(rodada), "grupo": grupo,
            "mandante": {"id": str(mandante[0]), "nome": mandante[1], "gols": gols[0], "panaltis": ""},
            "visitante": {"id": str(visitante[0]), "nome": visitante[1], "gols": gols[1], "panaltis": ""},
            "local": "Estádio Teste", "data": f" {data}", "hora": "16:00"}


PAGINA_TIME_UM = {
    "estatisticas": {"jogos_disputados": "3", "gols_feitos": "4", "gols_sofridos": "2", "jogos_sem_sofrer_gol": "1",
                     "cartoes_amarelos": "5", "cartoes_vermelhos": "0"},
    "jogos": [
        _jogo(901, 9, 1, "GRUPO A", (1, "Time Um"), (9, "Time Eliminado"), ("2", "2"), "06/04/2026"),
        _jogo(902, 186, 19, "GRUPO A", (8, "Outro Eliminado"), (1, "Time Um"), ("0", "1"), "29/08/2026"),
        _jogo(903, 191, 1, "GRUPO B", (1, "Time Um"), (2, "Time Dois"), ("1", "1"), "06/09/2026"),
    ],
}


@pytest.fixture()
def conexao():
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    c.executescript(db.SCHEMA)
    return c


def test_tabela_da_serie_c_le_todos_os_grupos_e_a_fase_atual():
    pagina = parse_tabela_completa(SERIE_C)
    assert [g["titulo"] for g in pagina["grupos"]] == ["GRUPO B", "GRUPO C"]
    assert [len(g["linhas"]) for g in pagina["grupos"]] == [2, 2]
    assert [f["fase_nome"] for f in pagina["fases"]] == ["1ª Fase", "2ª Fase"]
    assert pagina["indice_fase_atual"] == 1


def test_tabela_de_fase_unica_nao_guarda_titulo_nem_calendario():
    pagina = parse_tabela_completa(SERIE_A)
    assert [g["titulo"] for g in pagina["grupos"]] == [None]
    assert calendario_de_fases(pagina["fases"]) == []


def test_tabela_sem_dados_levanta_erro_claro():
    with pytest.raises(cbf_client.ErroColetaCBF):
        parse_tabela_completa(_html("página sem tabela"))


def test_calendario_numera_a_rodada_em_sequencia():
    calendario = calendario_de_fases([FASE_1, FASE_2])
    assert [(f["nome"], f["rodadas"], f["rodadas_antes"]) for f in calendario] == [("1ª Fase", 19, 0), ("2ª Fase", 6, 19)]


FINAL = {"fase_id": "12", "fase_nome": "3a Fase", "rodadas_qtd": "2", "partidas": "2"}


def _j(id_jogo, num_jogo, rodada):
    return {"id_jogo": id_jogo, "num_jogo": num_jogo, "rodada_fase": rodada}


def test_fase_pela_sequencia_nao_se_engana_com_a_contagem_por_grupo():
    # Série C 2024 (conferido em 07/10/2026): a CBF informa "12" partidas na 2ª fase, mas foram 24 (dois
    # grupos). Contando partidas, os jogos 203 a 214 cairiam na final; pela sequência de rodadas, não.
    calendario = calendario_de_fases([FASE_1, FASE_2, FINAL])
    jogos = ([_j(n, n, (n - 1) // 10 + 1) for n in range(1, 191)]
             + [_j(n, n, (n - 191) // 4 + 1) for n in range(191, 215)]
             + [_j(215, 215, 1), _j(216, 216, 2)])
    fases = fases_pela_sequencia(jogos, calendario)
    assert fases[190]["nome"] == "1ª Fase" and fases[191]["nome"] == "2ª Fase" and fases[214]["nome"] == "2ª Fase"
    assert fases[215]["nome"] == "3a Fase" and fases[216]["nome"] == "3a Fase"


def test_sequencia_que_nao_fecha_com_o_calendario_nao_grava_fase():
    calendario = calendario_de_fases([FASE_1, FASE_2])
    assert fases_pela_sequencia([_j(1, 1, 1), _j(2, 2, 1), _j(3, 3, 7)], [calendario[1]]) is None  # rodada 7 numa fase de 6
    assert fases_pela_sequencia([_j(1, 1, 2), _j(2, 2, 1), _j(3, 3, 1)], [calendario[1]]) is None  # mais fases que o calendário


def test_gravar_classificacao_da_2a_fase_nao_colide_com_a_1a(conexao):
    fase = calendario_de_fases([FASE_1, FASE_2])[1]
    gravar_classificacao(conexao, "serie-c", 2026, [_linha(1, "PE", "Time Um", 1)], "2026-10-07T10:00:00", fase, "GRUPO B")
    linha = conexao.execute("SELECT rodada, rodada_fase, fase, grupo FROM cbf_classificacao").fetchone()
    assert tuple(linha) == (24, 5, "2ª Fase", "GRUPO B")


def test_gravar_jogos_marca_fase_grupo_e_rodada_em_sequencia(conexao):
    calendario = calendario_de_fases([FASE_1, FASE_2])
    gravar_pagina_time(conexao, "serie-c", 2026, 1, PAGINA_TIME_UM, "2026-10-07T10:00:00", calendario)
    assert reatribuir_fases(conexao, "serie-c", 2026, calendario)
    linhas = conexao.execute("SELECT id_jogo, rodada, rodada_fase, fase, grupo FROM cbf_partidas ORDER BY id_jogo").fetchall()
    assert [tuple(x) for x in linhas] == [
        (901, 1, 1, "1ª Fase", "GRUPO A"), (902, 19, 19, "1ª Fase", "GRUPO A"), (903, 20, 1, "2ª Fase", "GRUPO B"),
    ]


def test_series_a_e_b_continuam_sem_fase_nem_grupo(conexao):
    gravar_classificacao(conexao, "serie-a", 2026, [_linha(100, "SP", "Time Alfa", 1, rodada="28")], "2026-10-07T10:00:00")
    gravar_pagina_time(conexao, "serie-a", 2026, 100, {"estatisticas": None, "jogos": [
        _jogo(1, 1, 28, "GRUPO ÚNICO", (100, "Time Alfa"), (200, "Time Beta"))]}, "2026-10-07T10:00:00")
    assert tuple(conexao.execute("SELECT rodada, fase, grupo, rodada_fase FROM cbf_classificacao").fetchone()) == (28, None, None, None)
    assert tuple(conexao.execute("SELECT rodada, fase, grupo, rodada_fase FROM cbf_partidas").fetchone()) == (28, None, None, None)


def _serie_c_no_banco(conexao) -> int:
    calendario = calendario_de_fases([FASE_1, FASE_2])
    gravar_classificacao(conexao, "serie-c", 2026, [_linha(1, "PE", "Time Um", 1)], "2026-10-07T10:00:00",
                         calendario[1], "GRUPO B")
    gravar_pagina_time(conexao, "serie-c", 2026, 1, PAGINA_TIME_UM, "2026-10-07T10:00:00", calendario)
    reatribuir_fases(conexao, "serie-c", 2026, calendario)
    participante = db.obter_ou_criar_participante(conexao, "TIME UM", "clube", "PE")
    conexao.execute("INSERT INTO mapa_cbf_participante (participante_id, cod_time, metodo) VALUES (?, 1, 'uf+nome')",
                    (participante,))
    return participante


def test_posicao_da_serie_c_diz_o_grupo_e_a_fase(conexao):
    participante = _serie_c_no_banco(conexao)
    classif = classificacao_do_participante(conexao, participante)
    assert resumo_curto_cbf(classif).startswith("CBF: 1º no Grupo B (2ª Fase) · 67% aprov. na fase")
    rodadas = [p["rodada"] for p in partidas_do_participante(conexao, participante)]
    assert rodadas == ["1ª da 2ª Fase (Grupo B)", "19ª da 1ª Fase (Grupo A)", "1ª da 1ª Fase (Grupo A)"]


def test_ano_em_curso_da_serie_c_soma_todas_as_fases(conexao):
    participante = _serie_c_no_banco(conexao)
    lado = lado_no_ano(conexao, {"id": participante, "nome": "TIME UM", "tipo": "clube"}, 2026)
    assert lado["fonte"] == "cbf" and lado["texto_fonte"].endswith("(Série C), todas as fases")
    assert (lado["jogos"], lado["vitorias"], lado["empates"], lado["derrotas"]) == (3, 1, 2, 0)
    assert (lado["gols_pro"], lado["gols_contra"]) == (4, 3) and lado["ultimos"] == ["E", "V", "E"]
    assert frase_do_lado(lado).startswith("1º no Grupo B (2ª Fase) da Série C · 1V 2E 0D em 3 jogos")


def test_serie_c_fica_fora_da_tabela_rodada_a_rodada(conexao):
    _serie_c_no_banco(conexao)
    assert serie_do_time(conexao, 1) is None
    assert temporadas_disponiveis(conexao) == []


def test_coleta_da_serie_c_segue_os_adversarios_e_a_da_serie_a_nao(conexao, monkeypatch):
    monkeypatch.setattr(config, "CBF_INTERVALO_SEGUNDOS", 0)
    pedidos = []

    def baixar(url):
        pedidos.append(url.rsplit("/", 1)[-1])
        if "/tabelas/" in url:
            return SERIE_C if "serie-c" in url else SERIE_A
        cod = int(url.rsplit("/", 1)[-1])
        jogos = PAGINA_TIME_UM["jogos"] if cod == 1 else []
        return _html('"estatisticas":[],"jogos":' + json.dumps(jogos))

    monkeypatch.setattr(cbf_client, "_baixar", baixar)
    resultado = cbf_client.coletar_competicao(conexao, "campeonato-brasileiro", "serie-c", 2026, forcar=True)
    assert resultado["times"] == 6  # 4 da tabela + 2 eliminados vistos nos jogos do Time Um
    assert pedidos[1:] == ["1", "2", "3", "4", "9", "8"]
    assert conexao.execute("SELECT COUNT(*) FROM cbf_classificacao WHERE grupo = 'GRUPO C'").fetchone()[0] == 2

    assert resultado["fases_conferem"] is True
    assert conexao.execute("SELECT fase FROM cbf_partidas WHERE id_jogo = 903").fetchone()[0] == "2ª Fase"

    pedidos.clear()
    resultado = cbf_client.coletar_competicao(conexao, "campeonato-brasileiro", "serie-a", 2026, forcar=True)
    assert resultado["times"] == 1 and pedidos[1:] == ["100"] and resultado["fases_conferem"] is None


def test_temporada_encerrada_sem_tabela_parte_dos_times_da_final(conexao, monkeypatch):
    # Página da Série C 2024 (conferido em 07/10/2026): a fase atual é a final, sem tabela, só os jogos.
    final = [_jogo(950, 215, 1, "GRUPO D", (1, "Time Um"), (2, "Time Dois"))]
    pagina = _html(
        f'1a:{{"competitionData":{{"phase":{json.dumps(FINAL)},"phasesList":{json.dumps([FASE_1, FASE_2, "$ref"])}}}}}\n'
        f'2b:[["$","$L3b",null,{{"data":{json.dumps(final)}}}]]'
    )
    assert parse_tabela_completa(pagina)["times_dos_jogos"] == [1, 2]
    monkeypatch.setattr(config, "CBF_INTERVALO_SEGUNDOS", 0)
    pedidos = []

    def baixar(url):
        pedidos.append(url.rsplit("/", 1)[-1])
        return pagina if "/tabelas/" in url else _html('"estatisticas":[],"jogos":[]')

    monkeypatch.setattr(cbf_client, "_baixar", baixar)
    resultado = cbf_client.coletar_competicao(conexao, "campeonato-brasileiro", "serie-c", 2024, forcar=True)
    assert pedidos[1:] == ["1", "2"] and resultado["times"] == 2
    assert conexao.execute("SELECT COUNT(*) FROM cbf_classificacao").fetchone()[0] == 0  # sem tabela, nada inventado
