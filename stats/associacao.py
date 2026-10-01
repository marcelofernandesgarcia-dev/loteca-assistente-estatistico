"""Estudo de associação (Fase Q4 / P3): cada fator objetivo contra o resultado do
jogo seguinte. Responde "este fator melhora a previsão do resultado, além do que o
retrospecto do time e o mando já dizem?" -- NÃO responde se ele causa o resultado.

Método (decidido antes de ver o resultado; parâmetros em `config.ASSOCIACAO_*`):
- unidade: um jogo de um time na temporada; resultado = pontos (0, 1 ou 3). Só entram jogos
  com pelo menos `ASSOCIACAO_JOGOS_ANTERIORES_MINIMOS` jogos anteriores do time na temporada;
- modelo base: pontos ~ retrospecto do time na temporada (pontos por jogo até o jogo anterior)
  + retrospecto do adversário (idem) + mando. Modelo com o fator: o mesmo mais o fator
  (mínimos quadrados). O adversário entrou no modelo base em 01/10/2026: sem ele, qualquer
  fator ligado a enfrentar times fortes ou fracos parecia efeito próprio;
- validação fora da amostra: cada temporada (série e ano) é deixada de fora, os dois modelos
  são ajustados nas outras e comparados na que ficou. Ganho = erro quadrático do modelo base
  menos o do modelo com o fator, jogo a jogo (positivo = o fator ajudou);
- intervalo de confiança e valor p por reamostragem de times na temporada (os jogos de um mesmo
  time não são independentes); valor q pela correção de Benjamini-Hochberg entre os testes.

Por que não comparar "dentro do time com permutação" (1ª versão, descartada em 01/10/2026): o
fator é calculado do histórico do próprio time; subtrair a média da temporada, que inclui esses
jogos, cria viés negativo, e permutar rótulos pressupõe intercambialidade que não existe. O
resultado eram sete "associações" com sinais coerentes demais -- artefato, não achado.

Limites que valem para qualquer resultado: associação não é causa; a marca de SAF vem do nome do
clube na CBF, que não prova a ausência de SAF, e a adoção do modelo não é aleatória.
"""
import datetime as dt

import numpy as np

import config
from stats import competicao
from stats.cbf import registrado_como_saf

AVISO = (
    "Associação não é causa. Nenhum achado muda o percentual do modelo: isso só ocorreria "
    "com um teste que mostre ganho sobre a frequência simples (o B3 mostrou que o modelo atual "
    "mal empata com ela)."
)

FATORES = (
    ("mando_casa", "Jogar em casa, comparado a jogar fora"),
    ("forma_boa", "Forma boa (pontos por jogo nos últimos jogos acima do limiar)"),
    ("forma_ruim", "Forma ruim (pontos por jogo nos últimos jogos abaixo do limiar)"),
    ("seq_vitorias", "Vir de uma sequência de vitórias"),
    ("seq_sem_vencer", "Vir de uma sequência de jogos sem vencer"),
    ("zona_topo", "Estar entre os primeiros da tabela antes do jogo"),
    ("zona_fundo", "Estar entre os últimos da tabela antes do jogo"),
    ("saf", "Time com SAF no nome da CBF na temporada"),
    ("descanso_curto", "Jogar com poucos dias de descanso desde o jogo anterior"),
    ("reta_final", "Jogar na reta final da temporada (últimas 10 rodadas)"),
)


def _dias_entre(data_anterior: str | None, data_atual: str | None) -> int | None:
    """Dias entre dois jogos; None se faltar data, não puder ser lida ou vier fora de ordem (jogo adiado)."""
    try:
        dias = (dt.date.fromisoformat(data_atual) - dt.date.fromisoformat(data_anterior)).days
    except (TypeError, ValueError):
        return None
    return dias if dias > 0 else None


def _retrospecto_ate(jogos_do_adversario: list[dict], rodada: int) -> float | None:
    """Pontos por jogo do adversário nos jogos de rodada anterior à informada; None sem jogos."""
    anteriores = [j["pontos"] for j in jogos_do_adversario if j["rodada"] < rodada]
    return sum(anteriores) / len(anteriores) if anteriores else None


