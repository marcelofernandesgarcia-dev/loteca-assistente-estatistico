"""Revisão pós-jogo e diagnóstico do concurso (itens D2 e D4 do plano v2, aprovado em 07/10/2026).
Funções puras: recebem o que o app guardou (percentuais do momento, marcação, resultado) e devolvem números
e leituras. Nada aqui muda percentual nem recalibra modelo: um concurso tem só 14 jogos, e ajustar o modelo
a ele seria ajustar ao acaso (decisão registrada no plano v2). A calibração usa todos os concursos.
"""
import bisect
import math

import config
from stats.analise_palpite import classificar_jogo

LEITURAS = {
    "acerto": "acerto",
    "erro": "erro",
    "zebra": "zebra (o app dava menos de {limiar:.0f}%)",
    "multiplo_util": "duplo/triplo útil (o resultado não era o mais provável entre os marcados)",
    "multiplo_dispensavel": "duplo/triplo dispensável (deu o mais provável entre os marcados)",
    "multiplo_nao_bastou": "duplo/triplo não bastou",
}


def surpresa(pct: dict, resultado: str) -> float:
    """−ln(chance que o app deu ao resultado). Perto de zero: esperado; acima de ln(1/0,15) ≈ 1,9: zebra."""
    return -math.log(max(pct[resultado], 1e-9) / 100.0)


def leitura_do_jogo(pct: dict, marcacoes: list[str], resultado: str) -> str:
    """Chave de LEITURAS para um jogo conferido."""
    leitura = classificar_jogo(pct, marcacoes)
    acertou = resultado in leitura["marcacoes"]
    if leitura["multiplicador"] > 1:
        if not acertou:
            return "multiplo_nao_bastou"
        return "multiplo_dispensavel" if resultado == leitura["melhor_marcada"] else "multiplo_util"
    if acertou:
        return "acerto"
    return "zebra" if pct[resultado] < config.ANALISE_LIMIAR_ZEBRA else "erro"


def texto_da_leitura(chave: str) -> str:
    return LEITURAS[chave].format(limiar=config.ANALISE_LIMIAR_ZEBRA)


def revisao_do_bilhete(jogos: list[dict], referencia: dict | None = None) -> dict:
    """`jogos`: [{'num_jogo', 'pct' (o percentual guardado), 'marcacoes', 'resultado', 'sugestao' (opcional)}].
    `referencia`: frequência simples de 1/X/2 em % (opcional), para dizer se o app ajudou neste concurso.
    Devolve as linhas por jogo e, do concurso, a perda logarítmica média do app e da referência."""
    linhas = []
    for jogo in jogos:
        chave = leitura_do_jogo(jogo["pct"], jogo["marcacoes"], jogo["resultado"])
        linhas.append({
            "num_jogo": jogo["num_jogo"], "leitura": chave, "texto": texto_da_leitura(chave),
            "surpresa": surpresa(jogo["pct"], jogo["resultado"]),
            "acertou": jogo["resultado"] in jogo["marcacoes"],
            "sugestao_acertou": jogo["resultado"] in jogo["sugestao"] if jogo.get("sugestao") else None,
        })
    perda_app = sum(l["surpresa"] for l in linhas) / len(linhas) if linhas else None
    perda_ref = (sum(surpresa(referencia, j["resultado"]) for j in jogos) / len(jogos)) if referencia and jogos else None
    return {
        "jogos": linhas,
        "perda_log_app": perda_app,
        "perda_log_referencia": perda_ref,
        "zebras": sum(1 for l in linhas if l["surpresa"] > -math.log(config.ANALISE_LIMIAR_ZEBRA / 100.0)),
    }


def diagnostico_do_concurso(concursos: list[dict], numero: int) -> dict | None:
    """Fácil, médio, difícil ou acumulou, pela POSIÇÃO do concurso. `concursos`: de
    stats.anti_manada.carregar_concursos (com ganhadores_14, arrecadacao, ganhadores_por_milhao, ano).
    None se o concurso não está entre eles (sem arrecadação ou sem os 14 jogos apurados)."""
    alvo = next((c for c in concursos if c["numero"] == numero), None)
    if alvo is None:
        return None
    com_ganhador = sorted(c["ganhadores_por_milhao"] for c in concursos if c["ganhadores_14"] > 0)
    do_ano = sorted(c["ganhadores_por_milhao"] for c in concursos if c["ano"] == alvo["ano"])
    valor = alvo["ganhadores_por_milhao"]
    posicao_ano = bisect.bisect_right(do_ano, valor) / len(do_ano)
    if alvo["ganhadores_14"] == 0:
        classe, posicao = "acumulou", None
    else:
        posicao = bisect.bisect_right(com_ganhador, valor) / len(com_ganhador)
        classe = ("fácil" if posicao > config.REVISAO_CORTE_FACIL
                  else "médio" if posicao > config.REVISAO_CORTE_DIFICIL else "difícil")
    return {
        "numero": numero, "ganhadores_14": alvo["ganhadores_14"], "por_milhao": valor, "classe": classe,
        "posicao_entre_com_ganhador": posicao, "posicao_no_ano": posicao_ano,
        "concursos_no_ano": len(do_ano), "maior_do_ano": valor >= do_ano[-1],
        "sem_ganhador_no_historico": sum(1 for c in concursos if c["ganhadores_14"] == 0), "total": len(concursos),
    }


def frase_do_diagnostico(d: dict) -> str:
    """Ex.: 'Concurso fácil: 96,3 ganhadores de 14 por milhão arrecadado, o maior dos 47 de 2026...'."""
    por_milhao = f"{d['por_milhao']:.1f}".replace(".", ",")
    if d["classe"] == "acumulou":
        return (f"Concurso difícil: ninguém fez 14 (acumulou), como em {d['sem_ganhador_no_historico']} dos "
                f"{d['total']} concursos com arrecadação registrada.")
    ano = " o maior do ano" if d["maior_do_ano"] else f" acima de {100 * d['posicao_no_ano']:.0f}% dos concursos do ano"
    texto = (f"Concurso {d['classe']}: {por_milhao} ganhadores de 14 por milhão arrecadado ({d['ganhadores_14']} "
             f"ganhadores),{ano}.")
    if d["classe"] == "fácil":
        texto += (" Num concurso de favoritos, o erro do app indica fraqueza do modelo ou falta de dado no jogo errado, "
                  "e não azar. Vale olhar os jogos errados; ajustar o modelo só com todos os concursos.")
    return texto
