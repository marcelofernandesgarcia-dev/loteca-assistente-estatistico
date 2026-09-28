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
    """Concurso cujo prazo de aposta cai dentro da janela de
    VARREDURA_DIAS_ANTES_DO_PRAZO dias a partir de hoje."""
    hoje = dt.date.today()
    linhas = conexao.execute(
        "SELECT numero, data_limite_aposta FROM concursos WHERE data_limite_aposta IS NOT NULL"
    ).fetchall()
    for linha in linhas:
        try:
            prazo = dt.date.fromisoformat(linha["data_limite_aposta"])
        except (TypeError, ValueError):
            continue
        if (prazo - hoje).days == config.VARREDURA_DIAS_ANTES_DO_PRAZO:
            return {"numero": linha["numero"], "data_limite_aposta": linha["data_limite_aposta"]}
    return None


def participantes_do_concurso(conexao, numero_concurso: int) -> list[dict]:
    linhas = conexao.execute(
        """
        SELECT DISTINCT p.id, p.nome FROM participantes p
        JOIN jogos j ON j.casa_id = p.id OR j.fora_id = p.id
        WHERE j.concurso_numero = ?
        """,
        (numero_concurso,),
    ).fetchall()
    return [{"id": linha["id"], "nome": linha["nome"]} for linha in linhas]


def executar_para_concurso(conexao, numero_concurso: int) -> list[dict]:
    """Roda a varredura para todos os participantes de um concurso e
    recalcula `percentuais`. Retorna um log resumido, útil para teste e
    para exibir na UI depois de rodar manualmente."""
    agora = dt.datetime.now().isoformat(timespec="seconds")
    resultados = []

    for participante in participantes_do_concurso(conexao, numero_concurso):
        noticias = buscar_noticias(participante["nome"])
        sinais = extrair_sinais(noticias)
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
