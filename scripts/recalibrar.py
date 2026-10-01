#!/usr/bin/env python3
"""Refaz a calibração dos percentuais (E4) com todos os concursos apurados e regrava os percentuais já
calculados pelas varreduras de notícias. É o que `atualizar_tudo.py` faz sozinho quando entra concurso novo;
este script serve para rodar à mão. Faz uma cópia do banco antes de gravar.

Uso: python scripts/recalibrar.py [--sem-copia]
"""
import logging
import shutil
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config
import db
from externo.varredura import recalcular_percentuais_gravados
from stats import calibracao

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("recalibrar")


def main() -> int:
    db.inicializar_schema()
    if "--sem-copia" not in sys.argv:
        copia = config.DB_PATH.with_name(f"{config.DB_PATH.name}.bak-{datetime.now():%Y%m%d-%H%M%S}-antes-recalibrar")
        shutil.copy2(config.DB_PATH, copia)
        logger.info("Cópia do banco: %s", copia.name)
    conexao = db.conectar()
    try:
        parametros = calibracao.recalibrar(conexao)
        if parametros is None:
            logger.error("Sem jogos apurados suficientes para calibrar; nada foi gravado.")
            return 1
        refeitos = recalcular_percentuais_gravados(conexao)
        db.registrar_execucao(conexao, "calibracao", sucesso=True, quantidade=sum(p["jogos"] for p in parametros.values()))
        conexao.commit()
    except Exception:
        conexao.rollback()
        logger.exception("Falha ao recalibrar; nenhuma alteração foi gravada.")
        return 1
    finally:
        conexao.close()
    for origem, p in parametros.items():
        aplicada = origem in config.CALIBRACAO_ORIGENS_APLICADAS
        logger.info("%s: expoente %.2f, mistura %.2f, %s jogos (%s)", origem, p["expoente"], p["mistura"], p["jogos"],
                    "aplicada" if aplicada else "gravada, mas o app não aplica nesta origem")
    logger.info("Percentuais regravados em %s concurso(s).", refeitos)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
