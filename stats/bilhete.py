"""Sugestão de bilhete: aposta simples, com no máximo UM jogo de cobertura
múltipla (um duplo OU um triplo). Regra definida pelo usuário em 27/09/2026.

Todos os jogos levam a coluna de maior percentual; o único jogo com cobertura
extra é o mais incerto (menor percentual do favorito). Vira triplo quando o
favorito fica abaixo do limiar de `config.SUGESTAO_LIMIAR_DUPLO`; senão, duplo.
Custo resultante: R$ 4,00 (duplo) ou R$ 6,00 (triplo), dentro do mínimo e do
máximo oficiais (Manual de Produtos v21, item 6.3.3). Não promete acerto.
"""
import config

PRECO_APOSTA = 2.0


def validar_volante(marcacoes: list[list[str]]) -> dict:
    """Confere o volante marcado pelo usuário, na ordem dos jogos. Jogo sem
    marcação NÃO vira coluna nenhuma por conta própria: ele bloqueia o
    salvamento e aparece em `jogos_sem_marcacao` (número do jogo, a partir de 1).
    Regras oficiais: ao menos 1 duplo ou triplo (mínimo de R$ 4,00) e no
    máximo `config.BILHETE_MAX_APOSTAS` apostas (Manual de Produtos v21, 6.3.3)."""
    sem_marcacao = [i + 1 for i, m in enumerate(marcacoes) if not m]
    duplos = sum(1 for m in marcacoes if len(m) == 2)
    triplos = sum(1 for m in marcacoes if len(m) == 3)
    apostas = (2**duplos) * (3**triplos)
    problemas = []
    if sem_marcacao:
        lista = ", ".join(map(str, sem_marcacao))
        problemas.append(f"Falta marcar o(s) jogo(s) {lista}.")
    if duplos + triplos == 0:
        problemas.append("O volante exige ao menos um duplo ou triplo (mínimo de R$ 4,00). Marque duas colunas em algum jogo.")
    if apostas > config.BILHETE_MAX_APOSTAS:
        problemas.append(
            f"Passa do máximo oficial de {config.BILHETE_MAX_APOSTAS} apostas. Tire algum duplo ou triplo."
        )
    return {
        "marcados": len(marcacoes) - len(sem_marcacao),
        "total": len(marcacoes),
        "jogos_sem_marcacao": sem_marcacao,
        "duplos": duplos,
        "triplos": triplos,
        "apostas": apostas,
        "custo": apostas * PRECO_APOSTA,
        "problemas": problemas,
        "pode_salvar": not problemas,
    }


def montar_bilhete(jogos: list[dict]) -> dict:
    """`jogos`: lista de {'1': %, 'X': %, '2': %}, na ordem dos jogos."""
    ordenados = [sorted(j, key=j.get, reverse=True) for j in jogos]
    marcacoes = [[colunas[0]] for colunas in ordenados]

    mais_incerto = min(range(len(jogos)), key=lambda i: jogos[i][ordenados[i][0]])
    favorito_pct = jogos[mais_incerto][ordenados[mais_incerto][0]]
    quantidade = 3 if favorito_pct < config.SUGESTAO_LIMIAR_DUPLO else 2
    marcacoes[mais_incerto] = ordenados[mais_incerto][:quantidade]

    apostas = quantidade
    probabilidade = 1.0
    for i, colunas in enumerate(marcacoes):
        probabilidade *= sum(jogos[i][c] for c in colunas) / 100.0
    return {
        "marcacoes": [sorted(m) for m in marcacoes],
        "jogo_multiplo": mais_incerto,
        "apostas": apostas,
        "custo": apostas * PRECO_APOSTA,
        "duplos": 1 if quantidade == 2 else 0,
        "triplos": 1 if quantidade == 3 else 0,
        "prob_todos_acertos": probabilidade,
    }
