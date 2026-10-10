"""Versões do palpite (pedido do usuário, 30/09/2026): analisar, mudar,
reanalisar e comparar a mesma marcação antes de salvar, e depois do resultado
aprender se as mudanças entre versões ajudaram.

As versões ficam no banco local (decisão do usuário: "registrado, com intuito
de fortalecer o aprendizado"). Sem dado pessoal: só a marcação, o percentual
do momento e o resumo da análise.

As funções de comparação são puras; as de banco recebem a conexão.
"""
import datetime as dt
import json

import config
from stats.bilhete import PRECO_APOSTA

COLUNAS = ("1", "X", "2")


class LimiteDeVersoes(Exception):
    """O concurso já tem o máximo de versões guardadas (config.VERSOES_MAX_POR_CONCURSO)."""


# ---------------------------------------------------------------------------
# Comparação (puras)
# ---------------------------------------------------------------------------

def _normalizar(marcacoes: dict) -> dict[int, list[str]]:
    """Chaves inteiras e colunas na ordem 1, X, 2 (JSON devolve chaves em texto)."""
    return {int(jogo): [c for c in COLUNAS if c in set(colunas)] for jogo, colunas in marcacoes.items()}


def apostas_de(marcacoes: dict) -> int:
    apostas = 1
    for colunas in marcacoes.values():
        apostas *= len(colunas)
    return apostas


def _tipo(colunas: list[str]) -> str:
    return {1: "seco", 2: "duplo", 3: "triplo"}.get(len(colunas), "vazio")


def diferencas(anterior: dict, atual: dict, num_jogo: dict[int, int] | None = None) -> list[dict]:
    """O que mudou de uma marcação para outra, jogo a jogo, na ordem do concurso.
    `num_jogo`: {jogo_id: número do jogo no concurso}, para ordenar e exibir."""
    anterior, atual = _normalizar(anterior), _normalizar(atual)
    num_jogo = num_jogo or {}
    mudancas = []
    for jogo_id in sorted(set(anterior) | set(atual), key=lambda j: (num_jogo.get(j, j), j)):
        de, para = anterior.get(jogo_id, []), atual.get(jogo_id, [])
        if de == para:
            continue
        mudancas.append({
            "jogo_id": jogo_id, "num_jogo": num_jogo.get(jogo_id, jogo_id), "de": de, "para": para,
            "de_tipo": _tipo(de), "para_tipo": _tipo(para),
            "acrescentou": [c for c in para if c not in de], "retirou": [c for c in de if c not in para],
        })
    return mudancas


def frase_da_mudanca(mudanca: dict) -> str:
    """Ex.: 'jogo 5: 1 (seco) virou 1X (duplo)'."""
    de = "".join(mudanca["de"]) or "em branco"
    para = "".join(mudanca["para"]) or "em branco"
    return f"jogo {mudanca['num_jogo']}: {de} ({mudanca['de_tipo']}) virou {para} ({mudanca['para_tipo']})"


def resumo_da_analise(analise: dict | None, marcacoes: dict) -> dict:
    """O que guardar da análise (stats.analise_palpite.analisar_palpite) junto com a versão."""
    marc = _normalizar(marcacoes)
    resumo = {
        "duplos": sum(1 for c in marc.values() if len(c) == 2),
        "triplos": sum(1 for c in marc.values() if len(c) == 3),
    }
    if analise:
        resumo.update(
            categorias=analise["resumo_categorias"],
            zebras=len(analise["zebras"]),
            sem_base_propria=len(analise["sem_base_propria"]),
        )
    return resumo


def acertos(marcacoes: dict, resultados: dict[int, str | None]) -> int | None:
    """Acertos da marcação contra o resultado real ({jogo_id: '1'|'X'|'2'}); None se falta resultado."""
    marc = _normalizar(marcacoes)
    if any(resultados.get(jogo_id) is None for jogo_id in marc):
        return None
    return sum(1 for jogo_id, colunas in marc.items() if resultados[jogo_id] in colunas)


