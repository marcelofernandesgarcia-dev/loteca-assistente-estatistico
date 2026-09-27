"""Extração de sinais estruturados a partir das notícias coletadas.

Puro (recebe a lista de notícias já coletada, não faz rede) -- testável com
notícias simuladas, sem depender de chamada real. Cada sinal é uma
categoria fechada (config.VARREDURA_PALAVRAS_CHAVE_PARA_SINAL), nunca texto
livre interpretado sem critério.
"""
import unicodedata

import config


def _normalizar(texto: str) -> str:
    sem_acento = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("ascii")
    return sem_acento.lower()


def extrair_sinais(noticias: list[dict]) -> list[dict]:
    """Retorna uma lista de {'sinal': str, 'evidencia': str, 'fonte': str},
    um por (palavra-chave, notícia) encontrada -- pode haver repetição de
    sinal se aparecer em mais de uma notícia (o cálculo do ajuste, em
    ajuste.py, decide como agregar)."""
    sinais = []
    for noticia in noticias:
        titulo_normalizado = _normalizar(noticia["titulo"])
        for palavra, tipo_sinal in config.VARREDURA_PALAVRAS_CHAVE_PARA_SINAL.items():
            if _normalizar(palavra) in titulo_normalizado:
                sinais.append(
                    {
                        "sinal": tipo_sinal,
                        "evidencia": noticia["titulo"],
                        "fonte": noticia.get("fonte") or noticia.get("url", ""),
                    }
                )
    return sinais
