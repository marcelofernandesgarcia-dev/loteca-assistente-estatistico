"""Chances por bilhete e por conjunto na tela: funções de texto (puras) e as páginas 'Concurso atual' e 'Meus bilhetes'
(Streamlit AppTest) sobre um banco sintético com um concurso de 14 jogos."""
import sys
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

import config
import db
from stats.bilhetes_salvos import salvar_bilhete

RAIZ = Path(__file__).resolve().parent.parent
PAGINA_ATUAL = RAIZ / "app" / "pages" / "1_Concurso_atual.py"
PAGINA_BILHETES = RAIZ / "app" / "pages" / "6_Meus_bilhetes.py"
for _pasta in (str(RAIZ), str(RAIZ / "app")):
    if _pasta not in sys.path:
        sys.path.insert(0, _pasta)

import chances_ui as ui  # noqa: E402
from stats import chances_bilhete as cb  # noqa: E402

PCT = {"1": 60.0, "X": 25.0, "2": 15.0}


def test_formatacao_de_porcentagem_reais_e_inteiros():
    assert ui.pct(0) == "0%" and ui.pct(0.00005) == "menos de 0,01%" and ui.pct(0.0042) == "0,42%" and ui.pct(0.1234) == "12,3%"
    assert ui.reais(4) == "R$ 4,00" and ui.reais(1728) == "R$ 1.728,00"
    assert ui.inteiro(864) == "864" and ui.inteiro(4782969) == "4.782.969"


def test_distribuicao_com_14_jogos_e_com_poucos_jogos():
    m14 = cb.medidas_do_bilhete([PCT] * 14, [["1", "X"]] * 14)
    linhas = ui.linhas_distribuicao(m14)
    assert [l[0] for l in linhas] == ["14 acertos", "13 acertos", "12 acertos", "11 acertos", "10 acertos ou menos"]
    assert all(len(l) == len(ui.CABECALHOS_DISTRIBUICAO) for l in linhas)
    m3 = cb.medidas_do_bilhete([PCT] * 3, [["1"]] * 3)
    assert [l[0] for l in ui.linhas_distribuicao(m3)] == ["3 acertos", "2 acertos", "1 acertos", "0 acertos"]  # sem faixa negativa


def test_frases_das_apostas_premiadas():
    simples = cb.medidas_do_bilhete([PCT] * 14, [["1"]] * 14)
    assert "única aposta" in ui.frase_das_apostas_premiadas(simples)
    com_duplo = cb.medidas_do_bilhete([PCT] * 14, [["1", "X"]] + [["1"]] * 13)
    texto = ui.frase_das_apostas_premiadas(com_duplo)
    assert "faz 14 e 1 aposta(s) fazem 13" in texto and "entre 1 e 2 apostas fazem 13" in texto
    todos_duplos = cb.medidas_do_bilhete([PCT] * 14, [["1", "X"]] * 14)
    assert "Se errar exatamente um jogo, 2 aposta(s) fazem 13." in ui.frase_das_apostas_premiadas(todos_duplos)


def test_linhas_do_ganho_dos_multiplos_escapam_html():
    jogos = [{"num_jogo": 1, "casa": "<i>A</i>", "fora": "B & C"}, {"num_jogo": 2, "casa": "D", "fora": "E"}]
    ganhos = cb.ganho_de_cada_multiplo([PCT, PCT], [["1", "X"], ["1", "X", "2"]])
    linhas = ui.linhas_ganho_dos_multiplos(ganhos, jogos)
    assert len(linhas) == 2 and all(len(l) == len(ui.CABECALHOS_GANHO) for l in linhas)
    assert "&lt;i&gt;A&lt;/i&gt;" in linhas[0][0] and "B &amp; C" in linhas[0][0]
    assert linhas[0][1] == "duplo; compara sem a coluna X" and linhas[1][1] == "triplo; compara sem a coluna 2"
    assert linhas[0][3].startswith("R$ ")


def _conjunto(marcas_por_bilhete, n=14):
    return cb.medidas_do_conjunto([PCT] * n, [{"id": i + 1, "marcacoes": m} for i, m in enumerate(marcas_por_bilhete)])


