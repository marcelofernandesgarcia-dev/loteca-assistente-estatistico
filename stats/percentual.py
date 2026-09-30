"""Percentual histórico de vitória/empate por participante em um confronto.

Método: distribuição de Poisson sobre a expectativa de gols de cada lado
(força de ataque em casa/fora x força de defesa do adversário, normalizada
pela média geral de gols), técnica padrão de análise esportiva -- não
depende de odds de mercado, só do próprio histórico importado (ver
docs/metodologia-estatistica-material-usuario.md, seção 4, e
docs/pesquisa-complementar-27-09.md, seção 3.6, sobre por que este projeto
não usa odds na v1).

Quando faltam jogos suficientes de um participante, cai para a frequência
global (regressão à média) em vez de extrapolar de amostra pequena --
evita apresentar um percentual "confiante" sem base.
"""
import logging
import math

import config
from stats.frequencia import frequencia_global

JOGOS_MINIMOS_PARA_FORCA_PROPRIA = 5


def _poisson_pmf(k: int, lam: float) -> float:
    if lam <= 0:
        return 1.0 if k == 0 else 0.0
    return math.exp(-lam) * (lam**k) / math.factorial(k)


def _media_gols_geral(conexao) -> float:
    linha = conexao.execute(
        "SELECT AVG(gpj) AS media FROM ("
        "  SELECT gols_casa AS gpj FROM jogos WHERE gols_casa IS NOT NULL"
        "  UNION ALL"
        "  SELECT gols_fora AS gpj FROM jogos WHERE gols_fora IS NOT NULL"
        ")"
    ).fetchone()
    return linha["media"] or 1.2  # média plausível de gols por lado se o banco estiver vazio


def _forca_ataque_casa(conexao, participante_id: int) -> tuple[float, int]:
    linha = conexao.execute(
        "SELECT AVG(gols_casa) AS media, COUNT(*) AS n FROM jogos "
        "WHERE casa_id = ? AND gols_casa IS NOT NULL",
        (participante_id,),
    ).fetchone()
    return (linha["media"] or 0.0), linha["n"]


def _forca_defesa_casa(conexao, participante_id: int) -> tuple[float, int]:
    linha = conexao.execute(
        "SELECT AVG(gols_fora) AS media, COUNT(*) AS n FROM jogos "
        "WHERE casa_id = ? AND gols_fora IS NOT NULL",
        (participante_id,),
    ).fetchone()
    return (linha["media"] or 0.0), linha["n"]


def _forca_ataque_fora(conexao, participante_id: int) -> tuple[float, int]:
    linha = conexao.execute(
        "SELECT AVG(gols_fora) AS media, COUNT(*) AS n FROM jogos "
        "WHERE fora_id = ? AND gols_fora IS NOT NULL",
        (participante_id,),
    ).fetchone()
    return (linha["media"] or 0.0), linha["n"]


def _forca_defesa_fora(conexao, participante_id: int) -> tuple[float, int]:
    linha = conexao.execute(
        "SELECT AVG(gols_casa) AS media, COUNT(*) AS n FROM jogos "
        "WHERE fora_id = ? AND gols_casa IS NOT NULL",
        (participante_id,),
    ).fetchone()
    return (linha["media"] or 0.0), linha["n"]


logger = logging.getLogger(__name__)


