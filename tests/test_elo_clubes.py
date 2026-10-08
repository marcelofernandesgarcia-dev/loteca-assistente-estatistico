"""Elo de clubes (sugestão S2, adotada em 08/10/2026). Banco SINTÉTICO com placares sorteados por semente fixa."""
import datetime as dt
import random
import sqlite3

import pytest

import config
import db
from externo import percentual_final
from externo.percentual_final import percentuais_do_jogo
from stats import backtest, elo_clubes
from stats.cobertura import cobertura_do_jogo


def _banco(concursos=60, jogos_por_concurso=6, futuro=True):
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    c.executescript(db.SCHEMA)
    clubes = [db.obter_ou_criar_participante(c, f"CLUBE {i}", "clube", "SP") for i in range(10)]
    forca = {t: i for i, t in enumerate(clubes)}
    sorteio = random.Random(8)
    inicio = dt.date(2017, 1, 7)
    for n in range(1, concursos + 1):
        data = (inicio + dt.timedelta(days=42 * n)).isoformat()
        c.execute("INSERT INTO concursos (numero) VALUES (?)", (n,))
        for k in range(jogos_por_concurso):
            casa, fora = sorteio.sample(clubes, 2)
            vantagem = (forca[casa] - forca[fora]) * 0.1 + 0.3
            r = sorteio.random() + vantagem * 0.3
            gc, gf = (2, 0) if r > 0.85 else (1, 1) if r > 0.55 else (0, 1)
            res = "1" if gc > gf else "X" if gc == gf else "2"
            c.execute("INSERT INTO jogos (concurso_numero, num_jogo, casa_id, fora_id, gols_casa, gols_fora, resultado, data_jogo)"
                      " VALUES (?, ?, ?, ?, ?, ?, ?, ?)", (n, k + 1, casa, fora, gc, gf, res, data))
    if futuro:
        c.execute("INSERT INTO concursos (numero) VALUES (?)", (concursos + 1,))
        c.execute("INSERT INTO jogos (concurso_numero, num_jogo, casa_id, fora_id, data_jogo) VALUES (?, 1, ?, ?, ?)",
                  (concursos + 1, clubes[9], clubes[0], (inicio + dt.timedelta(days=42 * (concursos + 1))).isoformat()))
    elo_clubes._cache.clear()
    return c, clubes


def test_rating_soma_zero_e_conta_jogos():
    r = elo_clubes.Ratings()
    r.aplicar({"casa_id": 1, "fora_id": 2, "resultado": "1", "gols_casa": 1, "gols_fora": 0})
    assert r.valor[1] + r.valor[2] == pytest.approx(2 * config.ELO_CLUBES_RATING_INICIAL)
    assert r.valor[1] > r.valor[2] and r.jogos[1] == r.jogos[2] == 1


def test_goleada_mexe_mais_no_rating_que_vitoria_simples(monkeypatch):
    # Variação V1 (margem de gols), aprovada no estudo S3 de 08/10/2026.
    simples, goleada = elo_clubes.Ratings(), elo_clubes.Ratings()
    simples.aplicar({"casa_id": 1, "fora_id": 2, "resultado": "1", "gols_casa": 1, "gols_fora": 0})
    goleada.aplicar({"casa_id": 1, "fora_id": 2, "resultado": "1", "gols_casa": 4, "gols_fora": 0})
    assert goleada.valor[1] > simples.valor[1]
    monkeypatch.setattr(config, "ELO_CLUBES_MARGEM_DE_GOLS", False)
    sem_margem = elo_clubes.Ratings()
    sem_margem.aplicar({"casa_id": 1, "fora_id": 2, "resultado": "1", "gols_casa": 4, "gols_fora": 0})
    assert sem_margem.valor[1] == pytest.approx(simples.valor[1])


def test_walk_forward_nao_olha_o_resultado_do_proprio_concurso():
    c, _ = _banco(futuro=False)
    jogos = backtest.carregar_jogos(c)
    antes = elo_clubes.prever_walk_forward(jogos, elo_clubes.clubes_do_banco(c), desde_ano=2020)
    ultimo = max(j["concurso_numero"] for j in jogos)
    trocados = [dict(j, resultado={"1": "2", "X": "1", "2": "X"}[j["resultado"]]) if j["concurso_numero"] == ultimo else j
                for j in jogos]
    depois = elo_clubes.prever_walk_forward(trocados, elo_clubes.clubes_do_banco(c), desde_ano=2020)
    ids = [j["id"] for j in jogos if j["concurso_numero"] == ultimo]
    assert ids and all(antes[i]["p"] == depois[i]["p"] for i in ids)


