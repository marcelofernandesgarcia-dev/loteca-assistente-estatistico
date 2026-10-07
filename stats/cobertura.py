"""Cobertura de dados de cada jogo (item A2 do plano v2, aprovado em 07/10/2026).

O app não esconde quando sabe pouco de um jogo. O nível vem só do que o app de fato tem, e o
que falta é listado como fato conferível (decisão do usuário: nível e lista, sem um percentual de
cobertura, que exigiria pesos escolhidos sem teste).

Níveis, do mais completo ao mais pobre:
- "completa": os dois times têm a temporada inteira da CBF (Séries A e B, pontos corridos);
- "selecoes": duas seleções, força pelo Elo da base aberta de resultados internacionais;
- "parcial": algum time só tem a fase atual da CBF (Série C) ou só os jogos que caíram na Loteca;
- "baixa": o percentual nem tem base própria (caiu na frequência geral de 1/X/2).
"Parcial" e "baixa" levam o aviso de alta incerteza. Usar a cobertura para escolher onde vai o
duplo ou o triplo é hipótese (item B4) e não mexe na sugestão sem teste.
"""
import datetime as dt

import config

NIVEIS = ("completa", "selecoes", "parcial", "baixa")
NOME_NIVEL = {
    "completa": "Completa (temporada da CBF)",
    "selecoes": "Seleções (Elo)",
    "parcial": "Parcial",
    "baixa": "Baixa",
}
NIVEIS_DE_ALTA_INCERTEZA = ("parcial", "baixa")


def cbf_do_lado(classificacao: dict | None) -> str | None:
    """'pontos_corridos', 'com_fases' (Série C) ou None (sem dados da CBF na temporada atual)."""
    if not classificacao:
        return None
    if classificacao.get("fase"):
        return "com_fases"
    return "pontos_corridos" if classificacao.get("serie") in config.CBF_SERIES_PONTOS_CORRIDOS else "com_fases"


def cobertura_do_jogo(casa: dict, fora: dict, metodo_percentual: str, agora: dt.datetime) -> dict:
    """`casa` e `fora`: {'nome', 'tipo', 'cbf' (de cbf_do_lado), 'jogos_no_ano', 'ano', 'noticias_em'
    (data e hora ISO da leitura mais recente, ou None)}. `metodo_percentual`: de
    stats.percentual.origem_do_percentual. Devolve {'nivel', 'nome_nivel', 'faltas', 'alta_incerteza'}."""
    faltas = []
    if metodo_percentual == "frequencia_global":
        nivel = "baixa"
        faltas.append("percentual sem base própria: poucos jogos na Loteca, usa a frequência geral de 1/X/2")
    elif metodo_percentual == "elo_selecoes":
        nivel = "selecoes"
    elif casa["cbf"] == "pontos_corridos" and fora["cbf"] == "pontos_corridos":
        nivel = "completa"
    else:
        nivel = "parcial"

    for lado in (casa, fora):
        nome = lado["nome"]
        if lado["tipo"] != "selecao":
            if lado["cbf"] == "com_fases":
                faltas.append(f"{nome}: competição com fases (Série C), tabela da CBF só da fase atual")
            elif lado["cbf"] is None:
                faltas.append(f"{nome}: sem dados da CBF na temporada, só os jogos que caíram na Loteca")
        jogos = lado.get("jogos_no_ano") or 0
        if jogos < config.ANO_CURSO_AMOSTRA_PEQUENA:
            faltas.append(f"{nome}: {jogos} jogo(s) encontrados em {lado['ano']}")
        if not lado.get("noticias_em"):
            faltas.append(f"{nome}: notícias não lidas para este concurso")
        else:
            dias = (agora.date() - dt.datetime.fromisoformat(lado["noticias_em"]).date()).days
            if dias > config.VARREDURA_DIAS_ANTES_DO_PRAZO:
                faltas.append(f"{nome}: notícias lidas há {dias} dias")
    return {
        "nivel": nivel,
        "nome_nivel": NOME_NIVEL[nivel],
        "faltas": faltas,
        "alta_incerteza": nivel in NIVEIS_DE_ALTA_INCERTEZA,
    }


def cobertura_do_concurso(conexao, jogos: list[dict], resumo_ano: list[dict], ajustes: dict[int, dict],
                          agora: dt.datetime) -> dict[int, dict]:
    """{jogo_id: cobertura}. `jogos`: id, num_jogo, casa_id, casa, fora_id, fora. `resumo_ano`: de
    stats.ano_em_curso.resumo_do_concurso_no_ano (mesma ordem de num_jogo). `ajustes`: de
    externo.percentual_final.ajustes_do_concurso. Só leitura do banco."""
    from stats.cbf import classificacao_do_participante
    from stats.percentual import origem_do_percentual

    tipos = {linha["id"]: linha["tipo"] for linha in conexao.execute("SELECT id, tipo FROM participantes")}
    ano_por_jogo = {r["num_jogo"]: r for r in resumo_ano}
    saida = {}
    for jogo in jogos:
        resumo = ano_por_jogo.get(jogo["num_jogo"], {})
        lados = []
        for lado in ("casa", "fora"):
            participante_id = jogo[f"{lado}_id"]
            ano = resumo.get(lado) or {}
            ajuste = ajustes.get(participante_id)
            lados.append({
                "nome": jogo[lado], "tipo": tipos.get(participante_id),
                "cbf": cbf_do_lado(classificacao_do_participante(conexao, participante_id)),
                "jogos_no_ano": ano.get("jogos", 0), "ano": ano.get("ano", agora.year),
                "noticias_em": ajuste["coletado_em"] if ajuste else None,
            })
        metodo = origem_do_percentual(conexao, jogo["casa_id"], jogo["fora_id"])["metodo"]
        saida[jogo["id"]] = cobertura_do_jogo(lados[0], lados[1], metodo, agora)
    return saida