def _prever_selecoes(conexao, casa_id: int, fora_id: int) -> dict | None:
    """Jogo entre duas seleções: força pela base aberta de resultados internacionais
    (stats/selecoes.py), que no teste jogo a jogo acertou bem mais que o histórico
    da Loteca (poucos jogos por seleção). None quando não se aplica (clube na jogada,
    chave desligada) ou quando a base não está disponível: cai no modelo anterior."""
    if config.MODELO_SELECOES != "elo":
        return None
    linhas = conexao.execute(
        "SELECT id, nome, tipo FROM participantes WHERE id IN (?, ?)", (casa_id, fora_id)
    ).fetchall()
    por_id = {linha["id"]: linha for linha in linhas}
    if casa_id not in por_id or fora_id not in por_id or any(l["tipo"] != "selecao" for l in por_id.values()):
        return None
    try:
        from stats.selecoes import modelo_em_cache

        return modelo_em_cache(conexao).prever(por_id[casa_id]["nome"], por_id[fora_id]["nome"])
    except (FileNotFoundError, ValueError) as erro:
        logger.warning("Base de seleções indisponível (%s); usando o modelo anterior.", erro)
        return None


def percentual_historico(conexao, casa_id: int, fora_id: int) -> dict:
    """Retorna {'1': %, 'X': %, '2': %} a partir do histórico próprio (ou, entre
    duas seleções, da força pela base aberta de resultados internacionais)."""
    selecoes = _prever_selecoes(conexao, casa_id, fora_id)
    if selecoes is not None:
        return selecoes
    media_geral = _media_gols_geral(conexao)

    ataque_casa, n1 = _forca_ataque_casa(conexao, casa_id)
    defesa_fora, n2 = _forca_defesa_fora(conexao, fora_id)
    ataque_fora, n3 = _forca_ataque_fora(conexao, fora_id)
    defesa_casa, n4 = _forca_defesa_casa(conexao, casa_id)

    amostra_suficiente = min(n1, n2, n3, n4) >= JOGOS_MINIMOS_PARA_FORCA_PROPRIA

    if amostra_suficiente and media_geral > 0:
        lambda_casa = (ataque_casa * defesa_fora) / media_geral
        lambda_fora = (ataque_fora * defesa_casa) / media_geral
    else:
        # Amostra pequena: regressão à média (frequência global), sem
        # extrapolar força de ataque/defesa de poucos jogos.
        freq = frequencia_global(conexao)
        return {"1": freq["1"] * 100, "X": freq["X"] * 100, "2": freq["2"] * 100}

    max_gols = 8
    p_casa_vence = p_empate = p_fora_vence = 0.0
    for gc in range(max_gols + 1):
        for gf in range(max_gols + 1):
            p = _poisson_pmf(gc, lambda_casa) * _poisson_pmf(gf, lambda_fora)
            if gc > gf:
                p_casa_vence += p
            elif gc == gf:
                p_empate += p
            else:
                p_fora_vence += p

    total = p_casa_vence + p_empate + p_fora_vence
    if total == 0:
        freq = frequencia_global(conexao)
        return {"1": freq["1"] * 100, "X": freq["X"] * 100, "2": freq["2"] * 100}
    return {
        "1": (p_casa_vence / total) * 100,
        "X": (p_empate / total) * 100,
        "2": (p_fora_vence / total) * 100,
    }


def origem_do_percentual(conexao, casa_id: int, fora_id: int) -> dict:
    """Diz se `percentual_historico` usou a força própria dos times (Poisson), a
    força por Elo da base aberta (duas seleções) ou caiu na frequência global por
    amostra pequena, e quantos jogos há na base da Loteca no cenário mais escasso."""
    if _prever_selecoes(conexao, casa_id, fora_id) is not None:
        return {"metodo": "elo_selecoes", "menor_amostra": None, "minimo_necessario": None}
    menor_amostra = min(
        _forca_ataque_casa(conexao, casa_id)[1],
        _forca_defesa_fora(conexao, fora_id)[1],
        _forca_ataque_fora(conexao, fora_id)[1],
        _forca_defesa_casa(conexao, casa_id)[1],
    )
    return {
        "metodo": "poisson" if menor_amostra >= JOGOS_MINIMOS_PARA_FORCA_PROPRIA else "frequencia_global",
        "menor_amostra": menor_amostra,
        "minimo_necessario": JOGOS_MINIMOS_PARA_FORCA_PROPRIA,
    }
