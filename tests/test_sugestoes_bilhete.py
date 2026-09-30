import pytest

import config
from stats.calibracao_bilhete import (
    efeito_medido_das_trocas,
    frase_da_calibracao,
    frase_do_efeito,
    frequencia_por_custo,
)
from stats.sugestoes_bilhete import (
    complexidade_dos_jogos,
    frase_da_economia,
    frase_da_troca,
    marcacao_contra_o_favorito,
    melhor_no_ano,
    montar_sugestoes,
)

FACIL = {"1": 70.0, "X": 20.0, "2": 10.0}
EQUILIBRADO = {"1": 36.0, "X": 33.0, "2": 31.0}
MEDIO = {"1": 50.0, "X": 30.0, "2": 20.0}


def _jogo(num, pct, marcacoes, categoria="a_favor"):
    return {"num_jogo": num, "pct": pct, "marcacoes": marcacoes, "categoria": categoria}


# --- Complexidade (recomendação 1) ---

def test_melhor_no_ano_so_quando_ha_confianca():
    assert melhor_no_ano({"melhor": "fora", "fontes_diferentes": False, "amostra_pequena": False}) == "fora"
    assert melhor_no_ano({"melhor": "fora", "fontes_diferentes": True, "amostra_pequena": False}) is None
    assert melhor_no_ano({"melhor": "fora", "fontes_diferentes": False, "amostra_pequena": True}) is None
    assert melhor_no_ano(None) is None


def test_complexidade_dos_jogos_usa_o_ano_so_com_confianca():
    jogos = [_jogo(1, FACIL, ["1"]), _jogo(2, FACIL, ["1"]), _jogo(3, EQUILIBRADO, ["1"])]
    niveis = complexidade_dos_jogos(
        jogos,
        {1: {"melhor": "fora", "fontes_diferentes": False, "amostra_pequena": False},
         2: {"melhor": "fora", "fontes_diferentes": True, "amostra_pequena": False}},
    )
    assert niveis[1]["nivel"] == "media" and "ano em curso" in niveis[1]["motivos"][0]
    assert niveis[2]["nivel"] == "baixa"
    assert niveis[3]["nivel"] == "alta"


# --- Sugestões (recomendações 2 e 4) ---

def test_sugestoes_mantem_o_custo_e_a_forma_do_bilhete():
    jogos = [_jogo(7, FACIL, ["1", "X"]), _jogo(8, EQUILIBRADO, ["1"]), _jogo(9, MEDIO, ["2"], "contra_o_favorito")]
    sugestoes = montar_sugestoes(jogos)
    assert sugestoes["custo"] == 2
    for troca in sugestoes["trocas"]:
        assert sum(len(m) for m in troca["marcacoes"]) == 4 and sorted(len(m) for m in troca["marcacoes"]) == [1, 1, 2]
        assert troca["chance_depois"] > troca["chance_antes"]
    # O jogo 9 está marcado em "2" (20%): levar o duplo para lá (1X) rende mais do que para o jogo 8.
    descricoes = [t["descricao"] for t in sugestoes["trocas"]]
    assert "levar o duplo do jogo 7 para o jogo 9" in descricoes[0]
    assert any("para o jogo 8" in d for d in descricoes)
    assert marcacao_contra_o_favorito(jogos) == [9]


def test_bilhete_ja_otimo_nao_recebe_troca_e_unico_duplo_nao_tem_economia():
    jogos = [_jogo(1, FACIL, ["1"]), _jogo(2, EQUILIBRADO, ["1", "X"])]
    sugestoes = montar_sugestoes(jogos)
    assert sugestoes["trocas"] == [] and sugestoes["economias"] == []  # o volante exige ao menos um duplo


def test_economia_aparece_com_dois_multiplos_e_nao_passa_do_limite_configurado():
    jogos = [_jogo(1, MEDIO, ["1", "X"]), _jogo(2, EQUILIBRADO, ["1", "X", "2"]), _jogo(3, FACIL, ["1", "X"])]
    economias = montar_sugestoes(jogos)["economias"]
    assert 1 <= len(economias) <= config.SUGESTOES_MAX_ECONOMIAS
    assert all(e["economia_reais"] > 0 for e in economias)


def test_frases_trazem_os_numeros_que_as_sustentam():
    troca = montar_sugestoes([_jogo(7, FACIL, ["1", "X"]), _jogo(8, EQUILIBRADO, ["1"])])["trocas"][0]
    frase = frase_da_troca(troca)
    assert frase.startswith("Levar o duplo do jogo 7") and "pelo mesmo custo" in frase and "%" in frase
    economia = montar_sugestoes([_jogo(1, MEDIO, ["1", "X"]), _jogo(2, EQUILIBRADO, ["1", "X", "2"])])["economias"][0]
    assert f"Jogo {economia['jogo']}: tirar a coluna {economia['tirar']}" in frase_da_economia(economia)


# --- Calibração (recomendação 3) ---

def _concursos(n, resultado="1"):
    pcts = [{"1": 60.0, "X": 25.0, "2": 15.0}] * 14
    return [[(p, resultado) for p in pcts] for _ in range(n)]


def test_frequencia_por_custo_conta_o_que_aconteceu_e_o_que_era_previsto():
    freq = frequencia_por_custo(_concursos(10), 1, 0)
    assert (freq["concursos"], freq["apostas"], freq["custo"]) == (10, 2, 4.0)
    assert freq["fez_14"] == 10 and freq["fez_13_ou_mais"] == 10  # todo favorito acertou
    assert 0 < freq["previsto_14"] < freq["previsto_13_ou_mais"] <= 10
    assert frequencia_por_custo(_concursos(10, "2"), 1, 0)["fez_12_ou_mais"] == 0


def test_frequencia_por_custo_recusa_combinacao_impossivel_e_base_vazia():
    assert frequencia_por_custo(_concursos(3), 10, 5) is None
    assert frequencia_por_custo([], 1, 0) is None


def test_frase_da_calibracao_com_e_sem_base_suficiente(monkeypatch):
    sem_base = frase_da_calibracao(frequencia_por_custo(_concursos(5), 2, 1))
    assert "Ainda não há concursos passados suficientes" in sem_base and "limite superior" in sem_base
    monkeypatch.setattr(config, "CALIBRACAO_MIN_CONCURSOS", 5)
    com_base = frase_da_calibracao(frequencia_por_custo(_concursos(5, "2"), 2, 1))
    assert "em 5 concursos passados" in com_base and "2 duplo(s) e 1 triplo(s) (R$ 24,00)" in com_base
    assert "fizeram 13 ou mais em 0 e 14 em 0" in com_base and "Os percentuais são mais confiantes" in com_base
    assert "Ainda não há" in frase_da_calibracao(None)


def test_efeito_medido_respeita_a_base_minima_e_a_combinacao(monkeypatch):
    assert efeito_medido_das_trocas(_concursos(5), 1, 0) is None  # poucos concursos
    monkeypatch.setattr(config, "CALIBRACAO_MIN_CONCURSOS", 5)
    assert efeito_medido_das_trocas(_concursos(5), 0, 0) is None
    assert efeito_medido_das_trocas(_concursos(5), 20, 0) is None
    assert frase_do_efeito(None) == ""


def test_frase_do_efeito_avisa_que_ajuda_pouco():
    frase = frase_do_efeito({"concursos": 1127, "diferenca_media": 0.3580, "ganhou": 628, "perdeu": 219})
    assert "+0,36 acerto por concurso" in frase and "Ajuda pouco" in frase and "13 ou 14" in frase
    assert "Nos 1.127 concursos testados" in frase  # separador de milhar em português
