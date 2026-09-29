"""Contexto de tabela (zona de classificação) por posição, segundo o
Regulamento Específico da Competição (REC) de cada série, ano a ano -- nunca
por suposição. Fontes lidas em 29/09/2026:
docs/fontes-oficiais/REC_Brasileiro_Serie_A_2026.pdf (Capítulo 2, Art. 6-8) e
REC_Brasileiro_Serie_B_2026.pdf (Capítulo 2, Art. 5, e Capítulo 4, Art. 13).

Cadastro em config.ZONAS_CBF, por (serie, ano). Série/ano sem cadastro não
recebe selo -- este módulo nunca inventa zona.
"""
import config

NOMES_ZONA = {
    "libertadores_grupos": "Libertadores (fase de grupos)",
    "libertadores_preliminar": "Libertadores (fase preliminar)",
    "sul_americana": "Sul-Americana",
    "acesso_direto": "Acesso direto à Série A",
    "playoff_acesso": "Playoff de acesso à Série A",
    "rebaixamento": "Rebaixamento",
    "meio_de_tabela": "Meio de tabela",
}


def zona_da_posicao(serie: str, ano: int, posicao: int | None) -> str | None:
    """Nome da zona (chave de NOMES_ZONA) para a posição, ou None se a série/ano
    não tem zonas cadastradas ou a posição não é conhecida. 'meio_de_tabela' é
    devolvido quando há cadastro mas a posição não cai em nenhuma zona listada."""
    zonas = config.ZONAS_CBF.get((serie, ano))
    if not zonas or posicao is None:
        return None
    for nome, intervalo in zonas.items():
        if posicao in intervalo:
            return nome
    return "meio_de_tabela"


def selo_da_posicao(serie: str, ano: int, posicao: int | None) -> str | None:
    """Texto curto pronto para exibir (ex.: 'Libertadores (fase de grupos)')."""
    zona = zona_da_posicao(serie, ano, posicao)
    return NOMES_ZONA.get(zona) if zona else None


def contexto_da_classificacao(serie: str, ano: int, classificacao: list[dict]) -> dict[int, dict] | None:
    """`classificacao`: lista com {'cod_time', 'posicao', 'pontos'}, de qualquer
    tamanho, não necessariamente ordenada. Retorna {cod_time: {...}} com a zona e
    a distância em pontos até a fronteira de zona mais próxima acima e abaixo
    (olhando só o vizinho imediato na tabela -- é aritmética simples sobre a
    classificação atual, não uma conta de quem ainda pode alcançar matematicamente).
    None se a série/ano não tem zonas cadastradas."""
    if not config.ZONAS_CBF.get((serie, ano)):
        return None
    ordenada = sorted(classificacao, key=lambda linha: linha["posicao"])
    zonas_por_time = {
        linha["cod_time"]: zona_da_posicao(serie, ano, linha["posicao"]) for linha in ordenada
    }
    resultado = {}
    for i, linha in enumerate(ordenada):
        cod, zona = linha["cod_time"], zonas_por_time[linha["cod_time"]]
        vizinho_acima = ordenada[i - 1] if i > 0 else None
        vizinho_abaixo = ordenada[i + 1] if i + 1 < len(ordenada) else None
        pontos_para_subir = None
        if vizinho_acima is not None and zonas_por_time[vizinho_acima["cod_time"]] != zona:
            pontos_para_subir = vizinho_acima["pontos"] - linha["pontos"]
        pontos_para_cair = None
        if vizinho_abaixo is not None and zonas_por_time[vizinho_abaixo["cod_time"]] != zona:
            pontos_para_cair = linha["pontos"] - vizinho_abaixo["pontos"]
        resultado[cod] = {
            "posicao": linha["posicao"],
            "pontos": linha["pontos"],
            "zona": zona,
            "rotulo": NOMES_ZONA.get(zona, zona),
            "pontos_para_subir_de_zona": pontos_para_subir,
            "pontos_para_cair_de_zona": pontos_para_cair,
        }
    return resultado
