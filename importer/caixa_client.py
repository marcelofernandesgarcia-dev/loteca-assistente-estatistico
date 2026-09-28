"""Cliente do endpoint não-oficial da CAIXA para a Loteca.

Ver docs/pesquisa-fontes-dados.md para o histórico da decisão. Busca é
sequencial com espaçamento (config.CAIXA_REQUEST_INTERVAL_SEGUNDOS) --
mais simples e seguro que paralelizar sobre um SQLite (escritor único),
e ainda respeita o limite observado da CAIXA sem sobrecarregar.

Dois endpoints, mesmo servidor:
- `/loteca` e `/loteca/<n>`: concurso já apurado (placares).
- `/loteca/programacao`: o concurso a jogar (14 jogos sem placar, prazo exato
  de apostas). É o que alimenta a página oficial de programação da Loteca.
"""
import logging
import time
from datetime import datetime

import requests

import config
import db
from stats.resultado import calcular_resultado, identidade_participante

logger = logging.getLogger(__name__)


class ErroImportacaoLoteca(Exception):
    """Erro ao consultar ou interpretar a resposta da API da CAIXA."""


def _buscar_json(sufixo: str = ""):
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
    try:
        corpo = resposta.json()
    except ValueError as erro:
        raise ErroImportacaoLoteca(f"Resposta que não é JSON em {url}") from erro
    if isinstance(corpo, dict) and "message" in corpo and "listaResultadoEquipeEsportiva" not in corpo:
        raise ErroImportacaoLoteca(f"Concurso indisponível ainda: {corpo.get('message')}")
    return corpo


def _situacao_do_jogo(jogo_json: dict) -> str:
    """`icSorteioResultado` = 1 indica resultado decidido por sorteio público
    (jogo adiado/antecipado/cancelado fora da janela do concurso; Manual de
    Produtos, item 10.3). Esses jogos não refletem o que aconteceu em campo e
    ficam marcados para não contaminar as estatísticas."""
    return "sorteio" if jogo_json.get("icSorteioResultado") == 1 else "normal"


def _parse_data(texto: str | None) -> str | None:
    """'26/09/2026' ou '26/09/2026 00:00:00' -> '2026-09-26'."""
    if not texto:
        return None
    try:
        return datetime.strptime(texto.strip()[:10], "%d/%m/%Y").date().isoformat()
    except ValueError:
        return None


def _gravar_jogos(conexao, numero: int, jogos: list[dict], preservar_placar: bool) -> None:
    """Grava os jogos de um concurso. Com `preservar_placar` (programação), um
    jogo que já tem placar no banco não volta a ficar vazio."""
    for jogo in jogos:
        casa = identidade_participante(jogo["nomeEquipeUm"], jogo.get("siglaUFUm"))
        fora = identidade_participante(jogo["nomeEquipeDois"], jogo.get("siglaUFDois"))
        casa_id = db.obter_ou_criar_participante(conexao, casa["nome"], casa["tipo"], casa["uf"])
        fora_id = db.obter_ou_criar_participante(conexao, fora["nome"], fora["tipo"], fora["uf"])

        gols_casa, gols_fora, resultado = None, None, None
        if not preservar_placar:
            gols_casa, gols_fora = jogo.get("nuGolEquipeUm"), jogo.get("nuGolEquipeDois")
            if gols_casa is not None and gols_fora is not None:
                resultado = calcular_resultado(gols_casa, gols_fora)

        atualizar_placar = (
            "gols_casa=COALESCE(jogos.gols_casa, excluded.gols_casa), "
            "gols_fora=COALESCE(jogos.gols_fora, excluded.gols_fora), "
            "resultado=COALESCE(jogos.resultado, excluded.resultado)"
            if preservar_placar
            else "gols_casa=excluded.gols_casa, gols_fora=excluded.gols_fora, resultado=excluded.resultado"
        )
        conexao.execute(
            f"""
            INSERT INTO jogos (concurso_numero, num_jogo, casa_id, fora_id, gols_casa, gols_fora,
                                resultado, campeonato, data_jogo, situacao)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(concurso_numero, num_jogo) DO UPDATE SET
                casa_id=excluded.casa_id, fora_id=excluded.fora_id,
                data_jogo=excluded.data_jogo, situacao=excluded.situacao, {atualizar_placar}
            """,
            (
                numero,
                jogo["nuSequencial"],
                casa_id,
                fora_id,
                gols_casa,
                gols_fora,
                resultado,
                jogo.get("nomeCampeonato") or None,
                _parse_data(jogo.get("dtJogo")),
                _situacao_do_jogo(jogo),
            ),
        )


