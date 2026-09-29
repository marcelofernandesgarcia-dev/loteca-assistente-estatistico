"""Contraste das cores da ficha do time (WCAG 2.1, nível AA)."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "app"))

from paleta import AZUL, BRANCO, CINZA, COR_RESULTADO, VERDE, VERMELHO, razao_de_contraste  # noqa: E402


def test_razao_de_contraste_dos_extremos():
    assert razao_de_contraste("#000000", "#ffffff") == pytest.approx(21.0)
    assert razao_de_contraste("#ffffff", "#ffffff") == pytest.approx(1.0)


@pytest.mark.parametrize("cor", [AZUL, VERMELHO, VERDE, CINZA, *COR_RESULTADO.values()])
def test_texto_branco_sobre_as_cores_tem_contraste_de_texto_normal(cor):
    assert razao_de_contraste(cor, BRANCO) >= 4.5, cor


@pytest.mark.parametrize("cor", [AZUL, VERMELHO, VERDE, CINZA])
def test_linhas_e_barras_sobre_fundo_branco_tem_contraste_de_elemento_grafico(cor):
    assert razao_de_contraste(cor, BRANCO) >= 3.0, cor


from paleta import CORES_LINHAS, MARCADORES_LINHAS, TRACOS_LINHAS  # noqa: E402


@pytest.mark.parametrize("cor", CORES_LINHAS)
def test_cores_das_linhas_do_painel_tem_contraste_de_elemento_grafico(cor):
    assert razao_de_contraste(cor, BRANCO) >= 3.0, cor


def test_cada_linha_do_painel_tem_cor_traco_e_marcador_diferentes():
    combinacoes = set(zip(CORES_LINHAS, TRACOS_LINHAS, MARCADORES_LINHAS))
    assert len(set(CORES_LINHAS)) == len(set(MARCADORES_LINHAS)) == len(combinacoes) == 8
