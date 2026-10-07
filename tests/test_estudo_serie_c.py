"""Estudo da Série C (itens B3 e C2 do plano v2): contas sobre banco SINTÉTICO."""
import random
import sqlite3

import pytest

import db
from stats import estudo_serie_c as e


@pytest.fixture()
def conexao():
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    c.executescript(db.SCHEMA)
    return c


def _partida(c, id_jogo, ano, fase, gm, gv, rodada=1, mandante=1, visitante=2, rodada_fase=None):
    c.execute(
        "INSERT INTO cbf_partidas (id_jogo, serie, ano, rodada, data_jogo, mandante_id, visitante_id, gols_mandante,"
        " gols_visitante, coletado_em, fase, rodada_fase) VALUES (?, 'serie-c', ?, ?, ?, ?, ?, ?, ?, 'x', ?, ?)",
        (id_jogo, ano, rodada, f"{ano}-05-{rodada:02d}", mandante, visitante, gm, gv, fase,
         rodada if rodada_fase is None else rodada_fase),
    )


def test_fase_decisiva_e_pela_posicao_e_nao_pelo_nome():
    # 2023: a CBF chamou a 1ª fase de "TURNO" (conferido em 07/10/2026).
    assert e._decisiva("TURNO", 5, 5) is False and e._decisiva("1ª Fase", 19, 19) is False
    assert e._decisiva("2a Fase", 20, 1) is True and e._decisiva("Final", 26, 1) is True
    assert e._decisiva(None, 3, 3) is None


def test_empates_por_fase_com_intervalo(conexao):
    for i, (fase, gm, gv) in enumerate([("1ª Fase", 1, 0), ("1ª Fase", 1, 1), ("1ª Fase", 2, 0), ("1ª Fase", 0, 1),
                                        ("2ª Fase", 1, 1), ("2ª Fase", 0, 0), ("2ª Fase", 2, 1), (None, 1, 1)]):
        decisiva = fase == "2ª Fase"
        _partida(conexao, i + 1, 2024, fase, gm, gv, rodada=20 if decisiva else 1, rodada_fase=1)
    r = e.empates_por_fase(conexao)
    assert (r["primeira_fase"]["empates"], r["primeira_fase"]["jogos"]) == (1, 4)
    assert (r["decisivas"]["empates"], r["decisivas"]["jogos"]) == (2, 3)  # o jogo sem fase fica de fora
    assert r["diferenca"]["pontos"] == pytest.approx(2 / 3 - 1 / 4)
    baixo, alto = r["decisivas"]["ic95"]
    assert baixo < 2 / 3 < alto


def test_cobertura_por_temporada(conexao):
    _partida(conexao, 1, 2024, "1ª Fase", 1, 0)
    _partida(conexao, 2, 2024, None, None, None)
    linha = e.cobertura(conexao)[0]
    assert (linha["ano"], linha["jogos"], linha["com_placar"], linha["fases"], linha["sem_fase"]) == (2024, 2, 1, 1, 1)


def test_indicador_de_fase_sem_efeito_real_nao_aparece_como_ganho():
    # Resultados sorteados sem relação com a fase: o ganho médio fica perto de zero e o intervalo cobre o zero.
    sorteio = random.Random(1)
    amostra, fases = [], {}
    for ano in range(2019, 2025):
        for i in range(150):
            id_jogo = ano * 1000 + i
            fases[id_jogo] = i >= 120
            amostra.append({"id_jogo": id_jogo, "ano": ano, "cluster": f"{ano}-{i // 10}",
                            "retro_casa": sorteio.uniform(0.5, 2.5), "retro_fora": sorteio.uniform(0.5, 2.5),
                            "resultado": sorteio.choice("11X22X1")})
    r = e.teste_fase_decisiva(amostra, fases)
    assert r["n"] == 5 * 150
    assert r["ic_inferior"] < 0 < r["ic_superior"] or r["media"] <= 0.002


def test_sem_dois_anos_com_fase_nao_testa():
    assert e.teste_fase_decisiva([{"id_jogo": 1, "ano": 2024, "cluster": "c", "retro_casa": 1, "retro_fora": 1,
                                   "resultado": "1"}], {1: False}) is None
