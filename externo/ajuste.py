"""Cálculo do ajuste externo limitado, a partir dos sinais extraídos.

Cada TIPO de sinal conta uma vez só (mesmo que apareça em várias notícias
na semana) -- evita que um mesmo fato repetido em manchetes diferentes
infle o ajuste. Soma limitada a config.AJUSTE_EXTERNO_TETO_PONTOS para o
ajuste nunca dominar o percentual histórico.
"""
import config


def calcular_ajuste(sinais: list[dict]) -> dict:
    tipos_encontrados = {sinal["sinal"] for sinal in sinais}
    soma = sum(config.AJUSTE_EXTERNO_PESOS.get(tipo, 0.0) for tipo in tipos_encontrados)
    teto = config.AJUSTE_EXTERNO_TETO_PONTOS
    ajuste_limitado = max(-teto, min(teto, soma))

    resumo_partes = [f"{tipo} ({config.AJUSTE_EXTERNO_PESOS.get(tipo, 0.0):+.1f})" for tipo in sorted(tipos_encontrados)]
    return {
        "ajuste_aplicado": ajuste_limitado,
        "soma_antes_do_teto": soma,
        "tipos_encontrados": sorted(tipos_encontrados),
        "resumo": "; ".join(resumo_partes) if resumo_partes else "nenhum sinal encontrado nesta semana",
    }
