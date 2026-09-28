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


from stats.competicao import (  # noqa: E402
    aproveitamento_movel,
    descrever_sequencia,
    frases_visao_geral,
    sequencia_atual,
    variacao_de_posicao,
)


def _jogos(resultados: str):
    pontos = {"V": 3, "E": 1, "D": 0}
    return [
        {"rodada": i + 1, "resultado": r, "pontos": pontos[r], "gols_pro": 1, "gols_contra": 0}
        for i, r in enumerate(resultados)
    ]


def test_sequencia_atual_conta_do_ultimo_para_tras():
    assert sequencia_atual(_jogos("DVVE")) == {"vitorias": 0, "sem_perder": 3, "sem_vencer": 1, "derrotas": 0}
    assert sequencia_atual(_jogos("VEDD")) == {"vitorias": 0, "sem_perder": 0, "sem_vencer": 3, "derrotas": 2}
    assert sequencia_atual([]) == {"vitorias": 0, "sem_perder": 0, "sem_vencer": 0, "derrotas": 0}


def test_descrever_sequencia_respeita_o_minimo():
    assert descrever_sequencia(sequencia_atual(_jogos("EVVV")), minimo=3) == "3 vitórias seguidas"
    assert descrever_sequencia(sequencia_atual(_jogos("VEEV")), minimo=3) == "4 jogos sem perder"
    assert descrever_sequencia(sequencia_atual(_jogos("VEDV")), minimo=3) is None
    assert descrever_sequencia(sequencia_atual(_jogos("VDEDE")), minimo=3) == "4 jogos sem vencer"


def test_aproveitamento_movel_so_comeca_com_a_janela_cheia():
    movel = aproveitamento_movel(_jogos("VVVEDD"), janela=3)
    assert [m["rodada"] for m in movel] == [3, 4, 5, 6]
    assert movel[0]["aproveitamento_movel"] == pytest.approx(100.0)
    assert movel[3]["aproveitamento_movel"] == pytest.approx(100 * 1 / 9)
    assert aproveitamento_movel(_jogos("VV"), janela=3) == []


def _evo(posicoes):
    return [
        {"rodada": i + 1, "posicao": p, "pontos": 10 + i, "jogos": i + 1, "aproveitamento": 50.0,
         "saldo": 0, "pontos_media_serie": 10 + i}
        for i, p in enumerate(posicoes)
    ]


def test_variacao_de_posicao_positiva_quando_sobe():
    assert variacao_de_posicao(_evo([10, 9, 8, 7, 6, 4]), rodadas=5) == {"de": 10, "para": 4, "variacao": 6, "rodadas": 5}
    assert variacao_de_posicao(_evo([3, 2]), rodadas=5) is None


def test_frases_trazem_o_numero_que_as_sustenta():
    evolucao = _evo([10, 9, 8, 7, 6, 4])
    evolucao[-1].update(pontos=20, pontos_media_serie=14.0, aproveitamento=40.0, jogos=6)
    frases = frases_visao_geral(evolucao, _jogos("DDVVVV"))
    texto = " ".join(frases)
    assert "4ª posição após a rodada 6" in texto and "20 pontos em 6 jogos" in texto
    assert "6 pontos a mais que a média da série" in texto
    assert "Subiu 6 posições" in texto
    assert "4 vitórias seguidas" in texto
    assert "acima dos 40%" in texto  # últimos 5 jogos: 4V+1D = 80%


def test_frases_sem_dados_nao_inventam_nada():
    assert frases_visao_geral([], []) == []


from stats.competicao import (  # noqa: E402
    gols_com_media_movel,
    medias_da_liga,
    perfil_de_gols,
    resumo_por_mando,
)


def _jg(rodada, mando, pro, contra, adv=9):
    resultado = "V" if pro > contra else "E" if pro == contra else "D"
    return {"rodada": rodada, "mando": mando, "gols_pro": pro, "gols_contra": contra, "resultado": resultado,
            "pontos": {"V": 3, "E": 1, "D": 0}[resultado], "adversario_id": adv}


JOGOS = [_jg(1, "casa", 2, 0), _jg(2, "fora", 0, 0), _jg(3, "casa", 1, 3), _jg(4, "fora", 4, 1, adv=7)]


def test_resumo_por_mando():
    resumo = resumo_por_mando(JOGOS)
    assert resumo["casa"]["jogos"] == 2 and resumo["casa"]["pontos"] == 3
    assert resumo["casa"]["aproveitamento"] == pytest.approx(50.0)
    assert resumo["fora"]["pontos"] == 4 and resumo["fora"]["aproveitamento"] == pytest.approx(100 * 4 / 6)
    assert resumo["fora"]["gols_pro_media"] == pytest.approx(2.0)


def test_resumo_por_mando_sem_jogos_nao_inventa_numero():
    resumo = resumo_por_mando([_jg(1, "casa", 1, 0)])
    assert resumo["fora"]["jogos"] == 0 and resumo["fora"]["aproveitamento"] is None


def test_medias_da_liga():
    partidas = [_p(1, A, B, 2, 0), _p(1, C, D, 1, 1)]
    m = medias_da_liga(partidas)
    assert m["gols_por_time_por_jogo"] == pytest.approx(1.0)  # 4 gols / (2*2)
    assert m["aproveitamento_casa"] == pytest.approx(100 * 4 / 6)  # 3 + 1 pontos
    assert m["aproveitamento_fora"] == pytest.approx(100 * 1 / 6)
    assert medias_da_liga([])["gols_por_time_por_jogo"] is None


