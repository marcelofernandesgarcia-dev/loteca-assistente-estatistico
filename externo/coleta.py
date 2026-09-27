"""Coleta de notícias recentes por participante, via RSS público do Google
Notícias (sem chave de API -- decisão de implementação registrada no plano
do app: um modelo de linguagem real fica para uma versão futura, se o
usuário decidir pagar por uma chave de API; a v1 usa palavra-chave sobre
notícia real, auditável e sem custo de terceiro).
"""
import xml.etree.ElementTree as ET
from urllib.parse import quote

import requests

import config

_RSS_BASE = "https://news.google.com/rss/search"


def buscar_noticias(participante_nome: str, max_itens: int = 8) -> list[dict]:
    query = quote(f'"{participante_nome}" futebol')
    url = f"{_RSS_BASE}?q={query}&hl=pt-BR&gl=BR&ceid=BR:pt-419"
    try:
        resposta = requests.get(
            url, headers={"User-Agent": config.CAIXA_USER_AGENT}, timeout=config.CAIXA_REQUEST_TIMEOUT_SEGUNDOS
        )
        resposta.raise_for_status()
    except requests.RequestException:
        return []

    try:
        raiz = ET.fromstring(resposta.content)
    except ET.ParseError:
        return []

    itens = []
    for item in raiz.findall("./channel/item")[:max_itens]:
        titulo = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        fonte_elem = item.find("source")
        fonte = fonte_elem.text if fonte_elem is not None else ""
        itens.append({"titulo": titulo, "url": link, "fonte": fonte})
    return itens
