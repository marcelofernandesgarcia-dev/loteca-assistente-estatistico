"""Cliente do endpoint não-oficial da CAIXA para a Loteca.

Ver docs/pesquisa-fontes-dados.md para o histórico da decisão. Busca é
sequencial com espaçamento (config.CAIXA_REQUEST_INTERVAL_SEGUNDOS) --
mais simples e seguro que paralelizar sobre um SQLite (escritor único),
e ainda respeita o limite observado da CAIXA sem sobrecarregar.
"""
import logging
import time
from datetime import datetime, timedelta

import requests

import config
import db
from stats.resultado import calcular_resultado, classificar_participante

logger = logging.getLogger(__name__)


class ErroImportacaoLoteca(Exception):
    """Erro ao consultar ou interpretar a resposta da API da CAIXA."""


def _buscar_json(sufixo: str = "") -> dict:
    url = f"{config.CAIXA_API_BASE}{sufixo}"
    try:
        resposta = requests.get(
            url,
            headers={"User-Agent": config.CAIXA_USER_AGENT},
            timeout=config.CAIXA_REQUEST_TIMEOUT_SEGUNDOS,
        )
    except requests.RequestException as erro:
        raise ErroImportacaoLoteca(f"Falha de rede ao consultar {url}") from erro
    if resposta.status_code != 200:
        raise ErroImportacaoLoteca(f"HTTP {resposta.status_code} ao consultar {url}")
    corpo = resposta.json()
    if "message" in corpo and "listaResultadoEquipeEsportiva" not in corpo:
        raise ErroImportacaoLoteca(f"Concurso indisponível ainda: {corpo.get('message')}")
    return corpo


def _situacao_do_jogo(jogo_json: dict, data_apuracao: datetime | None) -> str:
    """Casos especiais confirmados no Manual de Produtos (item 10.3.1/10.3.2):
    jogo fora da janela do concurso tem resultado por sorteio. Não temos como
    detectar isso a partir só do placar -- fica marcado 'normal' por padrão e
    o campo existe para registro manual/futuro cruzamento com a programação
    oficial (loterias.caixa.gov.br/Paginas/Programacao-Loteca.aspx).
    """
    return "normal"


def _parse_data(texto: str | None) -> str | None:
    if not texto:
        return None
    try:
        return datetime.strptime(texto, "%d/%m/%Y").date().isoformat()
    except ValueError:
        return texto


def importar_concurso(numero: int | None, conexao) -> int:
    """Importa um concurso (ou o vigente, se `numero` for None). Idempotente:
    pode rodar de novo sem duplicar (upsert por concurso_numero/num_jogo).
    Retorna o número do concurso importado.
    """
    sufixo = f"/{numero}" if numero is not None else ""
    corpo = _buscar_json(sufixo)
    numero_real = corpo["numero"]

    conexao.execute(
        """
        INSERT INTO concursos (numero, data_apuracao, data_proximo, tipo, acumulado, valor_estimado_proximo)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(numero) DO UPDATE SET
            data_apuracao=excluded.data_apuracao,
            data_proximo=excluded.data_proximo,
            acumulado=excluded.acumulado,
            valor_estimado_proximo=excluded.valor_estimado_proximo
        """,
        (
            numero_real,
            _parse_data(corpo.get("dataApuracao")),
            _parse_data(corpo.get("dataProximoConcurso")),
            "regular",
            1 if corpo.get("acumulado") else 0,
            corpo.get("valorEstimadoProximoConcurso"),
        ),
    )

    for jogo in corpo.get("listaResultadoEquipeEsportiva", []):
        casa_tipo = classificar_participante(jogo["nomeEquipeUm"], jogo.get("siglaUFUm"))
        fora_tipo = classificar_participante(jogo["nomeEquipeDois"], jogo.get("siglaUFDois"))
        casa_id = db.obter_ou_criar_participante(
            conexao, jogo["nomeEquipeUm"], casa_tipo, jogo.get("siglaUFUm") or jogo.get("siglaPaisUm")
        )
        fora_id = db.obter_ou_criar_participante(
            conexao, jogo["nomeEquipeDois"], fora_tipo, jogo.get("siglaUFDois") or jogo.get("siglaPaisDois")
        )

        gols_casa = jogo.get("nuGolEquipeUm")
        gols_fora = jogo.get("nuGolEquipeDois")
        resultado = None
        if gols_casa is not None and gols_fora is not None:
            resultado = calcular_resultado(gols_casa, gols_fora)

        conexao.execute(
            """
            INSERT INTO jogos (concurso_numero, num_jogo, casa_id, fora_id, gols_casa, gols_fora,
                                resultado, campeonato, data_jogo, situacao)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(concurso_numero, num_jogo) DO UPDATE SET
                gols_casa=excluded.gols_casa,
                gols_fora=excluded.gols_fora,
                resultado=excluded.resultado
            """,
            (
                numero_real,
                jogo["nuSequencial"],
                casa_id,
                fora_id,
                gols_casa,
                gols_fora,
                resultado,
                jogo.get("nomeCampeonato"),
                _parse_data(jogo.get("dtJogo")),
                _situacao_do_jogo(jogo, None),
            ),
        )

    # A API não devolve o prazo de aposta diretamente -- aproximamos pelo
    # primeiro dia de jogo do concurso, que na prática observada coincide
    # com o dia do encerramento das apostas (confirmado em
    # docs/grade-real-e-prazos-confirmados.md: concurso 1272, jogos e
    # prazo no mesmo sábado). Aproximação, não garantia -- por isso fica
    # num campo próprio, fácil de corrigir manualmente se precisar.
    primeiro_dia_jogo = conexao.execute(
        "SELECT MIN(data_jogo) AS data FROM jogos WHERE concurso_numero = ?", (numero_real,)
    ).fetchone()
    if primeiro_dia_jogo and primeiro_dia_jogo["data"]:
        conexao.execute(
            "UPDATE concursos SET data_limite_aposta = ? WHERE numero = ? AND data_limite_aposta IS NULL",
            (primeiro_dia_jogo["data"], numero_real),
        )

    for faixa in corpo.get("listaRateioPremio", []):
        conexao.execute(
            """
            INSERT INTO premiacoes (concurso_numero, faixa, pontos, ganhadores, valor_premio)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(concurso_numero, faixa) DO UPDATE SET
                ganhadores=excluded.ganhadores, valor_premio=excluded.valor_premio
            """,
            (
                numero_real,
                faixa.get("faixa"),
                14 if faixa.get("faixa") == 1 else 13,
                faixa.get("numeroDeGanhadores"),
                faixa.get("valorPremio"),
            ),
        )
    return numero_real


def importar_historico(conexao, inicio: int | None = None, fim: int | None = None) -> None:
    """Importa concurso a concurso, do mais antigo confirmado (1) até `fim`
    (ou até o vigente). Sequencial, com espaçamento entre chamadas.
    """
    inicio = inicio or config.PRIMEIRO_CONCURSO
    if fim is None:
        fim = importar_concurso(None, conexao)
    for numero in range(inicio, fim + 1):
        ja_existe = conexao.execute(
            "SELECT 1 FROM jogos WHERE concurso_numero = ? LIMIT 1", (numero,)
        ).fetchone()
        if ja_existe:
            continue
        try:
            importar_concurso(numero, conexao)
        except ErroImportacaoLoteca as erro:
            logger.warning("Concurso %s não importado: %s", numero, erro)
        time.sleep(config.CAIXA_REQUEST_INTERVAL_SEGUNDOS)
