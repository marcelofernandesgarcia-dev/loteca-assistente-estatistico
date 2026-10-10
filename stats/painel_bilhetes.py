"""Painel dos bilhetes conferidos por tipo de jogo (item D5 do plano v2, aprovado em 07/10/2026).

Separa as marcações já conferidas por origem do percentual, cobertura, faixa do favorito, presença de notícia
com efeito e tipo de marcação. A taxa de acerto só aparece com config.ANALISE_AMOSTRA_MINIMA marcações no
grupo; abaixo disso é ruído e a tela diz "aguardando amostra". Origem, cobertura e notícia só existem para
bilhetes salvos depois de 07/10/2026 (com retrato); os demais entram como "sem retrato".
"""
import json
import math

import config

SEM_RETRATO = "sem retrato (salvo antes de 07/10/2026)"
NOME_ORIGEM = {
    "retrospecto_cbf": "Séries A e B (temporada da CBF)",
    "temporada_cbf_e_elo": "Séries A e B (temporada da CBF + Elo)",
    "elo_clubes": "Outros clubes (Elo de clubes)",
    "elo_selecoes": "Seleções (Elo)",
    "poisson": "Outros clubes (histórico da Loteca)",
    "frequencia_global": "Sem base própria (frequência geral)",
}
DIMENSOES = {
    "origem": "Origem do percentual",
    "cobertura": "Cobertura de dados",
    "faixa": "Faixa do favorito",
    "noticia": "Notícia com efeito no jogo",
    "marcacao": "Tipo de marcação",
}


def _faixa(pct: dict) -> str:
    favorito = max(pct.values())
    if favorito < 45:
        return "favorito abaixo de 45%"
    if favorito < 60:
        return "favorito de 45% a 60%"
    return "favorito de 60% ou mais"


def segmentos_do_jogo(jogo: dict) -> dict[str, str]:
    """`jogo`: {'pct', 'marcacoes', 'resultado', 'retrato' (dict do retrato do jogo, ou None)}."""
    retrato = jogo.get("retrato")
    quantidade = len(jogo["marcacoes"])
    segmentos = {
        "faixa": _faixa(jogo["pct"]),
        "marcacao": {1: "simples", 2: "duplo", 3: "triplo"}[quantidade],
    }
    if retrato:
        segmentos["origem"] = NOME_ORIGEM.get(retrato.get("origem"), retrato.get("origem") or "-")
        segmentos["cobertura"] = retrato["cobertura"]["nome_nivel"]
        segmentos["noticia"] = "sim" if abs(retrato["noticias"].get("deslocamento") or 0.0) > 1e-9 else "não"
    else:
        segmentos["origem"] = segmentos["cobertura"] = segmentos["noticia"] = SEM_RETRATO
    return segmentos


def painel(jogos: list[dict]) -> dict[str, list[dict]]:
    """{dimensão: [{'grupo', 'marcacoes', 'acertos', 'taxa' (None abaixo da amostra mínima), 'surpresa_media'}]}."""
    contagem: dict[str, dict[str, list]] = {d: {} for d in DIMENSOES}
    for jogo in jogos:
        acertou = jogo["resultado"] in jogo["marcacoes"]
        surpresa = -math.log(max(jogo["pct"][jogo["resultado"]], 1e-9) / 100.0)
        for dimensao, grupo in segmentos_do_jogo(jogo).items():
            registro = contagem[dimensao].setdefault(grupo, [0, 0, 0.0])
            registro[0] += 1
            registro[1] += int(acertou)
            registro[2] += surpresa
    minimo = config.ANALISE_AMOSTRA_MINIMA
    return {
        dimensao: [
            {"grupo": grupo, "marcacoes": n, "acertos": a, "taxa": 100.0 * a / n if n >= minimo else None,
             "surpresa_media": s / n}
            for grupo, (n, a, s) in sorted(grupos.items())
        ]
        for dimensao, grupos in contagem.items()
    }


def jogos_conferidos(conexao) -> list[dict]:
    """Jogos dos bilhetes apostados e conferidos, com o percentual guardado e o retrato do jogo quando existe.
    Rascunho e simulação não contam (decisão do usuário, 10/10/2026)."""
    from stats.bilhetes_salvos import SO_APOSTADOS_B  # import local, como nos outros módulos de leitura

    filtro = f"AND {SO_APOSTADOS_B}"
    linhas = conexao.execute(
        f"""
        SELECT bj.bilhete_id, bj.jogo_id, bj.marcacoes, bj.percentual_1, bj.percentual_x, bj.percentual_2,
               j.resultado, r.conteudo AS retrato
        FROM bilhete_jogos bj
        JOIN bilhetes b ON b.id = bj.bilhete_id
        JOIN jogos j ON j.id = bj.jogo_id
        LEFT JOIN retratos_bilhete r ON r.bilhete_id = bj.bilhete_id AND r.jogo_id = bj.jogo_id
        WHERE b.conferido_em IS NOT NULL AND j.resultado IS NOT NULL AND bj.percentual_1 IS NOT NULL {filtro}
        """
    ).fetchall()
    return [
        {"pct": {"1": l["percentual_1"], "X": l["percentual_x"], "2": l["percentual_2"]},
         "marcacoes": l["marcacoes"].split(","), "resultado": l["resultado"],
         "retrato": json.loads(l["retrato"]) if l["retrato"] else None}
        for l in linhas
    ]