def aprendizado_das_versoes(versoes: list[dict], resultados: dict[int, str | None],
                            apostados: set[int] | None = None) -> dict | None:
    """Depois do resultado: a primeira versão x a que virou bilhete (ou a última, se nenhuma
    virou). None se há uma versão só ou falta resultado. `versoes` em ordem de criação.
    `apostados` (ids dos bilhetes confirmados como apostados): quando vem, só conta a versão
    que virou bilhete apostado; sem ela, o concurso não entra (decisão do usuário, 10/10/2026)."""
    if len(versoes) < 2:
        return None
    if apostados is not None:
        final = next((v for v in reversed(versoes) if v.get("bilhete_id") in apostados), None)
        if final is None:
            return None
    else:
        final = next((v for v in reversed(versoes) if v.get("bilhete_id")), versoes[-1])
    primeira = versoes[0]
    if final is primeira:
        return None
    acertos_primeira, acertos_final = acertos(primeira["marcacoes"], resultados), acertos(final["marcacoes"], resultados)
    if acertos_primeira is None or acertos_final is None:
        return None
    return {
        "versoes": len(versoes), "numero_final": final["numero_versao"],
        "acertos_primeira": acertos_primeira, "acertos_final": acertos_final,
        "saldo": acertos_final - acertos_primeira,
        "apostas_primeira": primeira["apostas"], "apostas_final": final["apostas"],
    }


def historia_do_bilhete(versoes: list[dict], bilhete_id: int, resultados: dict[int, str | None],
                        num_jogo: dict[int, int] | None = None) -> dict | None:
    """Como o bilhete foi montado: de qual versão veio, o que mudou desde a versão 1 e,
    se já há resultado, quantos acertos a versão 1 teria feito. None se o bilhete não
    está ligado a nenhuma versão."""
    ligada = next((v for v in versoes if v.get("bilhete_id") == bilhete_id), None)
    if not ligada:
        return None
    primeira = versoes[0]
    return {
        "versoes": len(versoes), "numero": ligada["numero_versao"],
        "mudancas": diferencas(primeira["marcacoes"], ligada["marcacoes"], num_jogo) if ligada is not primeira else [],
        "acertos_primeira": acertos(primeira["marcacoes"], resultados) if ligada is not primeira else None,
        "acertos_bilhete": acertos(ligada["marcacoes"], resultados),
    }


def agregar_aprendizado(por_concurso: list[dict]) -> dict:
    """Soma de `aprendizado_das_versoes` de vários concursos: em quantos as mudanças
    ajudaram, atrapalharam ou não mudaram o número de acertos."""
    total = len(por_concurso)
    return {
        "concursos": total,
        "ajudaram": sum(1 for a in por_concurso if a["saldo"] > 0),
        "atrapalharam": sum(1 for a in por_concurso if a["saldo"] < 0),
        "iguais": sum(1 for a in por_concurso if a["saldo"] == 0),
        "saldo_total": sum(a["saldo"] for a in por_concurso),
        "amostra_suficiente": total >= config.VERSOES_CONCURSOS_MINIMOS,
    }


# ---------------------------------------------------------------------------
# Banco
# ---------------------------------------------------------------------------

def _da_linha(linha) -> dict:
    versao = dict(linha)
    versao["marcacoes"] = _normalizar(json.loads(versao["marcacoes"]))
    versao["percentuais"] = {int(k): v for k, v in json.loads(versao["percentuais"]).items()}
    versao["resumo"] = json.loads(versao["resumo"]) if versao["resumo"] else {}
    return versao


def listar_versoes(conexao, concurso_numero: int) -> list[dict]:
    linhas = conexao.execute(
        "SELECT * FROM versoes_palpite WHERE concurso_numero = ? ORDER BY numero_versao", (concurso_numero,)
    ).fetchall()
    return [_da_linha(linha) for linha in linhas]


