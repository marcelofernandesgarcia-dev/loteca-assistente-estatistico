#!/usr/bin/env python3
"""Importa o histórico de concursos da CAIXA (do 1 ao último apurado) para o
banco local. Retomável: pode ser interrompido e rodado de novo; concursos que
já têm placar são pulados. Faz uma cópia do banco antes de começar.

Uso: python scripts/importar_historico.py [--inicio N] [--fim N] [--refazer]
"""
import argparse
import logging
import shutil
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config
import db
from importer.caixa_client import importar_historico
from importer.unificar_participantes import unificar, unificar_uf_ausente

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("importar_historico")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inicio", type=int, default=None)
    parser.add_argument("--fim", type=int, default=None)
    parser.add_argument("--refazer", action="store_true", help="reimporta mesmo os concursos que já têm placar")
    args = parser.parse_args()

    db.inicializar_schema()
    if config.DB_PATH.exists():
        copia = config.DB_PATH.with_name(f"{config.DB_PATH.name}.bak-{datetime.now().strftime('%Y%m%d-%H%M%S')}")
        shutil.copy2(config.DB_PATH, copia)
        logger.info("Cópia de segurança: %s", copia.name)

    conexao = db.conectar()
    try:
        resumo = importar_historico(conexao, args.inicio, args.fim, args.refazer)
        unidos_normalizacao = unificar(conexao)
        unidos_uf_ausente = unificar_uf_ausente(conexao)
        removidos = db.limpar_participantes_orfaos(conexao)
        conexao.commit()
    finally:
        conexao.close()
    logger.info(
        "Concluído: %s importados, %s já existiam, %s falhas, %s participantes órfãos removidos, "
        "%s grupos unidos por normalização, %s grupos unidos por UF ausente.",
        resumo["importados"], resumo["ja_existiam"], len(resumo["falhas"]), removidos,
        len(unidos_normalizacao), len(unidos_uf_ausente),
    )
    for numero, motivo in sorted(resumo["falhas"].items()):
        logger.warning("Falha no concurso %s: %s", numero, motivo)
    return 0 if not resumo["falhas"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
