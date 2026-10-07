"""Modelo da temporada da CBF em produção (item B2 do plano v2, aprovado em 07/10/2026).

É o "retrospecto" do estudo B2 (stats/backtest_loteca.py): logística multinomial sobre os pontos por jogo
de cada time na temporada da CBF até o dia do jogo, treinada só nos jogos da CBF de anos anteriores. No
estudo refeito em 07/10/2026 com o pareamento corrigido (1.676 jogos da Loteca, Séries A e B), a perda
logarítmica foi 1,0323, contra 1,0593 do modelo anterior do app e 1,0552 da frequência simples (q = 0,001).
A correção de calibração NÃO se aplica: aplicada ano a ano, piorou a perda (1,0264 para 1,0287).

Vale só quando os dois times estão na MESMA série de pontos corridos no ano e têm pelo menos
config.B2_JOGOS_ANTERIORES_MINIMOS jogos antes do dia -- o mesmo filtro do estudo. Nos demais jogos o app
segue com o modelo anterior. As funções reaproveitam as do estudo (TemporadaPorData, ajustar_logistica,
probabilidades_logistica): a paridade com o estudo é testada em tests/test_modelo_cbf.py.
Interruptor: LOTECA_MODELO_CLUBES=historico volta ao modelo anterior em todos os jogos.
"""
import logging

import numpy as np

import config
from stats import backtest_competicao as b2
from stats import competicao
from stats.backtest_loteca import TemporadaPorData

logger = logging.getLogger(__name__)

ORIGEM = "retrospecto_cbf"
_cache_pesos: dict[tuple, np.ndarray | None] = {}
_cache_temporadas: dict[tuple, TemporadaPorData] = {}


def _versao_dos_dados(conexao) -> tuple:
    linha = conexao.execute("SELECT COUNT(*), MAX(coletado_em) FROM cbf_partidas").fetchone()
    return tuple(linha)


def pesos_para_o_ano(conexao, ano: int) -> np.ndarray | None:
    """Pesos da logística treinada nos jogos da CBF (pontos corridos) de anos ANTERIORES a `ano`, com a
    mesma amostra do estudo (b2.amostra_da_temporada). None se não houver ano anterior."""
    chave = (ano, _versao_dos_dados(conexao))
    if chave in _cache_pesos:
        return _cache_pesos[chave]
    temporadas = conexao.execute(
        f"SELECT DISTINCT serie, ano FROM cbf_partidas WHERE ano < ? AND {competicao.so_pontos_corridos()} ORDER BY ano, serie",
        (ano,),
    ).fetchall()
    amostra = []
    for t in temporadas:
        amostra += b2.amostra_da_temporada(competicao.carregar_partidas(conexao, t["serie"], t["ano"]), t["serie"], t["ano"],
                                           com_poisson=False)
    pesos = None
    if amostra:
        indice = {"1": 0, "X": 1, "2": 2}
        X = np.column_stack([np.ones(len(amostra)), [o["retro_casa"] for o in amostra], [o["retro_fora"] for o in amostra]])
        pesos = b2.ajustar_logistica(X, np.array([indice[o["resultado"]] for o in amostra]))
    _cache_pesos[chave] = pesos
    return pesos


def _temporada(conexao, serie: str, ano: int) -> TemporadaPorData:
    chave = (serie, ano, _versao_dos_dados(conexao))
    if chave not in _cache_temporadas:
        _cache_temporadas[chave] = TemporadaPorData(competicao.carregar_partidas(conexao, serie, ano))
    return _cache_temporadas[chave]


def _serie_no_ano(conexao, cod_time: int, ano: int) -> str | None:
    linha = conexao.execute(
        f"SELECT serie FROM cbf_partidas WHERE ano = ? AND (mandante_id = ? OR visitante_id = ?) "
        f"AND {competicao.so_pontos_corridos()} ORDER BY serie LIMIT 1",
        (ano, cod_time, cod_time),
    ).fetchone()
    return linha["serie"] if linha else None


def prever(conexao, casa_id: int, fora_id: int, data_jogo: str | None) -> dict | None:
    """{'1','X','2'} em % pelo modelo da temporada, ou None quando o jogo está fora do alcance do modelo
    (sem data, time sem par na CBF, séries diferentes, poucos jogos antes do dia, sem ano de treino)."""
    if config.MODELO_CLUBES != ORIGEM or not data_jogo or len(data_jogo) < 10:
        return None
    pares = dict(conexao.execute(
        "SELECT participante_id, cod_time FROM mapa_cbf_participante WHERE participante_id IN (?, ?)", (casa_id, fora_id)
    ).fetchall())
    cod_casa, cod_fora = pares.get(casa_id), pares.get(fora_id)
    if cod_casa is None or cod_fora is None or cod_casa == cod_fora:
        return None
    ano, data = int(data_jogo[:4]), data_jogo[:10]
    serie = _serie_no_ano(conexao, cod_casa, ano)
    if serie is None or serie != _serie_no_ano(conexao, cod_fora, ano):
        return None
    temporada = _temporada(conexao, serie, ano)
    (pontos_casa, jogos_casa), (pontos_fora, jogos_fora) = temporada.retrospecto(cod_casa, data), temporada.retrospecto(cod_fora, data)
    minimo = config.B2_JOGOS_ANTERIORES_MINIMOS
    if jogos_casa < minimo or jogos_fora < minimo:
        return None
    pesos = pesos_para_o_ano(conexao, ano)
    if pesos is None:
        return None
    X = np.array([[1.0, pontos_casa / jogos_casa, pontos_fora / jogos_fora]])
    return b2._como_percentuais(b2.probabilidades_logistica(X, pesos)[0])
