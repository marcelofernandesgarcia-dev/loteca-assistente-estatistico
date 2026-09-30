"""Leitura das páginas públicas da CBF (não há API documentada).

As páginas do site são renderizadas no servidor (Next.js) e trazem os dados
embutidos no HTML, no fluxo `self.__next_f.push(...)`. Este módulo lê esse
conteúdo como um usuário comum que abre a página: uma página por vez,
intervalo entre chamadas, e não repete a coleta se o dado ainda está
fresco (config.CBF_VALIDADE_HORAS). Não toca em nenhuma rota de login.

Atenção aos termos de uso da CBF (item 6): o uso é decisão e risco do
usuário (registrada em docs/cbf-fonte-de-dados.md). Os dados ficam só no
banco local e nunca vão para o GitHub.
"""
import datetime as dt
import json
import logging
import re
import ssl
import time

import requests
import truststore
from requests.adapters import HTTPAdapter

import config

logger = logging.getLogger(__name__)

_PADRAO_PUSH = re.compile(r'self\.__next_f\.push\(\[1,"(.*?)"\]\)</script>', re.S)


class ErroColetaCBF(Exception):
    """Falha ao abrir ou interpretar uma página da CBF."""


def decodificar_fluxo(html: str) -> str:
    """Junta os pedaços do fluxo embutido e desfaz o escape de string JS."""
    bruto = "".join(_PADRAO_PUSH.findall(html))
    if not bruto:
        raise ErroColetaCBF("Fluxo de dados embutido não encontrado na página (o site pode ter mudado)")
    try:
        return json.loads('"' + bruto + '"')
    except json.JSONDecodeError as erro:
        raise ErroColetaCBF("Não foi possível decodificar o fluxo de dados da página") from erro


def json_apos(texto: str, marcador: str):
    """Decodifica o valor JSON que vem logo depois de `marcador`
    (ex.: '"estatisticas":'). Retorna None se o marcador não existe."""
    indice = texto.find(marcador)
    if indice < 0:
        return None
    try:
        valor, _ = json.JSONDecoder().raw_decode(texto[indice + len(marcador):])
    except json.JSONDecodeError:
        return None
    return valor


def parse_classificacao(html: str) -> list[dict]:
    texto = decodificar_fluxo(html)
    indice = texto.find('"data":[{"cod_time"')
    if indice < 0:
        raise ErroColetaCBF("Tabela de classificação não encontrada na página")
    dados, _ = json.JSONDecoder().raw_decode(texto[indice + len('"data":'):])
    return dados


def parse_pagina_time(html: str) -> dict:
    texto = decodificar_fluxo(html)
    estatisticas = json_apos(texto, '"estatisticas":') or []
    jogos = json_apos(texto, '"jogos":') or []
    if not isinstance(jogos, list):
        jogos = []
    return {"estatisticas": estatisticas[0] if estatisticas else None, "jogos": jogos}


def _inteiro(valor):
    if valor is None:
        return None
    texto = str(valor).strip().replace("+", "")
    if texto in ("", "-"):
        return None
    try:
        return int(texto)
    except ValueError:
        return None


def _decimal(valor):
    try:
        return float(str(valor).strip().replace(",", "."))
    except (TypeError, ValueError):
        return None


def data_iso(texto: str | None) -> str | None:
    if not texto or not texto.strip():
        return None
    try:
        return dt.datetime.strptime(texto.strip(), "%d/%m/%Y").date().isoformat()
    except ValueError:
        return None


class _AdaptadorRepositorioDoSistema(HTTPAdapter):
    """O servidor da CBF envia a cadeia de certificados incompleta (falta o
    intermediário). O Windows completa sozinho; o Python com o pacote
    `certifi` não. Usar o repositório de certificados do sistema
    (`truststore`) resolve SEM desligar a verificação do certificado."""

    def init_poolmanager(self, *args, **kwargs):
        kwargs["ssl_context"] = truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        super().init_poolmanager(*args, **kwargs)


def _sessao() -> requests.Session:
    sessao = requests.Session()
    sessao.mount("https://", _AdaptadorRepositorioDoSistema())
    return sessao


