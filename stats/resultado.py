"""Regras de negócio puras sobre resultado e classificação de participante.

Sem dependência de framework, sem I/O -- só matemática e as regras oficiais
da Loteca (ver docs/manual-produtos-caixa-v21.md, item 10, e
docs/grade-real-e-prazos-confirmados.md).
"""
import unicodedata

import config


def calcular_resultado(gols_casa: int, gols_fora: int) -> str:
    """Coluna vencedora (1/X/2) a partir do placar. A API da CAIXA nunca
    devolve isso pronto (campo `resultado` sempre `null`) -- é sempre
    calculado por nós a partir do placar oficial já apurado.
    """
    if gols_casa is None or gols_fora is None:
        raise ValueError("Placar incompleto -- não é possível calcular o resultado")
    if gols_casa > gols_fora:
        return "1"
    if gols_casa < gols_fora:
        return "2"
    return "X"


def _normalizar(nome: str) -> str:
    sem_acento = unicodedata.normalize("NFKD", nome).encode("ascii", "ignore").decode("ascii")
    return sem_acento.strip().upper()


def classificar_participante(nome: str, sigla_uf: str | None) -> str:
    """'clube' ou 'selecao'. Time brasileiro sempre tem UF preenchida (é
    sempre clube). Sem UF, checamos se o nome está na lista de seleções
    nacionais conhecidas (config.NOMES_SELECOES_NACIONAIS); senão, é clube
    estrangeiro (ex.: Barcelona, Real Madrid -- mesma ausência de UF que uma
    seleção, mas não são seleção).
    """
    if sigla_uf:
        return "clube"
    if _normalizar(nome) in config.NOMES_SELECOES_NACIONAIS:
        return "selecao"
    return "clube"
