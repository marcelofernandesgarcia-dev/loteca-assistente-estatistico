"""Força das seleções (stats/selecoes.py): Elo, curva de probabilidade, casamento
com a base e o teste sem olhar o futuro. Dados sintéticos; nada aqui faz rede."""
import math
import random
import sqlite3

import numpy as np
import pytest

import config
import db
from stats import selecoes as s


def _jogo(data, casa, fora, gc, gf, torneio="Friendly", neutro=False):
    return {"data": data, "casa": casa, "fora": fora, "gols_casa": gc, "gols_fora": gf, "torneio": torneio, "neutro": neutro}


# --- Elo ----------------------------------------------------------------------

@pytest.mark.parametrize(
    "torneio,k",
    [
        ("Friendly", 20.0), ("FIFA World Cup", 60.0), ("UEFA Euro", 50.0), ("Copa América", 50.0),
        ("FIFA World Cup qualification", 40.0), ("UEFA Nations League", 40.0), ("COSAFA Cup", 30.0),
    ],
)
def test_peso_do_torneio(torneio, k):
    assert s.peso_torneio(torneio) == k


def test_elo_e_soma_zero_e_vencedor_sobe():
    ratings = {}
    s.atualizar_elo(ratings, _jogo("2020-01-01", "A", "B", 2, 0))
    assert ratings["A"] > config.ELO_RATING_INICIAL > ratings["B"]
    assert ratings["A"] + ratings["B"] == pytest.approx(2 * config.ELO_RATING_INICIAL)


def test_empate_entre_iguais_em_campo_neutro_nao_mexe_nos_ratings():
    ratings = {}
    s.atualizar_elo(ratings, _jogo("2020-01-01", "A", "B", 1, 1, neutro=True))
    assert ratings["A"] == pytest.approx(config.ELO_RATING_INICIAL) == pytest.approx(ratings["B"])


def test_mandante_em_casa_ganha_menos_por_vencer_pois_ja_era_favorito():
    em_casa, neutro = {}, {}
    s.atualizar_elo(em_casa, _jogo("2020-01-01", "A", "B", 1, 0, neutro=False))
    s.atualizar_elo(neutro, _jogo("2020-01-01", "A", "B", 1, 0, neutro=True))
    assert em_casa["A"] - config.ELO_RATING_INICIAL < neutro["A"] - config.ELO_RATING_INICIAL


def test_goleada_vale_mais_que_vitoria_simples_e_torneio_maior_mexe_mais():
    simples, goleada, copa = {}, {}, {}
    s.atualizar_elo(simples, _jogo("2020-01-01", "A", "B", 1, 0))
    s.atualizar_elo(goleada, _jogo("2020-01-01", "A", "B", 4, 0))
    s.atualizar_elo(copa, _jogo("2020-01-01", "A", "B", 1, 0, torneio="FIFA World Cup"))
    assert goleada["A"] > simples["A"] and copa["A"] > simples["A"]


def test_esperado_soma_um_e_vantagem_de_mandante():
    assert s.esperado(1500, 1500, neutro=True) == pytest.approx(0.5)
    assert s.esperado(1500, 1500, neutro=False) > 0.5
    assert s.esperado(1700, 1500, True) + s.esperado(1500, 1700, True) == pytest.approx(1.0)


def test_jogo_so_entra_nos_ratings_depois_de_registrado_para_o_treino():
    """Sem vazamento: a amostra de treino de um jogo usa os ratings de ANTES dele."""
    jogos = [_jogo("2020-01-01", "A", "B", 5, 0), _jogo("2020-02-01", "A", "B", 0, 0)]
    d, h, y = s.amostras_de_treino(jogos, "2020-01-01", "2021-01-01")
    assert d[0] == 0.0  # o primeiro jogo vê os dois em 1500
    assert d[1] > 0.0  # o segundo já vê o resultado do primeiro
    assert list(y) == [2, 1]


def test_amostras_respeitam_a_janela_de_datas():
    jogos = [_jogo(f"20{a}-01-01", "A", "B", 1, 0) for a in ("10", "11", "12", "13")]
    d, _, _ = s.amostras_de_treino(jogos, "2011-01-01", "2013-01-01")
    assert len(d) == 2


