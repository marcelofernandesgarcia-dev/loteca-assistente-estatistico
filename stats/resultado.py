"""Regras de negócio puras sobre resultado e classificação de participante.

Sem dependência de framework, sem I/O -- só matemática e as regras oficiais
da Loteca (ver docs/manual-produtos-caixa-v21.md, item 10, e
docs/grade-real-e-prazos-confirmados.md).
"""
import csv
import re
import unicodedata
from functools import lru_cache

import config


def calcular_resultado(gols_casa: int, gols_fora: int) -> str:
    """Coluna vencedora (1/X/2) a partir do placar. A API da CAIXA nunca
    devolve isso pronto (campo `resultado` sempre `null`) -- é sempre
    calculado por nós a partir do placar oficial já apurado.
    """
    if gols_casa is None or gols_fora is None:
        raise ValueError("Placar incompleto -- não é possível calcular o resultado")
    if gols_casa > gols_fora:
        return "1"
    if gols_casa < gols_fora:
        return "2"
    return "X"


def _normalizar(nome: str) -> str:
    sem_acento = unicodedata.normalize("NFKD", nome).encode("ascii", "ignore").decode("ascii")
    return sem_acento.strip().upper()


_SUFIXO_CODIGO = re.compile(r"/[A-Za-z0-9]{2,4}$")


def limpar_nome(nome: str) -> str:
    """A API às vezes anexa um código ao nome ('SERVIA/SER', 'ESCOCIA/SCT').
    Sem tirar isso, a seleção não bate com a lista de seleções e o mesmo
    time vira participantes diferentes conforme o endpoint."""
    return " ".join(_SUFIXO_CODIGO.sub("", nome.strip()).split())


@lru_cache(maxsize=4)
def carregar_apelidos(caminho: str | None = None) -> dict:
    """{(variante, UF ou None): nome canônico}, do arquivo data/apelidos-participantes.csv.
    Une grafias diferentes do MESMO time na CAIXA ao longo dos anos (ex.: 'S. PAULO'
    e 'SAO PAULO'); cada linha traz a justificativa e só vale para a UF indicada."""
    arquivo = caminho or str(config.APELIDOS_PARTICIPANTES_CSV)
    apelidos = {}
    try:
        with open(arquivo, encoding="utf-8") as f:
            for linha in csv.DictReader((l for l in f if not l.startswith("#")), delimiter=";"):
                chave = (limpar_nome(linha["variante"]).upper(), (linha["uf"] or "").strip().upper() or None)
                apelidos[chave] = limpar_nome(linha["canonico"]).upper()
    except FileNotFoundError:
        return {}
    return apelidos


def identidade_participante(nome: str, sigla_uf: str | None) -> dict:
    """Nome limpo, tipo (clube/seleção) e o que identifica o participante:
    só a UF de clube brasileiro. Código de país NÃO entra na identidade -- o
    endpoint da programação não o preenche e o histórico sim, o que
    quebraria a continuidade das estatísticas do mesmo time."""
    uf = (sigla_uf or "").strip().upper() or None
    nome_limpo = limpar_nome(nome)
    nome_limpo = carregar_apelidos().get((nome_limpo.upper(), uf), nome_limpo)
    return {"nome": nome_limpo, "tipo": classificar_participante(nome_limpo, uf), "uf": uf}


def classificar_participante(nome: str, sigla_uf: str | None) -> str:
    """'clube' ou 'selecao'. Time brasileiro sempre tem UF preenchida (é
    sempre clube). Sem UF, checamos se o nome está na lista de seleções
    nacionais conhecidas (config.NOMES_SELECOES_NACIONAIS); senão, é clube
    estrangeiro (ex.: Barcelona, Real Madrid -- mesma ausência de UF que uma
    seleção, mas não são seleção).
    """
    if sigla_uf:
        return "clube"
    if _normalizar(nome) in config.NOMES_SELECOES_NACIONAIS:
        return "selecao"
    return "clube"
