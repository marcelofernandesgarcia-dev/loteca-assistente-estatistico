"""Calculadora de fechamento de bolão -- lê a tabela oficial validada
(data/loteca-boloes-oficial.csv, Anexo I do Manual de Produtos v21)."""
import csv
from functools import lru_cache

import config


@lru_cache(maxsize=1)
def _carregar_tabela() -> list[dict]:
    linhas = []
    with open(config.BOLOES_OFICIAL_CSV_PATH, encoding="utf-8") as arquivo:
        leitor = csv.DictReader(arquivo, delimiter=";")
        for linha in leitor:
            linhas.append(
                {
                    "triplos": int(linha["triplos"]),
                    "duplos": int(linha["duplos"]),
                    "apostas": int(linha["apostas"]),
                    "valor_reais": float(linha["valor_reais"]),
                    "cotas_min": int(linha["cotas_min"]) if linha["cotas_min"] else None,
                    "cotas_max": int(linha["cotas_max"]) if linha["cotas_max"] else None,
                    "valor_min_cota_reais": float(linha["valor_min_cota_reais"]) if linha["valor_min_cota_reais"] else None,
                }
            )
    return linhas


def consultar(triplos: int, duplos: int) -> dict | None:
    """Retorna a linha oficial para essa combinação de triplos/duplos, ou
    None se a combinação não existe na tabela oficial (ex.: acima do máximo
    de 864 apostas / 5 duplos + 3 triplos)."""
    for linha in _carregar_tabela():
        if linha["triplos"] == triplos and linha["duplos"] == duplos:
            return linha
    return None


def calcular(triplos: int, duplos: int) -> dict:
    """Calcula pela fórmula oficial (2^duplos x 3^triplos x R$2,00) mesmo
    para combinações fora da tabela de bolão -- útil para conferir o custo
    de uma aposta que não vai virar bolão fracionado."""
    apostas = (2**duplos) * (3**triplos)
    return {"triplos": triplos, "duplos": duplos, "apostas": apostas, "valor_reais": apostas * 2.0}
