#!/usr/bin/env python3
"""Gabarito das notícias (item A3 do plano v2, 07/10/2026).

Uso:
  python scripts/gabarito_noticias.py exportar 1274   -> data/gabarito-noticias/1274.csv, para o usuário rotular
  python scripts/gabarito_noticias.py medir           -> precisão e cobertura em todos os CSV rotulados

O arquivo exportado não é sobrescrito se já existir (o rótulo do usuário não se perde).
"""
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config
import db
from externo.gabarito import gravar_csv, ler_csv, linhas_para_rotular, medir
from externo.varredura import noticias_lidas_do_concurso

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("gabarito_noticias")
PASTA = config.BASE_DIR / "data" / "gabarito-noticias"


def exportar(numero: int) -> int:
    destino = PASTA / f"{numero}.csv"
    if destino.exists():
        logger.error("%s já existe; apague ou renomeie antes de exportar de novo (o rótulo seria perdido).", destino)
        return 1
    with db.sessao() as conexao:
        linhas = linhas_para_rotular(noticias_lidas_do_concurso(conexao, numero))
    if not linhas:
        logger.error("Concurso %s: nenhuma manchete com palavra de sinal registrada.", numero)
        return 1
    gravar_csv(linhas, destino)
    logger.info("%d manchetes exportadas para %s", len(linhas), destino)
    return 0


def medir_tudo() -> int:
    linhas = [linha for arquivo in sorted(PASTA.glob("*.csv")) for linha in ler_csv(arquivo)]
    resultado = medir(linhas)
    if resultado["precisao"] is None:
        logger.info("Nenhuma manchete aceita rotulada ainda (%d rotuladas).", resultado["rotuladas"])
        return 0
    baixo, alto = resultado["precisao_ic95"]
    logger.info(
        "Rotuladas: %d · aceitas: %d · precisão %.0f%% (IC 95%%: %.0f%% a %.0f%%; meta 90%%) · cobertura %s · "
        "descartes errados: %d",
        resultado["rotuladas"], resultado["aceitas"], 100 * resultado["precisao"], 100 * baixo, 100 * alto,
        "-" if resultado["cobertura"] is None else f"{100 * resultado['cobertura']:.0f}%", resultado["descartes_errados"],
    )
    return 0


def main() -> int:
    if len(sys.argv) >= 3 and sys.argv[1] == "exportar":
        return exportar(int(sys.argv[2]))
    if len(sys.argv) >= 2 and sys.argv[1] == "medir":
        return medir_tudo()
    print(__doc__)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
