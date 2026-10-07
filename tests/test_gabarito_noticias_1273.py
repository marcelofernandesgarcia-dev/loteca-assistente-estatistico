"""Gabarito das manchetes reais do concurso 1273 (validado pelo usuário em 07/10/2026).

Na análise do bilhete jogado, 4 de 9 sinais tinham caído no time errado (jogos 7, 8, 9 e 12).
Cada caso abaixo é a manchete coletada em 01/10/2026 e o que ela deve produzir para cada time.
"""
import pytest

from externo.ajuste import calcular_ajuste
from externo.analise import extrair_sinais

CONCURSO = [
    ("PORTUGAL", "NORUEGA", "selecao"), ("ATLETICO", "AMERICA", "clube"), ("CUIABA", "PONTE PRETA", "clube"),
    ("FLORESTA", "BOTAFOGO", "clube"), ("SANTA CRUZ", "MARINGA", "clube"), ("BOTAFOGO", "VILA NOVA", "clube"),
    ("ATLETICO", "BRAGANTINO", "clube"), ("INTER LIMEIRA", "BRUSQUE", "clube"), ("PAYSANDU", "FERROVIARIA", "clube"),
    ("ESPANHA", "REPUBLICA TCHECA", "selecao"), ("SUICA", "ESLOVENIA", "selecao"), ("GRECIA", "ALEMANHA", "selecao"),
    ("PAIS DE GALES", "DINAMARCA", "selecao"), ("HOLANDA", "SERVIA", "selecao"),
]
NOMES = [n for casa, fora, _ in CONCURSO for n in (casa, fora)]

M = {
    "1a": "Cristiano Ronaldo pode ser suspenso por seis meses por deixar concentração de Portugal - LANCE!",
    "1b": "Cristiano Ronaldo não treina de novo após 'entrevista bomba' de Jorge Jesus e aumenta crise em Portugal - ESPN Brasil",
    "2": "Jogadores do América-MG cruzam os braços e cancelam treino por causa de salários atrasados - ge",
    "3": "Cuiabá rescinde com goleiro Pedro Mello, que acerta com o Itaquá - ge",
    "7": "Atlético-MG pode ter \"um time\" de desfalques contra o Red Bull Bragantino - CNN Brasil",
    "8": "Desfalques Importantes Do Paysandu Para Jogo Contra A Inter De Limeira - portalgurupi.com.br",
    "9a": "América acerta contratação de atacante ex-Sport e Paysandu para 2027 - Tribuna do Norte",
    "9b": "Medina tem lesão confirmada pela Ferroviária e fica fora do restante da Série C - ge",
    "10": "Espanha tem maior sequência invicta de uma seleção na história; veja o top 10 - olympics.com",
    "12a": "Grécia coloca 'água no chope' da Alemanha, e Klopp segue sem vencer na Nations League - ESPN Brasil",
    "12b": "Reforço do Liverpool de quase R$ 1 bilhão é defendido por Klopp na seleção da Alemanha: 'Jogador excepcional' - ESPN Brasil",
}


def _sinais(time, adversario, tipo, chaves):
    noticias = [{"titulo": M[c], "fonte": "teste", "url": ""} for c in chaves]
    return extrair_sinais(noticias, participante_nome=time, adversario_nome=adversario, tipo_participante=tipo,
                          nomes_do_concurso=NOMES)


# (time, adversário, tipo, manchetes buscadas para o time, sinais esperados, ajuste esperado)
GABARITO = [
    ("PORTUGAL", "NORUEGA", "selecao", ["1a", "1b"], {"suspensao_possivel", "tendencia_negativa_imprensa"}, 0.0),
    ("AMERICA", "ATLETICO", "clube", ["2", "9a"], {"atraso_salarial", "contratacao"}, 0.0),
    ("CUIABA", "PONTE PRETA", "clube", ["3"], {"saida_de_jogador"}, 0.0),
    ("BRAGANTINO", "ATLETICO", "clube", ["7"], set(), 0.0),
    ("ATLETICO", "BRAGANTINO", "clube", ["7"], {"desfalque_possivel"}, 0.0),
    ("INTER LIMEIRA", "BRUSQUE", "clube", ["8"], set(), 0.0),
    ("PAYSANDU", "FERROVIARIA", "clube", ["8", "9a"], set(), 0.0),
    ("FERROVIARIA", "PAYSANDU", "clube", ["9b"], {"lesao_titular"}, -3.0),
    ("ESPANHA", "REPUBLICA TCHECA", "selecao", ["10"], {"sequencia_invicta_destacada"}, 1.5),
    ("GRECIA", "ALEMANHA", "selecao", ["12a"], set(), 0.0),
    ("ALEMANHA", "GRECIA", "selecao", ["12a", "12b"], set(), 0.0),
]


@pytest.mark.parametrize("time,adversario,tipo,chaves,esperado,ajuste", GABARITO, ids=[f"{g[0]}" for g in GABARITO])
def test_gabarito_do_concurso_1273(time, adversario, tipo, chaves, esperado, ajuste):
    sinais = _sinais(time, adversario, tipo, chaves)
    assert {s["sinal"] for s in sinais} == esperado
    assert calcular_ajuste(sinais)["ajuste_aplicado"] == ajuste


def test_nenhum_sinal_com_peso_no_time_errado():
    """Medida da Fase 1: no 1273 havia 4 sinais no time errado; agora nenhum."""
    com_peso_no_time_errado = []
    for time, adversario, tipo, chaves, esperado, _ in GABARITO:
        for s in _sinais(time, adversario, tipo, chaves):
            if s["sinal"] not in esperado:
                com_peso_no_time_errado.append((time, s["sinal"]))
    assert com_peso_no_time_errado == []


def test_contratacao_do_proprio_clube_continua_valendo():
    """'acerta com' sem saída: a contratação é do clube citado (não pode virar falso negativo)."""
    sinais = extrair_sinais([{"titulo": "Flamengo acerta com atacante uruguaio", "url": ""}], participante_nome="FLAMENGO",
                            adversario_nome="VASCO", tipo_participante="clube", nomes_do_concurso=["FLAMENGO", "VASCO"])
    assert [s["sinal"] for s in sinais] == ["contratacao"]


def test_palavra_comum_nao_vira_outro_time():
    """'Nova' não identifica o Vila Nova: a manchete do Portugal continua do Portugal."""
    sinais = extrair_sinais([{"titulo": "Nova lesão preocupa Portugal", "url": ""}], participante_nome="PORTUGAL",
                            adversario_nome="NORUEGA", tipo_participante="selecao", nomes_do_concurso=NOMES)
    assert [s["sinal"] for s in sinais] == ["lesao_titular"]


def test_desfalque_confirmado_do_proprio_jogo_continua_com_peso():
    sinais = extrair_sinais([{"titulo": "Paysandu tem três desfalques contra a Ferroviária", "url": ""}],
                            participante_nome="PAYSANDU", adversario_nome="FERROVIARIA", tipo_participante="clube",
                            nomes_do_concurso=NOMES)
    assert [s["sinal"] for s in sinais] == ["desfalque_multiplo"]
    assert calcular_ajuste(sinais)["ajuste_aplicado"] == -4.0


def test_sem_contexto_do_concurso_o_comportamento_antigo_se_mantem():
    """Chamada antiga (sem adversário nem nomes do concurso): só as barreiras 1 a 3."""
    sinais = extrair_sinais([{"titulo": M["7"], "url": ""}], participante_nome="BRAGANTINO")
    assert {s["sinal"] for s in sinais} == {"desfalque_possivel"}