# --- Curva (logística ordenada) ----------------------------------------------------

def test_ajuste_recupera_parametros_conhecidos():
    rng = np.random.default_rng(7)
    n = 20000
    d = rng.normal(0, 1.5, n)
    h = rng.integers(0, 2, n).astype(float)
    verdadeiros = (0.5, 0.4, -0.8, math.log(1.2))
    p_fora, p_empate, _ = s._probabilidades_array(verdadeiros, d, h)
    u = rng.random(n)
    y = np.where(u < p_fora, 0, np.where(u < p_fora + p_empate, 1, 2))
    b, c, t1, g = s.ajustar_curva(d, h, y)
    assert b == pytest.approx(0.5, abs=0.05) and c == pytest.approx(0.4, abs=0.08)
    assert t1 == pytest.approx(-0.8, abs=0.08) and g == pytest.approx(math.log(1.2), abs=0.08)


def test_probabilidades_somam_100_e_respeitam_a_forca():
    params = (0.5, 0.4, -0.8, 0.2)
    for diferenca in (-6, -1, 0, 1, 6):
        p = s.probabilidades(params, diferenca, 1.0)
        assert sum(p.values()) == pytest.approx(100.0) and all(v > 0 for v in p.values())
    forte, fraco = s.probabilidades(params, 3, 0.5), s.probabilidades(params, -3, 0.5)
    assert forte["1"] > 70 > 30 > fraco["1"] and forte["2"] == pytest.approx(fraco["1"], abs=15)


def test_campo_desconhecido_e_a_mistura_do_neutro_e_do_nao_neutro():
    params = (0.5, 0.4, -0.8, 0.2)
    meio = s.probabilidades(params, 0.5, 0.5)
    casa, neutro = s.probabilidades(params, 0.5, 1.0), s.probabilidades(params, 0.5, 0.0)
    assert meio["1"] == pytest.approx((casa["1"] + neutro["1"]) / 2)
    assert casa["1"] > neutro["1"]


def test_ajuste_com_amostra_pequena_e_erro_claro():
    with pytest.raises(ValueError, match="Amostra pequena"):
        s.ajustar_curva(np.zeros(10), np.zeros(10), np.zeros(10))


# --- Leitura e nomes -------------------------------------------------------------

def test_leitura_ordena_por_data_e_ignora_linha_sem_placar(tmp_path):
    arquivo = tmp_path / "base.csv"
    arquivo.write_text(
        "date,home_team,away_team,home_score,away_score,tournament,city,country,neutral\n"
        "2020-05-01,B,A,1,0,Friendly,X,Y,FALSE\n"
        "2020-01-01,A,B,2,2,FIFA World Cup,X,Y,TRUE\n"
        "2020-09-01,A,B,NA,NA,Friendly,X,Y,FALSE\n",
        encoding="utf-8",
    )
    jogos = s.carregar_resultados(str(arquivo))
    assert [j["data"] for j in jogos] == ["2020-01-01", "2020-05-01"]
    assert jogos[0]["neutro"] is True and jogos[1]["neutro"] is False and jogos[0]["gols_casa"] == 2


def test_mapa_de_nomes_real_cobre_as_74_selecoes_e_todos_existem_na_base():
    nomes = s.carregar_nomes()
    assert len(nomes) == 74 and nomes["PAIS DE GALES"] == "Wales" and nomes["IRLANDA"] == "Republic of Ireland"
    existentes = {j["casa"] for j in s.carregar_resultados()} | {j["fora"] for j in s.carregar_resultados()}
    assert [n for n in nomes.values() if n not in existentes] == []


# --- Casamento com a base ----------------------------------------------------------

BASE = [_jogo("2020-03-10", "Spain", "England", 2, 1, neutro=True), _jogo("2020-06-10", "England", "Spain", 0, 0)]


def test_casa_jogo_na_mesma_ordem_e_com_tolerancia_de_dias():
    indice = s.indexar_base(BASE)
    par = s.casar_jogo(indice, BASE, "Spain", "England", "2020-03-12")
    assert par["trocado"] is False and par["jogo"]["data"] == "2020-03-10"
    assert s.casar_jogo(indice, BASE, "Spain", "England", "2020-03-20") is None  # 10 dias: longe demais


