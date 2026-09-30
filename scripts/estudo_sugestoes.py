#!/usr/bin/env python3
"""Roda o E4 (teste das sugestões para jogos complexos) sobre o banco local, só
leitura, e imprime os números usados em docs/estudo-sugestoes-jogos-complexos-30-09-2026.md.

Uso: python scripts/estudo_sugestoes.py
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config
import db
from stats.backtest import carregar_jogos, prever_walk_forward
from stats.estudo_sugestoes import avaliar_orcamento, avaliar_trocas, concursos_completos


def main() -> int:
    with db.sessao() as conexao:
        jogos = carregar_jogos(conexao)
    previsoes = prever_walk_forward(jogos)
    concursos = concursos_completos(jogos, previsoes)
    print(f"concursos completos avaliados: {len(concursos)}")
    saida = {"concursos": len(concursos), "orcamentos": [], "trocas": []}
    for duplos, triplos in config.OTIMIZACAO_ORCAMENTOS_TESTE:
        resumo = avaliar_orcamento(concursos, duplos, triplos)
        saida["orcamentos"].append(resumo)
        print(json.dumps(resumo, ensure_ascii=False))
    for duplos, triplos in ((1, 0), (2, 1), (3, 2)):
        resumo = {"duplos": duplos, "triplos": triplos, **avaliar_trocas(concursos, duplos, triplos)}
        saida["trocas"].append(resumo)
        print(json.dumps(resumo, ensure_ascii=False))
    destino = Path(__file__).resolve().parent.parent / "docs" / "estudo-sugestoes-resultado.json"
    destino.write_text(json.dumps(saida, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"gravado em {destino}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
