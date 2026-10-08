"""Variações do Elo de clubes (sugestões S3 e S4, aprovadas em 07/10/2026). Só mede.

Base de comparação: o Elo de clubes em uso (stats/elo_clubes.py: K 20, mando 65, só jogos da Loteca). Variações
fixadas ANTES do resultado, todas andando no tempo e com a mesma curva (logística ordenada refeita por ano):
- V1, margem de gols: o ajuste do rating é multiplicado pela margem, como no Elo das seleções
  (stats.selecoes._multiplicador_de_gols);
- V2, K ajustado: o K é escolhido em {10, 15, 20, 30, 40} pela perda nos jogos de 2015 a 2019 (curva com os anos
  anteriores), e só depois testado de 2020 em diante;
- V3, pi-ratings (Constantinou e Fenton, 2013): rating de casa e de fora por time, atualizados pelo erro na
  diferença de gols, com as taxas do artigo (lambda 0,035, gama 0,7); a diferença esperada de gols entra na curva;
- V4, mais jogos (S4): o Elo também recebe os jogos da CBF (Séries A, B e C, 2019 em diante) dos clubes pareados,
  sem repetir jogo que já está na Loteca (mesmo par em até 1 dia) e sem jogo da CBF do dia do concurso em diante.
Critério do usuário: a variação só substitui o Elo em uso se a perda logarítmica fora da amostra for menor com
q < config.ASSOCIACAO_NIVEL_SIGNIFICANCIA (Benjamini-Hochberg entre as quatro).
"""
import datetime as dt
import math
from collections import defaultdict

import numpy as np

import config
from stats import backtest, backtest_competicao as b2
from stats.associacao import ajustar_benjamini_hochberg
from stats.elo_clubes import _Y, _ano, _por_concurso, clubes_do_banco
from stats.selecoes import _multiplicador_de_gols, ajustar_curva, probabilidades

K_CANDIDATOS = (10.0, 15.0, 20.0, 30.0, 40.0)
PI_LAMBDA, PI_GAMA, PI_B, PI_C = 0.035, 0.7, 10.0, 3.0  # Constantinou e Fenton (2013)


def _curva(amostra: list, ano: int, cache: dict):
    if ano not in cache:
        treino = [(d, y) for a, d, y in amostra if a is not None and a < ano]
        try:
            cache[ano] = ajustar_curva(np.array([t[0] for t in treino]), np.ones(len(treino)), np.array([t[1] for t in treino]))
        except ValueError:
            cache[ano] = None
    return cache[ano]


class _Elo:
    def __init__(self, k: float, margem: bool):
        self.k, self.margem = k, margem
        self.r = defaultdict(lambda: config.ELO_CLUBES_RATING_INICIAL)

    def diferenca(self, casa, fora) -> float:
        return (self.r[casa] - self.r[fora]) / 100.0

    def aplicar(self, casa, fora, gc, gf) -> None:
        esperado = 1.0 / (1.0 + 10 ** (-(self.r[casa] + config.ELO_CLUBES_VANTAGEM_MANDANTE - self.r[fora]) / 400.0))
        real = 1.0 if gc > gf else 0.5 if gc == gf else 0.0
        delta = self.k * (_multiplicador_de_gols(gc - gf) if self.margem else 1.0) * (real - esperado)
        self.r[casa] += delta
        self.r[fora] -= delta


class _Pi:
    """Pi-ratings: rating de casa (c) e de fora (f) por time; diferença esperada de gols."""

    def __init__(self):
        self.c = defaultdict(float)
        self.f = defaultdict(float)

    @staticmethod
    def _gols(rating: float) -> float:
        return math.copysign(PI_B ** (abs(rating) / PI_C) - 1, rating)

    def diferenca(self, casa, fora) -> float:
        return self._gols(self.c[casa]) - self._gols(self.f[fora])

    def aplicar(self, casa, fora, gc, gf) -> None:
        erro = (gc - gf) - self.diferenca(casa, fora)
        psi = PI_C * math.log10(1 + abs(erro)) * (1 if erro > 0 else -1 if erro < 0 else 0)
        antigo_cc, antigo_ff = self.c[casa], self.f[fora]
        self.c[casa] = antigo_cc + psi * PI_LAMBDA
        self.f[casa] += (self.c[casa] - antigo_cc) * PI_GAMA
        self.f[fora] = antigo_ff - psi * PI_LAMBDA
        self.c[fora] += (self.f[fora] - antigo_ff) * PI_GAMA


def _jogos_cbf(conexao, jogos_loteca: list[dict]) -> list[dict]:
    """Jogos da CBF com placar, já traduzidos para participantes da Loteca (o participante com mais jogos no
    caso de vários nomes para o mesmo código), sem os que já estão na Loteca."""
    from stats.cbf import codigos_equivalentes

    atual_de = {ant: atual for atual, antes in codigos_equivalentes().items() for ant in antes}
    contagem = defaultdict(int)
    for j in jogos_loteca:
        contagem[j["casa_id"]] += 1
        contagem[j["fora_id"]] += 1
    por_codigo: dict[int, int] = {}
    for participante, cod in conexao.execute("SELECT participante_id, cod_time FROM mapa_cbf_participante"):
        if cod not in por_codigo or contagem[participante] > contagem[por_codigo[cod]]:
            por_codigo[cod] = participante
    na_loteca = {(j["casa_id"], j["fora_id"], j["data_jogo"]) for j in jogos_loteca if j["data_jogo"]}
    saida = []
    for p in conexao.execute(
        "SELECT data_jogo, mandante_id, visitante_id, gols_mandante, gols_visitante FROM cbf_partidas "
        "WHERE gols_mandante IS NOT NULL AND gols_visitante IS NOT NULL AND data_jogo IS NOT NULL ORDER BY data_jogo"
    ):
        casa = por_codigo.get(atual_de.get(p["mandante_id"], p["mandante_id"]))
        fora = por_codigo.get(atual_de.get(p["visitante_id"], p["visitante_id"]))
        if casa is None or fora is None:
            continue
        data = dt.date.fromisoformat(p["data_jogo"])
        if any((casa, fora, (data + dt.timedelta(days=d)).isoformat()) in na_loteca for d in (-1, 0, 1)):
            continue
        saida.append({"data": p["data_jogo"], "casa": casa, "fora": fora, "gc": p["gols_mandante"], "gf": p["gols_visitante"]})
    return saida