def _baixar(url: str) -> str:
    try:
        resposta = _sessao().get(
            url,
            headers={"User-Agent": config.CBF_USER_AGENT, "Accept-Language": "pt-BR,pt;q=0.9"},
            timeout=config.CBF_TIMEOUT_SEGUNDOS,
        )
    except requests.RequestException as erro:
        raise ErroColetaCBF(f"Falha de rede ao abrir {url}") from erro
    if resposta.status_code != 200:
        raise ErroColetaCBF(f"HTTP {resposta.status_code} ao abrir {url}")
    return resposta.content.decode("utf-8", errors="replace")


def _agora() -> str:
    return dt.datetime.now().isoformat(timespec="seconds")


def _dado_fresco(conexao, serie: str, ano: int) -> bool:
    linha = conexao.execute(
        "SELECT MAX(coletado_em) AS ultimo FROM cbf_classificacao WHERE serie = ? AND ano = ?", (serie, ano)
    ).fetchone()
    if not linha or not linha["ultimo"]:
        return False
    idade = dt.datetime.now() - dt.datetime.fromisoformat(linha["ultimo"])
    return idade < dt.timedelta(hours=config.CBF_VALIDADE_HORAS)


def gravar_classificacao(conexao, serie: str, ano: int, linhas: list[dict], coletado_em: str) -> None:
    # `cbf_times` guarda o nome MAIS RECENTE do time. Uma temporada antiga não pode
    # sobrescrevê-lo (coletar 2019 depois de 2026 trocaria "Coritiba SAF" por
    # "Coritiba" e quebraria a marca de SAF e o link do Transfermarkt). O nome de
    # cada temporada fica em `cbf_classificacao.nome_no_ano`.
    ano_mais_recente = conexao.execute("SELECT MAX(ano) FROM cbf_classificacao").fetchone()[0]
    atualiza_nome_atual = ano_mais_recente is None or ano >= ano_mais_recente
    for linha in linhas:
        cod = _inteiro(linha["cod_time"])
        if atualiza_nome_atual:
            conexao.execute(
                "INSERT INTO cbf_times (cod_time, nome, uf) VALUES (?, ?, ?) "
                "ON CONFLICT(cod_time) DO UPDATE SET nome=excluded.nome, uf=excluded.uf",
                (cod, linha["time"], linha.get("uf_time")),
            )
        else:
            conexao.execute(
                "INSERT INTO cbf_times (cod_time, nome, uf) VALUES (?, ?, ?) ON CONFLICT(cod_time) DO NOTHING",
                (cod, linha["time"], linha.get("uf_time")),
            )
        # Temporada em andamento: objeto {id, time, escudo}. Temporada encerrada: a CBF
        # devolve uma lista (["nenhum"]) -- sem próximo jogo, não é erro.
        proximo = linha.get("proximo_jogo")
        proximo = proximo if isinstance(proximo, dict) else {}
        conexao.execute(
            """
            INSERT INTO cbf_classificacao (serie, ano, cod_time, rodada, posicao, pontos, jogos, vitorias, empates,
                derrotas, gols_pro, gols_contra, saldo, cartoes_amarelo, cartoes_vermelho, aproveitamento,
                ultimos_jogos, proximo_adversario, proximo_adversario_id, coletado_em, nome_no_ano)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(serie, ano, cod_time, rodada) DO UPDATE SET
                nome_no_ano=excluded.nome_no_ano,
                posicao=excluded.posicao, pontos=excluded.pontos, jogos=excluded.jogos,
                vitorias=excluded.vitorias, empates=excluded.empates, derrotas=excluded.derrotas,
                gols_pro=excluded.gols_pro, gols_contra=excluded.gols_contra, saldo=excluded.saldo,
                cartoes_amarelo=excluded.cartoes_amarelo, cartoes_vermelho=excluded.cartoes_vermelho,
                aproveitamento=excluded.aproveitamento, ultimos_jogos=excluded.ultimos_jogos,
                proximo_adversario=excluded.proximo_adversario,
                proximo_adversario_id=excluded.proximo_adversario_id, coletado_em=excluded.coletado_em
            """,
            (
                serie, ano, cod, _inteiro(linha.get("rodada")) or 0, _inteiro(linha.get("posicao")),
                _inteiro(linha.get("pontos")), _inteiro(linha.get("jogos")), _inteiro(linha.get("vitorias")),
                _inteiro(linha.get("empates")), _inteiro(linha.get("derrotas")), _inteiro(linha.get("gols_pro")),
                _inteiro(linha.get("gols_contra")), _inteiro(linha.get("gols_saldo")),
                _inteiro(linha.get("cartoes_amarelo")), _inteiro(linha.get("cartoes_vermelho")),
                _decimal(linha.get("aproveitamento")), ",".join(linha.get("ultimos_jogos") or []),
                proximo.get("time"), _inteiro(proximo.get("id")), coletado_em, linha["time"],
            ),
        )


