"""Orquestra a varredura semanal: para cada participante do próximo
concurso, busca notícias, extrai sinais, calcula o ajuste limitado, grava
o log em `fatores_externos` e atualiza `percentuais` (histórico + ajuste).

Agendamento: ver scripts/varredura_semanal.py e README.md (Agendador de
Tarefas do Windows) -- este módulo só decide O QUE fazer quando chamado,
não QUANDO; "2 dias antes do prazo" é calculado aqui a partir de
concursos.data_limite_aposta para o script decidir se já deve rodar hoje.
"""
import datetime as dt
import json
import logging

import config
from externo.ajuste import calcular_ajuste, montar_evidencias
from externo.analise import classificar_noticias, sinais_da_classificacao
from externo.coleta import buscar_noticias
from externo.percentual_final import ajustes_do_concurso, percentuais_do_jogo

logger = logging.getLogger(__name__)


def concurso_alvo_da_semana(conexao, agora: dt.datetime | None = None) -> dict | None:
    """Concurso ainda não varrido cujo prazo de aposta está a no máximo
    VARREDURA_DIAS_ANTES_DO_PRAZO dias de hoje (e não venceu).

    Janela de 0 a N dias, e não "exatamente N": com data exata, um dia sem o
    computador ligado deixava o concurso inteiro sem varredura, sem aviso.
    O concurso já varrido só é lido de novo no dia do prazo, uma vez ("segunda" leitura), se a
    leitura anterior foi em outro dia e já passou de config.VARREDURA_LEITURA_FINAL_HORA (13h, decisão
    do usuário em 07/10/2026: perto do prazo das 15h, para pegar escalação e desfalque confirmados).
    A percentual usa a leitura mais recente de cada time.
    """
    agora = agora or dt.datetime.now()
    hoje = agora.date()
    linhas = conexao.execute(
        """
        SELECT c.numero, c.data_limite_aposta,
               (SELECT MAX(substr(f.coletado_em, 1, 10)) FROM fatores_externos f WHERE f.concurso_numero = c.numero) AS ultima,
               (SELECT COUNT(DISTINCT substr(f.coletado_em, 1, 10)) FROM fatores_externos f WHERE f.concurso_numero = c.numero) AS leituras
        FROM concursos c
        WHERE c.data_limite_aposta IS NOT NULL
        ORDER BY c.data_limite_aposta
        """
    ).fetchall()
    for linha in linhas:
        try:
            prazo = dt.date.fromisoformat(linha["data_limite_aposta"])
        except (TypeError, ValueError):
            logger.warning("Concurso %s com data_limite_aposta inválida; ignorado na varredura.", linha["numero"])
            continue
        dias = (prazo - hoje).days
        if not linha["leituras"] and 0 <= dias <= config.VARREDURA_DIAS_ANTES_DO_PRAZO:
            return {"numero": linha["numero"], "data_limite_aposta": linha["data_limite_aposta"], "leitura": "primeira"}
        # Segunda leitura no dia do prazo (Fase 1 do plano de 07/10/2026): a primeira é feita até dois dias antes
        # e não pega desfalque confirmado nem escalação. Só uma vez, e só se a última leitura foi em outro dia.
        if (dias == 0 and linha["leituras"] and linha["leituras"] < config.VARREDURA_LEITURAS_POR_CONCURSO
                and linha["ultima"] < hoje.isoformat() and agora.hour >= config.VARREDURA_LEITURA_FINAL_HORA):
            return {"numero": linha["numero"], "data_limite_aposta": linha["data_limite_aposta"], "leitura": "segunda"}
    return None


def participantes_do_concurso(conexao, numero_concurso: int) -> list[dict]:
    """Cada participante do concurso com o tipo e o adversário da partida -- o contexto que o filtro de
    notícias usa para não pôr sinal no time errado (análise do concurso 1273, 07/10/2026)."""
    linhas = conexao.execute(
        """
        SELECT j.num_jogo, pc.id AS casa_id, pc.nome AS casa, pc.tipo AS casa_tipo,
               pf.id AS fora_id, pf.nome AS fora, pf.tipo AS fora_tipo
        FROM jogos j JOIN participantes pc ON pc.id = j.casa_id JOIN participantes pf ON pf.id = j.fora_id
        WHERE j.concurso_numero = ? ORDER BY j.num_jogo
        """,
        (numero_concurso,),
    ).fetchall()
    vistos, saida = set(), []
    for linha in linhas:
        for eu, adv in (("casa", "fora"), ("fora", "casa")):
            if linha[f"{eu}_id"] in vistos:
                continue
            vistos.add(linha[f"{eu}_id"])
            saida.append({"id": linha[f"{eu}_id"], "nome": linha[eu], "tipo": linha[f"{eu}_tipo"], "adversario": linha[adv]})
    return saida


