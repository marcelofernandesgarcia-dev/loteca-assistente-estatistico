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
        jogos_afetados = 0
        for outro in outros:
            for coluna in ("casa_id", "fora_id"):
                jogos_afetados += conexao.execute(
                    f"UPDATE jogos SET {coluna} = ? WHERE {coluna} = ?", (alvo["id"], outro["id"])
                ).rowcount
            conexao.execute("DELETE FROM mapa_cbf_participante WHERE participante_id = ? AND EXISTS "
                            "(SELECT 1 FROM mapa_cbf_participante WHERE participante_id = ?)", (outro["id"], alvo["id"]))
            conexao.execute("UPDATE mapa_cbf_participante SET participante_id = ? WHERE participante_id = ?", (alvo["id"], outro["id"]))
            conexao.execute("UPDATE fatores_externos SET participante_id = ? WHERE participante_id = ?", (alvo["id"], outro["id"]))
            conexao.execute("UPDATE OR IGNORE percentuais SET participante_id = ? WHERE participante_id = ?", (alvo["id"], outro["id"]))
            conexao.execute("DELETE FROM percentuais WHERE participante_id = ?", (outro["id"],))
            conexao.execute("DELETE FROM participantes WHERE id = ?", (outro["id"],))
        if outros or alvo["nome"] != canonico or alvo["tipo"] != tipo:
            conexao.execute("UPDATE participantes SET nome = ?, tipo = ? WHERE id = ?", (canonico, tipo, alvo["id"]))
        if outros:
            relatorio.append(
                {"canonico": canonico, "tipo": tipo, "uf": uf, "unidos": sorted({m["nome"] for m in membros}),
                 "jogos_afetados": jogos_afetados}
            )
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