def gravar_pagina_time(conexao, serie: str, ano: int, cod_time: int, dados: dict, coletado_em: str) -> None:
    est = dados.get("estatisticas")
    if est:
        conexao.execute(
            """
            INSERT INTO cbf_estatisticas_time (serie, ano, cod_time, jogos_disputados, gols_feitos, gols_sofridos,
                jogos_sem_sofrer_gol, cartoes_amarelos, cartoes_vermelhos, coletado_em)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(serie, ano, cod_time) DO UPDATE SET
                jogos_disputados=excluded.jogos_disputados, gols_feitos=excluded.gols_feitos,
                gols_sofridos=excluded.gols_sofridos, jogos_sem_sofrer_gol=excluded.jogos_sem_sofrer_gol,
                cartoes_amarelos=excluded.cartoes_amarelos, cartoes_vermelhos=excluded.cartoes_vermelhos,
                coletado_em=excluded.coletado_em
            """,
            (
                serie, ano, cod_time, _inteiro(est.get("jogos_disputados")), _inteiro(est.get("gols_feitos")),
                _inteiro(est.get("gols_sofridos")), _inteiro(est.get("jogos_sem_sofrer_gol")),
                _inteiro(est.get("cartoes_amarelos")), _inteiro(est.get("cartoes_vermelhos")), coletado_em,
            ),
        )
    for jogo in dados.get("jogos", []):
        mandante, visitante = jogo.get("mandante") or {}, jogo.get("visitante") or {}
        for lado in (mandante, visitante):
            if _inteiro(lado.get("id")) is not None and lado.get("nome"):
                conexao.execute(
                    "INSERT INTO cbf_times (cod_time, nome, uf) VALUES (?, ?, NULL) ON CONFLICT(cod_time) DO NOTHING",
                    (_inteiro(lado["id"]), lado["nome"]),
                )
        conexao.execute(
            """
            INSERT INTO cbf_partidas (id_jogo, serie, ano, rodada, data_jogo, hora, local, mandante_id, visitante_id,
                gols_mandante, gols_visitante, penaltis_mandante, penaltis_visitante, coletado_em)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id_jogo) DO UPDATE SET
                rodada=excluded.rodada, data_jogo=excluded.data_jogo, hora=excluded.hora, local=excluded.local,
                gols_mandante=excluded.gols_mandante, gols_visitante=excluded.gols_visitante,
                penaltis_mandante=excluded.penaltis_mandante, penaltis_visitante=excluded.penaltis_visitante,
                coletado_em=excluded.coletado_em
            """,
            (
                _inteiro(jogo.get("id_jogo")), serie, ano, _inteiro(jogo.get("rodada")), data_iso(jogo.get("data")),
                jogo.get("hora"), jogo.get("local"), _inteiro(mandante.get("id")), _inteiro(visitante.get("id")),
                _inteiro(mandante.get("gols")), _inteiro(visitante.get("gols")),
                _inteiro(mandante.get("panaltis")), _inteiro(visitante.get("panaltis")), coletado_em,
            ),
        )


