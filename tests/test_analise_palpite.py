import pytest

import config
from stats.analise_palpite import (
    A_FAVOR,
    COBERTURA_TOTAL,
    CONTRA_O_FAVORITO,
    EQUILIBRADO,
    NAO_BASTOU,
    NAO_FEZ_DIFERENCA,
    SALVOU,
    ZEBRA,
    agregar_historico,
    analisar_palpite,
    avaliar_depois_do_resultado,
    chance_do_bilhete,
    classificar_jogo,
    formatar_uma_em,
)

# Percentuais reais do concurso 1272 (jogos 1, 4 e 11), usados como exemplo.
INGLATERRA_ESPANHA = {"1": 21.0, "X": 27.0, "2": 52.0}
BOTAFOGO_MARINGA = {"1": 78.0, "X": 13.0, "2": 8.0}
FORTALEZA_ATHLETIC = {"1": 38.0, "X": 29.0, "2": 34.0}


@pytest.mark.parametrize(
    "pct, marcacoes, esperado",
    [
        (INGLATERRA_ESPANHA, ["2"], A_FAVOR),
        (INGLATERRA_ESPANHA, ["1"], ZEBRA),  # 21% < 25%
        (INGLATERRA_ESPANHA, ["X"], CONTRA_O_FAVORITO),  # 27%: possível, mas não o favorito
        (FORTALEZA_ATHLETIC, ["1"], EQUILIBRADO),  # favorito com 38% < 45%
        (FORTALEZA_ATHLETIC, ["1", "X", "2"], COBERTURA_TOTAL),
        (BOTAFOGO_MARINGA, ["X", "2"], ZEBRA),  # duplo só com zebras
    ],
)
def test_classificar_jogo(pct, marcacoes, esperado):
    assert classificar_jogo(pct, marcacoes)["categoria"] == esperado


def test_jogo_sem_marcacao_e_erro():
    with pytest.raises(ValueError):
        classificar_jogo(INGLATERRA_ESPANHA, [])


def test_duplo_informa_quanto_a_segunda_coluna_soma():
    leitura = classificar_jogo(INGLATERRA_ESPANHA, ["2", "X"])
    assert leitura["categoria"] == A_FAVOR
    assert leitura["chance_coberta"] == 79.0 and leitura["ganho_do_multiplo"] == 27.0
    assert leitura["melhor_marcada"] == "2" and leitura["multiplicador"] == 2


def test_duplo_com_zebra_lista_a_zebra_mesmo_a_favor():
    leitura = classificar_jogo(BOTAFOGO_MARINGA, ["1", "2"])
    assert leitura["categoria"] == A_FAVOR and leitura["zebras"] == ["2"]


def test_limiar_de_zebra_e_parametro(monkeypatch):
    monkeypatch.setattr(config, "ANALISE_LIMIAR_ZEBRA", 20.0)
    assert classificar_jogo(INGLATERRA_ESPANHA, ["1"])["categoria"] == CONTRA_O_FAVORITO


def test_chance_do_bilhete_exata_em_caso_pequeno():
    chance = chance_do_bilhete([50.0, 50.0])
    assert chance["chance_todos"] == pytest.approx(0.25)
    assert chance["chance_todos_menos_um_ou_mais"] == pytest.approx(0.75)
    assert chance["acertos_esperados"] == pytest.approx(1.0)


def test_chance_do_bilhete_com_triplos_e_100_por_cento():
    assert chance_do_bilhete([100.0] * 14)["chance_todos"] == pytest.approx(1.0)


@pytest.mark.parametrize(
    "p, texto",
    [(0.0, "praticamente nula"), (1 / 1297, "1 em 1.297"), (0.25, "25%"), (0.0084, "1 em 119")],
)
def test_formatar_uma_em(p, texto):
    assert formatar_uma_em(p) == texto


def _jogo(num, pct, marcacoes, **extra):
    return {"num_jogo": num, "casa": f"CASA{num}", "fora": f"FORA{num}", "pct": pct, "marcacoes": marcacoes, **extra}


def test_analise_sugere_mover_duplo_para_onde_rende_mais():
    jogos = [
        _jogo(1, BOTAFOGO_MARINGA, ["1", "X"]),  # duplo soma só 13
        _jogo(2, INGLATERRA_ESPANHA, ["2"]),  # aqui o duplo somaria 27
    ]
    analise = analisar_palpite(jogos)
    assert analise["melhores_duplos"][0] == {"num_jogo": 2, "coluna_extra": "X", "ganho": 27.0}
    assert analise["trocas"] == [{"de": 1, "ganho_atual": 13.0, "para": 2, "coluna_extra": "X", "ganho_novo": 27.0}]
    assert any("O duplo do jogo 1 soma 13 pontos" in f for f in analise["frases"])


