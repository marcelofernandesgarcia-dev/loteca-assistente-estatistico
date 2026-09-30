"""Precisão da extração de sinais (etapa C2 do roteiro) contra um conjunto de
manchetes ROTULADAS POR MIM (fictícias, nomes inventados) -- não são
manchetes reais nem foram validadas pelo usuário. Servem para provar, com
teste, que as duas barreiras (nome do participante no título; negação anula o
sinal) funcionam nos casos que motivaram o pedido (ver docs/plano-fase3-melhorias.md,
item C2). A medição de precisão contra notícia REAL, rotulada pelo usuário,
segue pendente -- ver docs/avaliacao-plano-tecnico-29-09-2026.md.
"""
import pytest

from externo.analise import extrair_sinais

PARTICIPANTE = "CLUBE ALFA"

# (titulo, deve_gerar_sinal, motivo) -- casos que o filtro atual RESOLVE.
CASOS = [
    ("Atacante do Clube Alfa está lesionado e desfalca o time", True, "sinal verdadeiro: nome + palavra-chave"),
    ("Zagueiro do Clube Alfa é suspenso pelo STJD", True, "sinal verdadeiro: nome + palavra-chave"),
    ("Clube Alfa vive crise após três derrotas seguidas", True, "sinal verdadeiro: nome + palavra-chave"),
    ("Atacante do Clube Alfa está sem lesão e treina normalmente", False, "negação: 'sem lesão' não é lesão"),
    ("Volante do Clube Alfa está recuperado e volta aos treinos", False, "negação: recuperado/volta aos treinos"),
    ("Zagueiro do Clube Alfa é liberado pelo departamento médico", False, "negação: liberado"),
    ("Atacante do Clube Beta está lesionado e desfalca o time", False, "outro participante, não o Clube Alfa"),
    ("Clube Alfa confirma treino aberto neste sábado", False, "sem palavra-chave"),
    # Fase Q1 (30/09/2026): sinais informativos, mesmas barreiras.
    ("Clube Alfa contrata meia para a sequência da Série B", True, "contratação"),
    ("Clube Alfa demite técnico após derrota em casa", True, "troca de técnico"),
    ("Jogadores do Clube Alfa cobram salários atrasados", True, "atraso de salário"),
    ("Zagueiro rescinde com o Clube Alfa e deixa o clube", True, "saída de jogador"),
    ("Clube Alfa desmente contratação de atacante", False, "negação: desmente"),
    ("Clube Alfa mantém o técnico mesmo após a derrota", False, "negação: mantém o técnico"),
    ("Clube Alfa quita salários atrasados do elenco", False, "negação: quita salários"),
    ("Clube Beta contrata meia do futebol paulista", False, "contratação de outro participante"),
    # Barreira 3 e "ex-", a partir da leitura de teste com notícia real (30/09/2026).
    ("Jogadoras do Clube Alfa cobram salários atrasados", False, "futebol feminino, não o time da Loteca"),
    ("Clube Alfa anuncia novo técnico do futebol feminino", False, "futebol feminino"),
    ("Atacante do sub-20 do Clube Alfa está lesionado", False, "categoria de base: não mexe no percentual"),
    ("Time Gama anuncia contratação de goleiro ex-Alfa", False, "ex-Alfa: jogador que já saiu do clube"),
    ("Ex-técnico do Clube Beta é o novo técnico do Clube Alfa", True, "'ex-técnico' não apaga a menção ao Alfa"),
    ("Clube Beta tem cinco desfalques diante do Clube Alfa", False, "Alfa é o adversário: desfalque é do Beta"),
    ("Com reforço na zaga, Clube Beta embarca para enfrentar o Clube Alfa", False, "Alfa é o adversário"),
    ("Clube Alfa tem desfalques contra o Clube Beta", True, "Alfa é o assunto; Beta, o adversário"),
]


