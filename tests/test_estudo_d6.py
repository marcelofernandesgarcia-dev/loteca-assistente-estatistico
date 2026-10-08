"""D6 — concursos pulverizados: contas sobre dados SINTÉTICOS."""
import random

import numpy as np
import pytest

import config
from stats import estudo_d6


def test_auc_valores_conhecidos():
    assert estudo_d6._auc(np.array([3.0, 4.0, 1.0, 2.0]), np.array([True, True, False, False])) == 1.0
    assert estudo_d6._auc(np.array([1.0, 2.0, 3.0, 4.0]), np.array([True, True, False, False])) == 0.0
    assert estudo_d6._auc(np.array([1.0, 1.0]), np.array([True, False])) == 0.5


def _linhas(sinal_real: bool, n=400):
    sorteio = random.Random(3)
    linhas = []
    for i in range(n):
        pulverizado = sorteio.random() < 0.1
        base = {k: sorteio.gauss(5, 1) for k in estudo_d6.ANTES}
        if sinal_real and pulverizado:
            base["selecoes"] += 2.0
        linhas.append({"ano": 2010 + i % 10, "pulverizado": pulverizado, **base})
    return linhas


def test_diferenca_detecta_sinal_real_e_nao_inventa(monkeypatch):
    monkeypatch.setattr(config, "Q7_PERMUTACOES", 300)
    assert estudo_d6._diferenca(_linhas(True), "selecoes", 1)["p"] < 0.01
    assert estudo_d6._diferenca(_linhas(False), "selecoes", 1)["p"] > 0.05


def test_teste_fora_da_amostra_ve_o_sinal_e_fica_no_acaso_sem_ele(monkeypatch):
    monkeypatch.setattr(config, "Q7_REPETICOES_BOOTSTRAP", 300)
    com = estudo_d6.teste_fora_da_amostra(_linhas(True, 1000))
    sem = estudo_d6.teste_fora_da_amostra(_linhas(False, 1000))
    assert com["auc"] > 0.75 and com["perceptivel"]
    assert sem["ic_inferior"] < 0.5 < sem["ic_superior"] or sem["auc"] == pytest.approx(0.5, abs=0.08)