def test_frases_da_repeticao_e_do_bilhete_unico():
    a = [["1", "X"]] + [["1"]] * 13
    b = [["2"]] + [["1"]] * 13
    sem_repeticao = _conjunto([a, b])
    assert "Nenhuma aposta se repete" in ui.frase_da_repeticao(sem_repeticao)
    com_repeticao = _conjunto([a, a])
    assert "2 aposta(s) aparecem em mais de um bilhete" in ui.frase_da_repeticao(com_repeticao) and "R$ 4,00 gastos" in ui.frase_da_repeticao(com_repeticao)

    frase = ui.frase_do_bilhete_unico(com_repeticao)
    assert "um único bilhete montado pela regra" in frase and "não escolhe por você" in frase
    sem_dinheiro = {**sem_repeticao, "bilhete_unico": None}
    assert ui.frase_do_bilhete_unico(sem_dinheiro) is None
    igual = {**sem_repeticao, "bilhete_unico": {**sem_repeticao["bilhete_unico"], "chance_13_ou_mais": sem_repeticao["chance_13_ou_mais"]}}
    assert "a mesma chance de 13 ou mais" in ui.frase_do_bilhete_unico(igual)
    menor = {**sem_repeticao, "bilhete_unico": {**sem_repeticao["bilhete_unico"], "chance_13_ou_mais": 0.0}}
    assert "uma chance de 13 ou mais menor" in ui.frase_do_bilhete_unico(menor)


def test_linhas_por_bilhete_e_pares():
    medidas = _conjunto([[["1", "X"]] + [["1"]] * 13, [["1", "X"]] + [["1"]] * 13])
    rotulos = {1: "Bilhete <1>", 2: "Bilhete 2"}
    por_bilhete = ui.linhas_por_bilhete(medidas, rotulos)
    assert all(len(l) == len(ui.CABECALHOS_POR_BILHETE) for l in por_bilhete)
    assert "&lt;1&gt;" in por_bilhete[0][0] and por_bilhete[1][3] == "nada"  # o segundo bilhete é cópia: nada acrescenta
    pares = ui.linhas_dos_pares(medidas, rotulos)
    assert len(pares) == 1 and pares[0][1] == "2" and pares[0][2] == "100,0%"


def test_nota_da_calibracao_nos_dois_estados(monkeypatch):
    assert "já corrigidos pela calibração" in ui.nota_da_calibracao()
    monkeypatch.setattr(config, "CALIBRACAO_ATIVA", False)
    assert "calibração está desligada" in ui.nota_da_calibracao()


# ---------------------------------------------------------------- páginas


