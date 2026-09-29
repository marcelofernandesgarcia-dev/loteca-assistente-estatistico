"""Executa a página 'Fechamento de bolão' (Streamlit AppTest). Não usa banco --
a calculadora lê só a tabela oficial versionada (data/loteca-boloes-oficial.csv)."""
import sys
from pathlib import Path

from streamlit.testing.v1 import AppTest

RAIZ = Path(__file__).resolve().parent.parent
PAGINA = RAIZ / "app" / "pages" / "4_Fechamento_de_bolao.py"

for _pasta in (str(RAIZ), str(RAIZ / "app")):
    if _pasta not in sys.path:
        sys.path.insert(0, _pasta)


def test_pagina_abre_sem_erro_com_valores_padrao():
    at = AppTest.from_file(str(PAGINA), default_timeout=60).run()
    assert not at.exception, [e.value for e in at.exception]
    assert [m.value for m in at.metric] and at.metric[0].value == "2"  # 1 duplo = 2 apostas


def test_combinacao_acima_do_maximo_mostra_aviso():
    at = AppTest.from_file(str(PAGINA), default_timeout=60).run()
    at.number_input[0].set_value(6).run()  # 6 triplos
    at.number_input[1].set_value(9).run()  # 9 duplos -> muito acima de 864 apostas
    assert not at.exception
    assert any("passa do máximo oficial" in w.value for w in at.warning)
