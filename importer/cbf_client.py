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


_TABELA = '"data":[{"cod_time"'
_JOGOS_DA_FASE = '"data":[{"id_jogo"'
_TITULO_DA_TABELA = re.compile(r'"title":"([^"]*)",$')


def parse_tabela_completa(html: str) -> dict:
    """Todas as tabelas da página e as fases da competição. Séries A e B: uma tabela
    ("GRUPO ÚNICO") e uma fase. Série C (conferido em 07/10/2026): a página mostra só a
    fase atual -- na 2ª fase, uma tabela por grupo ("GRUPO B", "GRUPO C") -- e a lista
    de fases (`phasesList`), em que a fase atual vem como referência ao objeto `phase`.
    Temporada encerrada da Série C: a fase atual é a final (mata-mata), sem tabela; a página
    traz só os jogos dela, e os times desses jogos servem de ponto de partida da coleta.

    Devolve {"grupos": [{"titulo", "linhas"}], "fases": [{fase_nome, rodadas_qtd, partidas, ...}],
    "indice_fase_atual": posição da fase atual em "fases" (None se a página não disser),
    "times_dos_jogos": códigos dos times nos jogos mostrados quando não há tabela}.
    O título só é guardado quando há mais de uma tabela (com uma só, ele não diz nada)."""
    texto = decodificar_fluxo(html)
    grupos, inicio = [], texto.find(_TABELA)
    while inicio >= 0:
        linhas, _ = json.JSONDecoder().raw_decode(texto[inicio + len('"data":'):])
        titulo = _TITULO_DA_TABELA.search(texto[max(0, inicio - 200):inicio])
        grupos.append({"titulo": titulo.group(1) if titulo else None, "linhas": linhas})
        inicio = texto.find(_TABELA, inicio + 1)
    if len(grupos) == 1:
        grupos[0]["titulo"] = None
    times_dos_jogos = []
    if not grupos:
        inicio = texto.find(_JOGOS_DA_FASE)
        if inicio < 0:
            raise ErroColetaCBF("Tabela de classificação não encontrada na página")
        jogos, _ = json.JSONDecoder().raw_decode(texto[inicio + len('"data":'):])
        for jogo in jogos:
            for lado in (jogo.get("mandante") or {}, jogo.get("visitante") or {}):
                cod = _inteiro(lado.get("id"))
                if cod is not None and cod not in times_dos_jogos:
                    times_dos_jogos.append(cod)
    fase_atual = json_apos(texto, '"phase":')
    fase_atual = fase_atual if isinstance(fase_atual, dict) else None
    fases = [f if isinstance(f, dict) else fase_atual for f in (json_apos(texto, '"phasesList":') or [])]
    fases = [f for f in fases if isinstance(f, dict)]
    indice_atual = next(
        (i for i, f in enumerate(fases) if fase_atual and f.get("fase_id") == fase_atual.get("fase_id")), None
    )
    return {"grupos": grupos, "fases": fases, "indice_fase_atual": indice_atual, "times_dos_jogos": times_dos_jogos}


def calendario_de_fases(fases: list[dict]) -> list[dict]:
    """Para cada fase, em ordem: nome, número de rodadas e quantas rodadas vêm antes dela (para numerar
    a rodada em sequência pela temporada). Vazio quando a competição tem uma fase só (Séries A e B):
    aí nada muda na gravação. A contagem de partidas da CBF NÃO é usada: ela é por grupo (2ª fase da
    Série C 2024: "12" partidas, 24 jogos em dois grupos)."""
    if len(fases) < 2:
        return []
    calendario, rodadas_antes = [], 0
    for fase in fases:
        rodadas = _inteiro(fase.get("rodadas_qtd")) or 0
        calendario.append({"nome": fase.get("fase_nome"), "rodadas": rodadas, "rodadas_antes": rodadas_antes})
        rodadas_antes += rodadas
    return calendario


def fases_pela_sequencia(jogos: list[dict], calendario: list[dict]) -> dict[int, dict] | None:
    """{id_jogo: fase do calendário} deduzida da sequência dos jogos: em ordem de `num_jogo`, a rodada
    não diminui dentro de uma fase (os grupos de uma fase jogam a mesma rodada lado a lado) e volta a 1
    quando começa a fase seguinte. `jogos`: [{'id_jogo', 'num_jogo', 'rodada_fase'}] da temporada.
    None quando a sequência não fecha com o calendário (mais trocas de fase do que fases, ou rodada
    acima do número de rodadas da fase): melhor sem fase do que com fase errada."""
    ordenados = sorted((j for j in jogos if j["num_jogo"] is not None and j["rodada_fase"] is not None),
                       key=lambda j: j["num_jogo"])
    saida, indice, anterior = {}, 0, None
    for jogo in ordenados:
        if anterior is not None and jogo["rodada_fase"] < anterior:
            indice += 1
        if indice >= len(calendario) or jogo["rodada_fase"] > calendario[indice]["rodadas"]:
            return None
        saida[jogo["id_jogo"]] = calendario[indice]
        anterior = jogo["rodada_fase"]
    return saida