def test_analise_nao_sugere_troca_abaixo_da_diferenca_minima():
    jogos = [_jogo(1, INGLATERRA_ESPANHA, ["2", "X"]), _jogo(2, {"1": 60.0, "X": 25.0, "2": 15.0}, ["1"])]
    assert analisar_palpite(jogos)["trocas"] == []  # 25 - 27 < 10


def test_analise_resume_categorias_zebras_e_jogos_sem_base():
    jogos = [
        _jogo(1, INGLATERRA_ESPANHA, ["1"]),
        _jogo(2, BOTAFOGO_MARINGA, ["1"]),
        _jogo(3, {"1": 47.0, "X": 26.0, "2": 27.0}, ["1"], sem_base_propria=True),
        _jogo(4, FORTALEZA_ATHLETIC, ["1", "X", "2"]),
    ]
    analise = analisar_palpite(jogos)
    assert analise["resumo_categorias"][ZEBRA] == 1 and analise["resumo_categorias"][A_FAVOR] == 2
    assert analise["zebras"] == [{"num_jogo": 1, "coluna": "1", "pct": 21.0, "casa": "CASA1", "fora": "FORA1"}]
    assert analise["sem_base_propria"] == [3]
    assert analise["multiplos"][0]["tipo"] == "triplo" and analise["multiplos"][0]["chance_depois"] == 101.0
    frases = " ".join(analise["frases"])
    assert "1 são zebra" in frases and "Nos jogos 3" in frases and "prêmio tende a ser menos dividido" in frases


def test_depois_do_resultado_diz_se_o_duplo_salvou():
    jogos = [
        {"pct": INGLATERRA_ESPANHA, "marcacoes": ["2", "X"], "resultado": "X", "num_jogo": 1},  # salvou
        {"pct": BOTAFOGO_MARINGA, "marcacoes": ["1", "X"], "resultado": "1", "num_jogo": 2},  # não fez diferença
        {"pct": FORTALEZA_ATHLETIC, "marcacoes": ["1", "X"], "resultado": "2", "num_jogo": 3},  # não bastou
        {"pct": INGLATERRA_ESPANHA, "marcacoes": ["2"], "resultado": "1", "num_jogo": 4},  # zebra aconteceu
    ]
    avaliacao = avaliar_depois_do_resultado(jogos)
    assert avaliacao["multiplos"] == {SALVOU: 1, NAO_FEZ_DIFERENCA: 1, NAO_BASTOU: 1}
    assert avaliacao["acertos"] == 2
    assert avaliacao["zebras_que_aconteceram"] == [{"num_jogo": 4, "marcou": False}]
    assert avaliacao["por_categoria"][A_FAVOR] == {"marcacoes": 3, "acertos": 2}


def test_historico_so_mostra_taxa_com_amostra_minima(monkeypatch):
    monkeypatch.setattr(config, "ANALISE_AMOSTRA_MINIMA", 3)
    bilhete = [
        {"pct": INGLATERRA_ESPANHA, "marcacoes": ["2"], "resultado": "2", "motivos": ["Intuição"]},
        {"pct": BOTAFOGO_MARINGA, "marcacoes": ["X"], "resultado": "1", "motivos": []},
    ]
    historico = agregar_historico([bilhete, bilhete])
    assert historico["bilhetes"] == 2 and historico["acertos_medios"] == 1.0
    assert historico["por_motivo"]["Intuição"] == {"marcacoes": 2, "acertos": 2, "taxa": None}  # 2 < 3
    assert historico["por_categoria"][A_FAVOR]["taxa"] is None
    # A sugestão do app para este par de jogos é: jogo 1 duplo 2X (o mais
    # incerto), jogo 2 seco 1. Você divergiu nos dois jogos, nos dois bilhetes:
    # no jogo 1 os dois acertam (resultado 2); no jogo 2 só o app (resultado 1).
    assert historico["divergencias"]["jogos"] == 4
    assert historico["divergencias"]["voce_acertou"] == 2 and historico["divergencias"]["app_acertou"] == 4


def test_historico_com_amostra_suficiente_calcula_taxa(monkeypatch):
    monkeypatch.setattr(config, "ANALISE_AMOSTRA_MINIMA", 2)
    bilhete = [{"pct": INGLATERRA_ESPANHA, "marcacoes": ["2"], "resultado": "2", "categoria": A_FAVOR}]
    historico = agregar_historico([bilhete, bilhete, bilhete])
    assert historico["por_categoria"][A_FAVOR]["taxa"] == 100.0


def test_historico_vazio():
    historico = agregar_historico([])
    assert historico["bilhetes"] == 0 and historico["acertos_medios"] is None
