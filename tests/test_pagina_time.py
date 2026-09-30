"""Executa a página 'Ficha do time' inteira (Streamlit AppTest) sobre um banco
SINTÉTICO com times fictícios -- nunca toca no banco real."""
import itertools
import sys
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

import config
import db
from stats.competicao import tabela_por_rodada

RAIZ = Path(__file__).resolve().parent.parent
PAGINA = RAIZ / "app" / "pages" / "3_Por_time.py"
ABAS = ["Visão geral", "Evolução na competição", "Jogo a jogo", "Ataque, defesa e mando",
        "Comparação com a liga", "Próximo jogo e resultados possíveis", "Na Loteca"]

PLACARES = [(2, 0), (1, 1), (0, 3), (1, 2), (0, 0), (3, 1), (2, 2), (1, 0), (0, 1), (4, 0), (1, 1), (2, 1)]


@pytest.fixture()
def banco(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DB_PATH", tmp_path / "sintetico.db")
    for pasta in (str(RAIZ), str(RAIZ / "app")):
        if pasta not in sys.path:
            sys.path.insert(0, pasta)
    db.inicializar_schema()
    with db.sessao() as c:
        for cod, nome, uf in ((1, "Time Alfa", "SP"), (2, "Time Beta", "RJ"), (3, "Time Gama", "MG"), (4, "Time Delta", "BA")):
            c.execute("INSERT INTO cbf_times (cod_time, nome, uf) VALUES (?, ?, ?)", (cod, nome, uf))
        partidas = []
        for i, ((m, v), (gm, gv)) in enumerate(zip(itertools.permutations((1, 2, 3, 4), 2), PLACARES)):
            partidas.append({"rodada": i // 2 + 1, "mandante_id": m, "visitante_id": v, "gols_mandante": gm, "gols_visitante": gv})
            c.execute(
                "INSERT INTO cbf_partidas (id_jogo, serie, ano, rodada, data_jogo, mandante_id, visitante_id,"
                " gols_mandante, gols_visitante, coletado_em) VALUES (?, 'serie-a', 2026, ?, ?, ?, ?, ?, ?, '2026-09-27T10:00:00')",
                (i + 1, i // 2 + 1, f"2026-03-{i + 1:02d}", m, v, gm, gv),
            )
        for linha in tabela_por_rodada(partidas)[max(p["rodada"] for p in partidas)]:
            c.execute(
                "INSERT INTO cbf_classificacao (serie, ano, cod_time, rodada, posicao, pontos, jogos, vitorias, empates,"
                " derrotas, gols_pro, gols_contra, saldo, cartoes_amarelo, cartoes_vermelho, aproveitamento, ultimos_jogos,"
                " proximo_adversario, proximo_adversario_id, coletado_em)"
                " VALUES ('serie-a', 2026, ?, 6, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, 0, ?, 'V,E,D', 'Time Beta', 2, '2026-09-27T10:00:00')",
                (linha["cod_time"], linha["posicao"], linha["pontos"], linha["jogos"], linha["vitorias"], linha["empates"],
                 linha["derrotas"], linha["gols_pro"], linha["gols_contra"], linha["saldo"], linha["aproveitamento"]),
            )
            c.execute(
                "INSERT INTO cbf_estatisticas_time (serie, ano, cod_time, jogos_disputados, gols_feitos, gols_sofridos,"
                " jogos_sem_sofrer_gol, cartoes_amarelos, cartoes_vermelhos, coletado_em)"
                " VALUES ('serie-a', 2026, ?, ?, ?, ?, 1, 5, 1, '2026-09-27T10:00:00')",
                (linha["cod_time"], linha["jogos"], linha["gols_pro"], linha["gols_contra"]),
            )
        alfa = db.obter_ou_criar_participante(c, "ALFA", "clube", "SP")
        beta = db.obter_ou_criar_participante(c, "BETA", "clube", "RJ")
        italia = db.obter_ou_criar_participante(c, "ITALIA", "selecao", None)
        c.execute("INSERT INTO mapa_cbf_participante (participante_id, cod_time, metodo) VALUES (?, 1, 'teste'), (?, 2, 'teste')", (alfa, beta))
        c.execute("INSERT INTO concursos (numero, data_apuracao, data_limite_aposta) VALUES (9001, '2026-03-05', '2026-03-01')")
        c.execute("INSERT INTO concursos (numero, data_limite_aposta, horario_fim_apostas) VALUES (9002, '2099-01-01', 15)")
        jogos = [(9001, 1, alfa, beta, 2, 1, "1"), (9001, 2, italia, alfa, 0, 0, "X"), (9001, 3, beta, alfa, 1, 3, "2"),
                 (9002, 1, alfa, beta, None, None, None)]
        for concurso, num, casa, fora, gc, gf, res in jogos:
            c.execute(
                "INSERT INTO jogos (concurso_numero, num_jogo, casa_id, fora_id, gols_casa, gols_fora, resultado, data_jogo)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, '2026-03-02')", (concurso, num, casa, fora, gc, gf, res),
            )
    return True


def _abrir(participante: str) -> AppTest:
    at = AppTest.from_file(str(PAGINA), default_timeout=90).run()
    assert not at.exception
    at.selectbox[0].select(participante).run()
    return at


def test_clube_com_dados_da_cbf_abre_a_ficha_completa_sem_erro(banco):
    at = _abrir("ALFA (clube)")
    assert not at.exception, [e.value for e in at.exception]
    assert [t.label for t in at.tabs] == ABAS
    assert any("Ficha completa" in s.value for s in at.success)
    assert [h.value for h in at.header] == [
        "Visão geral", "Evolução na competição", "Jogo a jogo", "Ataque, defesa e mando", "Comparação com a liga",
        "Próximo jogo e resultados possíveis", "Na Loteca"]


def test_selecao_sem_cbf_abre_a_ficha_reduzida_com_dados_da_loteca(banco):
    at = _abrir("ITALIA (selecao)")
    assert not at.exception, [e.value for e in at.exception]
    textos = " ".join(i.value for i in at.info)
    assert "Ficha reduzida" in textos
    assert "A evolução rodada a rodada só existe" in textos
    marcadores = " ".join(m.value for m in at.markdown)
    assert "Na grade da Loteca: 1 jogos" in marcadores


def test_clube_da_cbf_tem_link_de_consulta_manual_ao_bid_e_selecao_nao(banco):
    marcadores = " ".join(m.value for m in _abrir("ALFA (clube)").markdown)
    assert "[consultar o BID da CBF](https://bid.cbf.com.br/home)" in marcadores
    assert "a UF SP e o clube de código 1" in marcadores and "não coleta nem guarda nada do BID" in marcadores
    assert "consultar o BID" not in " ".join(m.value for m in _abrir("ITALIA (selecao)").markdown)


def test_link_do_transfermarkt_aparece_para_clube_e_selecao_e_avisa_quando_o_termo_nao_foi_testado(banco):
    clube = _abrir("ALFA (clube)")
    marcadores = " ".join(m.value for m in clube.markdown)
    assert "[buscar no Transfermarkt](https://www.transfermarkt.com.br/schnellsuche/ergebnis/schnellsuche?query=Time+Alfa)" in marcadores
    assert "O app não coleta nem guarda nada de lá" in marcadores
    assert any("Este termo não foi testado" in c.value for c in clube.caption)  # Time Alfa não está na lista curada

    selecao = _abrir("ITALIA (selecao)")
    assert "query=Italia" in " ".join(m.value for m in selecao.markdown)


def test_marca_de_saf_aparece_so_quando_o_nome_da_cbf_traz_saf(banco):
    with db.sessao() as c:
        c.execute("UPDATE cbf_times SET nome = 'Time Alfa SAF' WHERE cod_time = 1")
    com_saf = " ".join(i.value for i in _abrir("ALFA (clube)").info)
    assert "Registrado como SAF na CBF desde 2026" in com_saf and "Lei nº 14.193/2021" in com_saf
    assert "não muda o percentual" in com_saf
    sem_saf = " ".join(i.value for i in _abrir("BETA (clube)").info)
    assert "SAF" not in sem_saf  # e nenhuma frase do tipo "não é SAF"


def test_marca_de_saf_conta_o_nome_de_anos_anteriores_mesmo_quando_o_de_hoje_nao_traz(banco):
    """Como o Cruzeiro: 'Saf' no nome da CBF em anos anteriores, mas o de hoje não traz."""
    with db.sessao() as c:
        c.execute("UPDATE cbf_classificacao SET nome_no_ano = 'Time Alfa Saf' WHERE cod_time = 1 AND rodada = 6")
        c.execute("INSERT INTO cbf_classificacao (serie, ano, cod_time, rodada, coletado_em, nome_no_ano)"
                  " VALUES ('serie-a', 2025, 1, 38, 'x', 'Time Alfa Saf')")
        c.execute("UPDATE cbf_classificacao SET nome_no_ano = 'Time Alfa' WHERE cod_time = 1 AND ano = 2026")
    info = " ".join(i.value for i in _abrir("ALFA (clube)").info)
    assert "Consta como SAF no nome da CBF em 2025" in info and "o nome de hoje não traz" in info
    assert "Registrado como SAF na CBF desde" not in info  # não afirma "desde": o de hoje não traz


def test_titulos_seguem_a_hierarquia_da_pagina(banco):
    at = _abrir("ALFA (clube)")
    assert [t.value for t in at.title] == ["Ficha do time"]
    assert len(at.subheader) > 0  # seções dentro de cada aba
