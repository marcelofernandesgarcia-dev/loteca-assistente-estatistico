"""Retrato do que o app mostrava ao salvar um bilhete (item A1 do plano v2, aprovado em 07/10/2026).

Guarda, por jogo, o modelo e a origem do percentual, as três camadas do percentual (modelo, base
corrigida e final com notícias), a calibração, as notícias usadas, a cobertura, a complexidade, o ano
em curso e a sugestão do app; e, do bilhete, a versão do app e as chaves de configuração que mudam o
cálculo. Serve para a revisão pós-jogo mostrar exatamente o que você viu, e para comparar modelos.

Imutável: a tabela `retratos_bilhete` tem gatilhos que recusam UPDATE e DELETE. Uma correção é um
bilhete (ou versão) novo, nunca a reescrita do retrato. Só marcação, números e manchetes públicas;
nenhum dado pessoal.
"""
import datetime as dt
import json
import logging

import config

logger = logging.getLogger(__name__)


def versao_do_app() -> str:
    """Commit do repositório em uso (12 caracteres), lido de .git sem chamar programa externo.
    'desconhecida' quando não dá para ler (cópia sem .git, por exemplo)."""
    git = config.BASE_DIR / ".git"
    try:
        cabeca = (git / "HEAD").read_text(encoding="utf-8").strip()
        if not cabeca.startswith("ref: "):
            return cabeca[:12]
        referencia = cabeca[5:]
        arquivo = git / referencia
        if arquivo.exists():
            return arquivo.read_text(encoding="utf-8").strip()[:12]
        for linha in (git / "packed-refs").read_text(encoding="utf-8").splitlines():
            if linha.endswith(" " + referencia):
                return linha.split()[0][:12]
    except OSError as erro:
        logger.warning("Versão do app não lida de %s: %s", git, erro)
    return "desconhecida"


def retrato_geral(agora: dt.datetime | None = None) -> dict:
    return {
        "salvo_em": (agora or dt.datetime.now()).isoformat(timespec="seconds"),
        "versao_app": versao_do_app(),
        "calibracao_ativa": config.CALIBRACAO_ATIVA,
        "modelo_selecoes": config.MODELO_SELECOES,
        "versao_regras_noticias": config.VARREDURA_VERSAO_REGRAS,
        "teto_noticias_pontos": config.AJUSTE_EXTERNO_TETO_PONTOS,
    }


def _noticia_do_lado(ajuste: dict | None) -> dict | None:
    if not ajuste:
        return None
    return {"ajuste": ajuste["ajuste"], "resumo": ajuste["resumo"], "lido_em": ajuste["coletado_em"],
            "evidencias": ajuste.get("evidencias") or []}


def retrato_do_jogo(jogo: dict, calculo: dict, ajustes: dict[int, dict], cobertura: dict, complexidade: dict | None,
                    ano_casa: str | None, ano_fora: str | None, sugestao: list[str], marcacao: list[str]) -> dict:
    """`jogo`: num_jogo, casa, casa_id, fora, fora_id. `calculo`: de externo.percentual_final.percentuais_do_jogo.
    `ajustes`: de ajustes_do_concurso (para guardar também a leitura sem sinal). `ano_casa`/`ano_fora`:
    frase do ano em curso (stats.ano_em_curso.frase_do_lado)."""
    calibracao = calculo["calibracao"]
    return {
        "num_jogo": jogo["num_jogo"], "casa": jogo["casa"], "fora": jogo["fora"],
        "origem": calibracao["origem"],
        "percentual": {"modelo": calculo["original"], "base": calculo["historico"], "final": calculo["final"],
                       "anterior": calculo.get("anterior")},
        "calibracao": {k: calibracao[k] for k in ("aplicada", "expoente", "mistura", "motivo")},
        "noticias": {"casa": _noticia_do_lado(ajustes.get(jogo["casa_id"])),
                     "fora": _noticia_do_lado(ajustes.get(jogo["fora_id"])),
                     "deslocamento": calculo["deslocamento"]},
        "cobertura": cobertura,
        "complexidade": complexidade,
        "ano_em_curso": {"casa": ano_casa, "fora": ano_fora},
        "sugestao_do_app": sugestao,
        "marcacao": marcacao,
    }


def gravar_retrato(conexao, bilhete_id: int, geral: dict, por_jogo: dict[int, dict]) -> None:
    """`por_jogo`: {jogo_id: retrato_do_jogo}. O retrato geral fica na linha com jogo_id vazio."""
    criado_em = geral["salvo_em"]
    conexao.execute(
        "INSERT INTO retratos_bilhete (bilhete_id, jogo_id, criado_em, conteudo) VALUES (?, NULL, ?, ?)",
        (bilhete_id, criado_em, json.dumps(geral, ensure_ascii=False)),
    )
    for jogo_id, retrato in por_jogo.items():
        conexao.execute(
            "INSERT INTO retratos_bilhete (bilhete_id, jogo_id, criado_em, conteudo) VALUES (?, ?, ?, ?)",
            (bilhete_id, jogo_id, criado_em, json.dumps(retrato, ensure_ascii=False)),
        )


def retrato_do_bilhete(conexao, bilhete_id: int) -> dict | None:
    """{'geral': {...}, 'jogos': [retrato por jogo, em ordem de num_jogo]}, ou None para bilhete salvo antes
    de 07/10/2026 (sem retrato)."""
    linhas = conexao.execute(
        "SELECT jogo_id, conteudo FROM retratos_bilhete WHERE bilhete_id = ? ORDER BY id", (bilhete_id,)
    ).fetchall()
    if not linhas:
        return None
    geral, jogos = None, []
    for linha in linhas:
        conteudo = json.loads(linha["conteudo"])
        if linha["jogo_id"] is None:
            geral = conteudo
        else:
            jogos.append(conteudo)
    return {"geral": geral, "jogos": sorted(jogos, key=lambda j: j["num_jogo"])}
