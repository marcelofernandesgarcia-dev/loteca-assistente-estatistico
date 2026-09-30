#!/usr/bin/env python3
"""Coleta ÚNICA das temporadas passadas (2019 a 2025) das Séries A e B da CBF, para
ter amostra de verdade (5.320 jogos contra os 573 de uma temporada só). Mesma fonte
e mesmo método da coleta de 2026 (páginas públicas, 2 s entre páginas). Autorizado
pelo usuário em 30/09/2026 (docs/priorizacao-estatistica-30-09-2026.md, item P2).

Retomável: temporada que já está completa e confere com a classificação final da CBF
é pulada. Confirma cada temporada no banco antes de passar para a próxima. Não
mexe no nome atual dos times (ver gravar_classificacao) nem no pareamento com a Loteca.
Leva cerca de 10 minutos.

Uso: python scripts/coleta_cbf_historico.py [--forcar]
"""
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config
import db
from importer.cbf_client import (
    ErroColetaCBF,
    coletar_competicao,
    divergencias_de_resultado,
    preencher_nome_do_ano_mais_recente,
    temporada_completa,
)
from stats.competicao import validar_temporada

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("coleta_cbf_historico")


def main() -> int:
    forcar = "--forcar" in sys.argv
    if not config.CBF_HABILITADO:
        logger.info("Coleta da CBF desligada (LOTECA_CBF_HABILITADO=0).")
        return 0
    db.inicializar_schema()
    with db.sessao() as conexao:
        preenchidas = preencher_nome_do_ano_mais_recente(conexao)
        logger.info("Nome da temporada mais recente preenchido em %s linhas.", preenchidas)

    falhas = 0
    for campeonato, serie, ano in sorted(config.CBF_TEMPORADAS_PASSADAS, key=lambda t: (t[2], t[1])):
        with db.sessao() as conexao:
            if not forcar and temporada_completa(conexao, serie, ano):
                logger.info("%s %s: já completa e conferida, pulando.", serie, ano)
                continue
            try:
                resultado = coletar_competicao(conexao, campeonato, serie, ano, forcar=True)
            except ErroColetaCBF as erro:
                logger.error("%s %s não coletada: %s", serie, ano, erro)
                falhas += 1
                continue
        with db.sessao() as conexao:
            validacao = validar_temporada(conexao, serie, ano)
            graves = divergencias_de_resultado(validacao)
            so_gols = len(validacao["divergencias_numeros"]) - len(graves)
            logger.info(
                "%s %s: %s times coletados; jogos e pontos %s a classificação da CBF%s.",
                serie, ano, resultado["times"], "conferem com" if not graves else "DIVERGEM de",
                f" ({so_gols} diferença(s) só de gols, inconsistência da própria CBF)" if so_gols else "",
            )
            anomalia = config.CBF_ANOMALIAS_CONHECIDAS.get((serie, ano))
            if graves and anomalia:
                logger.warning("%s %s: anomalia conhecida da CBF: %s", serie, ano, anomalia["descricao"])
            elif graves:
                logger.error("%s %s: divergências de resultado: %s", serie, ano, graves)
                falhas += 1
    logger.info("Fim: %s temporada(s) com problema.", falhas)
    return 1 if falhas else 0


if __name__ == "__main__":
    raise SystemExit(main())
