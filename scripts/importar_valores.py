#!/usr/bin/env python3
"""Preenche a arrecadação, os acumulados e a premiação dos concursos já importados
(pedido do usuário, 30/09/2026: valores de cada concurso). Retomável e sem tocar em
jogos nem participantes. Faz backup do banco antes. Cerca de 15 a 20 minutos para
1.272 concursos (um pedido por concurso, com espaçamento).

Uso: python scripts/importar_valores.py [--inicio N] [--fim N]
"""
import argparse
import datetime as dt
import logging
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config
import db
from importer.caixa_client import completar_valores_do_historico, normalizar_valores_ja_gravados

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--inicio", type=int)
    parser.add_argument("--fim", type=int)
    argumentos = parser.parse_args()

    db.inicializar_schema()
    copia = config.DB_PATH.with_name(
        f"{config.DB_PATH.name}.bak-{dt.datetime.now().strftime('%Y%m%d-%H%M%S')}-antes-valores-dos-concursos"
    )
    shutil.copy2(config.DB_PATH, copia)
    logging.info("Backup do banco em %s", copia.name)

    conexao = db.conectar()
    try:
        logging.info("Ajuste do que já foi gravado: %s", normalizar_valores_ja_gravados(conexao))
        resumo = completar_valores_do_historico(conexao, argumentos.inicio, argumentos.fim)
    finally:
        conexao.close()
    logging.info(
        "Concluído: %s atualizados, %s já tinham, %s sem valor na API, %s falhas",
        resumo["atualizados"], resumo["ja_tinham"], len(resumo["sem_valor_na_api"]), len(resumo["falhas"]),
    )
    if resumo["sem_valor_na_api"]:
        logging.info("Sem arrecadação na API: %s", resumo["sem_valor_na_api"][:30])
    for numero, motivo in list(resumo["falhas"].items())[:20]:
        logging.warning("Falha no concurso %s: %s", numero, motivo)
    return 1 if resumo["falhas"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