def test_perfil_de_gols_extremos_e_contagens():
    perfil = perfil_de_gols(JOGOS)
    assert perfil["jogos"] == 4 and perfil["gols_pro_media"] == pytest.approx(1.75)
    assert perfil["jogos_marcando"] == 3 and perfil["jogos_sem_sofrer_gol"] == 2
    assert perfil["jogos_3_ou_mais_gols_marcados"] == 1 and perfil["jogos_3_ou_mais_gols_sofridos"] == 1
    assert perfil["maior_vitoria"]["rodada"] == 4 and perfil["maior_vitoria"]["adversario_id"] == 7
    assert perfil["pior_derrota"]["rodada"] == 3
    assert perfil["desvio_gols_pro"] > 0


def test_perfil_de_gols_sem_vitorias_e_sem_jogos():
    assert perfil_de_gols([]) == {"jogos": 0}
    assert perfil_de_gols([_jg(1, "casa", 0, 1)])["maior_vitoria"] is None
    assert perfil_de_gols([_jg(1, "casa", 0, 1)])["desvio_gols_pro"] is None


def test_gols_com_media_movel_so_apos_encher_a_janela():
    linhas = gols_com_media_movel(JOGOS, janela=2)
    assert linhas[0]["pro_movel"] is None
    assert linhas[1]["pro_movel"] == pytest.approx(1.0) and linhas[1]["contra_movel"] == pytest.approx(0.0)
    assert linhas[3]["pro_movel"] == pytest.approx(2.5) and linhas[3]["contra_movel"] == pytest.approx(2.0)


from stats.competicao import (  # noqa: E402
    comparar_com_liga,
    disciplina_da_liga,
    forca_do_calendario,
    metricas_por_time,
    posicao_no_ranking,
)

# Liga sintética de 4 times, turno único (números conferidos à mão):
# A 9 pts (gp 6, gc 1) · D 4 pts (gp 4, gc 4) · C 2 pts (gp 2, gc 3) · B 1 pt (gp 1, gc 5)
LIGA = [
    _p(1, A, B, 2, 0), _p(1, C, D, 1, 1),
    _p(2, A, C, 1, 0), _p(2, B, D, 0, 2),
    _p(3, A, D, 3, 1), _p(3, B, C, 1, 1),
]


def test_metricas_por_time():
    m = metricas_por_time(LIGA)
    assert m[A]["aproveitamento"] == pytest.approx(100.0) and m[A]["ataque"] == pytest.approx(2.0)
    assert m[B]["defesa"] == pytest.approx(5 / 3) and m[D]["aproveitamento"] == pytest.approx(100 * 4 / 9)
    assert m[A]["aproveitamento_fora"] is None  # A só jogou em casa


def test_posicao_no_ranking_percentil_e_empate():
    valores = {1: 10.0, 2: 20.0, 3: 20.0, 4: 30.0}
    r = posicao_no_ranking(valores, 2)
    assert (r["posicao"], r["de"]) == (2, 4) and r["percentil"] == pytest.approx(100 * 2 / 3)
    assert posicao_no_ranking(valores, 3)["posicao"] == 2  # empate divide a posição
    assert posicao_no_ranking(valores, 1, menor_e_melhor=True)["posicao"] == 1
    assert posicao_no_ranking(valores, 99) is None
    assert posicao_no_ranking({1: 5.0}, 1)["percentil"] == 100.0


def test_comparar_com_liga_defesa_menor_e_melhor_e_time_sem_mando_fica_de_fora():
    a = comparar_com_liga(LIGA, A)
    assert a["aproveitamento"]["posicao"] == 1 and a["ataque"]["posicao"] == 1 and a["defesa"]["posicao"] == 1
    assert "aproveitamento_fora" not in a  # A não tem jogo fora
    c = comparar_com_liga(LIGA, C)
    assert c["defesa"]["posicao"] == 2 and c["ataque"]["posicao"] == 3
    b = comparar_com_liga(LIGA, B, cartoes_por_jogo={A: 2.0, B: 3.0, C: 1.0, D: 2.5})
    assert b["cartoes_por_jogo"]["posicao"] == 4  # mais cartões = pior


def test_forca_do_calendario_de_A():
    f = forca_do_calendario(LIGA, A)
    # forças sem contar jogos contra A: B 1/6, C 2/6, D 4/6 -> média 38,9
    assert f["forca_media_adversarios"] == pytest.approx(100 * (1 / 6 + 2 / 6 + 4 / 6) / 3)
    fortes = f["grupos"]["fortes"]
    assert (fortes["jogos"], fortes["vitorias"], fortes["aproveitamento"]) == (1, 1, 100.0)
    assert f["grupos"]["medios"]["jogos"] == 1 and f["grupos"]["fracos"]["jogos"] == 1
    assert f["posicao_dificuldade"] in range(1, 5) and f["times_comparados"] == 4


def test_forca_do_calendario_sem_jogos_devolve_none():
    assert forca_do_calendario([], A) is None
    assert forca_do_calendario(LIGA, 99) is None


def test_disciplina_da_liga_le_o_banco():
    conexao = sqlite3.connect(":memory:")
    conexao.row_factory = sqlite3.Row
    conexao.executescript(db.SCHEMA)
    conexao.execute(
        "INSERT INTO cbf_estatisticas_time (serie, ano, cod_time, jogos_disputados, cartoes_amarelos, cartoes_vermelhos, coletado_em)"
        " VALUES ('serie-a', 2026, 1, 10, 18, 2, 'x'), ('serie-a', 2026, 2, 0, 0, 0, 'x')"
    )
    assert disciplina_da_liga(conexao, "serie-a", 2026) == {1: 2.0}
