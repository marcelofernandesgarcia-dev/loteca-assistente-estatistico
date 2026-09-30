"""Regras do painel comparativo (stats/painel.py), sobre dados sintéticos."""
import pytest

import config
from stats import competicao
from stats.painel import (
    erro_da_projecao,
    frase_de_projecao,
    frases_da_loteca,
    media_da_liga,
    peso_do_time,
    pontos_por_jogo_recentes,
    projetar_temporada,
    ritmo_cautelosa,
    resumo_loteca,
    reta_anual,
    reta_de_tendencia,
    tendencia_anual_loteca,
    tendencia_do_aproveitamento,
)
from stats.contexto import NOMES_ZONA


def _partida(rodada, casa, fora, gc, gf, id_jogo=None):
    return {
        "id_jogo": id_jogo or rodada * 100 + casa, "rodada": rodada, "data_jogo": f"2026-01-{rodada:02d}",
        "mandante_id": casa, "visitante_id": fora, "gols_mandante": gc, "gols_visitante": gf,
    }


def _liga(rodadas=6):
    """2 times, um jogo por rodada: o time 1 vence as 3 primeiras e perde as
    demais; o time 2 é o espelho."""
    partidas = []
    for r in range(1, rodadas + 1):
        casa, fora = (1, 2) if r % 2 else (2, 1)
        vence_1 = r <= 3
        gols_1, gols_2 = (1, 0) if vence_1 else (0, 1)
        partidas.append(_partida(r, casa, fora, gols_1 if casa == 1 else gols_2, gols_2 if casa == 1 else gols_1))
    return partidas


@pytest.fixture()
def temporada_curta(monkeypatch):
    monkeypatch.setitem(config.TEMPORADA_JOGOS_POR_TIME, ("teste", 2026), 10)
    monkeypatch.setattr(config, "COMPETICAO_JANELA_MOVEL", 3)


