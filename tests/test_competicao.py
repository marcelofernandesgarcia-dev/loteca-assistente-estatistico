"""Testes de stats/competicao.py com uma liga SINTÉTICA de 4 times fictícios."""
import sqlite3

import pytest

import db
from stats.competicao import (
    carregar_partidas,
    evolucao_do_time,
    jogos_do_time,
    serie_do_time,
    tabela_por_rodada,
    validar_contra_classificacao,
)

A, B, C, D = 1, 2, 3, 4


def _p(rodada, mandante, visitante, gm, gv, data="2026-03-01"):
    return {"id_jogo": rodada * 10 + mandante, "rodada": rodada, "data_jogo": data,
            "mandante_id": mandante, "visitante_id": visitante, "gols_mandante": gm, "gols_visitante": gv}


PARTIDAS = [
    _p(1, A, B, 2, 0), _p(1, C, D, 1, 1),
    _p(2, B, C, 0, 3), _p(2, D, A, 1, 1),
    _p(3, A, C, 0, 1),  # o jogo B x D da rodada 3 ainda não foi disputado
]


def _linha(tabela, cod):
    return next(x for x in tabela if x["cod_time"] == cod)


def test_tabela_acumulada_por_rodada():
    tabelas = tabela_por_rodada(PARTIDAS)
    assert list(tabelas) == [1, 2, 3]
    r1 = tabelas[1]
    assert _linha(r1, A)["pontos"] == 3 and _linha(r1, B)["derrotas"] == 1
    assert _linha(r1, C)["empates"] == 1 and _linha(r1, D)["empates"] == 1
    r3 = tabelas[3]
    assert _linha(r3, C)["pontos"] == 7 and _linha(r3, C)["posicao"] == 1
    assert _linha(r3, A)["jogos"] == 3 and _linha(r3, B)["jogos"] == 2


def test_todos_os_times_aparecem_em_todas_as_rodadas_mesmo_sem_jogo():
    tabelas = tabela_por_rodada([_p(1, A, B, 1, 0)] + [_p(2, C, D, 0, 0)])
    assert len(tabelas[1]) == 4 and _linha(tabelas[1], C)["jogos"] == 0


def test_desempate_por_vitorias_saldo_e_gols_pro():
    partidas = [_p(1, A, B, 1, 0), _p(1, C, D, 0, 0), _p(2, A, C, 0, 0), _p(2, B, D, 3, 0), _p(3, D, A, 0, 2)]
    final = tabela_por_rodada(partidas)[3]
    # A: 7 pts (2V 1E); B: 3 pts; C: 2 pts; D: 1 pt
    assert [x["cod_time"] for x in final] == [A, B, C, D]
    # empate em pontos e vitórias: melhor saldo fica na frente
    empate = tabela_por_rodada([_p(1, A, B, 3, 0), _p(1, C, D, 1, 0)])[1]
    assert [x["cod_time"] for x in empate][:2] == [A, C]


def test_jogos_do_time_com_mando_e_resultado():
    jogos = jogos_do_time(PARTIDAS, A)
    assert [(j["rodada"], j["mando"], j["resultado"], j["pontos"]) for j in jogos] == [
        (1, "casa", "V", 3), (2, "fora", "E", 1), (3, "casa", "D", 0)]
    assert jogos[1]["adversario_id"] == D and (jogos[1]["gols_pro"], jogos[1]["gols_contra"]) == (1, 1)


def test_evolucao_do_time_traz_posicao_e_media_da_serie():
    evolucao = evolucao_do_time(tabela_por_rodada(PARTIDAS), A)
    assert [e["rodada"] for e in evolucao] == [1, 2, 3]
    assert evolucao[0]["posicao"] == 1 and evolucao[0]["pontos"] == 3
    assert evolucao[2]["jogos"] == 3 and evolucao[2]["aproveitamento"] == pytest.approx(100 * 4 / 9)
    # media de pontos dos times que já jogaram após a rodada 1: (3+0+1+1)/4
    assert evolucao[0]["pontos_media_serie"] == pytest.approx(1.25)


def test_evolucao_ignora_rodadas_antes_da_estreia_do_time():
    tabelas = tabela_por_rodada([_p(1, A, B, 1, 0), _p(2, C, D, 0, 0)])
    assert [e["rodada"] for e in evolucao_do_time(tabelas, C)] == [2]


def _oficial(tabela):
    return [{k: x[k] for k in ("cod_time", "posicao", "jogos", "pontos", "gols_pro", "gols_contra")} for x in tabela]


def test_validacao_confere_quando_os_numeros_batem():
    final = tabela_por_rodada(PARTIDAS)[3]
    resultado = validar_contra_classificacao(final, _oficial(final))
    assert resultado["confere"] and resultado["divergencias_posicao"] == []


def test_validacao_aponta_jogo_faltando_e_posicao_diferente():
    final = tabela_por_rodada(PARTIDAS)[3]
    oficial = _oficial(final)
    oficial[1]["pontos"] += 3
    oficial[1]["jogos"] += 1
    oficial[0]["posicao"], oficial[1]["posicao"] = oficial[1]["posicao"], oficial[0]["posicao"]
    resultado = validar_contra_classificacao(final, oficial)
    assert not resultado["confere"]
    campos = {d["campo"] for d in resultado["divergencias_numeros"]}
    assert campos == {"jogos", "pontos"}
    assert len(resultado["divergencias_posicao"]) == 2


def test_validacao_time_ausente_na_base():
    final = tabela_por_rodada(PARTIDAS)[3]
    oficial = _oficial(final) + [{"cod_time": 99, "posicao": 5, "jogos": 3, "pontos": 3, "gols_pro": 1, "gols_contra": 1}]
    resultado = validar_contra_classificacao(final, oficial)
    assert not resultado["confere"] and resultado["divergencias_numeros"][0]["cod_time"] == 99


def test_carregar_partidas_e_serie_do_time_leem_o_banco():
    conexao = sqlite3.connect(":memory:")
    conexao.row_factory = sqlite3.Row
    conexao.executescript(db.SCHEMA)
    linhas = [
        (1, "serie-a", 2026, 1, "2026-03-01", A, B, 2, 0),
        (2, "serie-a", 2026, 2, "2026-03-08", C, A, None, None),
        (3, "serie-b", 2025, 1, "2025-03-01", A, D, 1, 1),
    ]
    for id_jogo, serie, ano, rodada, data, m, v, gm, gv in linhas:
        conexao.execute(
            "INSERT INTO cbf_partidas (id_jogo, serie, ano, rodada, data_jogo, mandante_id, visitante_id,"
            " gols_mandante, gols_visitante, coletado_em) VALUES (?,?,?,?,?,?,?,?,?, 'x')",
            (id_jogo, serie, ano, rodada, data, m, v, gm, gv),
        )
    assert [p["id_jogo"] for p in carregar_partidas(conexao, "serie-a", 2026)] == [1]
    assert serie_do_time(conexao, A) == ("serie-a", 2026)
    assert serie_do_time(conexao, 999) is None
