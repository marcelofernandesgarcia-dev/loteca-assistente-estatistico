"""Testes do modelo experimental da temporada com ligas SINTÉTICAS."""
import itertools

import pytest

from stats.modelo_temporada import (
    analisar_confronto,
    forcas_da_serie,
    gols_esperados,
    matriz_de_placares,
    resumo_da_matriz,
)


def _liga_simetrica(placar_casa=1, placar_fora=1, times=(1, 2, 3, 4)):
    """Turno e returno, todos com o mesmo placar: nenhum time é melhor que outro."""
    partidas = []
    for i, (m, v) in enumerate(itertools.permutations(times, 2)):
        partidas.append({"rodada": i + 1, "mandante_id": m, "visitante_id": v,
                         "gols_mandante": placar_casa, "gols_visitante": placar_fora})
    return partidas


def test_liga_simetrica_deixa_todas_as_forcas_em_um():
    forcas = forcas_da_serie(_liga_simetrica(2, 1))
    assert all(v == pytest.approx(1.0, abs=1e-6) for v in forcas["ataque"].values())
    assert all(v == pytest.approx(1.0, abs=1e-6) for v in forcas["defesa"].values())
    assert forcas["media_casa"] == 2 and forcas["media_fora"] == 1


def test_mandante_tem_mais_gols_esperados_quando_a_liga_favorece_mandantes():
    forcas = forcas_da_serie(_liga_simetrica(2, 1))
    casa, fora = gols_esperados(forcas, 1, 2)
    assert casa == pytest.approx(2.0) and fora == pytest.approx(1.0)


def _liga_com_time_forte():
    partidas = _liga_simetrica(1, 1)
    for p in partidas:
        if p["mandante_id"] == 1:
            p["gols_mandante"], p["gols_visitante"] = 3, 0
        elif p["visitante_id"] == 1:
            p["gols_mandante"], p["gols_visitante"] = 0, 2
    return partidas


def test_time_dominante_tem_ataque_maior_e_defesa_melhor():
    forcas = forcas_da_serie(_liga_com_time_forte(), peso_prior=1.0)
    assert forcas["ataque"][1] > 1.3 and forcas["defesa"][1] < 0.7
    assert forcas["ataque"][1] > forcas["ataque"][2]
    esp_forte, esp_fraco = gols_esperados(forcas, 1, 2)
    assert esp_forte > esp_fraco


def test_prior_grande_puxa_as_forcas_para_um():
    solto = forcas_da_serie(_liga_com_time_forte(), peso_prior=0.5)
    preso = forcas_da_serie(_liga_com_time_forte(), peso_prior=200.0)
    assert abs(preso["ataque"][1] - 1) < abs(solto["ataque"][1] - 1)
    assert preso["ataque"][1] == pytest.approx(1.0, abs=0.05)


def test_matriz_soma_um_e_resumo_bate_com_ela():
    matriz = matriz_de_placares(1.6, 0.9)
    assert sum(sum(linha) for linha in matriz) == pytest.approx(1.0)
    r = resumo_da_matriz(matriz)
    assert r["p_casa"] + r["p_empate"] + r["p_fora"] == pytest.approx(1.0)
    assert r["p_casa"] > r["p_fora"]
    assert r["p_casa_marca"] == pytest.approx(1 - 2.718281828 ** -1.6, abs=0.002)
    ordem = [x["probabilidade"] for x in r["placares_mais_provaveis"]]
    assert ordem == sorted(ordem, reverse=True) and len(ordem) == 5


def test_confronto_de_times_iguais_e_simetrico_sem_vantagem_de_mando():
    forcas = forcas_da_serie(_liga_simetrica(1, 1))
    r = analisar_confronto(forcas, 1, 2)
    assert r["p_casa"] == pytest.approx(r["p_fora"])


def test_time_desconhecido_ou_confronto_consigo_mesmo_devolve_none():
    forcas = forcas_da_serie(_liga_simetrica())
    assert analisar_confronto(forcas, 1, 99) is None
    assert analisar_confronto(forcas, 1, 1) is None
    assert forcas_da_serie([]) is None