def test_desfalque_diante_do_adversario_fica_so_com_quem_tem_o_desfalque():
    titulo = [{"titulo": "Escalação: Clube Beta tem cinco desfalques diante do Clube Alfa", "fonte": "X"}]
    assert not extrair_sinais(titulo, participante_nome="CLUBE ALFA")
    assert {s["sinal"] for s in extrair_sinais(titulo, participante_nome="CLUBE BETA")} == {"desfalque_multiplo"}


@pytest.mark.parametrize("titulo,deve_gerar_sinal,motivo", CASOS)
def test_caso_rotulado(titulo, deve_gerar_sinal, motivo):
    sinais = extrair_sinais([{"titulo": titulo, "fonte": "Veículo de teste"}], participante_nome=PARTICIPANTE)
    if deve_gerar_sinal:
        assert sinais, motivo
    else:
        assert not sinais, motivo


@pytest.mark.parametrize(
    "titulo,sinal",
    [
        ("Clube Alfa contrata meia para a sequência da Série B", "contratacao"),
        ("Clube Alfa demite técnico após derrota em casa", "troca_de_tecnico"),
        ("Jogadores do Clube Alfa cobram salários atrasados", "atraso_salarial"),
        ("Zagueiro rescinde com o Clube Alfa e deixa o clube", "saida_de_jogador"),
    ],
)
def test_sinais_informativos_recebem_o_tipo_certo(titulo, sinal):
    sinais = extrair_sinais([{"titulo": titulo, "fonte": "Veículo de teste"}], participante_nome=PARTICIPANTE)
    assert {s["sinal"] for s in sinais} == {sinal}


def test_precisao_no_conjunto_rotulado_e_100_por_cento():
    """Nenhum falso positivo nem falso negativo nos casos acima -- conjunto
    pequeno e desenhado para cobrir os riscos que motivaram o C2, não uma
    amostra representativa de notícia real."""
    acertos = 0
    for titulo, deve_gerar_sinal, _motivo in CASOS:
        sinais = extrair_sinais([{"titulo": titulo, "fonte": "Veículo de teste"}], participante_nome=PARTICIPANTE)
        if bool(sinais) == deve_gerar_sinal:
            acertos += 1
    assert acertos == len(CASOS)


def test_limitacao_conhecida_jogador_do_adversario_ainda_gera_falso_positivo():
    """Documenta, sem maquiar, um caso que o filtro NÃO resolve: a manchete
    fala do jogador do ADVERSÁRIO do Clube Alfa, não de um jogador do Time
    Alfa -- mas como o nome 'Clube Alfa' aparece no título, passa pela barreira
    de menção. Distinguir sujeito da frase (quem sofreu a suspensão) exigiria
    análise sintática, fora do escopo da heurística por palavra-chave (ver
    docs/plano-fase3-melhorias.md: leitura por modelo de linguagem fica como
    opção futura). Este teste falha se alguém 'consertar' isso sem querer
    quebrar outra coisa -- é um lembrete, não uma meta batida."""
    sinais = extrair_sinais(
        [{"titulo": "Craque do adversário do Clube Alfa é suspenso pelo STJD", "fonte": "Veículo de teste"}],
        participante_nome=PARTICIPANTE,
    )
    assert sinais  # falso positivo conhecido, registrado de propósito


def test_sem_nome_do_participante_nao_filtra_por_mencao():
    """Chamada antiga (sem participante_nome) mantém compatibilidade: não filtra
    por menção, só por negação -- comportamento de transição, não recomendado
    para código novo (a varredura real sempre passa o nome)."""
    sinais = extrair_sinais([{"titulo": "Atacante do Clube Beta está lesionado", "fonte": "X"}])
    assert sinais


def test_sigla_curta_usa_o_nome_inteiro_como_substring():
    sinais = extrair_sinais(
        [{"titulo": "CRB confirma lesão do zagueiro titular", "fonte": "X"}], participante_nome="CRB"
    )
    assert sinais
    sem_mencao = extrair_sinais(
        [{"titulo": "Zagueiro do rival está lesionado", "fonte": "X"}], participante_nome="CRB"
    )
    assert not sem_mencao
