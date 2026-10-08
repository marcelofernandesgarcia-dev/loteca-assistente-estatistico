"""S6 — termômetro do perfil do concurso (aprovado pelo usuário em 08/10/2026). Só informativo.

Base: estudo D6 (docs/d6-concursos-pulverizados-08-10-2026.md). Os concursos "pulverizados" (os 10% com mais
ganhadores de 14 por milhão arrecadado no ano) têm, antes do prazo, mais jogos de seleções e mais favoritos claros.
O sinal é fraco: área sob a curva ROC de 0,585 fora da amostra (0,5 é o acaso). Por isso o termômetro:
- mostra a posição do concurso entre os passados e a taxa de concursos pulverizados na mesma faixa, medida fora da
  amostra (cada ano previsto só com os anos anteriores);
- traz a medida de acerto escrita ao lado;
- não muda a sugestão, não diz quais jogos vão sair e não estima prêmio em reais.

Limitação: o histórico usa as previsões que o app faria na época (Elo de clubes, Elo das seleções e modelo
histórico). O concurso de hoje usa os percentuais da tela, que também trazem o modelo da temporada da CBF e as
notícias. Os sinais são contagens (favoritos de 60% ou mais, jogos equilibrados etc.) e mudam pouco com isso.
"""
import numpy as np

import config
from stats import anti_manada, estudo_d6

FAIXAS = {
    "favoritos": "perfil de favoritos: tende a ter mais ganhadores que o comum",
    "comum": "perfil comum",
    "dificil": "perfil difícil: tende a ter menos ganhadores que o comum",
}
CHAVES = list(estudo_d6.ANTES)


def faixa_da_posicao(posicao: float) -> str:
    if posicao >= config.PERFIL_LIMITE_FAVORITOS:
        return "favoritos"
    if posicao <= config.PERFIL_LIMITE_DIFICIL:
        return "dificil"
    return "comum"


def taxas_por_faixa(posicoes: list[float], rotulos: list[bool]) -> dict[str, dict]:
    """Concursos pulverizados em cada faixa, a partir das posições medidas fora da amostra."""
    saida = {}
    for faixa in FAIXAS:
        na_faixa = [r for p, r in zip(posicoes, rotulos) if faixa_da_posicao(p) == faixa]
        saida[faixa] = {"concursos": len(na_faixa), "pulverizados": int(sum(na_faixa)),
                        "taxa": sum(na_faixa) / len(na_faixa) if na_faixa else None}
    saida["geral"] = {"concursos": len(rotulos), "pulverizados": int(sum(rotulos)),
                      "taxa": sum(rotulos) / len(rotulos) if rotulos else None}
    return saida


def preparar_de_linhas(linhas: list[dict]) -> dict | None:
    """Ajusta o termômetro com todos os concursos passados (linhas de stats.estudo_d6.montar). None se forem menos de
    config.PERFIL_MIN_CONCURSOS."""
    if len(linhas) < config.PERFIL_MIN_CONCURSOS:
        return None
    X = np.array([[l[k] for k in CHAVES] for l in linhas], dtype=float)
    modelo = estudo_d6.ajustar_logistica(X, np.array([int(l["pulverizado"]) for l in linhas]))
    teste = estudo_d6.teste_fora_da_amostra(linhas)
    return {
        "modelo": modelo,
        "historico": np.sort(estudo_d6.pontuar(X, modelo)),
        "medias": {k: float(X[:, i].mean()) for i, k in enumerate(CHAVES)},
        "concursos": len(linhas),
        "teste": {k: teste[k] for k in ("auc", "ic_inferior", "ic_superior", "concursos_testados", "pulverizados_testados")},
        "faixas": taxas_por_faixa(teste["posicoes"], teste["rotulos"]),
    }


def preparar(conexao) -> dict | None:
    # Saída barata antes de montar as previsões da época (que leem o Elo das seleções): sem concursos com arrecadação
    # suficientes, o termômetro não sai de qualquer jeito.
    concursos, _ = anti_manada.carregar_concursos(conexao)
    if len(concursos) < config.PERFIL_MIN_CONCURSOS:
        return None
    return preparar_de_linhas(estudo_d6.montar(conexao))


def avaliar(preparo: dict, jogos: list[dict], numero_concurso: int, anterior_acumulou: bool | None) -> dict:
    """`jogos`: como em stats.estudo_d6.sinais_dos_jogos, os 14 do concurso. Devolve {'disponivel': False, 'motivo'}
    ou a posição (0 a 1) entre os concursos passados, a faixa e cada sinal com a média histórica."""
    if len(jogos) != 14:
        return {"disponivel": False, "motivo": f"o termômetro só é calculado com os 14 jogos (o concurso tem {len(jogos)})"}
    sinais = estudo_d6.sinais_dos_jogos(jogos)
    sinais["final_0_ou_5"] = float(numero_concurso % 5 == 0)
    # Sem o resultado do concurso anterior, o sinal fica neutro (a média histórica), e a tela avisa.
    sinais["anterior_acumulou"] = preparo["medias"]["anterior_acumulou"] if anterior_acumulou is None else float(anterior_acumulou)
    pontos = estudo_d6.pontuar(np.array([[sinais[k] for k in CHAVES]], dtype=float), preparo["modelo"])[0]
    historico = preparo["historico"]
    posicao = float(np.searchsorted(historico, pontos, side="right") / len(historico))
    faixa = faixa_da_posicao(posicao)
    return {
        "disponivel": True, "posicao": posicao, "faixa": faixa, "nome_faixa": FAIXAS[faixa],
        "anterior_desconhecido": anterior_acumulou is None,
        "sinais": [{"chave": k, "descricao": estudo_d6.ANTES[k], "valor": sinais[k], "media": preparo["medias"][k]}
                   for k in CHAVES],
    }
