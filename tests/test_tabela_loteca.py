"""Tabelas da Loteca (08/10/2026): combinações, valores e chances, conferidos contra as fontes oficiais do repositório."""
import csv

import pytest

import config
from stats import tabela_loteca as tl
from stats.chances_bilhete import medidas_do_bilhete


def _anexo_i() -> set[tuple[int, int, int, float]]:
    with open(config.BOLOES_OFICIAL_CSV_PATH, encoding="utf-8") as arquivo:
        return {(int(l["duplos"]), int(l["triplos"]), int(l["apostas"]), float(l["valor_reais"]))
                for l in csv.DictReader(arquivo, delimiter=";")}


def test_combinacoes_e_valores_batem_com_o_anexo_i_do_manual():
    tabela = {(l["duplos"], l["triplos"], l["apostas"], l["valor"]) for l in tl.tabela_de_valores()}
    assert len(tabela) == 38 and tabela == _anexo_i()


def test_grupos_como_no_caixa_informa_e_ordem_por_triplos():
    linhas = tl.tabela_de_valores()
    assert linhas[0] == {"duplos": 1, "triplos": 0, "apostas": 2, "valor": 4.0, "grupo": "ate_1_triplo"}
    assert {l["grupo"] for l in linhas if l["triplos"] >= 2} == {"2_ou_mais_triplos"}
    assert [l["triplos"] for l in linhas] == sorted(l["triplos"] for l in linhas)
    assert max(l["apostas"] for l in linhas) == config.BILHETE_MAX_APOSTAS


@pytest.mark.parametrize("duplos, triplos, trecho", [
    (0, 0, "ao menos um duplo"), (6, 3, "máximo oficial"), (10, 5, "não cabem"), (-1, 1, "negativa"),
])
def test_combinacao_invalida_tem_motivo(duplos, triplos, trecho):
    assert trecho in tl.motivo_invalida(duplos, triplos)
    with pytest.raises(ValueError, match=trecho):
        tl.chances_metodo_caixa(duplos, triplos)


def test_aposta_minima_reproduz_o_item_6_3_6_do_manual():
    c = tl.chances_metodo_caixa(1, 0)
    assert tl.uma_em(c["total_resultados"], c["casos_14"]) == "1 em 2.391.485"  # 4.782.969 / 2, metade para cima
    assert tl.uma_em(c["total_resultados"], c["casos_13_caixa"]) == "1 em 85.410"
    assert c["casos_premiar"] == 55  # 2 com 14 e 53 com 13: o bilhete conta cada resultado uma vez


def test_exemplo_do_usuario_1_duplo_e_3_triplos():
    c = tl.chances_metodo_caixa(1, 3)
    assert c["apostas"] == 54 and tl.valor(1, 3)["valor"] == 108.0
    assert tl.uma_em(c["total_resultados"], c["casos_14"]) == "1 em 88.574"
    assert tl.uma_em(c["total_resultados"], c["casos_13_caixa"]) == "1 em 3.163"
    assert tl.uma_em(c["total_resultados"], c["casos_premiar"]) == "1 em 4.120"


def test_contagem_do_bilhete_premiar_bate_com_o_calculo_exato_com_um_terco():
    uniforme = [{"1": 100 / 3, "X": 100 / 3, "2": 100 / 3}] * 14
    for d, t in ((1, 0), (2, 1), (5, 3), (0, 6)):
        marcacoes = [["1", "X"]] * d + [["1", "X", "2"]] * t + [["1"]] * (14 - d - t)
        exato = medidas_do_bilhete(uniforme, marcacoes)
        c = tl.chances_metodo_caixa(d, t)
        assert c["chance_premiar"] == pytest.approx(exato["chance_13_ou_mais"], rel=1e-9)
        assert c["chance_14"] == pytest.approx(exato["chance_14"], rel=1e-9)


def test_chances_pelos_percentuais_poe_o_triplo_no_jogo_mais_incerto():
    pcts = [{"1": 70, "X": 20, "2": 10}] * 13 + [{"1": 34, "X": 33, "2": 33}]
    r = tl.chances_pelos_percentuais(pcts, 0, 1)
    assert r["marcacoes"][13] == ["1", "X", "2"] and r["apostas"] == 3
    assert r["chance_14"] == pytest.approx(0.7**13)


def test_tabela_de_chances_sem_concurso_e_sem_historico():
    linhas = tl.tabela_de_chances(None, None)
    assert len(linhas) == 38 and all(l["percentuais"] is None and l["historico"] is None for l in linhas)
    com = tl.tabela_de_chances([{"1": 50, "X": 30, "2": 20}] * 14, {(1, 0): {"fez_13_ou_mais": 0}})
    assert com[0]["percentuais"]["apostas"] == 2 and com[0]["historico"] == {"fez_13_ou_mais": 0}
    assert com[1]["historico"] is None
