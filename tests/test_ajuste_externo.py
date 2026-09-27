import config
from externo.ajuste import calcular_ajuste
from externo.analise import extrair_sinais


def test_extrai_sinal_de_lesao_do_titulo():
    noticias = [{"titulo": "Atacante lesionado desfalca o time no fim de semana", "fonte": "Site X"}]
    sinais = extrair_sinais(noticias)
    tipos = {s["sinal"] for s in sinais}
    assert "lesao_titular" in tipos


def test_sem_noticias_relevantes_nao_gera_sinal():
    noticias = [{"titulo": "Time confirma treino aberto ao público neste sábado", "fonte": "Site Y"}]
    sinais = extrair_sinais(noticias)
    assert sinais == []


def test_ajuste_e_zero_sem_sinais():
    resultado = calcular_ajuste([])
    assert resultado["ajuste_aplicado"] == 0.0
    assert "nenhum sinal" in resultado["resumo"]


def test_ajuste_respeita_o_teto():
    sinais = [
        {"sinal": "lesao_titular", "evidencia": "", "fonte": ""},
        {"sinal": "suspensao_titular", "evidencia": "", "fonte": ""},
        {"sinal": "desfalque_multiplo", "evidencia": "", "fonte": ""},
        {"sinal": "tendencia_negativa_imprensa", "evidencia": "", "fonte": ""},
    ]
    resultado = calcular_ajuste(sinais)
    soma_bruta = sum(config.AJUSTE_EXTERNO_PESOS[s["sinal"]] for s in sinais)
    assert soma_bruta < -config.AJUSTE_EXTERNO_TETO_PONTOS
    assert resultado["ajuste_aplicado"] == -config.AJUSTE_EXTERNO_TETO_PONTOS


def test_mesmo_sinal_repetido_em_varias_noticias_conta_uma_vez():
    sinais = [
        {"sinal": "lesao_titular", "evidencia": "manchete 1", "fonte": "A"},
        {"sinal": "lesao_titular", "evidencia": "manchete 2", "fonte": "B"},
    ]
    resultado = calcular_ajuste(sinais)
    assert resultado["ajuste_aplicado"] == config.AJUSTE_EXTERNO_PESOS["lesao_titular"]