def test_casa_jogo_com_a_ordem_trocada_e_resultado_na_orientacao_da_loteca():
    indice = s.indexar_base(BASE)
    par = s.casar_jogo(indice, BASE, "England", "Spain", "2020-03-10")  # a Loteca listou England como mandante
    assert par["trocado"] is True
    assert s._resultado_da_base(par["jogo"], par["trocado"]) == "2"  # Spain (mandante da base) venceu; para a Loteca, visitante


def test_resultado_da_base_empate_e_vitoria_do_mandante():
    assert s._resultado_da_base(_jogo("2020-01-01", "A", "B", 1, 1), False) == "X"
    assert s._resultado_da_base(_jogo("2020-01-01", "A", "B", 3, 1), False) == "1"


# --- Teste sem olhar o futuro ----------------------------------------------------------

def test_ratings_usam_so_jogos_estritamente_anteriores():
    jogos = [_jogo("2020-01-01", "A", "B", 3, 0), _jogo("2020-02-01", "A", "B", 3, 0)]
    antes_primeiro = s._ratings_antes_de_cada_jogo(jogos, [("2020-01-01", "A", "B")])[0]
    assert antes_primeiro == (config.ELO_RATING_INICIAL, config.ELO_RATING_INICIAL)  # o próprio dia não entra
    (a1, _), (a2, _) = s._ratings_antes_de_cada_jogo(jogos, [("2020-01-02", "A", "B"), ("2020-02-02", "A", "B")])
    assert a2 > a1 > config.ELO_RATING_INICIAL


def _base_sintetica(anos=range(1995, 2022)):
    """Base com 3 seleções de força bem diferente, jogos toda semana (só para exercitar o teste)."""
    rng = random.Random(3)
    forca = {"Forte": 2.2, "Media": 1.4, "Fraca": 0.7}
    jogos = []
    for ano in anos:
        for mes in range(1, 13):
            for a, b in (("Forte", "Media"), ("Media", "Fraca"), ("Forte", "Fraca")):
                if mes % 3 == 0:  # o mais forte também joga fora: senão "sempre mandante" empataria com o Elo
                    a, b = b, a
                gols = lambda lam: sum(1 for _ in range(6) if rng.random() < lam / 6)
                jogos.append(_jogo(f"{ano}-{mes:02d}-10", a, b, gols(forca[a]), gols(forca[b]), neutro=(mes % 2 == 0)))
    jogos.sort(key=lambda j: j["data"])
    return jogos


def test_backtest_de_ponta_a_ponta_em_banco_sintetico():
    jogos = _base_sintetica()
    nomes = {"FORTE": "Forte", "MEDIA": "Media", "FRACA": "Fraca"}
    conexao = sqlite3.connect(":memory:")
    conexao.row_factory = sqlite3.Row
    conexao.executescript(db.SCHEMA)
    ids = {n: db.obter_ou_criar_participante(conexao, n, "selecao", None) for n in nomes}
    numero = 0
    for j in jogos:
        if j["data"] < "2010-06-01":
            continue
        numero += 1
        casa, fora = j["casa"].upper(), j["fora"].upper()
        resultado = "1" if j["gols_casa"] > j["gols_fora"] else "X" if j["gols_casa"] == j["gols_fora"] else "2"
        conexao.execute("INSERT INTO concursos (numero) VALUES (?)", (numero,))
        conexao.execute(
            "INSERT INTO jogos (concurso_numero, num_jogo, casa_id, fora_id, gols_casa, gols_fora, resultado, data_jogo)"
            " VALUES (?, 1, ?, ?, ?, ?, ?, ?)", (numero, ids[casa], ids[fora], j["gols_casa"], j["gols_fora"], resultado, j["data"]),
        )
    r = s.backtest_selecoes(conexao, jogos_base=jogos, nomes=nomes)
    assert r["jogos_da_loteca"] == r["casados_com_a_base"] == numero and r["sem_par_na_base"] == 0
    assert r["resultado_diferente"] == 0 and r["avaliados"] > 300
    # Forças bem diferentes: o Elo precisa bater a frequência simples com folga.
    assert r["contra_frequencia"]["veredito"] == "melhor que a referência"
    assert r["metricas"]["elo"]["acuracia"] > r["metricas"]["frequencia"]["acuracia"]


