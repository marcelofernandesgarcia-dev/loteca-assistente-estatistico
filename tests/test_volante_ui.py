"""Volante de leitura (08/10/2026): HTML dos bilhetes salvos, versões e conferidos, sobre dados SINTÉTICOS."""
import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
if str(RAIZ / "app") not in sys.path:
    sys.path.insert(0, str(RAIZ / "app"))

from paleta import BRANCO, VERDE, VERMELHO, razao_de_contraste  # noqa: E402
from volante_ui import jogos_para_o_volante, renderizar_volante  # noqa: E402

PCT = {"1": 38.0, "X": 29.0, "2": 33.0}


def _jogo(**extra):
    return {"num_jogo": 8, "casa": "LIVERPOOL", "fora": "MANCHESTER CITY", "marcacoes": ["1", "X"], "pct": PCT, **extra}


def _colunas(html_volante: str) -> list[str]:
    return re.findall(r'<span>(1|X|2)</span><span class="vl-sr">, (marcado|não marcado)</span>', html_volante)


def test_marcacao_aparece_com_simbolo_e_texto_nao_so_cor():
    saida = renderizar_volante([_jogo()], "Bilhete nº 9")
    assert _colunas(saida) == [("1", "marcado"), ("X", "marcado"), ("2", "não marcado")]
    assert saida.count("vl-quadrado vl-marcado") == 2 and saida.count("✓") == 2
    assert 'aria-label="Bilhete nº 9"' in saida and "\n" not in saida.split("</style>")[1]


def test_percentual_do_momento_com_maior_em_negrito():
    saida = renderizar_volante([_jogo()], "b")
    assert "<strong>38%</strong> (maior)" in saida and ">29%<" in saida and ">33%<" in saida


def test_sem_percentual_salvo_mostra_traco():
    saida = renderizar_volante([_jogo(pct=None)], "b")
    assert saida.count('<div class="vl-pct">-</div>') == 3


def test_resultado_escrito_acertou_e_errou():
    acertou = renderizar_volante([_jogo(resultado="X")], "b")
    errou = renderizar_volante([_jogo(resultado="2")], "b")
    sem = renderizar_volante([_jogo(resultado=None)], "b")
    assert 'class="vl-jogo vl-acertou"' in acertou and "✓ acertou" in acertou and "Resultado: <strong>X</strong>" in acertou
    assert 'class="vl-jogo vl-errou"' in errou and "✗ errou" in errou
    assert "Resultado" not in sem and 'class="vl-jogo"' in sem


def test_nome_de_time_e_rotulo_sao_escapados():
    saida = renderizar_volante([_jogo(casa="A<script>", fora="B & C")], 'x"y')
    assert "A&lt;script&gt;" in saida and "B &amp; C" in saida and 'aria-label="x&quot;y"' in saida


def test_cores_do_volante_tem_contraste_de_elemento_grafico():
    assert razao_de_contraste(VERMELHO, BRANCO) >= 3 and razao_de_contraste(VERDE, BRANCO) >= 3


def test_jogos_para_o_volante_converte_as_linhas_do_banco():
    linhas = [{"num_jogo": 1, "casa": "A", "fora": "B", "marcacoes": ["1"], "percentual_1": 50.0,
               "percentual_x": 30.0, "percentual_2": 20.0, "resultado": "1"},
              {"num_jogo": 2, "casa": "C", "fora": "D", "marcacoes": ["X", "2"], "percentual_1": None,
               "percentual_x": None, "percentual_2": None, "resultado": None}]
    assert jogos_para_o_volante(linhas) == [
        {"num_jogo": 1, "casa": "A", "fora": "B", "marcacoes": ["1"], "pct": {"1": 50.0, "X": 30.0, "2": 20.0}, "resultado": "1"},
        {"num_jogo": 2, "casa": "C", "fora": "D", "marcacoes": ["X", "2"], "pct": None, "resultado": None},
    ]