def test_producao_da_o_mesmo_numero_que_o_estudo():
    """Paridade: o jogo a jogar é previsto pela tela com a mesma conta que o estudo faria para ele."""
    c, clubes = _banco()
    futuro = c.execute("SELECT id, casa_id, fora_id, data_jogo, concurso_numero FROM jogos WHERE resultado IS NULL").fetchone()
    producao = elo_clubes.prever(c, futuro["casa_id"], futuro["fora_id"], futuro["data_jogo"])
    # o estudo, com o jogo já apurado (o resultado não entra na previsão dele mesmo):
    c.execute("UPDATE jogos SET gols_casa = 1, gols_fora = 0, resultado = '1' WHERE id = ?", (futuro["id"],))
    estudo = elo_clubes.prever_walk_forward(backtest.carregar_jogos(c), elo_clubes.clubes_do_banco(c), desde_ano=2020)
    assert producao == pytest.approx(estudo[futuro["id"]]["p"])
    assert sum(producao.values()) == pytest.approx(100.0)


def test_selecao_e_interruptor_ficam_fora():
    c, clubes = _banco()
    selecao = db.obter_ou_criar_participante(c, "ALEMANHA", "selecao", "GER")
    data = c.execute("SELECT data_jogo FROM jogos WHERE resultado IS NULL").fetchone()[0]
    assert elo_clubes.prever(c, clubes[0], selecao, data) is None
    assert elo_clubes.prever(c, clubes[0], clubes[1], None) is None


def test_combinacao_no_percentual(monkeypatch):
    c, clubes = _banco()
    cbf = {"1": 60.0, "X": 25.0, "2": 15.0}
    elo = {"1": 40.0, "X": 30.0, "2": 30.0}
    monkeypatch.setattr(percentual_final, "prever_cbf", lambda *a: cbf)
    monkeypatch.setattr(percentual_final, "prever_elo", lambda *a: elo)
    r = percentuais_do_jogo(c, clubes[0], clubes[1], {}, "2026-01-01")
    assert r["origem"] == "temporada_cbf_e_elo" and r["original"] == {"1": 50.0, "X": 27.5, "2": 22.5}
    assert r["anterior"] is not None and not r["calibracao"]["aplicada"]
    monkeypatch.setattr(percentual_final, "prever_cbf", lambda *a: None)
    r = percentuais_do_jogo(c, clubes[0], clubes[1], {}, "2026-01-01")
    assert r["origem"] == "elo_clubes" and r["original"] == elo
    monkeypatch.setattr(percentual_final, "prever_elo", lambda *a: None)
    r = percentuais_do_jogo(c, clubes[0], clubes[1], {}, "2026-01-01")
    assert r["origem"] in ("poisson", "frequencia_global") and r["anterior"] is None


def test_interruptor_desliga_o_elo(monkeypatch):
    c, clubes = _banco()
    data = c.execute("SELECT data_jogo FROM jogos WHERE resultado IS NULL").fetchone()[0]
    assert elo_clubes.prever(c, clubes[0], clubes[1], data) is not None
    monkeypatch.setattr(config, "ELO_CLUBES_ATIVO", False)
    assert elo_clubes.prever(c, clubes[0], clubes[1], data) is None


def test_cobertura_do_elo_com_poucos_jogos_e_baixa():
    agora = dt.datetime(2026, 10, 10, 9)
    lado = lambda nome, n: {"nome": nome, "tipo": "clube", "cbf": None, "jogos_no_ano": 10, "ano": 2026,  # noqa: E731
                            "noticias_em": "2026-10-10T08:00:00", "jogos_rating": n}
    pouca = cobertura_do_jogo(lado("MONZA", 3), lado("LAZIO", 40), "elo_clubes", agora)
    assert pouca["nivel"] == "baixa" and "MONZA: só 3 jogo(s) da Loteca no rating Elo" in pouca["faltas"]
    assert cobertura_do_jogo(lado("A", 40), lado("B", 40), "elo_clubes", agora)["nivel"] == "parcial"
