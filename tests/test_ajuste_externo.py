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


import itertools  # noqa: E402
import json  # noqa: E402
import sqlite3  # noqa: E402

import pytest  # noqa: E402

import db  # noqa: E402
from externo import varredura  # noqa: E402
from externo.ajuste import aplicar_ajuste, montar_evidencias  # noqa: E402
from externo.percentual_final import ajustes_do_concurso, percentuais_do_jogo  # noqa: E402

HISTORICOS = [
    {"1": 47.0, "X": 26.0, "2": 27.0},
    {"1": 80.0, "X": 15.0, "2": 5.0},
    {"1": 3.0, "X": 2.0, "2": 95.0},
    {"1": 100.0, "X": 0.0, "2": 0.0},
    {"1": 34.0, "X": 33.0, "2": 33.0},
]
AJUSTES = [-8.0, -3.0, -0.5, 0.0, 1.0, 4.0, 8.0]


def test_aplicar_ajuste_sempre_soma_100_sem_negativos_e_dentro_do_teto():
    teto = config.AJUSTE_EXTERNO_TETO_PONTOS
    for hist, ac, af in itertools.product(HISTORICOS, AJUSTES, AJUSTES):
        final = aplicar_ajuste(hist, ac, af)["final"]
        assert sum(final.values()) == pytest.approx(100.0), (hist, ac, af)
        assert all(v >= -1e-9 for v in final.values()), (hist, ac, af)
        for chave in hist:
            assert abs(final[chave] - hist[chave]) <= teto + 1e-9, (hist, ac, af, chave)


def test_ajuste_zero_nao_muda_nada():
    hist = {"1": 47.0, "X": 26.0, "2": 27.0}
    resultado = aplicar_ajuste(hist, 0.0, 0.0)
    assert resultado["final"] == hist and resultado["deslocamento"] == 0.0


def test_lesao_no_mandante_favorece_visitante_e_o_que_sai_e_proporcional():
    resultado = aplicar_ajuste({"1": 50.0, "X": 30.0, "2": 20.0}, -4.0, 0.0)
    assert resultado["final"]["2"] == pytest.approx(24.0)  # visitante ganha os 4 pontos
    assert resultado["final"]["1"] == pytest.approx(50.0 - 4 * 50 / 80)
    assert resultado["final"]["X"] == pytest.approx(30.0 - 4 * 30 / 80)
    assert resultado["deslocamento"] == pytest.approx(-4.0)


def test_ajustes_iguais_nos_dois_times_se_compensam():
    hist = {"1": 47.0, "X": 26.0, "2": 27.0}
    assert aplicar_ajuste(hist, -3.0, -3.0)["final"] == hist


def test_ajuste_liquido_e_limitado_ao_teto_mesmo_com_os_dois_lados_no_maximo():
    hist = {"1": 47.0, "X": 26.0, "2": 27.0}
    resultado = aplicar_ajuste(hist, 8.0, -8.0)
    assert resultado["deslocamento"] == pytest.approx(config.AJUSTE_EXTERNO_TETO_PONTOS)
    assert resultado["final"]["1"] == pytest.approx(55.0)


def test_favorito_absoluto_nao_passa_de_100():
    resultado = aplicar_ajuste({"1": 100.0, "X": 0.0, "2": 0.0}, 8.0, 0.0)
    assert resultado["final"] == {"1": 100.0, "X": 0.0, "2": 0.0}


def test_montar_evidencias_tira_repeticao_e_guarda_manchete_veiculo_e_link():
    sinais = [
        {"sinal": "lesao_titular", "evidencia": "Zagueiro lesionado", "fonte": "Veículo A", "url": "http://a"},
        {"sinal": "lesao_titular", "evidencia": "Zagueiro lesionado", "fonte": "Veículo A", "url": "http://a"},
        {"sinal": "suspensao_titular", "evidencia": "Volante suspenso", "fonte": "Veículo B"},
    ]
    evidencias = montar_evidencias(sinais)
    assert len(evidencias) == 2
    assert evidencias[0] == {"sinal": "lesao_titular", "manchete": "Zagueiro lesionado", "fonte": "Veículo A", "url": "http://a", "publicado_em": ""}
    assert evidencias[1]["url"] == ""


