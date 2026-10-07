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
from externo.analise import extrair_sinais
from externo.coleta import buscar_noticias
from externo.percentual_final import ajustes_do_concurso, percentuais_do_jogo

logger = logging.getLogger(__name__)


def concurso_alvo_da_semana(conexao) -> dict | None:
    """Concurso ainda não varrido cujo prazo de aposta está a no máximo
    VARREDURA_DIAS_ANTES_DO_PRAZO dias de hoje (e não venceu).

    Janela de 0 a N dias, e não "exatamente N": com data exata, um dia sem o
    computador ligado deixava o concurso inteiro sem varredura, sem aviso.
    O concurso que já tem linha em `fatores_externos` não é varrido de novo.
    """
    hoje = dt.date.today()
    linhas = conexao.execute(
        """
        SELECT c.numero, c.data_limite_aposta FROM concursos c
        WHERE c.data_limite_aposta IS NOT NULL
          AND NOT EXISTS (SELECT 1 FROM fatores_externos f WHERE f.concurso_numero = c.numero)
        ORDER BY c.data_limite_aposta
        """
    ).fetchall()
    for linha in linhas:
        try:
            prazo = dt.date.fromisoformat(linha["data_limite_aposta"])
        except (TypeError, ValueError):
            logger.warning("Concurso %s com data_limite_aposta inválida; ignorado na varredura.", linha["numero"])
            continue
        if 0 <= (prazo - hoje).days <= config.VARREDURA_DIAS_ANTES_DO_PRAZO:
            return {"numero": linha["numero"], "data_limite_aposta": linha["data_limite_aposta"]}
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
        sinais = extrair_sinais(
            noticias, participante_nome=participante["nome"], adversario_nome=participante["adversario"],
            tipo_participante=participante["tipo"], nomes_do_concurso=nomes_do_concurso,
        )
        ajuste = calcular_ajuste(sinais)

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
        "SELECT id, casa_id, fora_id FROM jogos WHERE concurso_numero = ?", (numero_concurso,)
    ).fetchall()
    for jogo in jogos:
        calculado = percentuais_do_jogo(conexao, jogo["casa_id"], jogo["fora_id"], ajustes)
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
