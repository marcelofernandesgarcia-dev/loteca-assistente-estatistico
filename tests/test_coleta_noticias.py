import externo.coleta as coleta

RSS = b"""<?xml version="1.0"?><rss><channel>
<item><title>Atacante lesionado desfalca o time</title><link>http://x/1</link><source>ge</source></item>
<item><title>Time confirma treino aberto</title><link>http://x/2</link><source>ESPN Brasil</source></item>
</channel></rss>"""


class _Resposta:
    content = RSS

    def raise_for_status(self):
        pass


def test_busca_geral_mais_fontes_prioritarias_com_janela(monkeypatch):
    consultas = []

    def falso_get(url, **_):
        consultas.append(url)
        return _Resposta()

    monkeypatch.setattr(coleta.requests, "get", falso_get)
    monkeypatch.setattr(coleta.time, "sleep", lambda _: None)
    noticias = coleta.buscar_noticias("TIME ALFA")

    assert len(consultas) == 1 + len(coleta.config.NOTICIAS_FONTES_PRIORITARIAS)
    assert all("when%3A" in c for c in consultas)  # sempre limitado à janela recente
    assert any("site%3Age.globo.com" in c for c in consultas)
    assert any("site%3Aespn.com.br" in c for c in consultas)
    # as mesmas manchetes repetidas nas 3 consultas viram só 2 itens únicos
    assert [n["titulo"] for n in noticias] == ["Atacante lesionado desfalca o time", "Time confirma treino aberto"]
    assert noticias[0]["prioritaria"] is False  # veio da busca geral (primeira ocorrência)


def test_falha_de_rede_devolve_lista_vazia_sem_quebrar(monkeypatch):
    def falha(*_a, **_k):
        raise coleta.requests.ConnectionError("sem rede")

    monkeypatch.setattr(coleta.requests, "get", falha)
    monkeypatch.setattr(coleta.time, "sleep", lambda _: None)
    assert coleta.buscar_noticias("TIME ALFA") == []