def reatribuir_fases(conexao, serie: str, ano: int, calendario: list[dict]) -> bool:
    """Grava fase e rodada em sequência em todos os jogos da temporada, a partir da rodada de cada fase
    (`rodada_fase`) e do número do jogo. Devolve False (e registra o motivo) quando a sequência não fecha."""
    jogos = [dict(l) for l in conexao.execute(
        "SELECT id_jogo, num_jogo, rodada_fase FROM cbf_partidas WHERE serie = ? AND ano = ?", (serie, ano)
    )]
    fases = fases_pela_sequencia(jogos, calendario)
    if fases is None:
        logger.warning("%s %s: a sequência de rodadas não fecha com as %d fases da CBF; fase não gravada.",
                       serie, ano, len(calendario))
        conexao.execute("UPDATE cbf_partidas SET fase = NULL, rodada = rodada_fase WHERE serie = ? AND ano = ?", (serie, ano))
        return False
    for id_jogo, fase in fases.items():
        conexao.execute(
            "UPDATE cbf_partidas SET fase = ?, rodada = rodada_fase + ? WHERE id_jogo = ?",
            (fase["nome"], fase["rodadas_antes"], id_jogo),
        )
    return True


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


def gravar_classificacao(
    conexao, serie: str, ano: int, linhas: list[dict], coletado_em: str, fase: dict | None = None,
    grupo: str | None = None,
) -> None:
    """`fase` (de `calendario_de_fases`) e `grupo` só nas competições com mais de uma fase: a rodada
    guardada passa a seguir a sequência da temporada e a rodada da fase vai para `rodada_fase`."""
    rodadas_antes = fase["rodadas_antes"] if fase else 0
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
                ultimos_jogos, proximo_adversario, proximo_adversario_id, coletado_em, nome_no_ano, fase, grupo,
                rodada_fase)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(serie, ano, cod_time, rodada) DO UPDATE SET
                nome_no_ano=excluded.nome_no_ano, fase=excluded.fase, grupo=excluded.grupo,
                rodada_fase=excluded.rodada_fase,
                posicao=excluded.posicao, pontos=excluded.pontos, jogos=excluded.jogos,
                vitorias=excluded.vitorias, empates=excluded.empates, derrotas=excluded.derrotas,
                gols_pro=excluded.gols_pro, gols_contra=excluded.gols_contra, saldo=excluded.saldo,
                cartoes_amarelo=excluded.cartoes_amarelo, cartoes_vermelho=excluded.cartoes_vermelho,
                aproveitamento=excluded.aproveitamento, ultimos_jogos=excluded.ultimos_jogos,
                proximo_adversario=excluded.proximo_adversario,
                proximo_adversario_id=excluded.proximo_adversario_id, coletado_em=excluded.coletado_em
            """,
            (
                serie, ano, cod, (_inteiro(linha.get("rodada")) or 0) + rodadas_antes, _inteiro(linha.get("posicao")),
                _inteiro(linha.get("pontos")), _inteiro(linha.get("jogos")), _inteiro(linha.get("vitorias")),
                _inteiro(linha.get("empates")), _inteiro(linha.get("derrotas")), _inteiro(linha.get("gols_pro")),
                _inteiro(linha.get("gols_contra")), _inteiro(linha.get("gols_saldo")),
                _inteiro(linha.get("cartoes_amarelo")), _inteiro(linha.get("cartoes_vermelho")),
                _decimal(linha.get("aproveitamento")), ",".join(linha.get("ultimos_jogos") or []),
                proximo.get("time"), _inteiro(proximo.get("id")), coletado_em, linha["time"],
                fase["nome"] if fase else None, grupo, _inteiro(linha.get("rodada")) if fase else None,
            ),
        )


def gravar_pagina_time(
    conexao, serie: str, ano: int, cod_time: int, dados: dict, coletado_em: str, calendario: list[dict] | None = None,
) -> None:
    """`calendario` (de `calendario_de_fases`) só nas competições com mais de uma fase: cada jogo guarda a
    rodada da fase e o grupo que a CBF informa; a fase e a rodada em sequência são gravadas depois, com a
    temporada inteira, por `reatribuir_fases` (a fase de um jogo depende da sequência dos outros)."""
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
        rodada = _inteiro(jogo.get("rodada"))
        com_fases = bool(calendario)
        conexao.execute(
            """
            INSERT INTO cbf_partidas (id_jogo, serie, ano, rodada, data_jogo, hora, local, mandante_id, visitante_id,
                gols_mandante, gols_visitante, penaltis_mandante, penaltis_visitante, coletado_em, fase, grupo,
                rodada_fase, num_jogo)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, ?, ?, ?)
            ON CONFLICT(id_jogo) DO UPDATE SET
                rodada=excluded.rodada, data_jogo=excluded.data_jogo, hora=excluded.hora, local=excluded.local,
                gols_mandante=excluded.gols_mandante, gols_visitante=excluded.gols_visitante,
                penaltis_mandante=excluded.penaltis_mandante, penaltis_visitante=excluded.penaltis_visitante,
                coletado_em=excluded.coletado_em, grupo=excluded.grupo,
                rodada_fase=excluded.rodada_fase, num_jogo=excluded.num_jogo
            """,
            (
                _inteiro(jogo.get("id_jogo")), serie, ano, rodada, data_iso(jogo.get("data")),
                jogo.get("hora"), jogo.get("local"), _inteiro(mandante.get("id")), _inteiro(visitante.get("id")),
                _inteiro(mandante.get("gols")), _inteiro(visitante.get("gols")),
                _inteiro(mandante.get("panaltis")), _inteiro(visitante.get("panaltis")), coletado_em,
                jogo.get("grupo") if com_fases else None, rodada if com_fases else None, _inteiro(jogo.get("num_jogo")),
            ),
        )


def coletar_competicao(conexao, campeonato: str, serie: str, ano: int, forcar: bool = False) -> dict:
    """Lê a classificação e a página de cada time da competição. Pula se o
    dado já é recente (a menos que `forcar`)."""
    if not forcar and _dado_fresco(conexao, serie, ano):
        return {"serie": serie, "ano": ano, "pulou": True, "times": 0}

    url_tabela = f"{config.CBF_BASE_URL}/futebol-brasileiro/tabelas/{campeonato}/{serie}/{ano}"
    pagina = parse_tabela_completa(_baixar(url_tabela))
    calendario = calendario_de_fases(pagina["fases"])
    indice = pagina["indice_fase_atual"]
    fase_atual = calendario[indice] if calendario and indice is not None else None
    if calendario and fase_atual is None:
        raise ErroColetaCBF(f"{serie} {ano}: a página tem várias fases mas não diz qual é a atual")
    coletado_em = _agora()
    for grupo in pagina["grupos"]:
        gravar_classificacao(conexao, serie, ano, grupo["linhas"], coletado_em, fase_atual, grupo["titulo"])

    # Fila de times: os da tabela e, numa competição com fases, os adversários que aparecem nas páginas
    # (na 2ª fase da Série C a tabela mostra só 8 dos 20 clubes; os eliminados estão nos jogos da 1ª fase).
    fila = [_inteiro(linha["cod_time"]) for grupo in pagina["grupos"] for linha in grupo["linhas"]]
    fila += [cod for cod in pagina["times_dos_jogos"] if cod not in fila]  # temporada encerrada: só a final
    vistos, coletados = set(fila), 0
    while fila and coletados < config.CBF_MAX_TIMES_POR_COMPETICAO:
        cod = fila.pop(0)
        time.sleep(config.CBF_INTERVALO_SEGUNDOS)
        url_time = f"{config.CBF_BASE_URL}/futebol-brasileiro/times/{campeonato}/{serie}/{ano}/{cod}"
        try:
            dados = parse_pagina_time(_baixar(url_time))
        except ErroColetaCBF as erro:
            logger.warning("Time %s de %s %s não coletado: %s", cod, serie, ano, erro)
            continue
        gravar_pagina_time(conexao, serie, ano, cod, dados, coletado_em, calendario)
        coletados += 1
        if calendario:
            for jogo in dados["jogos"]:
                for lado in (jogo.get("mandante") or {}, jogo.get("visitante") or {}):
                    novo = _inteiro(lado.get("id"))
                    if novo is not None and novo not in vistos:
                        vistos.add(novo)
                        fila.append(novo)
    if fila:
        logger.warning("%s %s: %d time(s) ficaram de fora pelo teto de páginas", serie, ano, len(fila))
    fases_ok = reatribuir_fases(conexao, serie, ano, calendario) if calendario else None
    return {"serie": serie, "ano": ano, "pulou": False, "times": coletados, "fases_conferem": fases_ok}


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
