#!/usr/bin/env python3
"""Ponto de entrada chamado pelo Agendador de Tarefas do Windows (ver
README.md para o comando `schtasks` de configuração). Roda sozinho, sem
depender da UI Streamlit estar aberta.

Uso: python scripts/varredura_semanal.py
"""
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import db
from externo.varredura import concurso_alvo_da_semana, executar_para_concurso

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("varredura_semanal")


def main() -> int:
    db.inicializar_schema()
    with db.sessao() as conexao:
        alvo = concurso_alvo_da_semana(conexao)
        if not alvo:
            logger.info("Nenhum concurso na janela de varredura hoje. Nada a fazer.")
            return 0
        logger.info("Rodando varredura para o concurso %s (prazo %s)", alvo["numero"], alvo["data_limite_aposta"])
        resultados = executar_para_concurso(conexao, alvo["numero"])
        for item in resultados:
            logger.info("%s: ajuste=%.1f (%s)", item["participante"], item["ajuste_aplicado"], item["resumo"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
