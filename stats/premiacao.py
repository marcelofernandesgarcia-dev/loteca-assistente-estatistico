"""Valores de cada concurso: arrecadação, ganhadores e prêmio por faixa, totais pagos e acumulados
(pedido do usuário, 30/09/2026). Só leitura do que a CAIXA publicou e aritmética simples.

O que é dado e o que é conta:
- DADO (publicado pela CAIXA, guardado em `concursos` e `premiacoes`): arrecadação total, acumulados,
  ganhadores e valor do prêmio por ganhador em cada faixa.
- CONTA: total pago por faixa = ganhadores x valor por ganhador; total pago no concurso = soma das faixas.

Limites honestos: o total pago de um concurso inclui valor acumulado de concursos anteriores (a 1ª faixa soma o
que ficou acumulado quando ninguém fez 14) e já desconta o Imposto de Renda, então NÃO é "retorno sobre a
arrecadação" e não deve ser comparado como tal.

Decisão de 30/09/2026 (medida nos dados): o app NÃO deriva valores da regra de divisão do Manual de Produtos
v21 (55% da arrecadação para prêmios; 70/10/10/10 entre as faixas). Nos concursos recentes (1260 a 1272) o
acumulado de final zero/cinco cresce 3,85% da arrecadação por concurso e zera nos concursos de final 5 e 0,
como a regra prevê; nos antigos, e até em alguns recentes, a relação entre o pago e o previsto pela regra não é
constante (na 2ª faixa, de 0,70 a mais de 1,0 do previsto). Por isso a tela mostra só o que foi publicado.
"""
import statistics

NOME_FAIXA = {1: "1ª faixa (14 acertos)", 2: "2ª faixa (13 acertos)"}


def _produto(ganhadores, valor):
    if ganhadores is None or valor is None:
        return None
    return ganhadores * valor


def resumo_do_concurso(concurso: dict, premiacoes: list[dict]) -> dict:
    """`concurso`: linha de `concursos` (valor_arrecadado, valor_acumulado_final_0_5,
    valor_acumulado_especial, valor_acumulado_proximo, valor_estimado_proximo, acumulado).
    `premiacoes`: linhas de `premiacoes` do concurso (faixa, pontos, ganhadores, valor_premio).
    Valor ausente fica None, nunca 0 por suposição."""
    arrecadado = concurso.get("valor_arrecadado")
    faixas = []
    for p in sorted(premiacoes, key=lambda x: x["faixa"]):
        faixas.append({
            "faixa": p["faixa"], "pontos": p["pontos"], "nome": NOME_FAIXA.get(p["faixa"], f"{p['faixa']}ª faixa"),
            "ganhadores": p["ganhadores"], "valor_por_ganhador": p["valor_premio"],
            "total": _produto(p["ganhadores"], p["valor_premio"]),
        })
    totais = [f["total"] for f in faixas if f["total"] is not None]
    primeira = next((f for f in faixas if f["faixa"] == 1), None)
    return {
        "numero": concurso.get("numero"),
        "arrecadado": arrecadado,
        "faixas": faixas,
        "total_pago": sum(totais) if totais else None,
        "ganhadores_total": sum(f["ganhadores"] or 0 for f in faixas) if faixas else None,
        "sem_ganhador_14": bool(primeira and primeira["ganhadores"] == 0),
        "acumulado_final_0_5": concurso.get("valor_acumulado_final_0_5"),
        "acumulado_especial": concurso.get("valor_acumulado_especial"),
        "acumulado_proximo": concurso.get("valor_acumulado_proximo"),
        "estimativa_proximo": concurso.get("valor_estimado_proximo"),
    }


def premiacoes_do_concurso(conexao, numero: int) -> list[dict]:
    return [dict(l) for l in conexao.execute(
        "SELECT faixa, pontos, ganhadores, valor_premio FROM premiacoes WHERE concurso_numero = ? ORDER BY faixa",
        (numero,),
    )]


def resumo_por_numero(conexao, numero: int) -> dict | None:
    linha = conexao.execute("SELECT * FROM concursos WHERE numero = ?", (numero,)).fetchone()
    if linha is None:
        return None
    return resumo_do_concurso(dict(linha), premiacoes_do_concurso(conexao, numero))


def serie_historica(conexao) -> list[dict]:
    """Uma linha por concurso apurado, do mais antigo ao mais novo: arrecadação e as duas faixas.
    Só concursos com premiação registrada (os apurados)."""
    linhas = conexao.execute(
        """
        SELECT c.numero, c.data_apuracao, c.valor_arrecadado,
               p1.ganhadores AS ganhadores_14, p1.valor_premio AS premio_14,
               p2.ganhadores AS ganhadores_13, p2.valor_premio AS premio_13
        FROM concursos c
        JOIN premiacoes p1 ON p1.concurso_numero = c.numero AND p1.faixa = 1
        LEFT JOIN premiacoes p2 ON p2.concurso_numero = c.numero AND p2.faixa = 2
        ORDER BY c.numero
        """
    ).fetchall()
    serie = []
    for l in linhas:
        pago = [t for t in (_produto(l["ganhadores_14"], l["premio_14"]), _produto(l["ganhadores_13"], l["premio_13"])) if t is not None]
        serie.append({**dict(l), "total_pago": sum(pago) if pago else None})
    return serie


def estatisticas_do_historico(serie: list[dict]) -> dict:
    """Resumo da série: quantos concursos, em quantos ninguém fez 14, maior prêmio de 14 acertos,
    arrecadação mediana. Só conta concursos com o dado em questão."""
    n = len(serie)
    com_14 = [s for s in serie if s["ganhadores_14"] is not None]
    sem_ganhador = sum(1 for s in com_14 if s["ganhadores_14"] == 0)
    premios_14 = [s for s in serie if s["premio_14"] and s["ganhadores_14"]]
    arrecadacoes = [s["valor_arrecadado"] for s in serie if s["valor_arrecadado"]]
    maior = max(premios_14, key=lambda s: s["premio_14"]) if premios_14 else None
    return {
        "concursos": n,
        "com_dado_de_14": len(com_14),
        "sem_ganhador_14": sem_ganhador,
        "percentual_sem_ganhador_14": 100.0 * sem_ganhador / len(com_14) if com_14 else None,
        "maior_premio_14": {"numero": maior["numero"], "valor": maior["premio_14"]} if maior else None,
        "arrecadacao_mediana": statistics.median(arrecadacoes) if arrecadacoes else None,
        "com_arrecadacao": len(arrecadacoes),
    }


def reais(valor: float | None) -> str:
    """R$ 1.294.441,38; valor ausente vira 'sem dado'."""
    if valor is None:
        return "sem dado"
    texto = f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {texto}"