@pytest.fixture()
def banco(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DB_PATH", tmp_path / "sintetico.db")
    db.inicializar_schema()
    with db.sessao() as c:
        alfa = db.obter_ou_criar_participante(c, "ALFA", "clube", "SP")
        beta = db.obter_ou_criar_participante(c, "BETA", "clube", "RJ")
        c.execute("INSERT INTO concursos (numero, data_apuracao, data_limite_aposta) VALUES (9001, '2026-03-05', '2026-03-01')")
        c.execute("INSERT INTO concursos (numero, data_limite_aposta, horario_fim_apostas) VALUES (9002, '2099-01-01', 15)")
        for i in range(1, 15):
            casa, fora = (alfa, beta) if i % 2 else (beta, alfa)
            c.execute(
                "INSERT INTO jogos (concurso_numero, num_jogo, casa_id, fora_id, gols_casa, gols_fora, resultado, data_jogo)"
                " VALUES (9001, ?, ?, ?, 2, 0, '1', '2026-03-02')", (i, casa, fora),
            )
            c.execute("INSERT INTO jogos (concurso_numero, num_jogo, casa_id, fora_id, data_jogo) VALUES (9002, ?, ?, ?, '2099-01-02')", (i, casa, fora))
    return True


def _textos(at):
    return " ".join(m.value for m in at.markdown) + " " + " ".join(c.value for c in at.caption)


def test_concurso_atual_mostra_as_chances_assim_que_o_volante_esta_completo(banco):
    at = AppTest.from_file(str(PAGINA_ATUAL), default_timeout=120).run()
    assert not at.exception, [e.value for e in at.exception]
    assert "Chances deste bilhete" not in _textos(at)  # volante em branco: nada a calcular
    next(b for b in at.button if b.label == "Preencher com a sugestão").click().run()
    assert not at.exception, [e.value for e in at.exception]
    rotulos = [m.label for m in at.metric]
    assert "14 acertos" in rotulos and "13 acertos ou mais" in rotulos and "12 acertos ou mais" in rotulos and "Acertos esperados" in rotulos
    textos = _textos(at)
    assert "Chances deste bilhete" in textos and "Chance de cada número de acertos" in textos
    assert "já corrigidos pela calibração" in textos


def test_chances_somem_se_faltar_marcar_algum_jogo(banco):
    at = AppTest.from_file(str(PAGINA_ATUAL), default_timeout=120).run()
    next(b for b in at.button if b.label == "Preencher com a sugestão").click().run()
    por_jogo = {}
    for c in at.checkbox:
        por_jogo.setdefault(c.key.rsplit("_", 1)[0], []).append(c)
    primeiro_jogo = next(iter(por_jogo.values()))
    marcado = next(c for c in primeiro_jogo if c.value)
    if len([c for c in primeiro_jogo if c.value]) == 1:  # a sugestão deixa o jogo com uma só coluna: desmarcar o deixa em branco
        at.checkbox(key=marcado.key).uncheck().run()
        assert not at.exception, [e.value for e in at.exception]
        assert "Chances deste bilhete" not in _textos(at)
    else:  # com duplo/triplo, desmarcar tira só uma coluna; limpar todas as colunas do jogo é o que deixa em branco
        for c in primeiro_jogo:
            at.checkbox(key=c.key).uncheck()
        at.run()
        assert not at.exception, [e.value for e in at.exception]
        assert "Chances deste bilhete" not in _textos(at)


def _salvar(banco_pronto, marcas_por_jogo):
    with db.sessao() as c:
        jogos = c.execute("SELECT id, num_jogo FROM jogos WHERE concurso_numero = 9002 ORDER BY num_jogo").fetchall()
        pct = {"1": 50.0, "X": 28.0, "2": 22.0}
        return salvar_bilhete(c, 9002, {j["id"]: marcas_por_jogo[j["num_jogo"] - 1] for j in jogos}, {j["id"]: pct for j in jogos})


def test_meus_bilhetes_mostra_chances_do_bilhete_e_do_conjunto(banco):
    a = [["1", "X"]] + [["1"]] * 13
    b = [["2"]] + [["1"]] * 13
    id_a, id_b = _salvar(banco, a), _salvar(banco, b)
    at = AppTest.from_file(str(PAGINA_BILHETES), default_timeout=180).run()
    assert not at.exception, [e.value for e in at.exception]
    textos = _textos(at)
    assert "Conjunto de bilhetes do concurso" in " ".join(h.value for h in at.subheader)
    assert "Chances do conjunto de bilhetes" in textos and "Cada bilhete dentro do conjunto" in textos
    assert "Sobreposição entre os bilhetes" in textos
    assert f"Bilhete {id_a}" in textos and f"Bilhete {id_b}" in textos
    assert "Chances calculadas com os percentuais de hoje" in textos  # cada bilhete aberto também mostra as suas
    assert any(m.label == "Custo total" and m.value == "R$ 6,00" for m in at.metric)  # 2 + 1 apostas, mas só 3 apostas = R$ 6,00


def test_conjunto_com_um_so_bilhete_e_sem_nenhum(banco):
    a = [["1", "X"]] + [["1"]] * 13
    b = [["2"]] + [["1"]] * 13
    id_a, id_b = _salvar(banco, a), _salvar(banco, b)
    at = AppTest.from_file(str(PAGINA_BILHETES), default_timeout=180).run()
    seletor = at.multiselect(key="conjunto_bilhetes_9002")
    seletor.set_value([id_a]).run()
    assert not at.exception, [e.value for e in at.exception]
    assert "Sobreposição entre os bilhetes" not in _textos(at)  # sem par, sem sobreposição
    at.multiselect(key="conjunto_bilhetes_9002").set_value([]).run()
    assert not at.exception, [e.value for e in at.exception]
    assert any("Marque pelo menos um bilhete" in i.value for i in at.info)


def test_sem_concurso_aberto_a_secao_do_conjunto_orienta(banco):
    with db.sessao() as c:
        jogos = c.execute("SELECT id, num_jogo FROM jogos WHERE concurso_numero = 9001 ORDER BY num_jogo").fetchall()
        salvar_bilhete(c, 9001, {j["id"]: ["1"] for j in jogos}, {j["id"]: {"1": 50.0, "X": 28.0, "2": 22.0} for j in jogos})
    at = AppTest.from_file(str(PAGINA_BILHETES), default_timeout=180).run()
    assert not at.exception, [e.value for e in at.exception]
    assert any("Aparece quando houver bilhetes salvos de um concurso ainda não apurado" in i.value for i in at.info)
