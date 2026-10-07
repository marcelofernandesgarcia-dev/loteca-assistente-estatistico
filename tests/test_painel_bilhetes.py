"""Painel dos bilhetes por tipo de jogo (item D5 do plano v2, 07/10/2026)."""
import config
from stats.painel_bilhetes import SEM_RETRATO, painel, segmentos_do_jogo

PCT = {"1": 62.0, "X": 23.0, "2": 15.0}
RETRATO = {"origem": "retrospecto_cbf", "cobertura": {"nome_nivel": "Completa (temporada da CBF)"},
           "noticias": {"deslocamento": -2.0}}


def test_segmentos_com_e_sem_retrato():
    com = segmentos_do_jogo({"pct": PCT, "marcacoes": ["1", "X"], "resultado": "1", "retrato": RETRATO})
    assert com == {"faixa": "favorito de 60% ou mais", "marcacao": "duplo", "origem": "Séries A e B (temporada da CBF)",
                   "cobertura": "Completa (temporada da CBF)", "noticia": "sim"}
    sem = segmentos_do_jogo({"pct": PCT, "marcacoes": ["1"], "resultado": "1", "retrato": None})
    assert sem["origem"] == SEM_RETRATO and sem["marcacao"] == "simples"


def test_taxa_so_com_amostra_minima(monkeypatch):
    monkeypatch.setattr(config, "ANALISE_AMOSTRA_MINIMA", 3)
    jogos = [{"pct": PCT, "marcacoes": ["1"], "resultado": r, "retrato": None} for r in ("1", "1", "X")]
    jogos.append({"pct": PCT, "marcacoes": ["1", "X", "2"], "resultado": "2", "retrato": None})
    por_marcacao = {g["grupo"]: g for g in painel(jogos)["marcacao"]}
    assert por_marcacao["simples"]["marcacoes"] == 3 and round(por_marcacao["simples"]["taxa"]) == 67
    assert por_marcacao["triplo"]["taxa"] is None  # 1 marcação: aguardando amostra