def observacoes_de_jogos(partidas: list[dict], serie: str, ano: int, nomes: dict[int, str | None] | None = None) -> list[dict]:
    """Uma observação por jogo de cada time da temporada, com os fatores calculados só
    com o que veio antes do jogo. `partidas` vem de `competicao.carregar_partidas`;
    `nomes` = {cod_time: nome do clube na CBF naquele ano}, para a marca de SAF."""
    if not partidas:
        return []
    nomes = nomes or {}
    tabelas = competicao.tabela_por_rodada(partidas)
    rodadas = sorted(tabelas)
    times = {p["mandante_id"] for p in partidas} | {p["visitante_id"] for p in partidas}
    minimo = config.ASSOCIACAO_JOGOS_ANTERIORES_MINIMOS
    janela = config.ASSOCIACAO_FORMA_JANELA
    zona = config.ASSOCIACAO_ZONA_TAMANHO
    observacoes = []

    jogos_por_time = {cod_time: competicao.jogos_do_time(partidas, cod_time) for cod_time in times}
    for cod_time in times:
        jogos = jogos_por_time[cod_time]
        saf = registrado_como_saf(nomes.get(cod_time))
        for i, jogo in enumerate(jogos):
            if i < minimo:
                continue
            retrospecto_adversario = _retrospecto_ate(jogos_por_time[jogo["adversario_id"]], jogo["rodada"])
            if retrospecto_adversario is None:
                continue  # adversário ainda sem jogo anterior: sem controle de força, o jogo não entra
            dias = _dias_entre(jogos[i - 1]["data"], jogo["data"])
            anteriores = jogos[:i]
            recentes = anteriores[-janela:]
            forma = sum(j["pontos"] for j in recentes) / len(recentes)
            sequencia = competicao.sequencia_atual(anteriores)

            rodada_anterior = max((r for r in rodadas if r < jogo["rodada"]), default=None)
            posicao = None
            if rodada_anterior is not None:
                linha = next((x for x in tabelas[rodada_anterior] if x["cod_time"] == cod_time), None)
                posicao = linha["posicao"] if linha else None

            observacoes.append(
                {
                    "temporada": f"{serie}-{ano}",
                    "cluster": f"{serie}-{ano}-{cod_time}",
                    "pontos": jogo["pontos"],
                    "retrospecto": sum(j["pontos"] for j in anteriores) / len(anteriores),
                    "adversario": retrospecto_adversario,
                    "mando_casa": jogo["mando"] == "casa",
                    "forma_boa": forma >= config.ASSOCIACAO_FORMA_BOA,
                    "forma_ruim": forma <= config.ASSOCIACAO_FORMA_RUIM,
                    "seq_vitorias": sequencia["vitorias"] >= config.ASSOCIACAO_SEQUENCIA_MINIMA,
                    "seq_sem_vencer": sequencia["sem_vencer"] >= config.ASSOCIACAO_SEQUENCIA_MINIMA,
                    "zona_topo": None if posicao is None else posicao <= zona,
                    "zona_fundo": None if posicao is None else posicao > len(times) - zona,
                    "saf": saf,
                    "descanso_curto": None if dias is None else dias <= config.ASSOCIACAO_DESCANSO_CURTO_DIAS,
                    "reta_final": jogo["rodada"] >= config.ASSOCIACAO_RETA_FINAL_A_PARTIR_DA_RODADA,
                }
            )
    return observacoes


def carregar_observacoes(conexao) -> list[dict]:
    """Observações de jogos de todas as temporadas coletadas. Só lê o banco."""
    temporadas = conexao.execute("SELECT DISTINCT serie, ano FROM cbf_partidas ORDER BY ano, serie").fetchall()
    nomes_atuais = {linha["cod_time"]: linha["nome"] for linha in conexao.execute("SELECT cod_time, nome FROM cbf_times")}
    observacoes = []
    for temporada in temporadas:
        serie, ano = temporada["serie"], temporada["ano"]
        partidas = competicao.carregar_partidas(conexao, serie, ano)
        nomes = {
            registro["cod_time"]: registro["nome_no_ano"] or nomes_atuais.get(registro["cod_time"])
            for registro in conexao.execute(
                "SELECT cod_time, nome_no_ano FROM cbf_classificacao WHERE serie = ? AND ano = ?", (serie, ano)
            )
        }
        observacoes += observacoes_de_jogos(partidas, serie, ano, nomes)
    return observacoes


def ajustar_benjamini_hochberg(valores_p: list[float]) -> list[float]:
    """Valor q de cada teste, na mesma ordem da entrada (controle da taxa de falsas descobertas)."""
    n = len(valores_p)
    if n == 0:
        return []
    ordem = sorted(range(n), key=lambda i: valores_p[i])
    q = [0.0] * n
    menor = 1.0
    for posicao in range(n, 0, -1):
        i = ordem[posicao - 1]
        menor = min(menor, valores_p[i] * n / posicao)
        q[i] = menor
    return q


def _matriz(
    retrospecto: np.ndarray, adversario: np.ndarray, mando: np.ndarray, fator: np.ndarray, com_fator: bool, chave: str
) -> np.ndarray:
    colunas = [np.ones(len(retrospecto)), retrospecto, adversario]
    if chave != "mando_casa":
        colunas.append(mando)
    if com_fator:
        colunas.append(fator)
    return np.column_stack(colunas)


