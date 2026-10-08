#!/usr/bin/env python3
"""Atualiza as fontes de dado (CAIXA, CBF, calibração dos percentuais, notícias) numa só chamada,
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

import config
import db
from externo.varredura import concurso_alvo_da_semana, executar_para_concurso, recalcular_percentuais_gravados
from importer.caixa_client import importar_concurso, importar_programacao
from importer.cbf_client import coletar_todas
from importer.cbf_mapeamento import parear
from stats import calibracao, confiabilidade

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
    # Pareia de novo a cada coleta: um clube que entra na CBF (ex.: Série C, 07/10/2026) só ganha a
    # ficha da CBF no app depois de pareado com o participante da Loteca.
    pareamento = parear(conexao)
    for aviso in pareamento["ambiguos"]:
        logger.warning("Sem par único CBF x Loteca: %s", aviso)
    for removido in pareamento["removidos"]:
        logger.warning("Par CBF x Loteca removido (a regra não o sustenta mais): %s", removido)
    conexao.commit()
    total_times = sum(r.get("times", 0) for r in resultados if "erro" not in r)
    erros = [r["erro"] for r in resultados if "erro" in r]
    db.registrar_execucao(conexao, "cbf", sucesso=not erros, quantidade=total_times, erro="; ".join(erros) or None)
    conexao.commit()
    logger.info("CBF: %s times coletados, %s erro(s)", total_times, len(erros))


def _atualizar_calibracao(conexao) -> None:
    """Refaz a calibração dos percentuais quando entrou concurso apurado novo (ou ainda não há parâmetros) e
    regrava os percentuais já calculados pelas varreduras. Roda antes das notícias, que usam o percentual corrigido."""
    if not config.CALIBRACAO_ATIVA:
        logger.info("Calibração: desligada (LOTECA_CALIBRACAO=0); nada a fazer.")
        return
    if not calibracao.precisa_recalibrar(conexao):
        logger.info("Calibração: parâmetros já em dia com o último concurso apurado.")
        return
    parametros = calibracao.recalibrar(conexao)
    if parametros is None:
        raise RuntimeError("sem jogos apurados suficientes para calibrar")
    refeitos = recalcular_percentuais_gravados(conexao)
    conexao.commit()
    db.registrar_execucao(conexao, "calibracao", sucesso=True, quantidade=sum(p["jogos"] for p in parametros.values()))
    conexao.commit()
    logger.info("Calibração: %s; %s concurso(s) com percentuais regravados.",
                "; ".join(f"{o} expoente {p['expoente']:.2f} mistura {p['mistura']:.2f}" for o, p in parametros.items()), refeitos)


def _atualizar_noticias(conexao) -> None:
    alvo = concurso_alvo_da_semana(conexao)
    if not alvo:
        logger.info("Notícias: nenhum concurso na janela de varredura hoje -- nada a registrar.")
        return
    resultados = executar_para_concurso(conexao, alvo["numero"])
    conexao.commit()
    db.registrar_execucao(conexao, "noticias", sucesso=True, quantidade=len(resultados))
    conexao.commit()
    logger.info("Notícias: concurso %s, %s leitura, %s participantes.", alvo["numero"], alvo.get("leitura", "primeira"),
                len(resultados))


def _atualizar_medicao(conexao) -> None:
    """Refaz a medição de confiabilidade do app de hoje (sugestão S1) quando entrou concurso apurado novo.
    Leva cerca de 1 a 2 minutos; a página 'Confiabilidade do modelo' só lê o resultado gravado."""
    if not confiabilidade.precisa_medir(conexao):
        logger.info("Medição de confiabilidade: já em dia com o último concurso apurado.")
        return
    medicao = confiabilidade.medir(conexao)
    if medicao is None:
        logger.info("Medição de confiabilidade: sem jogos no período.")
        return
    confiabilidade.gravar(conexao, medicao)
    conexao.commit()
    db.registrar_execucao(conexao, "medicao", sucesso=True, quantidade=medicao["total"]["n"])
    conexao.commit()
    logger.info("Medição de confiabilidade: %s jogos, perda log %.4f contra %.4f da frequência.",
                medicao["total"]["n"], medicao["total"]["perda_log"], medicao["total"]["perda_log_frequencia"])


def main() -> int:
    db.inicializar_schema()
    conexao = db.conectar()
    falhas = 0
    try:
        for nome, funcao in (
            ("caixa", _atualizar_caixa), ("cbf", _atualizar_cbf), ("calibracao", _atualizar_calibracao), ("noticias", _atualizar_noticias),
            ("medicao", _atualizar_medicao),
        ):
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
