"""app/estudos_ui.py: frases, tabelas e figuras dos estudos estatísticos (funções puras, sem Streamlit)."""
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
for pasta in (str(RAIZ), str(RAIZ / "app")):
    if pasta not in sys.path:
        sys.path.insert(0, pasta)

import estudos_ui as ui  # noqa: E402


def _fator(chave, conclusao, avaliado=True, descricao=None):
    base = {"fator": chave, "descricao": descricao or chave, "conclusao": conclusao, "avaliado": avaliado, "n_exposto": 100, "n_referencia": 900, "p": 0.5, "q": 0.5}
    if avaliado:
        base |= {"ganho": 0.01, "ganho_relativo": -0.0002, "ganho_ic_inferior": -0.001, "ganho_ic_superior": 0.0,
                 "coeficiente": 0.02, "coef_ic_inferior": -0.05, "coef_ic_superior": 0.09}
    return base | ({} if avaliado else {"p": None, "q": None})


def test_formatacao_de_numeros_com_virgula_e_sinal():
    assert ui.num(0.6543, 2, True) == "+0,65" and ui.num(-0.0002, 4, True) == "-0,0002" and ui.num(None) == "—"
    assert ui.num(-0.0004, 2, True) == "0,00" and ui.num(0.0, 2, True) == "0,00" and ui.num(-0.0004, 2) == "0,00"  # zero sem sinal
    assert ui.texto_p(0.0004) == "<0,001" and ui.texto_p(0.5) == "0,500" and ui.texto_p(None) == "—"
    assert ui.inteiro(10192) == "10.192" and ui.inteiro(7) == "7"


def test_frase_de_fatores_nos_tres_casos():
    com_um = ui.frase_fatores([_fator("a", "melhora a previsão fora da amostra", descricao="Jogar em casa"), _fator("b", "não melhora a previsão")])
    assert "Dos 2 fatores testados, 1 melhora(m)" in com_um and "jogar em casa" in com_um
    nenhum = ui.frase_fatores([_fator("a", "não melhora a previsão"), _fator("b", "não melhora a previsão")])
    assert nenhum.startswith("Nenhum dos 2 fatores testados melhora a previsão")
    sem_amostra = ui.frase_fatores([_fator("a", "amostra insuficiente", avaliado=False)])
    assert sem_amostra == "Nenhum fator tem jogos suficientes para ser testado."
    misto = ui.frase_fatores([_fator("a", "não melhora a previsão"), _fator("b", "amostra insuficiente", avaliado=False, descricao="SAF")])
    assert "Sem jogos suficientes para testar: saf." in misto


def test_linhas_de_fatores_escapam_html_e_tem_o_numero_de_colunas_do_cabecalho():
    linhas = ui.linhas_fatores([_fator("a", "não melhora a previsão", descricao="<b>x</b> & y"), _fator("b", "amostra insuficiente", avaliado=False)])
    assert all(len(l) == len(ui.CABECALHOS_FATORES) for l in linhas)
    assert "&lt;b&gt;x&lt;/b&gt; &amp; y" in linhas[0][0] and "<b>" not in linhas[0][0]
    assert linhas[1][3] == "—" and linhas[1][4] == "—"


def test_figura_de_coeficientes_ignora_nao_avaliados_e_devolve_none_sem_nenhum():
    assert ui.figura_coeficientes([_fator("a", "amostra insuficiente", avaliado=False)]) is None
    figura = ui.figura_coeficientes([_fator("a", "melhora a previsão fora da amostra"), _fator("b", "amostra insuficiente", avaliado=False)])
    assert len(figura.data) == 1 and list(figura.data[0].y) == ["a"]  # fator sem rótulo curto cai para a descrição
    curto = ui.figura_coeficientes([_fator("mando_casa", "melhora a previsão fora da amostra", descricao="Jogar em casa, comparado a jogar fora")])
    assert list(curto.data[0].y) == ["Jogar em casa"] and list(curto.data[0].customdata) == ["Jogar em casa, comparado a jogar fora"]


def _ic(media, p=0.001):
    return {"media": media, "ic_inferior": media - 0.01, "ic_superior": media + 0.01, "p": p}


