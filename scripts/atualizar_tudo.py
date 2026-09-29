#!/usr/bin/env python3
"""Atualiza as três fontes de dado (CAIXA, CBF, notícias) numa só chamada,
registrando o resultado de cada uma em `execucoes` -- o painel "Status dos
dados" da página inicial lê essa tabela (etapa D1 do roteiro).

Isolamento deliberado: a falha de uma fonte NÃO impede as outras -- cada
`try/except Exception` aqui existe para isso (orquestrador de fontes
independentes), não para escamotear erro de negócio.

Uso: python scripts/atualizar_tudo.py
"""
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import db
from externo.varredura import concurso_alvo_da_semana, executar_para_concurso
from importer.caixa_client import importar_concurso, importar_programacao
from importer.cbf_client import coletar_todas

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("atualizar_tudo")


def _atualizar_caixa(conexao) -> None:
    programados = importar_programacao(conexao)
    apurado = importar_concurso(None, conexao)
    conexao.commit()
    db.registrar_execucao(conexao, "caixa", sucesso=True, quantidade=len(programados) + 1)
    conexao.commit()
    logger.info("CAIXA: programação %s, último apurado %s", programados, apurado)


def _atualizar_cbf(conexao) -> None:
    resultados = coletar_todas(conexao)
    conexao.commit()
    total_times = sum(r.get("times", 0) for r in resultados if "erro" not in r)
    erros = [r["erro"] for r in resultados if "erro" in r]
    db.registrar_execucao(conexao, "cbf", sucesso=not erros, quantidade=total_times, erro="; ".join(erros) or None)
    conexao.commit()
    logger.info("CBF: %s times coletados, %s erro(s)", total_times, len(erros))


def _atualizar_noticias(conexao) -> None:
    alvo = concurso_alvo_da_semana(conexao)
    if not alvo:
        logger.info("Notícias: nenhum concurso na janela de varredura hoje -- nada a registrar.")
        return
    resultados = executar_para_concurso(conexao, alvo["numero"])
    conexao.commit()
    db.registrar_execucao(conexao, "noticias", sucesso=True, quantidade=len(resultados))
    conexao.commit()
    logger.info("Notícias: concurso %s, %s participantes.", alvo["numero"], len(resultados))


def main() -> int:
    db.inicializar_schema()
    conexao = db.conectar()
    falhas = 0
    try:
        for nome, funcao in (("caixa", _atualizar_caixa), ("cbf", _atualizar_cbf), ("noticias", _atualizar_noticias)):
            try:
                funcao(conexao)
            except Exception as erro:
                falhas += 1
                logger.error("%s falhou: %s", nome, erro)
                conexao.rollback()
                db.registrar_execucao(conexao, nome, sucesso=False, erro=str(erro))
                conexao.commit()
    finally:
        conexao.close()
    return 1 if falhas else 0


if __name__ == "__main__":
    raise SystemExit(main())