def _linha(cod, jogos, pontos):
    return {"cod_time": cod, "jogos": jogos, "pontos": pontos, "vitorias": pontos // 3, "saldo": 0, "gols_pro": 0}


@pytest.fixture()
def k_pequeno(monkeypatch):
    """k = 6 jogos de média da liga: contas redondas nos exemplos abaixo."""
    monkeypatch.setattr(config, "PROJECAO_JOGOS_DE_MEDIA_DA_LIGA", 6)


def test_ritmo_recente_exige_janela_cheia(temporada_curta):
    jogos = competicao.jogos_do_time(_liga(2), 1)
    assert pontos_por_jogo_recentes(jogos) is None
    assert pontos_por_jogo_recentes(competicao.jogos_do_time(_liga(6), 1)) == 0.0  # perdeu os 3 últimos


def test_peso_do_time_cresce_com_os_jogos_disputados(k_pequeno):
    assert peso_do_time(0) == 0.0
    assert peso_do_time(6) == pytest.approx(0.5)  # jogos = k: metade time, metade liga
    assert peso_do_time(2) < peso_do_time(6) < peso_do_time(38) < 1.0


def test_ritmo_cautelosa_mistura_o_time_com_a_media_da_liga(k_pequeno):
    # 30 pontos em 6 jogos (5 por jogo, exagero de amostra pequena), média da liga 1,5, peso 0,5 -> 3,25.
    assert ritmo_cautelosa(30, 6, 1.5) == pytest.approx(0.5 * 5.0 + 0.5 * 1.5)
    assert ritmo_cautelosa(0, 0, 1.5) == 1.5  # sem jogos, é a média da liga
    assert ritmo_cautelosa(9, 6, 1.5) == pytest.approx(1.5)  # time igual à média: nada muda


def test_media_da_liga_e_pontos_por_jogo_de_um_time_tipico():
    assert media_da_liga([_linha(1, 6, 15), _linha(2, 6, 3)]) == pytest.approx(18 / 12)
    assert media_da_liga([]) == 0.0


def test_projecao_nos_dois_cenarios(monkeypatch, k_pequeno):
    monkeypatch.setitem(config.TEMPORADA_JOGOS_POR_TIME, ("teste", 2026), 10)
    tabela = [_linha(1, 6, 15), _linha(2, 6, 3)]  # média da liga 1,5; peso do time 0,5; faltam 4 jogos
    projecao = projetar_temporada(tabela, "teste", 2026)
    a, b = projecao[1], projecao[2]
    assert (a["restantes"], a["peso_do_time"], a["media_da_liga"]) == (4, 0.5, pytest.approx(1.5))
    assert a["pontos_proj_temporada"] == pytest.approx(15 + 4 * 2.5)  # 25: o ritmo do time se repete
    assert a["pontos_proj_cautelosa"] == pytest.approx(15 + 4 * (0.5 * 2.5 + 0.5 * 1.5))  # 23: puxado para a média
    assert b["pontos_proj_temporada"] == pytest.approx(3 + 4 * 0.5)
    assert b["pontos_proj_cautelosa"] == pytest.approx(3 + 4 * (0.5 * 0.5 + 0.5 * 1.5))  # 7: sobe para a média
    assert a["zona_proj_temporada"] is None  # série de teste sem zonas cadastradas


def test_cautelosa_pode_inverter_a_ordem_quando_o_ritmo_vem_de_poucos_jogos(monkeypatch):
    monkeypatch.setitem(config.TEMPORADA_JOGOS_POR_TIME, ("teste", 2026), 38)
    monkeypatch.setattr(config, "PROJECAO_JOGOS_DE_MEDIA_DA_LIGA", 20)
    # A: 6 pontos em 2 jogos (3,0/jogo, amostra minúscula). B: 26 em 12 (2,17/jogo). C: 10 em 10.
    projecao = projetar_temporada([_linha(1, 2, 6), _linha(2, 12, 26), _linha(3, 10, 10)], "teste", 2026)
    assert (projecao[1]["posicao_proj_temporada"], projecao[2]["posicao_proj_temporada"]) == (1, 2)  # só o ritmo: A na frente
    assert (projecao[2]["posicao_proj_cautelosa"], projecao[1]["posicao_proj_cautelosa"]) == (1, 2)  # cautelosa: B passa
    assert projecao[3]["posicao_proj_temporada"] == projecao[3]["posicao_proj_cautelosa"] == 3
    assert projecao[1]["peso_do_time"] < projecao[2]["peso_do_time"]  # quem jogou menos vale menos


def test_sem_tamanho_de_temporada_cadastrado_nao_projeta():
    assert projetar_temporada([_linha(1, 6, 9)], "serie-inexistente", 2026) is None


def test_time_que_ja_jogou_tudo_nao_tem_o_que_projetar(monkeypatch, k_pequeno):
    monkeypatch.setitem(config.TEMPORADA_JOGOS_POR_TIME, ("teste", 2026), 6)
    projecao = projetar_temporada([_linha(1, 6, 9), _linha(2, 6, 9)], "teste", 2026)
    assert projecao[1]["restantes"] == 0 and projecao[1]["pontos_proj_temporada"] == 9 == projecao[1]["pontos_proj_cautelosa"]
    assert frase_de_projecao("TIME 1", projecao[1], NOMES_ZONA) is None


def test_frase_de_projecao_traz_os_dois_cenarios(monkeypatch, k_pequeno):
    monkeypatch.setitem(config.TEMPORADA_JOGOS_POR_TIME, ("teste", 2026), 10)
    projecao = projetar_temporada([_linha(1, 6, 15), _linha(2, 6, 3)], "teste", 2026)
    frase = frase_de_projecao("TIME 1", projecao[1], NOMES_ZONA)
    assert frase.startswith("TIME 1: no ritmo da temporada, terminaria com 25 pontos, em 1º")
    assert "na projeção cautelosa (50% do ritmo do time e o resto pela média da liga), 23 pontos, em 1º" in frase
    assert frase.endswith("Faltam 4 jogos.")


def test_erro_da_projecao_mede_contra_o_que_aconteceu(temporada_curta, monkeypatch):
    monkeypatch.setattr(config, "PROJECAO_JOGOS_DE_MEDIA_DA_LIGA", 3)
    # Da rodada 3 até a 6: time 1 tinha 9 pts em 3 jogos (ritmo 3) -> projetaria 18, fez 9 (erro 9).
    # Time 2 tinha 0 -> projetaria 0, fez 9 (erro 9). Média 9 nos dois ritmos.
    # Cautelosa (média da liga 1,5; peso 0,5): time 1 -> 9 + 3*2,25 = 15,75 (erro 6,75); time 2 -> 0 + 3*0,75 = 2,25 (erro 6,75).
    erro = erro_da_projecao(_liga(6), rodada_teste=3)
    assert erro["rodada_atual"] == 6 and erro["times"] == 2
    assert erro["erro_medio_temporada"] == pytest.approx(9.0) and erro["erro_medio_recente"] == pytest.approx(9.0)
    assert erro["erro_medio_cautelosa"] == pytest.approx(6.75)


def test_erro_da_projecao_sem_rodadas_depois_do_teste(temporada_curta):
    assert erro_da_projecao(_liga(3), rodada_teste=3) is None


def test_reta_de_tendencia_exata_e_ponderada():
    assert reta_de_tendencia([(1, 10), (2, 20), (3, 30)]) == pytest.approx((0.0, 10.0))
    a, b = reta_de_tendencia([(1, 0), (2, 100)], pesos=[1, 1])
    assert (a, b) == pytest.approx((-100.0, 100.0))
    assert reta_de_tendencia([(1, 5), (1, 7)]) is None  # um x só


def test_tendencia_do_aproveitamento_fica_entre_0_e_100():
    movel = [{"rodada": 5, "aproveitamento_movel": 40.0}, {"rodada": 6, "aproveitamento_movel": 80.0}]
    reta = tendencia_do_aproveitamento(movel, ate_rodada=38)
    assert reta[0] == {"rodada": 5, "valor": 40.0} and reta[-1] == {"rodada": 38, "valor": 100.0}
    assert tendencia_do_aproveitamento(movel, ate_rodada=None) is None


# --- Várias temporadas (coleta histórica) ------------------------------------------------

import random
import sqlite3

import db
from stats.painel import (
    erro_da_projecao_entre_temporadas,
    frase_erro_entre_temporadas,
    nomes_da_temporada,
    temporadas_atuais,
    temporadas_disponiveis,
)


def _banco_com_temporadas(anos=(2024, 2025), semente=1):
    """4 times, turno e returno (12 jogos, 6 rodadas) por temporada, resultados sorteados."""
    conexao = sqlite3.connect(":memory:")
    conexao.row_factory = sqlite3.Row
    conexao.executescript(db.SCHEMA)
    rng = random.Random(semente)
    turno = [[(1, 2), (3, 4)], [(1, 3), (2, 4)], [(1, 4), (2, 3)]]
    id_jogo = 0
    for ano in anos:
        rodadas = turno + [[(b, a) for a, b in r] for r in turno]
        for numero, pares in enumerate(rodadas, start=1):
            for casa, fora in pares:
                id_jogo += 1
                conexao.execute(
                    "INSERT INTO cbf_partidas (id_jogo, serie, ano, rodada, data_jogo, mandante_id, visitante_id,"
                    " gols_mandante, gols_visitante, coletado_em) VALUES (?, 'serie-a', ?, ?, ?, ?, ?, ?, ?, 'x')",
                    (id_jogo, ano, numero, f"{ano}-05-{numero:02d}", casa, fora, rng.randint(0, 3), rng.randint(0, 2)),
                )
    return conexao


def test_temporadas_atuais_sao_so_as_do_ano_mais_recente():
    todas = [("serie-a", 2026), ("serie-b", 2026), ("serie-a", 2025), ("serie-b", 2019)]
    assert temporadas_atuais(todas) == [("serie-a", 2026), ("serie-b", 2026)]
    assert temporadas_atuais([]) == []


def test_temporadas_disponiveis_lista_todas_da_mais_recente_para_a_mais_antiga():
    assert temporadas_disponiveis(_banco_com_temporadas((2019, 2025, 2022))) == [
        ("serie-a", 2025), ("serie-a", 2022), ("serie-a", 2019),
    ]


def test_nome_do_time_naquela_temporada_cai_no_nome_atual_quando_falta():
    conexao = _banco_com_temporadas()
    conexao.execute("INSERT INTO cbf_times (cod_time, nome) VALUES (1, 'Time Um SAF'), (2, 'Time Dois')")
    conexao.execute(
        "INSERT INTO cbf_classificacao (serie, ano, cod_time, rodada, coletado_em, nome_no_ano)"
        " VALUES ('serie-a', 2019, 1, 38, 'x', 'Time Um')"
    )
    assert nomes_da_temporada(conexao, "serie-a", 2019) == {1: "Time Um", 2: "Time Dois"}  # 1 tem nome do ano; 2 cai no atual
    assert nomes_da_temporada(conexao, "serie-a", 2026)[1] == "Time Um SAF"  # sem nome guardado para 2026: nome atual


def test_erro_entre_temporadas_mede_so_temporadas_completas(monkeypatch):
    monkeypatch.setattr(config, "CBF_JOGOS_TEMPORADA_COMPLETA", 12)
    monkeypatch.setattr(config, "COMPETICAO_JANELA_MOVEL", 2)
    conexao = _banco_com_temporadas((2024, 2025))
    conexao.execute("DELETE FROM cbf_partidas WHERE ano = 2025 AND rodada = 6")  # 2025 incompleta: fica de fora
    resumo = erro_da_projecao_entre_temporadas(conexao, rodadas_de_teste=(2, 4))
    assert resumo["temporadas"] == [("serie-a", 2024)]
    assert set(resumo["por_rodada"]) == {2, 4}
    r2, r4 = resumo["por_rodada"][2], resumo["por_rodada"][4]
    assert (r2["temporadas"], r2["jogos_restantes"], r4["jogos_restantes"]) == (1, 4, 2)
    assert r2["erro_temporada"] >= 0 and r2["erro_cautelosa"] >= 0 and r2["erro_recente"] >= 0 and r2["com_recente"] == 1
    assert 0 <= r2["cautelosa_melhor_em"] <= 1 and 0 <= r2["recente_melhor_em"] <= 1


def test_erro_entre_temporadas_sem_temporada_completa_devolve_none():
    assert erro_da_projecao_entre_temporadas(_banco_com_temporadas((2025,))) is None  # 12 jogos < 380


def test_erro_entre_temporadas_calcula_a_media_das_temporadas(monkeypatch):
    monkeypatch.setattr(config, "CBF_JOGOS_TEMPORADA_COMPLETA", 12)
    monkeypatch.setattr(config, "COMPETICAO_JANELA_MOVEL", 2)
    conexao = _banco_com_temporadas((2023, 2024, 2025))
    resumo = erro_da_projecao_entre_temporadas(conexao, rodadas_de_teste=(3,))
    from stats.painel import erro_da_projecao
    from stats import competicao

    por_temporada = [
        erro_da_projecao(competicao.carregar_partidas(conexao, "serie-a", ano), rodada_teste=3)
        for ano in (2023, 2024, 2025)
    ]
    assert resumo["por_rodada"][3]["temporadas"] == 3
    assert resumo["por_rodada"][3]["erro_temporada"] == pytest.approx(sum(e["erro_medio_temporada"] for e in por_temporada) / 3)
    assert resumo["por_rodada"][3]["erro_cautelosa"] == pytest.approx(sum(e["erro_medio_cautelosa"] for e in por_temporada) / 3)
    melhores = sum(1 for e in por_temporada if e["erro_medio_cautelosa"] < e["erro_medio_temporada"])
    assert resumo["por_rodada"][3]["cautelosa_melhor_em"] == melhores


def test_frase_do_erro_entre_temporadas_traz_os_numeros_e_o_periodo():
    resumo = {
        "temporadas": [("serie-a", 2019), ("serie-b", 2025)],
        "por_rodada": {
            28: {"temporadas": 2, "jogos_restantes": 10, "erro_temporada": 2.5, "erro_cautelosa": 2.4, "cautelosa_melhor_em": 2,
                 "erro_recente": 3.5, "recente_melhor_em": 0, "com_recente": 2},
            19: {"temporadas": 2, "jogos_restantes": 19, "erro_temporada": 4.0, "erro_cautelosa": 3.1, "cautelosa_melhor_em": 1,
                 "erro_recente": 5.0, "recente_melhor_em": 1, "com_recente": 2},
        },
    }
    frase = frase_erro_entre_temporadas(resumo)
    assert "2 temporadas completas (2019 a 2025, Séries A e B)" in frase
    assert ("faltando 10 jogos, o ritmo da temporada errou 2,5 pontos por time e a projeção cautelosa 2,4 "
            "(a cautelosa foi melhor em 2 de 2 temporadas)") in frase
    assert ("faltando 19 jogos, o ritmo da temporada errou 4,0 pontos por time e a projeção cautelosa 3,1 "
            "(a cautelosa foi melhor em 1 de 2 temporadas)") in frase
    # O ritmo recente saiu do painel, mas a frase conta por que: melhor em 1 de 4 medições.
    assert "foi melhor que o da temporada em 1 de 4 medições e saiu do painel" in frase
    assert frase_erro_entre_temporadas(None) is None and frase_erro_entre_temporadas({"temporadas": [], "por_rodada": {}}) is None


def _jogo_loteca(ano, resultado, mando="casa", pro=1, contra=0):
    pontos = {"V": 3, "E": 1, "D": 0}[resultado]
    return {"ano": ano, "mando": mando, "gols_pro": pro, "gols_contra": contra, "resultado": resultado, "pontos": pontos}


def test_resumo_loteca_usa_aproveitamento_por_pontos():
    jogos = [_jogo_loteca(2024, "V"), _jogo_loteca(2024, "E", "fora", 1, 1), _jogo_loteca(None, "D", "fora", 0, 2)]
    resumo = resumo_loteca(jogos)
    assert (resumo["jogos"], resumo["vitorias"], resumo["empates"], resumo["derrotas"]) == (3, 1, 1, 1)
    assert resumo["aproveitamento"] == pytest.approx(100 * 4 / 9)  # não é % de vitórias (33%)
    assert resumo["aproveitamento_casa"] == 100.0 and resumo["aproveitamento_fora"] == pytest.approx(100 / 6)
    assert resumo["amostra_pequena"] and resumo["aproveitamento_recente"] is None


def test_resumo_loteca_com_periodo_exclui_e_conta_jogos_sem_data():
    jogos = [_jogo_loteca(2020, "V"), _jogo_loteca(2024, "D"), _jogo_loteca(None, "V")]
    resumo = resumo_loteca(jogos, ano_inicial=2021, ano_final=2026)
    assert resumo["jogos"] == 1 and resumo["derrotas"] == 1 and resumo["sem_data_excluidos"] == 1


def test_resumo_loteca_sem_jogos_nao_divide_por_zero():
    resumo = resumo_loteca([])
    assert resumo["jogos"] == 0 and resumo["aproveitamento"] is None
    assert frases_da_loteca("X", resumo) == ["X: sem jogos no período."]


def test_ritmo_recente_na_loteca(monkeypatch):
    monkeypatch.setattr(config, "PAINEL_JANELA_RECENTE_LOTECA", 2)
    monkeypatch.setattr(config, "PAINEL_MIN_JOGOS_LOTECA", 2)
    jogos = [_jogo_loteca(2020, "D"), _jogo_loteca(2020, "D"), _jogo_loteca(2021, "V"), _jogo_loteca(2021, "V")]
    resumo = resumo_loteca(jogos)
    assert resumo["aproveitamento_recente"] == 100.0 and resumo["aproveitamento"] == 50.0
    assert "nos últimos 2 jogos na Loteca, aproveitamento de 100%, acima dos 50%" in frases_da_loteca("X", resumo)[0]


def test_tendencia_anual_marca_ano_fraco_e_conta_sem_data():
    jogos = [_jogo_loteca(2020, "V")] * 3 + [_jogo_loteca(2021, "D")] + [_jogo_loteca(None, "V")]
    tendencia = tendencia_anual_loteca(jogos)
    assert tendencia["anos"] == [
        {"ano": 2020, "jogos": 3, "aproveitamento": 100.0, "fraco": False},
        {"ano": 2021, "jogos": 1, "aproveitamento": 0.0, "fraco": True},
    ]
    assert tendencia["sem_data"] == 1


def test_reta_anual_exige_anos_com_base_e_estende_um_ano():
    anos = [
        {"ano": 2020, "jogos": 5, "aproveitamento": 40.0, "fraco": False},
        {"ano": 2021, "jogos": 5, "aproveitamento": 50.0, "fraco": False},
        {"ano": 2022, "jogos": 1, "aproveitamento": 0.0, "fraco": True},
    ]
    assert reta_anual(anos) is None  # só 2 anos com base
    anos.append({"ano": 2023, "jogos": 5, "aproveitamento": 70.0, "fraco": False})
    reta = reta_anual(anos)
    assert [p["ano"] for p in reta] == [2020, 2024]
    assert 0.0 <= reta[-1]["valor"] <= 100.0 and reta[-1]["valor"] > reta[0]["valor"]