def _resumo_b2(retro, poisson, entre):
    return {
        "n": 400,
        "metricas": {m: {"n": 400, "acuracia": 47.0, "brier": 0.63, "perda_log": 1.05} for m in ("referencia", "retrospecto", "poisson")},
        "comparacoes": [
            {"modelo": "retrospecto", "contra": "referencia", "perda_log": _ic(0.02), "brier": _ic(0.01), "q": 0.001, "conclusao": retro},
            {"modelo": "poisson", "contra": "referencia", "perda_log": _ic(0.02), "brier": _ic(0.01), "q": 0.001, "conclusao": poisson},
            {"modelo": "poisson", "contra": "retrospecto", "perda_log": _ic(0.0), "brier": _ic(0.0), "q": 0.8, "conclusao": entre},
        ],
    }


def test_frase_b2_cobre_melhor_pior_e_sem_diferenca():
    melhor = ui.frase_b2(_resumo_b2("melhor", "melhor", "sem diferença perceptível"))
    assert "retrospecto dos dois times (logística) e poisson da temporada" in melhor and "Entre os dois modelos não há diferença perceptível" in melhor
    pior = ui.frase_b2(_resumo_b2("pior", "sem diferença perceptível", "pior"))
    assert "fica pior que a frequência simples" in pior and "O retrospecto é melhor que o Poisson" in pior
    nada = ui.frase_b2(_resumo_b2("sem diferença perceptível", "sem diferença perceptível", "melhor"))
    assert "Nenhum dos modelos testados se distingue" in nada and "O Poisson da temporada é melhor que o retrospecto" in nada
    assert "vale só para jogos das Séries A e B" in nada


def test_linhas_e_figura_do_b2():
    resumo = _resumo_b2("melhor", "melhor", "sem diferença perceptível")
    assert all(len(l) == len(ui.CABECALHOS_B2) for l in ui.linhas_b2(resumo))
    comparacoes = ui.linhas_b2_comparacoes(resumo)
    assert all(len(l) == len(ui.CABECALHOS_B2_COMPARACAO) for l in comparacoes)
    assert comparacoes[0][0].endswith("contra frequência simples de 1/X/2") and "+0,0200 (+0,0100 a +0,0300)" in comparacoes[0][1]
    assert len(ui.figura_comparacoes_b2(resumo).data[0].y) == 3


def _q7(rho, conclusao, chave="fora_da_coluna_1"):
    return {"exposicao": chave, "descricao": chave, "n": 837, "rho": rho, "ic_inferior": None if rho is None else rho - 0.05,
            "ic_superior": None if rho is None else rho + 0.05, "p": 0.001, "q": 0.001, "conclusao": conclusao}


def test_frase_q7_negativa_positiva_nula_e_sem_dados():
    negativa = ui.frase_q7([_q7(-0.41, "associação detectada (negativa)")], 837, (2009, 2026))
    assert "Em 837 concursos de 2009 a 2026" in negativa and "menos ganhadores de 14 acertos" in negativa
    assert "-0,41" in negativa and "não indica o que vai acontecer" in negativa
    assert "mais ganhadores" in ui.frase_q7([_q7(0.3, "associação detectada (positiva)")], 10, (2020, 2021))
    nula = ui.frase_q7([_q7(0.02, "sem diferença perceptível")], 10, (2020, 2021))
    assert "não houve relação perceptível" in nula
    assert ui.frase_q7([_q7(None, "amostra insuficiente")], 0, (0, 0)) == "Não há concursos suficientes para a análise."


def test_linhas_e_figura_do_q7():
    linhas = ui.linhas_q7([_q7(-0.41, "associação detectada (negativa)"), _q7(None, "amostra insuficiente", "empates")])
    assert all(len(l) == len(ui.CABECALHOS_Q7) for l in linhas) and linhas[1][2] == "—" and linhas[1][3] == "—"
    faixas = [{"faixa": "0 a 4", "concursos": 43, "ganhadores_por_milhao": 34.35, "sem_ganhador_14": 7.0, "premio_mediano": 25458.15},
              {"faixa": "9 a 14", "concursos": 5, "ganhadores_por_milhao": 1.0, "sem_ganhador_14": 70.0, "premio_mediano": None}]
    linhas_faixas = ui.linhas_q7_faixas(faixas, lambda v: f"R$ {v:.2f}")
    assert all(len(l) == len(ui.CABECALHOS_Q7_FAIXAS) for l in linhas_faixas)
    assert linhas_faixas[0][4] == "R$ 25458.15" and linhas_faixas[1][4] == "—" and linhas_faixas[0][2] == "34,4"
    assert list(ui.figura_faixas_q7(faixas).data[0].x) == ["0 a 4", "9 a 14"]
