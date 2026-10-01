"""stats/associacao.py: estudo de associação. Dados sintéticos, sem rede e sem
tocar no banco real."""
import numpy as np
import pytest

import config
from stats import associacao


def _partida(rodada, mandante, visitante, gm, gv):
    return {
        "id_jogo": f"{rodada}-{mandante}-{visitante}", "rodada": rodada, "data_jogo": f"2026-01-{rodada:02d}",
        "mandante_id": mandante, "visitante_id": visitante, "gols_mandante": gm, "gols_visitante": gv,
    }


def _liga_de_dois_times(resultado_do_sexto_jogo_de_a):
    """A vence B nas rodadas 1 a 5; na 6, A joga fora e o resultado é o informado ('V', 'E' ou 'D')."""
    partidas = []
    for rodada in range(1, 6):
        partidas.append(_partida(rodada, 1, 2, 2, 0) if rodada % 2 else _partida(rodada, 2, 1, 0, 2))
    gols_a = {"V": 3, "E": 1, "D": 0}[resultado_do_sexto_jogo_de_a]
    partidas.append(_partida(6, 2, 1, 1, gols_a))  # rodada par: A é visitante
    return partidas


def _temporada_sintetica(rng, ano, n_times=20, vantagem_casa=0.25):
    """Pontos corridos de turno e returno; força de cada time constante e resultados independentes
    entre si: nenhum fator do histórico tem informação além do retrospecto."""
    forca = rng.normal(0, 0.3, n_times)
    times = list(range(n_times))
    partidas, rodada = [], 0
    for volta in range(2):
        rotativos = times[1:]
        for _ in range(n_times - 1):
            rodada += 1
            ordem = [times[0]] + rotativos
            for i in range(n_times // 2):
                a, b = ordem[i], ordem[n_times - 1 - i]
                casa, fora = (a, b) if volta == 0 else (b, a)
                gm = rng.poisson(np.exp(vantagem_casa + 0.3 * (forca[casa] - forca[fora])))
                gv = rng.poisson(np.exp(-0.05 + 0.3 * (forca[fora] - forca[casa])))
                partidas.append(_partida(rodada, casa, fora, int(gm), int(gv)))
            rotativos = rotativos[-1:] + rotativos[:-1]
    return partidas


def test_benjamini_hochberg_valores_conhecidos():
    q = associacao.ajustar_benjamini_hochberg([0.01, 0.04, 0.03, 0.005])
    assert q == pytest.approx([0.02, 0.04, 0.04, 0.02])


def test_benjamini_hochberg_vazio_e_unico():
    assert associacao.ajustar_benjamini_hochberg([]) == []
    assert associacao.ajustar_benjamini_hochberg([0.2]) == [0.2]


def test_fatores_usam_so_o_que_veio_antes_do_jogo():
    vitoria = [o for o in associacao.observacoes_de_jogos(_liga_de_dois_times("V"), "serie-a", 2026) if o["cluster"].endswith("-1")]
    derrota = [o for o in associacao.observacoes_de_jogos(_liga_de_dois_times("D"), "serie-a", 2026) if o["cluster"].endswith("-1")]
    assert len(vitoria) == len(derrota) == 1  # só o 6º jogo tem 5 jogos antes
    assert vitoria[0]["pontos"] == 3 and derrota[0]["pontos"] == 0
    # o resultado do próprio jogo não altera nenhum fator calculado antes dele
    for chave in ("forma_boa", "forma_ruim", "seq_vitorias", "seq_sem_vencer", "mando_casa", "retrospecto"):
        assert vitoria[0][chave] == derrota[0][chave]
    assert vitoria[0]["forma_boa"] and vitoria[0]["seq_vitorias"] and not vitoria[0]["mando_casa"]
    assert vitoria[0]["retrospecto"] == 3.0


def test_time_com_poucos_jogos_nao_gera_observacao():
    assert associacao.observacoes_de_jogos(_liga_de_dois_times("V")[:5], "serie-a", 2026) == []
    assert associacao.observacoes_de_jogos([], "serie-a", 2026) == []


def test_saf_vem_do_nome_do_clube_na_cbf():
    obs = associacao.observacoes_de_jogos(
        _liga_de_dois_times("V"), "serie-a", 2026, {1: "Clube Um Saf", 2: "Clube Dois"}
    )
    por_cluster = {o["cluster"]: o for o in obs}
    assert por_cluster["serie-a-2026-1"]["saf"] is True
    assert por_cluster["serie-a-2026-2"]["saf"] is False


def _observacoes_com_efeito(efeito, semente, temporadas=4, times=15, jogos=25):
    rng = np.random.default_rng(semente)
    observacoes = []
    for t in range(temporadas):
        for c in range(times):
            forca = rng.normal(1.3, 0.4)
            for _ in range(jogos):
                retro = float(np.clip(forca + rng.normal(0, 0.3), 0, 3))
                marcado = bool(rng.random() < 0.4)
                casa = bool(rng.random() < 0.5)
                observacoes.append(
                    {"temporada": f"s-{t}", "cluster": f"s-{t}-{c}", "retrospecto": retro, "mando_casa": casa,
                     "pontos": forca + 0.4 * casa + efeito * marcado + rng.normal(0, 1.0), "fator_x": marcado}
                )
    return observacoes


def test_efeito_plantado_melhora_a_previsao_e_o_intervalo_exclui_zero():
    obs = _observacoes_com_efeito(efeito=0.8, semente=1)
    r = associacao.avaliar_fator(obs, "fator_x", repeticoes=400, repeticoes_coeficiente=100, semente=3)
    assert r["avaliado"] and r["ganho"] > 0 and r["ganho_ic_inferior"] > 0 and r["p"] < 0.01
    assert r["coeficiente"] == pytest.approx(0.8, abs=0.15)
    assert r["coef_ic_inferior"] < r["coeficiente"] < r["coef_ic_superior"]


def test_fator_sem_efeito_nao_melhora_a_previsao_com_frequencia_acima_do_esperado():
    falsos, ganhos = 0, []
    for semente in range(20):
        obs = _observacoes_com_efeito(efeito=0.0, semente=100 + semente, temporadas=3, times=10)
        r = associacao.avaliar_fator(obs, "fator_x", repeticoes=200, repeticoes_coeficiente=20, semente=semente)
        falsos += r["p"] < 0.05
        ganhos.append(r["ganho"])
    assert falsos <= 3  # esperado: 1 em 20; folga para o acaso
    assert np.mean(ganhos) <= 0.005  # parâmetro a mais não ajuda fora da amostra


def test_amostra_insuficiente_nao_testa_e_valor_nulo_fica_fora():
    obs = _observacoes_com_efeito(0.0, 5, temporadas=2, times=2, jogos=10)  # 40 jogos
    for i, o in enumerate(obs):
        o["raro"] = i < 5  # 5 com o fator, abaixo do mínimo
        o["zona"] = None if i % 2 else True
    r = associacao.avaliar_fator(obs, "raro", 100, 10, 1)
    assert r == {"n_exposto": 5, "n_referencia": 35, "avaliado": False}
    r_nulo = associacao.avaliar_fator(obs, "zona", 100, 10, 1)
    assert r_nulo["n_exposto"] == 20 and r_nulo["n_referencia"] == 0 and not r_nulo["avaliado"]


def test_sem_observacoes_tudo_vira_amostra_insuficiente():
    resultados = associacao.estudar([])
    assert [r["conclusao"] for r in resultados] == ["amostra insuficiente"] * len(associacao.FATORES)
    assert all(r["p"] is None and r["q"] is None for r in resultados)


def test_resultado_e_reprodutivel_com_a_mesma_semente():
    obs = _observacoes_com_efeito(0.3, 9)
    a = associacao.avaliar_fator(obs, "fator_x", 200, 30, 11)
    b = associacao.avaliar_fator(obs, "fator_x", 200, 30, 11)
    assert a == b


def test_regressao_do_artefato_historico_puro_nao_vira_achado(monkeypatch):
    """Resultados independentes, força constante: forma, sequência e tabela são só ruído em torno
    do retrospecto. A 1ª versão do método (comparar dentro do time e permutar rótulos) apontava
    todos como "associação detectada". Aqui nenhum pode melhorar a previsão; o mando, que existe
    na simulação, serve de controle positivo."""
    monkeypatch.setattr(config, "ASSOCIACAO_REPETICOES_BOOTSTRAP", 300)
    monkeypatch.setattr(config, "ASSOCIACAO_REPETICOES_COEFICIENTE", 30)
    rng = np.random.default_rng(42)
    observacoes = []
    for ano in range(2019, 2023):
        observacoes += associacao.observacoes_de_jogos(_temporada_sintetica(rng, ano), "serie-a", ano)
    resultados = {r["fator"]: r for r in associacao.estudar(observacoes)}
    for chave in ("forma_boa", "forma_ruim", "seq_vitorias", "seq_sem_vencer", "zona_topo", "zona_fundo"):
        assert resultados[chave]["conclusao"] != "melhora a previsão fora da amostra", chave
    assert resultados["saf"]["conclusao"] == "amostra insuficiente"  # ninguém é SAF nesta simulação
    assert resultados["mando_casa"]["conclusao"] == "melhora a previsão fora da amostra"