def versao_igual(conexao, concurso_numero: int, marcacoes: dict) -> dict | None:
    """A versão já guardada com exatamente esta marcação, se houver (a mais recente)."""
    alvo = _normalizar(marcacoes)
    return next((v for v in reversed(listar_versoes(conexao, concurso_numero)) if v["marcacoes"] == alvo), None)


def guardar_versao(conexao, concurso_numero: int, marcacoes: dict, percentuais: dict, analise: dict | None) -> dict:
    """Guarda a marcação como nova versão. Idempotente: se já existe uma versão com a
    mesma marcação, devolve ela ({'versao': ..., 'nova': False}) sem duplicar.
    Levanta LimiteDeVersoes quando o concurso já tem o máximo."""
    marc = _normalizar(marcacoes)
    if not marc or any(not colunas for colunas in marc.values()):
        raise ValueError("Só dá para guardar versão com todos os jogos marcados.")
    existente = versao_igual(conexao, concurso_numero, marc)
    if existente:
        return {"versao": existente, "nova": False}
    quantidade, maior = conexao.execute(
        "SELECT COUNT(*), COALESCE(MAX(numero_versao), 0) FROM versoes_palpite WHERE concurso_numero = ?",
        (concurso_numero,),
    ).fetchone()
    if quantidade >= config.VERSOES_MAX_POR_CONCURSO:
        raise LimiteDeVersoes(
            f"O concurso {concurso_numero} já tem {quantidade} versões guardadas (máximo {config.VERSOES_MAX_POR_CONCURSO})."
        )
    apostas = apostas_de(marc)
    chance = (analise or {}).get("chance") or {}
    conexao.execute(
        "INSERT INTO versoes_palpite (concurso_numero, numero_versao, criado_em, marcacoes, percentuais, apostas, custo,"
        " chance_todos, chance_todos_menos_um, acertos_esperados, resumo) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            concurso_numero, maior + 1, dt.datetime.now().isoformat(timespec="seconds"),
            json.dumps({str(k): v for k, v in marc.items()}),
            json.dumps({str(k): v for k, v in percentuais.items()}),
            apostas, apostas * PRECO_APOSTA,
            chance.get("chance_todos"), chance.get("chance_todos_menos_um_ou_mais"), chance.get("acertos_esperados"),
            json.dumps(resumo_da_analise(analise, marc), ensure_ascii=False),
        ),
    )
    return {"versao": versao_igual(conexao, concurso_numero, marc), "nova": True}


def ligar_ao_bilhete(conexao, versao_id: int, bilhete_id: int) -> None:
    conexao.execute("UPDATE versoes_palpite SET bilhete_id = ? WHERE id = ?", (bilhete_id, versao_id))


def resultados_do_concurso(conexao, concurso_numero: int) -> dict[int, str | None]:
    return {
        linha["id"]: linha["resultado"]
        for linha in conexao.execute("SELECT id, resultado FROM jogos WHERE concurso_numero = ?", (concurso_numero,))
    }


def aprendizado_de_todos_os_concursos(conexao) -> list[dict]:
    """`aprendizado_das_versoes` de cada concurso com mais de uma versão, resultado completo e bilhete apostado
    (rascunho e simulação não contam)."""
    from stats.bilhetes_salvos import SO_APOSTADOS  # import local: bilhetes_salvos não depende deste módulo

    apostados = {linha[0] for linha in conexao.execute(f"SELECT id FROM bilhetes WHERE {SO_APOSTADOS}")}
    concursos = [
        linha[0] for linha in conexao.execute(
            "SELECT concurso_numero FROM versoes_palpite GROUP BY concurso_numero HAVING COUNT(*) > 1 ORDER BY concurso_numero"
        )
    ]
    saida = []
    for numero in concursos:
        leitura = aprendizado_das_versoes(listar_versoes(conexao, numero), resultados_do_concurso(conexao, numero), apostados)
        if leitura:
            saida.append({"concurso_numero": numero, **leitura})
    return saida
