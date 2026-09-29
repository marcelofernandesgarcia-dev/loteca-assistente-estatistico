"""Coleta de manchetes recentes por participante, via RSS público do Google
Notícias (sem chave de API). Além da busca geral, consulta os veículos
prioritários indicados pelo usuário (config.NOTICIAS_FONTES_PRIORITARIAS:
ge/Globo-SporTV e ESPN Brasil) com `site:`, e limita tudo à janela recente
(config.NOTICIAS_JANELA_DIAS) para que uma lesão antiga não vire sinal falso.

Só manchete, veículo e link são lidos -- o texto das matérias não é copiado.
Canais de TV (Globo, Premiere, BandSports) e de vídeo (YouTube) não são
fontes de dado aqui; ver docs/fontes-de-noticias.md.
"""
import time
import xml.etree.ElementTree as ET
from urllib.parse import quote

import requests

import config

_RSS_BASE = "https://news.google.com/rss/search"


def _buscar_rss(consulta: str, max_itens: int, prioritaria: bool) -> list[dict]:
    url = f"{_RSS_BASE}?q={quote(consulta)}&hl=pt-BR&gl=BR&ceid=BR:pt-419"
    try:
        resposta = requests.get(
            url, headers={"User-Agent": config.CAIXA_USER_AGENT}, timeout=config.CAIXA_REQUEST_TIMEOUT_SEGUNDOS
        )
        resposta.raise_for_status()
        raiz = ET.fromstring(resposta.content)
    except (requests.RequestException, ET.ParseError):
        return []

    itens = []
    for item in raiz.findall("./channel/item")[:max_itens]:
        fonte_elem = item.find("source")
        itens.append(
            {
                "titulo": (item.findtext("title") or "").strip(),
                "url": (item.findtext("link") or "").strip(),
                "fonte": fonte_elem.text if fonte_elem is not None else "",
                "publicado_em": (item.findtext("pubDate") or "").strip(),
                "prioritaria": prioritaria,
            }
        )
    return itens


def buscar_noticias(participante_nome: str, max_itens: int = 8) -> list[dict]:
    janela = f"when:{config.NOTICIAS_JANELA_DIAS}d"
    base = f'"{participante_nome}" futebol {janela}'

    resultados = _buscar_rss(base, max_itens, prioritaria=False)
    for dominio, _rotulo in config.NOTICIAS_FONTES_PRIORITARIAS:
        time.sleep(config.NOTICIAS_INTERVALO_SEGUNDOS)
        resultados += _buscar_rss(f"{base} site:{dominio}", config.NOTICIAS_MAX_ITENS_POR_FONTE, prioritaria=True)

    vistos, unicos = set(), []
    for noticia in resultados:
        chave = noticia["titulo"].lower()
        if noticia["titulo"] and chave not in vistos:
            vistos.add(chave)
            unicos.append(noticia)
    return unicos
