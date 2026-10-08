"""Elo de clubes com os jogos da própria Loteca (sugestão S2 do diagnóstico de confiabilidade, aprovada em
07/10/2026).

Cada participante tem um rating que sobe ou desce a cada jogo apurado da Loteca (todos os jogos entram no
rating; só os jogos entre dois clubes usam a previsão). A diferença de rating vira 1/X/2 pela mesma curva do
Elo das seleções (logística ordenada, stats.selecoes.ajustar_curva), ajustada só com jogos de anos ANTERIORES
ao do jogo previsto. Base: Hvattum e Arntzen (2010), International Journal of Forecasting 26, 460-470.

Parâmetros em config.ELO_CLUBES_*, de convenção e fixados antes do teste. O teste exploratório de 07/10/2026
(3.549 jogos "demais" de 2020 a 2026) deu perda logarítmica 1,0311 contra 1,0597 do modelo anterior; o estudo
formal está em scripts/estudo_elo_clubes.py e só depois dele o modelo vale na tela.
"""
import logging
from collections import defaultdict

import numpy as np

import config
from stats import backtest
from stats.selecoes import ajustar_curva, probabilidades

logger = logging.getLogger(__name__)

ORIGEM = "elo_clubes"
_Y = {"1": 2, "X": 1, "2": 0}  # codificação da curva: 0 = fora, 1 = empate, 2 = casa


def _ano(data: str | None) -> int | None:
    return int(data[:4]) if data and data[:4].isdigit() else None


class Ratings:
    """Ratings e quantos jogos cada participante já tem no rating."""

    def __init__(self):
        self.valor: dict[int, float] = defaultdict(lambda: config.ELO_CLUBES_RATING_INICIAL)
        self.jogos: dict[int, int] = defaultdict(int)

    def diferenca(self, casa: int, fora: int) -> float:
        """Em centenas de pontos, sem a vantagem de mando (a curva tem um termo próprio para o mando)."""
        return (self.valor[casa] - self.valor[fora]) / 100.0

    def aplicar(self, jogo: dict) -> None:
        casa, fora = jogo["casa_id"], jogo["fora_id"]
        esperado = 1.0 / (1.0 + 10 ** (-(self.valor[casa] + config.ELO_CLUBES_VANTAGEM_MANDANTE - self.valor[fora]) / 400.0))
        real = {"1": 1.0, "X": 0.5, "2": 0.0}[jogo["resultado"]]
        delta = config.ELO_CLUBES_K * (real - esperado)
        self.valor[casa] += delta
        self.valor[fora] -= delta
        self.jogos[casa] += 1
        self.jogos[fora] += 1


def _por_concurso(jogos: list[dict]) -> list[tuple[int, list[dict]]]:
    lotes: list[tuple[int, list[dict]]] = []
    for jogo in jogos:
        if not lotes or lotes[-1][0] != jogo["concurso_numero"]:
            lotes.append((jogo["concurso_numero"], []))
        lotes[-1][1].append(jogo)
    return lotes


def _curva_do_ano(amostra: list[tuple[int | None, float, int]], ano: int, cache: dict) -> tuple | None:
    """Curva ajustada com os jogos de anos anteriores a `ano`; None com menos de 100 jogos."""
    if ano not in cache:
        treino = [(d, y) for a, d, y in amostra if a is not None and a < ano]
        try:
            cache[ano] = ajustar_curva(np.array([t[0] for t in treino]), np.ones(len(treino)), np.array([t[1] for t in treino]))
        except ValueError:
            cache[ano] = None
    return cache[ano]


def prever_walk_forward(jogos: list[dict], clubes: set[int], desde_ano: int | None = None) -> dict[int, dict]:
    """{id_do_jogo: {'p': {'1','X','2'} em %, 'concurso', 'jogos_casa', 'jogos_fora'}} para os jogos entre dois
    clubes de `desde_ano` em diante, cada concurso previsto só com os concursos anteriores. `jogos`: de
    stats.backtest.carregar_jogos (apurados, em ordem de concurso)."""
    desde_ano = config.ELO_CLUBES_TESTE_DESDE if desde_ano is None else desde_ano
    ratings, amostra, curvas, previsoes = Ratings(), [], {}, {}
    for numero, lote in _por_concurso(jogos):
        for jogo in lote:
            ano = _ano(jogo["data_jogo"])
            d = ratings.diferenca(jogo["casa_id"], jogo["fora_id"])
            if ano is not None and ano >= desde_ano and jogo["casa_id"] in clubes and jogo["fora_id"] in clubes:
                curva = _curva_do_ano(amostra, ano, curvas)
                if curva is not None:
                    previsoes[jogo["id"]] = {
                        "p": probabilidades(curva, d, 1.0), "concurso": numero,
                        "jogos_casa": ratings.jogos[jogo["casa_id"]], "jogos_fora": ratings.jogos[jogo["fora_id"]],
                    }
            amostra.append((ano, d, _Y[jogo["resultado"]]))
        for jogo in lote:
            ratings.aplicar(jogo)
    return previsoes


def clubes_do_banco(conexao) -> set[int]:
    return {linha[0] for linha in conexao.execute("SELECT id FROM participantes WHERE tipo = 'clube'")}


# ------------------------------------------------------------------ produção

_cache: dict[tuple, tuple] = {}


def _estado(conexao) -> tuple[Ratings, list, set[int], dict]:
    """(ratings depois de todos os jogos apurados, amostra para a curva, clubes, curvas já ajustadas por ano).
    Refeito quando entra jogo apurado novo."""
    chave = tuple(conexao.execute(
        "SELECT COUNT(*), MAX(concurso_numero) FROM jogos WHERE resultado IS NOT NULL").fetchone())
    if chave not in _cache:
        _cache.clear()
        ratings, amostra = Ratings(), []
        for _, lote in _por_concurso(backtest.carregar_jogos(conexao)):
            for jogo in lote:
                amostra.append((_ano(jogo["data_jogo"]), ratings.diferenca(jogo["casa_id"], jogo["fora_id"]), _Y[jogo["resultado"]]))
            for jogo in lote:
                ratings.aplicar(jogo)
        _cache[chave] = (ratings, amostra, clubes_do_banco(conexao), {})
    return _cache[chave]


def prever(conexao, casa_id: int, fora_id: int, data_jogo: str | None) -> dict | None:
    """{'1','X','2'} em % pelo Elo de clubes, ou None (interruptor desligado, não são dois clubes, sem data,
    ou sem anos anteriores para a curva). Mesma conta do estudo: rating com todos os jogos apurados e curva
    com os anos anteriores ao do jogo."""
    if not config.ELO_CLUBES_ATIVO or not data_jogo:
        return None
    ratings, amostra, clubes, curvas = _estado(conexao)
    if casa_id not in clubes or fora_id not in clubes:
        return None
    curva = _curva_do_ano(amostra, _ano(data_jogo), curvas)
    if curva is None:
        return None
    return probabilidades(curva, ratings.diferenca(casa_id, fora_id), 1.0)


def jogos_no_rating(conexao, participante_id: int) -> int:
    """Quantos jogos apurados da Loteca o participante tem no rating (para a cobertura)."""
    ratings, _, _, _ = _estado(conexao)
    return ratings.jogos[participante_id]