def executar_para_concurso(conexao, numero_concurso: int) -> list[dict]:
    """Roda a varredura para todos os participantes de um concurso e
    recalcula `percentuais`. Retorna um log resumido, útil para teste e
    para exibir na UI depois de rodar manualmente."""
    agora = dt.datetime.now().isoformat(timespec="seconds")
    resultados = []

    participantes = participantes_do_concurso(conexao, numero_concurso)
    nomes_do_concurso = [p["nome"] for p in participantes]
    for participante in participantes:
        noticias = buscar_noticias(participante["nome"])
        classificacao = classificar_noticias(
            noticias, participante_nome=participante["nome"], adversario_nome=participante["adversario"],
            tipo_participante=participante["tipo"], nomes_do_concurso=nomes_do_concurso,
        )
        sinais = sinais_da_classificacao(classificacao)
        ajuste = calcular_ajuste(sinais)
        gravar_noticias_lidas(conexao, numero_concurso, participante["id"], agora, classificacao)

        conexao.execute(
            """
            INSERT INTO fatores_externos (participante_id, concurso_numero, coletado_em, resumo, fontes, ajuste_aplicado, sinal, evidencias)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                participante["id"],
                numero_concurso,
                agora,
                ajuste["resumo"],
                "; ".join(n.get("fonte", "") for n in noticias if n.get("fonte")),
                ajuste["ajuste_aplicado"],
                ",".join(ajuste["tipos_encontrados"]) or None,
                json.dumps(montar_evidencias(sinais), ensure_ascii=False),
            ),
        )
        resultados.append({"participante": participante["nome"], **ajuste})

    _recalcular_percentuais_do_concurso(conexao, numero_concurso, agora)
    return resultados


def gravar_noticias_lidas(conexao, numero_concurso: int, participante_id: int, coletado_em: str,
                          classificacao: list[dict]) -> int:
    """Grava cada manchete lida com a decisão do filtro (item A3 do plano v2). Devolve quantas."""
    for item in classificacao:
        noticia = item["noticia"]
        conexao.execute(
            """
            INSERT INTO noticias_lidas (concurso_numero, participante_id, coletado_em, titulo, fonte, url, publicado_em,
                situacao, aceitos, descartes, versao_regras)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                numero_concurso, participante_id, coletado_em, noticia["titulo"], noticia.get("fonte"),
                noticia.get("url"), noticia.get("publicado_em"), item["situacao"],
                json.dumps(item["aceitos"], ensure_ascii=False), json.dumps(item["descartes"], ensure_ascii=False),
                config.VARREDURA_VERSAO_REGRAS,
            ),
        )
    return len(classificacao)


def noticias_lidas_do_concurso(conexao, numero_concurso: int, so_ultima_leitura: bool = True) -> list[dict]:
    """Manchetes lidas no concurso, com nome do participante e a decisão do filtro. Por padrão, só a
    leitura mais recente de cada participante (a que vale para o percentual)."""
    filtro = (
        "AND n.coletado_em = (SELECT MAX(coletado_em) FROM noticias_lidas x "
        "WHERE x.concurso_numero = n.concurso_numero AND x.participante_id = n.participante_id)"
        if so_ultima_leitura else ""
    )
    linhas = conexao.execute(
        f"""
        SELECT n.*, p.nome AS participante FROM noticias_lidas n JOIN participantes p ON p.id = n.participante_id
        WHERE n.concurso_numero = ? {filtro}
        ORDER BY p.nome, n.id
        """,
        (numero_concurso,),
    ).fetchall()
    return [
        {**dict(linha), "aceitos": json.loads(linha["aceitos"] or "[]"), "descartes": json.loads(linha["descartes"] or "[]")}
        for linha in linhas
    ]


def recalcular_percentuais_gravados(conexao) -> int:
    """Refaz o registro de `percentuais` dos concursos que já tiveram varredura, com a calibração atual.
    Devolve quantos concursos foram refeitos. Não faz commit."""
    agora = dt.datetime.now().isoformat(timespec="seconds")
    concursos = [linha[0] for linha in conexao.execute("SELECT DISTINCT concurso_numero FROM fatores_externos ORDER BY 1")]
    for numero in concursos:
        _recalcular_percentuais_do_concurso(conexao, numero, agora)
    return len(concursos)


def _recalcular_percentuais_do_concurso(conexao, numero_concurso: int, agora: str) -> None:
    """Grava em `percentuais` o que a varredura calculou: histórico, ajuste do
    participante e percentual final já normalizado para somar 100%."""
    ajustes = ajustes_do_concurso(conexao, numero_concurso)
    jogos = conexao.execute(
        "SELECT id, casa_id, fora_id, data_jogo FROM jogos WHERE concurso_numero = ?", (numero_concurso,)
    ).fetchall()
    for jogo in jogos:
        calculado = percentuais_do_jogo(conexao, jogo["casa_id"], jogo["fora_id"], ajustes, jogo["data_jogo"])
        for participante_id, chave in ((jogo["casa_id"], "1"), (jogo["fora_id"], "2")):
            ajuste = ajustes.get(participante_id, {}).get("ajuste", 0.0)
            hist = calculado["historico"][chave]
            final = calculado["final"][chave]
            conexao.execute(
                """
                INSERT INTO percentuais (jogo_id, participante_id, percentual_historico, ajuste_externo, percentual_final, calculado_em)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(jogo_id, participante_id) DO UPDATE SET
                    percentual_historico=excluded.percentual_historico,
                    ajuste_externo=excluded.ajuste_externo,
                    percentual_final=excluded.percentual_final,
                    calculado_em=excluded.calculado_em
                """,
                (jogo["id"], participante_id, hist, ajuste, final, agora),
            )
