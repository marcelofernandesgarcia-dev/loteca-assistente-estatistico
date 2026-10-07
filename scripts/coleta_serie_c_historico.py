#!/usr/bin/env python3
"""Coleta ÚNICA das Séries C passadas da CBF (2019 a 2025), autorizada pelo usuário em 07/10/2026 (plano v2,
item B3): serve para repetir o teste B2 com a Série C antes de usar o modelo da temporada nela, e para testar
se a fase decisiva empata mais (item C2).

Mesma fonte e método da Série C de 2026 (importer/cbf_client.coletar_competicao): página da tabela (numa
temporada encerrada, só os jogos da final), página de cada time e dos adversários encontrados, 2 s entre
páginas. A fase de cada jogo vem da sequência das rodadas; se a sequência não fechar com as fases da CBF,
a temporada fica sem fase e o log avisa. Retomável: pula a temporada que já tem fase em todos os jogos
(use --forcar para refazer). Faz cópia do banco antes. Os dados ficam só no banco local.

Uso: python scripts/coleta_serie_c_historico.py [--forcar] [anos...]   (padrão: 2019 a 2025)
"""
import datetime as dt
import logging
import shutil
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config
import db
from importer.cbf_client import ErroColetaCBF, coletar_competicao

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("coleta_serie_c_historico")
ANOS_PADRAO = list(range(2019, 2026))


def _completa(conexao, ano: int) -> bool:
    linha = conexao.execute(
        "SELECT COUNT(*) AS n, SUM(fase IS NULL) AS sem_fase FROM cbf_partidas WHERE serie = 'serie-c' AND ano = ?", (ano,)
    ).fetchone()
    return bool(linha["n"]) and not linha["sem_fase"]


def main() -> int:
    forcar = "--forcar" in sys.argv
    anos = [int(a) for a in sys.argv[1:] if a.isdigit()] or ANOS_PADRAO
    if not config.CBF_HABILITADO:
        logger.info("Coleta da CBF desligada (LOTECA_CBF_HABILITADO=0).")
        return 0
    db.inicializar_schema()
    copia = config.DB_PATH.with_name(f"{config.DB_PATH.name}.bak-{dt.datetime.now():%Y%m%d-%H%M%S}-antes-serie-c-historico")
    shutil.copy2(config.DB_PATH, copia)
    logger.info("Cópia do banco: %s", copia)
    falhas = 0
    with db.sessao() as conexao:
        for ano in anos:
            if not forcar and _completa(conexao, ano):
                logger.info("Série C %s já completa; pulando.", ano)
                continue
            try:
                resultado = coletar_competicao(conexao, "campeonato-brasileiro", "serie-c", ano, forcar=True)
            except ErroColetaCBF as erro:
                logger.error("Série C %s não coletada: %s", ano, erro)
                falhas += 1
                continue
            conexao.commit()
            jogos = conexao.execute(
                "SELECT COUNT(*), SUM(gols_mandante IS NOT NULL), COUNT(DISTINCT fase) FROM cbf_partidas"
                " WHERE serie = 'serie-c' AND ano = ?", (ano,),
            ).fetchone()
            logger.info("Série C %s: %s times, %s jogos (%s com placar), %s fase(s), sequência confere: %s",
                        ano, resultado["times"], jogos[0], jogos[1], jogos[2], resultado["fases_conferem"])
            time.sleep(config.CBF_INTERVALO_SEGUNDOS)
    return 1 if falhas else 0


if __name__ == "__main__":
    raise SystemExit(main())
