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


def _compativeis(loteca: frozenset[str], cbf: frozenset[str]) -> bool:
    """Toda palavra do nome da Loteca precisa estar no nome da CBF (a Loteca abrevia: "SPORT" ->
    "Sport Recife"). O sentido contrário NÃO vale: palavra a mais na Loteca indica outro time
    ("PALMEIRAS B", time reserva; "VITORIA CONQUISTA", "GREMIO MARINGA"), achado ao repetir o
    pareamento com as temporadas de 2019 a 2026 em 07/10/2026."""
    return bool(loteca) and bool(cbf) and loteca <= cbf


_UF_NO_LOCAL = re.compile(r"-\s*([A-Z]{2})\s*$")


def inferir_uf_pelo_estadio(conexao) -> list[dict]:
    """Preenche a UF dos times da CBF que vieram só das páginas de jogos (sem tabela de classificação, como os
    eliminados na 1ª fase da Série C), pelo estádio dos jogos em casa ("Centenário - Caxias do Sul - RS").
    Só com config.CBF_UF_ESTADIO_MINIMO_JOGOS jogos em casa ou mais e todos no mesmo estado; sem unanimidade,
    a UF fica vazia (melhor sem par do que com o time errado). Marca uf_origem = 'estadio'. Devolve o que
    preencheu."""
    preenchidos = []
    for time in conexao.execute("SELECT cod_time, nome FROM cbf_times WHERE uf IS NULL").fetchall():
        ufs = set()
        jogos = 0
        for (local,) in conexao.execute(
            "SELECT local FROM cbf_partidas WHERE mandante_id = ? AND local IS NOT NULL", (time["cod_time"],)
        ):
            achado = _UF_NO_LOCAL.search(local.strip())
            if achado:
                ufs.add(achado.group(1))
                jogos += 1
        if jogos >= config.CBF_UF_ESTADIO_MINIMO_JOGOS and len(ufs) == 1:
            uf = ufs.pop()
            conexao.execute("UPDATE cbf_times SET uf = ?, uf_origem = 'estadio' WHERE cod_time = ?", (uf, time["cod_time"]))
            preenchidos.append({"cod_time": time["cod_time"], "nome": time["nome"], "uf": uf, "jogos": jogos})
    return preenchidos


def parear(conexao, equivalentes: dict[int, list[int]] | None = None) -> dict:
    """Recalcula `mapa_cbf_participante`. Retorna contagem de pareados e a
    lista de clubes brasileiros sem par único (para revisão manual). Um par
    automático que a regra deixou de sustentar (o time da CBF não é mais
    candidato) é removido; par ambíguo já existente fica como está.

    `equivalentes` ({código atual: [anteriores]}, padrão: a tabela validada de
    stats.cbf.codigos_equivalentes): dois códigos do MESMO clube contam como um
    candidato só, o atual. Sem isso, um clube que trocou de código na CBF (ex.:
    Bahia, Atlético Mineiro) fica sempre "ambíguo"."""
    if equivalentes is None:
        from stats.cbf import codigos_equivalentes

        equivalentes = codigos_equivalentes()
    ufs_deduzidas = inferir_uf_pelo_estadio(conexao)
    atual_de = {anterior: atual for atual, anteriores in equivalentes.items() for anterior in anteriores}
    times_cbf = conexao.execute("SELECT cod_time, nome, uf FROM cbf_times WHERE uf IS NOT NULL").fetchall()
    clubes = conexao.execute(
        "SELECT id, nome, pais_ou_uf FROM participantes WHERE tipo = 'clube' AND length(pais_ou_uf) = 2"
    ).fetchall()

    atuais = {
        linha["participante_id"]: linha["cod_time"]
        for linha in conexao.execute("SELECT participante_id, cod_time FROM mapa_cbf_participante WHERE metodo = 'uf+nome'")
    }
    pareados, pendentes, removidos = 0, [], []
    for clube in clubes:
        alvo = tokens(clube["nome"])
        brutos = set()
        excluido = (clube["nome"].strip().upper(), clube["pais_ou_uf"]) in config.CBF_PAREAMENTO_EXCLUIDO
        if not excluido and not clube["nome"].upper().startswith(config.LOTECA_PREFIXOS_OUTRA_CATEGORIA):
            brutos = {
                t["cod_time"] for t in times_cbf
                if t["uf"] == clube["pais_ou_uf"] and _compativeis(alvo, tokens(t["nome"]))
            }
        candidatos = sorted({atual_de.get(cod, cod) for cod in brutos})
        if clube["id"] in atuais and atuais[clube["id"]] not in brutos | set(candidatos):
            conexao.execute("DELETE FROM mapa_cbf_participante WHERE participante_id = ?", (clube["id"],))
            removidos.append(f"{clube['nome']}/{clube['pais_ou_uf']}")
        if len(candidatos) == 1:
            conexao.execute(
                "INSERT INTO mapa_cbf_participante (participante_id, cod_time, metodo) VALUES (?, ?, 'uf+nome') "
                "ON CONFLICT(participante_id) DO UPDATE SET cod_time=excluded.cod_time, metodo=excluded.metodo",
                (clube["id"], candidatos[0]),
            )
            pareados += 1
        elif len(candidatos) > 1:
            pendentes.append(f"{clube['nome']}/{clube['pais_ou_uf']}: {len(candidatos)} candidatos")
    return {"pareados": pareados, "ambiguos": pendentes, "removidos": removidos, "ufs_deduzidas": ufs_deduzidas}