def test_backtest_sem_jogos_de_selecoes_no_banco_devolve_zero_avaliados():
    conexao = sqlite3.connect(":memory:")
    conexao.row_factory = sqlite3.Row
    conexao.executescript(db.SCHEMA)
    r = s.backtest_selecoes(conexao, jogos_base=_base_sintetica(), nomes={"FORTE": "Forte"})
    assert r["avaliados"] == 0 and r["jogos_da_loteca"] == 0


# --- Modelo de produção e integração com o percentual -------------------------------------

def test_modelo_de_producao_preve_pelo_nome_da_loteca_e_devolve_none_para_nome_desconhecido():
    jogos = _base_sintetica()
    conexao = sqlite3.connect(":memory:")
    conexao.row_factory = sqlite3.Row
    conexao.executescript(db.SCHEMA)
    nomes = {"FORTE": "Forte", "FRACA": "Fraca"}
    modelo = s.construir_modelo(conexao, jogos_base=jogos, nomes=nomes)
    p = modelo.prever("forte", "FRACA")
    assert sum(p.values()) == pytest.approx(100.0) and p["1"] > p["2"]
    assert modelo.prever("FORTE", "TIME QUE NAO EXISTE") is None
    assert modelo.rating("FORTE") > modelo.rating("FRACA") and modelo.rating("XYZ") is None
    assert modelo.nao_neutro == 0.5  # sem jogos recentes da Loteca no banco, cai no valor neutro da incerteza


@pytest.fixture()
def banco_percentual(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DB_PATH", tmp_path / "sintetico.db")
    db.inicializar_schema()
    with db.sessao() as c:
        ids = {
            "ALEMANHA": db.obter_ou_criar_participante(c, "ALEMANHA", "selecao", None),
            "GIBRALTAR": db.obter_ou_criar_participante(c, "GIBRALTAR", "selecao", None),
            "CLUBE": db.obter_ou_criar_participante(c, "CLUBE ALFA", "clube", "SP"),
        }
    return ids


def test_percentual_entre_selecoes_usa_o_elo_e_o_favorito_e_a_alemanha(banco_percentual):
    from stats.percentual import origem_do_percentual, percentual_historico

    with db.sessao() as c:
        p = percentual_historico(c, banco_percentual["ALEMANHA"], banco_percentual["GIBRALTAR"])
        assert sum(p.values()) == pytest.approx(100.0) and p["1"] > 80  # Alemanha x Gibraltar, sem nenhum jogo na Loteca
        assert origem_do_percentual(c, banco_percentual["ALEMANHA"], banco_percentual["GIBRALTAR"])["metodo"] == "elo_selecoes"


def test_chave_historico_volta_ao_modelo_anterior(banco_percentual, monkeypatch):
    from stats.percentual import origem_do_percentual

    monkeypatch.setattr(config, "MODELO_SELECOES", "historico")
    with db.sessao() as c:
        # Sem jogos na Loteca, o modelo anterior cai na frequência global: prova que o Elo ficou desligado.
        assert origem_do_percentual(c, banco_percentual["ALEMANHA"], banco_percentual["GIBRALTAR"])["metodo"] == "frequencia_global"


def test_confronto_com_clube_nao_usa_o_elo(banco_percentual):
    from stats.percentual import origem_do_percentual

    with db.sessao() as c:
        assert origem_do_percentual(c, banco_percentual["CLUBE"], banco_percentual["ALEMANHA"])["metodo"] != "elo_selecoes"


def test_base_ausente_cai_no_modelo_anterior_sem_quebrar(banco_percentual, monkeypatch, tmp_path):
    from stats import selecoes
    from stats.percentual import origem_do_percentual

    monkeypatch.setattr(config, "SELECOES_BASE_CSV", tmp_path / "nao-existe.csv")
    selecoes._CACHE_MODELO.clear()
    with db.sessao() as c:
        assert origem_do_percentual(c, banco_percentual["ALEMANHA"], banco_percentual["GIBRALTAR"])["metodo"] == "frequencia_global"
