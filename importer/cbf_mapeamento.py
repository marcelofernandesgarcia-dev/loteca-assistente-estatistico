"""Pareia participantes da Loteca com times da CBF.

Regra: só clubes brasileiros (a Loteca informa a UF deles); dentro da mesma
UF, os nomes se comparam por conjunto de palavras (sem acento, sem "SAF"/"FC"
etc.) e o par vale se um conjunto estiver contido no outro. Se mais de um
time da CBF servir, NÃO pareia (fica pendente para revisão) -- melhor sem par
do que com o time errado (há Botafogo em SP e no RJ, Atlético em MG e GO...).
"""
import re
import unicodedata

import config


def tokens(nome: str) -> frozenset[str]:
    sem_acento = unicodedata.normalize("NFKD", nome).encode("ascii", "ignore").decode("ascii").upper()
    palavras = re.findall(r"[A-Z0-9]+", sem_acento)
    return frozenset(p for p in palavras if p not in config.CBF_TOKENS_IGNORADOS)


def _compativeis(a: frozenset[str], b: frozenset[str]) -> bool:
    return bool(a) and bool(b) and (a <= b or b <= a)


def parear(conexao) -> dict:
    """Recalcula `mapa_cbf_participante`. Retorna contagem de pareados e a
    lista de clubes brasileiros sem par único (para revisão manual)."""
    times_cbf = conexao.execute("SELECT cod_time, nome, uf FROM cbf_times WHERE uf IS NOT NULL").fetchall()
    clubes = conexao.execute(
        "SELECT id, nome, pais_ou_uf FROM participantes WHERE tipo = 'clube' AND length(pais_ou_uf) = 2"
    ).fetchall()

    pareados, pendentes = 0, []
    for clube in clubes:
        alvo = tokens(clube["nome"])
        candidatos = [
            t for t in times_cbf if t["uf"] == clube["pais_ou_uf"] and _compativeis(alvo, tokens(t["nome"]))
        ]
        if len(candidatos) == 1:
            conexao.execute(
                "INSERT INTO mapa_cbf_participante (participante_id, cod_time, metodo) VALUES (?, ?, 'uf+nome') "
                "ON CONFLICT(participante_id) DO UPDATE SET cod_time=excluded.cod_time, metodo=excluded.metodo",
                (clube["id"], candidatos[0]["cod_time"]),
            )
            pareados += 1
        elif len(candidatos) > 1:
            pendentes.append(f"{clube['nome']}/{clube['pais_ou_uf']}: {len(candidatos)} candidatos")
    return {"pareados": pareados, "ambiguos": pendentes}
