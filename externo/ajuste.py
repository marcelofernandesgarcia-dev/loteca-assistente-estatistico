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


def montar_evidencias(sinais: list[dict]) -> list[dict]:
    """Manchete, veículo e link que sustentam cada sinal (sem repetição), para
    o usuário conferir de onde veio o ajuste. Nada além disso é guardado."""
    vistos, saida = set(), []
    for sinal in sinais:
        chave = (sinal["sinal"], sinal["evidencia"])
        if chave in vistos:
            continue
        vistos.add(chave)
        saida.append(
            {"sinal": sinal["sinal"], "manchete": sinal["evidencia"], "fonte": sinal.get("fonte", ""), "url": sinal.get("url", "")}
        )
    return saida


def aplicar_ajuste(historico: dict, ajuste_casa: float, ajuste_fora: float) -> dict:
    """Aplica os ajustes externos de mandante e visitante a um {'1','X','2'} em %.

    Efeito no jogo = ajuste do mandante MENOS ajuste do visitante (dois times
    igualmente afetados se compensam), limitado a ±teto. O resultado favorecido
    ganha exatamente esse deslocamento; o que ele ganha sai dos outros dois
    resultados, na proporção deles. Assim a soma continua 100%, nenhum valor
    fica negativo e nenhum percentual se afasta do histórico além do teto.
    Retorna {'final': {...}, 'deslocamento': pontos, positivo = a favor do mandante}."""
    teto = config.AJUSTE_EXTERNO_TETO_PONTOS
    liquido = max(-teto, min(teto, ajuste_casa - ajuste_fora))
    favorecido, outros = ("1", ("X", "2")) if liquido >= 0 else ("2", ("X", "1"))
    massa_dos_outros = historico[outros[0]] + historico[outros[1]]
    movimento = min(abs(liquido), 100.0 - historico[favorecido], massa_dos_outros)
    final = dict(historico)
    if movimento > 0 and massa_dos_outros > 0:
        final[favorecido] = historico[favorecido] + movimento
        for chave in outros:
            final[chave] = historico[chave] - movimento * historico[chave] / massa_dos_outros
    else:
        movimento = 0.0
    return {"final": final, "deslocamento": movimento if favorecido == "1" else -movimento}