@pytest.fixture()
def banco():
    conexao = sqlite3.connect(":memory:")
    conexao.row_factory = sqlite3.Row
    conexao.executescript(db.SCHEMA)
    casa = db.obter_ou_criar_participante(conexao, "TIME A", "clube", "SP")
    fora = db.obter_ou_criar_participante(conexao, "TIME B", "clube", "RJ")
    conexao.execute("INSERT INTO concursos (numero) VALUES (7)")
    conexao.execute(
        "INSERT INTO jogos (concurso_numero, num_jogo, casa_id, fora_id) VALUES (7, 1, ?, ?)", (casa, fora)
    )
    for numero, resultado in enumerate("1111" "1XXX" "22", start=1):  # histórico mínimo: 50% / 30% / 20%
        conexao.execute("INSERT INTO historico_valorfinal (concurso, num_jogo, resultado) VALUES (1, ?, ?)", (numero, resultado))
    return conexao, casa, fora


def test_varredura_grava_evidencias_e_percentual_final_que_soma_100(banco, monkeypatch):
    conexao, casa, fora = banco
    noticias = {
        "TIME A": [{"titulo": "Atacante do Time A está lesionado e desfalca o time", "fonte": "Veículo X", "url": "http://x/1"}],
        "TIME B": [],
    }
    monkeypatch.setattr(varredura, "buscar_noticias", lambda nome, **kw: noticias[nome])
    varredura.executar_para_concurso(conexao, 7)

    ajustes = ajustes_do_concurso(conexao, 7)
    assert ajustes[casa]["ajuste"] < 0 and ajustes[fora]["ajuste"] == 0
    assert ajustes[casa]["evidencias"][0]["manchete"] == "Atacante do Time A está lesionado e desfalca o time"
    assert ajustes[casa]["evidencias"][0]["url"] == "http://x/1"

    linhas = {r["participante_id"]: r for r in conexao.execute("SELECT * FROM percentuais")}
    calculado = percentuais_do_jogo(conexao, casa, fora, ajustes)
    assert linhas[casa]["percentual_final"] == pytest.approx(calculado["final"]["1"])
    assert linhas[fora]["percentual_final"] == pytest.approx(calculado["final"]["2"])
    assert linhas[casa]["percentual_historico"] == pytest.approx(calculado["historico"]["1"])
    assert calculado["ajustado"] and calculado["final"]["2"] > calculado["historico"]["2"]
    assert sum(calculado["final"].values()) == pytest.approx(100.0)


def test_sem_varredura_o_percentual_final_e_o_historico(banco):
    conexao, casa, fora = banco
    calculado = percentuais_do_jogo(conexao, casa, fora, ajustes_do_concurso(conexao, 7))
    assert calculado["final"] == calculado["historico"] and not calculado["ajustado"]
    assert calculado["ajustes"] == {"casa": None, "fora": None}


def test_ultima_varredura_de_cada_participante_prevalece(banco):
    conexao, casa, _ = banco
    for coletado, ajuste, evidencias in (("2026-09-20T10:00:00", -3.0, "[]"), ("2026-09-24T10:00:00", 0.0, "[]")):
        conexao.execute(
            "INSERT INTO fatores_externos (participante_id, concurso_numero, coletado_em, ajuste_aplicado, evidencias)"
            " VALUES (?, 7, ?, ?, ?)", (casa, coletado, ajuste, evidencias),
        )
    assert ajustes_do_concurso(conexao, 7)[casa]["ajuste"] == 0.0


def test_evidencias_corrompidas_nao_derrubam_a_leitura(banco):
    conexao, casa, _ = banco
    conexao.execute(
        "INSERT INTO fatores_externos (participante_id, concurso_numero, coletado_em, ajuste_aplicado, evidencias)"
        " VALUES (?, 7, '2026-09-24T10:00:00', -2.0, '{quebrado')", (casa,),
    )
    assert ajustes_do_concurso(conexao, 7)[casa]["evidencias"] == []
