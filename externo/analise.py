"""Extração de sinais estruturados a partir das notícias coletadas.

Puro (recebe a lista de notícias já coletada, não faz rede) -- testável com
notícias simuladas, sem depender de chamada real. Cada sinal é uma categoria
fechada (config.VARREDURA_PALAVRAS_CHAVE_PARA_SINAL), nunca texto livre
interpretado sem critério.

Duas barreiras contra falso positivo, adicionadas depois de revisão externa
(ver docs/plano-fase3-melhorias.md, item C2):
1. o nome do participante precisa aparecer no título -- corta notícia do
   adversário ou de outro assunto que só bateu na busca por coincidência;
2. título com expressão de negação/recuperação (config.VARREDURA_PALAVRAS_DE_NEGACAO)
   é descartado inteiro -- "sem lesão" não vira sinal de lesão.
"""
import unicodedata

import config

_CONECTIVOS = {
    "de", "da", "do", "das", "dos", "e", "fc", "sc", "ec", "afc", "saf",
    # palavras genéricas de futebol -- sozinhas, não identificam qual time é
    "time", "clube", "esporte", "esportivo", "futebol", "equipe", "jogo", "sport",
}


def _normalizar(texto: str) -> str:
    sem_acento = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("ascii")
    return sem_acento.lower()


def _menciona_participante(titulo_normalizado: str, participante_normalizado: str) -> bool:
    """Ao menos um token relevante do nome do participante precisa aparecer no
    título. Tokens curtos e conectivos são ignorados para não exigir demais de
    nomes compostos ('CLUBE DE REGATAS X') -- mas siglas curtas (ex. 'CRB')
    usam o nome inteiro, já que não sobra token longo para checar."""
    tokens = [t for t in participante_normalizado.split() if len(t) >= 4 and t not in _CONECTIVOS]
    if not tokens:
        return participante_normalizado in titulo_normalizado
    return any(token in titulo_normalizado for token in tokens)


def extrair_sinais(noticias: list[dict], participante_nome: str | None = None) -> list[dict]:
    """Retorna uma lista de {'sinal': str, 'evidencia': str, 'fonte': str, 'url': str,
    'publicado_em': str}, um por (palavra-chave, notícia) encontrada -- pode haver
    repetição de sinal se aparecer em mais de uma notícia (o cálculo do ajuste, em
    ajuste.py, decide como agregar). `participante_nome`: quando informado, notícia
    cujo título não menciona o participante é ignorada (barreira 1); sempre
    recomendado -- só fica opcional para não quebrar chamada antiga sem esse dado."""
    participante_normalizado = _normalizar(participante_nome) if participante_nome else None
    negacoes_normalizadas = [_normalizar(frase) for frase in config.VARREDURA_PALAVRAS_DE_NEGACAO]

    sinais = []
    for noticia in noticias:
        titulo_normalizado = _normalizar(noticia["titulo"])
        if participante_normalizado and not _menciona_participante(titulo_normalizado, participante_normalizado):
            continue
        if any(negacao in titulo_normalizado for negacao in negacoes_normalizadas):
            continue
        for palavra, tipo_sinal in config.VARREDURA_PALAVRAS_CHAVE_PARA_SINAL.items():
            if _normalizar(palavra) in titulo_normalizado:
                sinais.append(
                    {
                        "sinal": tipo_sinal,
                        "evidencia": noticia["titulo"],
                        "fonte": noticia.get("fonte") or noticia.get("url", ""),
                        "url": noticia.get("url", ""),
                        "publicado_em": noticia.get("publicado_em", ""),
                    }
                )
    return sinais
