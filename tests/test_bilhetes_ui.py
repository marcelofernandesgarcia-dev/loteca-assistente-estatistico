"""Quadro de bilhetes do concurso (08/10/2026): texto das linhas e cabeçalhos, sobre dados SINTÉTICOS."""
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
if str(RAIZ / "app") not in sys.path:
    sys.path.insert(0, str(RAIZ / "app"))

from bilhetes_ui import cabecalhos, linhas_do_quadro  # noqa: E402


def _linha(**extra):
    base = {"id": 6, "origem": "ajuste_leve", "criado_em": "2026-10-08T14:34:34", "apostas": 8, "custo": 16.0,
            "chance_todos": 1 / 2952, "chance_todos_menos_um": 1 / 243, "acertos_esperados": 8.03, "duplos": 3,
            "triplos": 0, "zebras": 0, "situacao": "rascunho", "acertos": None, "total_jogos": 14}
    return {**base, **extra}


def test_linha_traz_as_colunas_da_tabela_de_versoes():
    assert linhas_do_quadro([_linha()]) == [[
        "nº 6", "Ajuste leve", "08/10 14:34", "8 (R$ 16,00)", "1 em 2.952", "1 em 243", "8,0", "3 / 0", "0",
        "rascunho (sem resposta)",
    ]]
    assert cabecalhos([_linha()])[4:6] == ["Chance de 14 (pelos percentuais)", "Chance de 13 ou mais (pelos percentuais)"]


def test_bilhete_antigo_sem_analise_e_sem_origem():
    linha = linhas_do_quadro([_linha(origem=None, chance_todos=None, chance_todos_menos_um=None,
                                     acertos_esperados=None, zebras=None, situacao="apostado")])[0]
    assert linha[1] == "Seu volante" and linha[4:7] == ["-", "-", "-"] and linha[8] == "-" and linha[9] == "apostado"


def test_coluna_de_acertos_so_aparece_com_resultado():
    sem = [_linha()]
    com = [_linha(acertos=10), _linha(id=7, acertos=None)]
    assert "Acertos" not in cabecalhos(sem) and len(linhas_do_quadro(sem)[0]) == 10
    assert cabecalhos(com)[-1] == "Acertos"
    assert [l[-1] for l in linhas_do_quadro(com)] == ["10 de 14", "-"]