def prever(jogos: list[dict], clubes: set[int], modelo, extras: list[dict] | None = None, desde_ano: int = 2020,
           ate_ano: int | None = None) -> dict[int, dict]:
    """Previsões andando no tempo com qualquer modelo que tenha diferenca() e aplicar(). `extras` (jogos da CBF)
    entram no rating antes do concurso cujo primeiro jogo é depois deles."""
    extras = extras or []
    proximo, amostra, curvas, previsoes = 0, [], {}, {}
    for numero, lote in _por_concurso(jogos):
        datas = [j["data_jogo"] for j in lote if j["data_jogo"]]
        corte = min(datas) if datas else None
        while corte and proximo < len(extras) and extras[proximo]["data"] < corte:
            e = extras[proximo]
            modelo.aplicar(e["casa"], e["fora"], e["gc"], e["gf"])
            proximo += 1
        for jogo in lote:
            ano = _ano(jogo["data_jogo"])
            d = modelo.diferenca(jogo["casa_id"], jogo["fora_id"])
            dentro = ano is not None and ano >= desde_ano and (ate_ano is None or ano <= ate_ano)
            if dentro and jogo["casa_id"] in clubes and jogo["fora_id"] in clubes:
                curva = _curva(amostra, ano, curvas)
                if curva is not None:
                    previsoes[jogo["id"]] = {"p": probabilidades(curva, d, 1.0), "concurso": numero}
            amostra.append((ano, d, _Y[jogo["resultado"]]))
        for jogo in lote:
            modelo.aplicar(jogo["casa_id"], jogo["fora_id"], jogo["gols_casa"], jogo["gols_fora"])
    return previsoes


def _perda(previsoes: dict, jogos_por_id: dict, ids: list[int]) -> np.ndarray:
    return np.array([-math.log(max(previsoes[i]["p"][jogos_por_id[i]["resultado"]] / 100.0, 1e-9)) for i in ids])


def escolher_k(jogos: list[dict], clubes: set[int]) -> tuple[float, dict]:
    """K de menor perda nos jogos de 2015 a 2019 (nada de 2020 em diante entra na escolha)."""
    por_id = {j["id"]: j for j in jogos}
    perdas = {}
    for k in K_CANDIDATOS:
        prev = prever(jogos, clubes, _Elo(k, False), desde_ano=2015, ate_ano=2019)
        perdas[k] = float(_perda(prev, por_id, list(prev)).mean())
    return min(perdas, key=perdas.get), perdas


def estudar(conexao) -> dict:
    jogos = backtest.carregar_jogos(conexao)
    clubes = clubes_do_banco(conexao)
    por_id = {j["id"]: j for j in jogos}
    base = prever(jogos, clubes, _Elo(config.ELO_CLUBES_K, False))
    k_escolhido, perdas_k = escolher_k(jogos, clubes)
    variacoes = {
        "V1 margem de gols": prever(jogos, clubes, _Elo(config.ELO_CLUBES_K, True)),
        f"V2 K ajustado ({k_escolhido:.0f})": prever(jogos, clubes, _Elo(k_escolhido, False)),
        "V3 pi-ratings": prever(jogos, clubes, _Pi()),
        "V4 com os jogos da CBF": prever(jogos, clubes, _Elo(config.ELO_CLUBES_K, False), _jogos_cbf(conexao, jogos)),
    }
    ids = sorted(set(base).intersection(*[set(v) for v in variacoes.values()]))
    clusters = np.array([str(por_id[i]["concurso_numero"]) for i in ids])
    perda_base = _perda(base, por_id, ids)
    resultados = []
    for indice, (nome, prev) in enumerate(variacoes.items()):
        perda = _perda(prev, por_id, ids)
        r = b2._bootstrap_por_cluster(perda_base - perda, clusters, config.B2_REPETICOES_BOOTSTRAP, config.B2_SEMENTE + 800 + indice)
        acerto = float(100 * np.mean([max(prev[i]["p"], key=prev[i]["p"].get) == por_id[i]["resultado"] for i in ids]))
        resultados.append({"variacao": nome, "perda_log": float(perda.mean()), "acerto": acerto, **r})
    for r, q in zip(resultados, ajustar_benjamini_hochberg([r["p"] for r in resultados])):
        r["q"] = q
        r["conclusao"] = ("melhor" if q < config.ASSOCIACAO_NIVEL_SIGNIFICANCIA
                          else "pior" if r["ic_superior"] < 0 else "sem diferença perceptível")
    acerto_base = float(100 * np.mean([max(base[i]["p"], key=base[i]["p"].get) == por_id[i]["resultado"] for i in ids]))
    return {"n": len(ids), "base": {"perda_log": float(perda_base.mean()), "acerto": acerto_base},
            "k_escolhido": k_escolhido, "perdas_k_2015_2019": perdas_k, "variacoes": resultados}
