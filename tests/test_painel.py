"""Regras do painel comparativo (stats/painel.py), sobre dados sintéticos."""
import pytest

import config
from stats import competicao
from stats.painel import (
    erro_da_projecao,
    frase_de_projecao,
    frases_da_loteca,
    pontos_por_jogo_recentes,
    projetar_temporada,
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


def _projetar(partidas, serie="teste"):
    tabelas = competicao.tabela_por_rodada(partidas)
    jogos = {cod: competicao.jogos_do_time(partidas, cod) for cod in (1, 2)}
    return projetar_temporada(tabelas[max(tabelas)], jogos, serie, 2026)


def test_ritmo_recente_exige_janela_cheia(temporada_curta):
    jogos = competicao.jogos_do_time(_liga(2), 1)
    assert pontos_por_jogo_recentes(jogos) is None
    assert pontos_por_jogo_recentes(competicao.jogos_do_time(_liga(6), 1)) == 0.0  # perdeu os 3 últimos


def test_projecao_nos_dois_ritmos(temporada_curta):
    projecao = _projetar(_liga(6))
    time1 = projecao[1]
    # 9 pontos em 6 jogos, faltam 4: ritmo da temporada 1,5/jogo -> 15; ritmo recente 0/jogo -> 9.
    assert (time1["pontos"], time1["restantes"]) == (9, 4)
    assert time1["pontos_proj_temporada"] == pytest.approx(15.0)
    assert time1["pontos_proj_recente"] == pytest.approx(9.0)
    # O time 2 (9 pontos, ganhou os 3 últimos) passa à frente no ritmo recente: 9 + 4*3 = 21.
    assert projecao[2]["pontos_proj_recente"] == pytest.approx(21.0)
    assert (time1["posicao_proj_recente"], projecao[2]["posicao_proj_recente"]) == (2, 1)
    assert time1["zona_proj_temporada"] is None  # série de teste sem zonas cadastradas


def test_sem_tamanho_de_temporada_cadastrado_nao_projeta(temporada_curta):
    assert _projetar(_liga(6), serie="serie-inexistente") is None


def test_time_que_ja_jogou_tudo_nao_tem_o_que_projetar(temporada_curta, monkeypatch):
    monkeypatch.setitem(config.TEMPORADA_JOGOS_POR_TIME, ("teste", 2026), 6)
    projecao = _projetar(_liga(6))
    assert projecao[1]["restantes"] == 0 and projecao[1]["pontos_proj_temporada"] == 9
    assert frase_de_projecao("TIME 1", projecao[1], NOMES_ZONA) is None


def test_frase_de_projecao_traz_os_dois_ritmos(temporada_curta):
    frase = frase_de_projecao("TIME 1", _projetar(_liga(6))[1], NOMES_ZONA)
    assert frase.startswith("TIME 1: no ritmo da temporada, terminaria com 15 pontos, em 1º")
    assert "no ritmo dos últimos 3 jogos, 9 pontos, em 2º" in frase and frase.endswith("Faltam 4 jogos.")


def test_erro_da_projecao_mede_contra_o_que_aconteceu(temporada_curta):
    # Da rodada 3 até a 6: time 1 tinha 9 pts em 3 jogos (ritmo 3) -> projetaria 18, fez 9 (erro 9).
    # Time 2 tinha 0 -> projetaria 0, fez 9 (erro 9). Média 9 nos dois ritmos.
    erro = erro_da_projecao(_liga(6), rodada_teste=3)
    assert erro["rodada_atual"] == 6 and erro["times"] == 2
    assert erro["erro_medio_temporada"] == pytest.approx(9.0) and erro["erro_medio_recente"] == pytest.approx(9.0)


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