def importar_concurso(numero: int | None, conexao) -> int:
    """Importa um concurso já apurado (ou o último apurado, se `numero` for
    None). Idempotente: pode rodar de novo sem duplicar.
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

    _gravar_jogos(conexao, numero_real, corpo.get("listaResultadoEquipeEsportiva", []), preservar_placar=False)

    # Concursos apurados não trazem o prazo de aposta: aproximamos pelo primeiro
    # dia de jogo (na prática coincide com o encerramento; ver
    # docs/grade-real-e-prazos-confirmados.md). Não sobrescreve um prazo exato
    # já conhecido pela programação.
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


def importar_programacao(conexao) -> list[int]:
    """Importa o(s) concurso(s) a jogar: os 14 jogos sem placar e o prazo
    EXATO de apostas (data e hora de encerramento). Retorna os números."""
    programacao = _buscar_json("/programacao")
    if not isinstance(programacao, list):
        raise ErroImportacaoLoteca("Programação em formato inesperado (esperava uma lista de concursos)")

    numeros = []
    for concurso in programacao:
        numero = concurso["nuConcurso"]
        horario = concurso.get("horarioFimApostas")
        conexao.execute(
            """
            INSERT INTO concursos (numero, data_limite_aposta, horario_fim_apostas, data_proximo, tipo,
                                   valor_estimado_proximo)
            VALUES (?, ?, ?, ?, 'regular', ?)
            ON CONFLICT(numero) DO UPDATE SET
                data_limite_aposta=excluded.data_limite_aposta,
                horario_fim_apostas=excluded.horario_fim_apostas,
                data_proximo=excluded.data_proximo,
                valor_estimado_proximo=excluded.valor_estimado_proximo
            """,
            (
                numero,
                _parse_data(concurso.get("dataFimApostas")),
                int(horario) if str(horario or "").strip().isdigit() else None,
                _parse_data(concurso.get("dataProximoConcurso")),
                concurso.get("valorEstimadoProximoConcurso"),
            ),
        )
        _gravar_jogos(conexao, numero, concurso.get("listaJogos", []), preservar_placar=True)
        numeros.append(numero)
    return numeros


def importar_historico(conexao, inicio: int | None = None, fim: int | None = None, refazer: bool = False) -> None:
    """Importa concurso a concurso, do mais antigo confirmado (1) até `fim`
    (ou até o último apurado). Sequencial, com espaçamento entre chamadas.
    Retomável: pula concursos que já têm placar, a menos que `refazer`.
    """
    inicio = inicio or config.PRIMEIRO_CONCURSO
    if fim is None:
        fim = importar_concurso(None, conexao)
    for numero in range(inicio, fim + 1):
        if not refazer:
            ja_existe = conexao.execute(
                "SELECT 1 FROM jogos WHERE concurso_numero = ? AND resultado IS NOT NULL LIMIT 1", (numero,)
            ).fetchone()
            if ja_existe:
                continue
        try:
            importar_concurso(numero, conexao)
        except ErroImportacaoLoteca as erro:
            logger.warning("Concurso %s não importado: %s", numero, erro)
        time.sleep(config.CAIXA_REQUEST_INTERVAL_SEGUNDOS)
