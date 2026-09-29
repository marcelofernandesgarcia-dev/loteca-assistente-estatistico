"""Junta participantes que são o mesmo time com grafias diferentes.

Duas fontes de unificação, ambas explícitas:
- normalização automática do nome (espaços repetidos, código de país no fim);
- apelidos de `data/apelidos-participantes.csv` (variante + UF -> nome canônico).

Nada é unido por semelhança de nome: `candidatos_a_duplicidade` só LISTA pares
parecidos para revisão humana.
"""
import difflib
from collections import defaultdict

from stats.resultado import identidade_participante


def _chave_canonica(nome: str, uf: str | None) -> tuple[str, str, str | None]:
    identidade = identidade_participante(nome, uf)
    return identidade["nome"], identidade["tipo"], identidade["uf"]


def _absorver(conexao, alvo_id: int, outro_id: int) -> int:
    """Move tudo do participante `outro_id` para `alvo_id` e apaga `outro_id`.
    Retorna quantas linhas de `jogos` foram afetadas."""
    jogos_afetados = 0
    for coluna in ("casa_id", "fora_id"):
        jogos_afetados += conexao.execute(
            f"UPDATE jogos SET {coluna} = ? WHERE {coluna} = ?", (alvo_id, outro_id)
        ).rowcount
    conexao.execute(
        "DELETE FROM mapa_cbf_participante WHERE participante_id = ? AND EXISTS "
        "(SELECT 1 FROM mapa_cbf_participante WHERE participante_id = ?)", (outro_id, alvo_id),
    )
    conexao.execute("UPDATE mapa_cbf_participante SET participante_id = ? WHERE participante_id = ?", (alvo_id, outro_id))
    conexao.execute("UPDATE fatores_externos SET participante_id = ? WHERE participante_id = ?", (alvo_id, outro_id))
    conexao.execute("UPDATE OR IGNORE percentuais SET participante_id = ? WHERE participante_id = ?", (alvo_id, outro_id))
    conexao.execute("DELETE FROM percentuais WHERE participante_id = ?", (outro_id,))
    conexao.execute("DELETE FROM participantes WHERE id = ?", (outro_id,))
    return jogos_afetados


def unificar(conexao) -> list[dict]:
    """Aplica a unificação no banco. Idempotente. Retorna o que foi unido:
    [{'canonico', 'tipo', 'uf', 'unidos': [nomes antigos], 'jogos_afetados': n}]."""
    grupos = defaultdict(list)
    for linha in conexao.execute("SELECT id, nome, tipo, pais_ou_uf FROM participantes ORDER BY id"):
        grupos[_chave_canonica(linha["nome"], linha["pais_ou_uf"])].append(dict(linha))

    relatorio = []
    for (canonico, tipo, uf), membros in grupos.items():
        alvo = next((m for m in membros if m["nome"] == canonico), membros[0])
        outros = [m for m in membros if m["id"] != alvo["id"]]
        jogos_afetados = sum(_absorver(conexao, alvo["id"], outro["id"]) for outro in outros)
        if outros or alvo["nome"] != canonico or alvo["tipo"] != tipo:
            conexao.execute("UPDATE participantes SET nome = ?, tipo = ? WHERE id = ?", (canonico, tipo, alvo["id"]))
        if outros:
            relatorio.append(
                {"canonico": canonico, "tipo": tipo, "uf": uf, "unidos": sorted({m["nome"] for m in membros}),
                 "jogos_afetados": jogos_afetados}
            )
    return relatorio


def unificar_uf_ausente(conexao) -> list[dict]:
    """Junta um participante SEM UF a outro do MESMO nome que TEM UF -- só
    quando existe exatamente um UF não nulo para aquele nome, ou seja, não há
    ambiguidade sobre qual clube é (times brasileiros sempre têm UF; UF nula
    é lacuna de importação, não uma entidade diferente).

    Nomes homônimos com UFs DIFERENTES de verdade (ex.: 'AMERICA' em MG, RN,
    PE...) nunca são tocados aqui -- ficam de fora mesmo com alguma linha sem
    UF, porque não dá para saber a qual dos vários pertence. Use
    `candidatos_a_duplicidade` para revisar esses manualmente."""
    grupos = defaultdict(list)
    for linha in conexao.execute("SELECT id, nome, pais_ou_uf FROM participantes WHERE tipo = 'clube'"):
        grupos[linha["nome"]].append(dict(linha))

    relatorio = []
    for nome, membros in grupos.items():
        ufs_distintos = {m["pais_ou_uf"] for m in membros if m["pais_ou_uf"]}
        sem_uf = [m for m in membros if not m["pais_ou_uf"]]
        if len(ufs_distintos) != 1 or not sem_uf:
            continue
        uf = next(iter(ufs_distintos))
        alvo = next(m for m in membros if m["pais_ou_uf"] == uf)
        jogos_afetados = sum(_absorver(conexao, alvo["id"], outro["id"]) for outro in sem_uf)
        relatorio.append({"nome": nome, "uf": uf, "linhas_sem_uf_unidas": len(sem_uf), "jogos_afetados": jogos_afetados})
    return relatorio


def candidatos_a_duplicidade(conexao, similaridade_minima: float = 0.8) -> list[dict]:
    """Pares de clubes da MESMA UF com nomes parecidos que nunca aparecem juntos
    no mesmo concurso (se aparecem juntos, são times diferentes). Só para revisão."""
    participantes = conexao.execute(
        "SELECT id, nome, pais_ou_uf FROM participantes WHERE tipo = 'clube' AND pais_ou_uf IS NOT NULL ORDER BY nome"
    ).fetchall()
    jogos = defaultdict(int)
    for linha in conexao.execute("SELECT casa_id, fora_id FROM jogos"):
        jogos[linha["casa_id"]] += 1
        jogos[linha["fora_id"]] += 1
    juntos = {
        (min(l["casa_id"], l["fora_id"]), max(l["casa_id"], l["fora_id"]))
        for l in conexao.execute("SELECT casa_id, fora_id FROM jogos")
    }
    concursos = defaultdict(set)
    for linha in conexao.execute("SELECT concurso_numero, casa_id, fora_id FROM jogos"):
        concursos[linha["concurso_numero"]].update((linha["casa_id"], linha["fora_id"]))
    no_mesmo_concurso = {
        (min(a, b), max(a, b)) for ids in concursos.values() for a in ids for b in ids if a < b
    }
    por_uf = defaultdict(list)
    for p in participantes:
        por_uf[p["pais_ou_uf"]].append(p)
    candidatos = []
    for uf, lista in por_uf.items():
        for i, a in enumerate(lista):
            for b in lista[i + 1:]:
                razao = difflib.SequenceMatcher(None, a["nome"], b["nome"]).ratio()
                if razao >= similaridade_minima and (min(a["id"], b["id"]), max(a["id"], b["id"])) not in no_mesmo_concurso:
                    candidatos.append(
                        {"uf": uf, "a": a["nome"], "b": b["nome"], "jogos_a": jogos[a["id"]], "jogos_b": jogos[b["id"]],
                         "similaridade": round(razao, 2)}
                    )
    return sorted(candidatos, key=lambda x: (-x["similaridade"], x["uf"]))