def coletar_competicao(conexao, campeonato: str, serie: str, ano: int, forcar: bool = False) -> dict:
    """Lê a classificação e a página de cada time da competição. Pula se o
    dado já é recente (a menos que `forcar`)."""
    if not forcar and _dado_fresco(conexao, serie, ano):
        return {"serie": serie, "ano": ano, "pulou": True, "times": 0}

    url_tabela = f"{config.CBF_BASE_URL}/futebol-brasileiro/tabelas/{campeonato}/{serie}/{ano}"
    linhas = parse_classificacao(_baixar(url_tabela))
    coletado_em = _agora()
    gravar_classificacao(conexao, serie, ano, linhas, coletado_em)

    coletados = 0
    for linha in linhas:
        cod = _inteiro(linha["cod_time"])
        time.sleep(config.CBF_INTERVALO_SEGUNDOS)
        url_time = f"{config.CBF_BASE_URL}/futebol-brasileiro/times/{campeonato}/{serie}/{ano}/{cod}"
        try:
            dados = parse_pagina_time(_baixar(url_time))
        except ErroColetaCBF as erro:
            logger.warning("Time %s (%s) não coletado: %s", linha.get("time"), cod, erro)
            continue
        gravar_pagina_time(conexao, serie, ano, cod, dados, coletado_em)
        coletados += 1
    return {"serie": serie, "ano": ano, "pulou": False, "times": coletados}


def preencher_nome_do_ano_mais_recente(conexao) -> int:
    """Linhas da temporada mais recente coletadas antes de existir `nome_no_ano`
    recebem o nome atual do time (que, para essa temporada, é o nome dela). Só a
    temporada mais recente: nas antigas, o nome atual pode ser outro."""
    return conexao.execute(
        """
        UPDATE cbf_classificacao
        SET nome_no_ano = (SELECT t.nome FROM cbf_times t WHERE t.cod_time = cbf_classificacao.cod_time)
        WHERE nome_no_ano IS NULL AND ano = (SELECT MAX(ano) FROM cbf_classificacao)
        """
    ).rowcount


def divergencias_de_resultado(validacao: dict) -> list[dict]:
    """Das divergências entre a tabela reconstruída e a classificação da CBF, só as que
    mudam RESULTADO: jogo faltando, ou pontos diferentes. Diferença de gols (achada
    em 2019: 1 gol a mais na lista de jogos do que na tabela da CBF, com jogos e pontos
    iguais) é inconsistência dentro das páginas da CBF e não invalida a temporada."""
    return [
        d for d in validacao["divergencias_numeros"]
        if "motivo" in d or d.get("campo") in ("jogos", "pontos")
    ]


def temporada_completa(conexao, serie: str, ano: int) -> bool:
    """Todos os jogos da temporada estão no banco e os resultados batem com a
    classificação final da CBF (jogos e pontos de cada time). Serve para a coleta
    histórica pular o que já está bom."""
    from stats.competicao import validar_temporada

    jogos = conexao.execute(
        "SELECT COUNT(*) FROM cbf_partidas WHERE serie = ? AND ano = ? AND gols_mandante IS NOT NULL", (serie, ano)
    ).fetchone()[0]
    anomalia = config.CBF_ANOMALIAS_CONHECIDAS.get((serie, ano))
    minimo = config.CBF_JOGOS_TEMPORADA_COMPLETA - (anomalia["jogos_faltando"] if anomalia else 0)
    if jogos < minimo:
        return False
    # Temporada com anomalia conhecida (config.CBF_ANOMALIAS_CONHECIDAS): basta ter todos os jogos que
    # a CBF publica; as diferenças já foram entendidas e registradas.
    return bool(anomalia) or not divergencias_de_resultado(validar_temporada(conexao, serie, ano))


def coletar_todas(conexao, forcar: bool = False) -> list[dict]:
    if not config.CBF_HABILITADO:
        logger.info("Coleta da CBF desligada (LOTECA_CBF_HABILITADO=0).")
        return []
    resultados = []
    for campeonato, serie, ano in config.CBF_COMPETICOES:
        try:
            resultados.append(coletar_competicao(conexao, campeonato, serie, ano, forcar))
        except ErroColetaCBF as erro:
            logger.error("Competição %s %s não coletada: %s", serie, ano, erro)
            resultados.append({"serie": serie, "ano": ano, "erro": str(erro)})
        time.sleep(config.CBF_INTERVALO_SEGUNDOS)
    return resultados