def _ajustar(X: np.ndarray, y: np.ndarray) -> np.ndarray:
    return np.linalg.lstsq(X, y, rcond=None)[0]


def avaliar_fator(observacoes: list[dict], chave: str, repeticoes: int, repeticoes_coeficiente: int, semente: int) -> dict:
    """Ganho de previsão fora da amostra do fator `chave` (ver o topo do módulo). Observações com o
    fator nulo ficam fora dos DOIS modelos, para que a comparação use exatamente os mesmos jogos."""
    usadas = [o for o in observacoes if o.get(chave) is not None]
    y = np.array([o["pontos"] for o in usadas], dtype=float)
    retro = np.array([o["retrospecto"] for o in usadas], dtype=float)
    adversario = np.array([o["adversario"] for o in usadas], dtype=float)
    mando = np.array([o["mando_casa"] for o in usadas], dtype=float)
    fator = np.array([o[chave] for o in usadas], dtype=float)
    temporada = np.array([o["temporada"] for o in usadas])
    cluster = np.array([o["cluster"] for o in usadas])
    n1, n0 = int(fator.sum()), int(len(fator) - fator.sum())
    resultado = {"n_exposto": n1, "n_referencia": n0}
    if n1 < config.ASSOCIACAO_AMOSTRA_MINIMA or n0 < config.ASSOCIACAO_AMOSTRA_MINIMA:
        return resultado | {"avaliado": False}

    X0 = _matriz(retro, adversario, mando, fator, False, chave)
    X1 = _matriz(retro, adversario, mando, fator, True, chave)
    perda_base = np.zeros(len(y))
    perda_com_fator = np.zeros(len(y))
    for t in np.unique(temporada):
        teste = temporada == t
        treino = ~teste
        perda_base[teste] = (y[teste] - X0[teste] @ _ajustar(X0[treino], y[treino])) ** 2
        perda_com_fator[teste] = (y[teste] - X1[teste] @ _ajustar(X1[treino], y[treino])) ** 2
    ganho = perda_base - perda_com_fator  # positivo: o fator ajudou

    rng = np.random.default_rng(semente)
    _, cl = np.unique(cluster, return_inverse=True)
    k = cl.max() + 1
    soma = np.bincount(cl, weights=ganho, minlength=k)
    cont = np.bincount(cl, minlength=k).astype(float)
    sorteio = rng.integers(0, k, size=(repeticoes, k))
    medias = soma[sorteio].sum(axis=1) / cont[sorteio].sum(axis=1)
    ic_ganho = np.percentile(medias, [2.5, 97.5])
    p = (1 + int((medias <= 0).sum())) / (1 + repeticoes)  # unilateral: só interessa se melhora

    coeficiente = float(_ajustar(X1, y)[-1])
    indices_por_cluster = [np.flatnonzero(cl == c) for c in range(k)]
    coeficientes = []
    for _ in range(repeticoes_coeficiente):
        escolhidos = rng.integers(0, k, size=k)
        indice = np.concatenate([indices_por_cluster[c] for c in escolhidos])
        coeficientes.append(_ajustar(X1[indice], y[indice])[-1])
    ic_coeficiente = np.percentile(coeficientes, [2.5, 97.5])

    return resultado | {
        "avaliado": True,
        "ganho": float(ganho.mean()),
        "ganho_relativo": float(ganho.mean() / perda_base.mean()),
        "ganho_ic_inferior": float(ic_ganho[0]),
        "ganho_ic_superior": float(ic_ganho[1]),
        "p": p,
        "coeficiente": coeficiente,
        "coef_ic_inferior": float(ic_coeficiente[0]),
        "coef_ic_superior": float(ic_coeficiente[1]),
    }


def estudar(observacoes: list[dict]) -> list[dict]:
    """Roda todos os fatores de `FATORES`; devolve um resultado por fator, com o valor q e a
    conclusão em linguagem simples."""
    resultados = []
    for indice, (chave, descricao) in enumerate(FATORES):
        r = avaliar_fator(
            observacoes, chave, config.ASSOCIACAO_REPETICOES_BOOTSTRAP,
            config.ASSOCIACAO_REPETICOES_COEFICIENTE, config.ASSOCIACAO_SEMENTE + indice,
        )
        resultados.append({"fator": chave, "descricao": descricao, "p": None, "q": None, **r})

    avaliados = [r for r in resultados if r["avaliado"]]
    for r, q in zip(avaliados, ajustar_benjamini_hochberg([r["p"] for r in avaliados])):
        r["q"] = q
        r["conclusao"] = (
            "melhora a previsão fora da amostra" if q < config.ASSOCIACAO_NIVEL_SIGNIFICANCIA and r["ganho"] > 0
            else "não melhora a previsão"
        )
    for r in resultados:
        if not r["avaliado"]:
            r["conclusao"] = "amostra insuficiente"
    return resultados
