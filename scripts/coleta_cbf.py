#!/usr/bin/env python3
"""Coleta agendada das páginas públicas da CBF (Série A e B). Chamado pelo
Agendador de Tarefas do Windows (comando `schtasks` no README.md); roda
sozinho, sem a UI aberta. Pula competições cujo dado ainda é recente
(config.CBF_VALIDADE_HORAS), então pode ser agendado com folga.

Uso: python scripts/coleta_cbf.py [--forcar]
"""
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import db
from importer.cbf_client import coletar_todas
from importer.cbf_mapeamento import parear

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("coleta_cbf")


def main() -> int:
    forcar = "--forcar" in sys.argv
    db.inicializar_schema()
    with db.sessao() as conexao:
        for resultado in coletar_todas(conexao, forcar=forcar):
            logger.info("Resultado: %s", resultado)
        pareamento = parear(conexao)
        logger.info("Pareamento CBF x Loteca: %s times pareados", pareamento["pareados"])
        for aviso in pareamento["ambiguos"]:
            logger.warning("Sem par único: %s", aviso)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
