"""S6 — termômetro do perfil do concurso: contas e textos sobre dados SINTÉTICOS."""
import random
import sys
from pathlib import Path

import pytest

import config
from stats import estudo_d6
from stats import perfil_concurso as pc

RAIZ = Path(__file__).resolve().parent.parent
if str(RAIZ / "app") not in sys.path:
    sys.path.insert(0, str(RAIZ / "app"))


def _linhas(n=600):
    """Concursos sintéticos em que os pulverizados têm mais jogos de seleções (o achado do D6, exagerado)."""
    sorteio = random.Random(5)
    linhas = []
    for i in range(n):
        pulverizado = sorteio.random() < 0.1
        base = {k: sorteio.gauss(5, 1) for k in estudo_d6.ANTES}
        base["selecoes"] = sorteio.gauss(1, 0.7) + (3 if pulverizado else 0)
        linhas.append({"ano": 2010 + i % 12, "pulverizado": pulverizado, **base})
    return linhas


def _jogos(tipo: tuple, n=14):
    return [{"p": {"1": 50, "X": 30, "2": 20}, "casa": tipo, "fora": tipo} for _ in range(n)]


SELECAO, CLUBE_BR = ("selecao", "BRA"), ("clube", "SP")


@pytest.fixture(scope="module")
def preparo():
    return pc.preparar_de_linhas(_linhas())


def test_faixa_da_posicao_nos_limites():
    assert pc.faixa_da_posicao(config.PERFIL_LIMITE_FAVORITOS) == "favoritos"
    assert pc.faixa_da_posicao(config.PERFIL_LIMITE_DIFICIL) == "dificil"
    assert pc.faixa_da_posicao(0.5) == "comum"


def test_taxas_por_faixa_contam_cada_faixa_e_o_geral():
    taxas = pc.taxas_por_faixa([0.9, 0.95, 0.5, 0.1], [True, False, False, False])
    assert taxas["favoritos"] == {"concursos": 2, "pulverizados": 1, "taxa": 0.5}
    assert taxas["dificil"]["taxa"] == 0.0 and taxas["geral"]["pulverizados"] == 1
    assert pc.taxas_por_faixa([], [])["favoritos"]["taxa"] is None


def test_sem_concursos_suficientes_nao_prepara(monkeypatch):
    monkeypatch.setattr(config, "PERFIL_MIN_CONCURSOS", 1000)
    assert pc.preparar_de_linhas(_linhas(300)) is None


def test_concurso_de_selecoes_fica_acima_do_de_clubes(preparo):
    selecoes = pc.avaliar(preparo, _jogos(SELECAO), 1274, False)
    clubes = pc.avaliar(preparo, _jogos(CLUBE_BR), 1274, False)
    assert selecoes["posicao"] > clubes["posicao"]
    assert selecoes["faixa"] == "favoritos" and selecoes["nome_faixa"].startswith("perfil de favoritos")
    # O teste fora da amostra vê o sinal sintético, e a faixa de favoritos tem mais pulverizados que o geral.
    assert preparo["teste"]["auc"] > 0.7
    assert preparo["faixas"]["favoritos"]["taxa"] > preparo["faixas"]["geral"]["taxa"]


def test_menos_de_14_jogos_nao_calcula(preparo):
    resultado = pc.avaliar(preparo, _jogos(CLUBE_BR, 3), 1274, False)
    assert resultado == {"disponivel": False, "motivo": "o termômetro só é calculado com os 14 jogos (o concurso tem 3)"}


def test_concurso_anterior_sem_resultado_fica_neutro(preparo):
    resultado = pc.avaliar(preparo, _jogos(CLUBE_BR), 1275, None)
    anterior = next(s for s in resultado["sinais"] if s["chave"] == "anterior_acumulou")
    assert resultado["anterior_desconhecido"] and anterior["valor"] == pytest.approx(anterior["media"])
    assert next(s for s in resultado["sinais"] if s["chave"] == "final_0_ou_5")["valor"] == 1.0


def test_textos_trazem_a_medida_e_o_aviso_so_no_perfil_de_favoritos(preparo):
    from perfil_ui import frase_da_manada, frase_da_medida, frase_principal, linhas_dos_sinais

    selecoes = pc.avaliar(preparo, _jogos(SELECAO), 1274, None)
    principal = frase_principal(selecoes, preparo)
    assert "perfil de favoritos" in principal and f"dos {preparo['concursos']} concursos passados" in principal
    medida = frase_da_medida(selecoes, preparo)
    assert "área sob a curva ROC" in medida and "0,5 é o acaso" in medida and "não estima prêmio" in medida
    faixa = preparo["faixas"]["favoritos"]
    assert f"{faixa['pulverizados']} de {faixa['concursos']}" in medida
    assert "dividir o prêmio" in frase_da_manada(selecoes)
    assert frase_da_manada({**selecoes, "faixa": "comum"}) is None
    assert frase_da_manada({**selecoes, "faixa": "dificil"}) is None
    linhas = {l[0]: l[1] for l in linhas_dos_sinais(selecoes)}
    assert linhas[estudo_d6.ANTES["anterior_acumulou"]] == "ainda sem resultado (fica neutro)"
    assert linhas[estudo_d6.ANTES["selecoes"]] == "14,0"
