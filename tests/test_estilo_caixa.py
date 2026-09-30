"""A marca de destaque nunca pode depender só da cor (e-MAG/WCAG 2.1 AA)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "app"))

from estilo_caixa import AZUL_CABECALHO, VERMELHO_DESTAQUE, renderizar_cartao  # noqa: E402
from paleta import AZUL, VERMELHO  # noqa: E402

LINHA = {
    "num_jogo": 1, "casa": "TIME A", "fora": "TIME B", "data": "01/01/2026",
    "valor_casa": "50%", "valor_x": "30%", "valor_fora": "20%",
    "destaque_casa": True, "destaque_x": False, "destaque_fora": False,
}


def test_estilo_caixa_reaproveita_as_cores_de_paleta_sem_duplicar():
    assert AZUL_CABECALHO == AZUL and VERMELHO_DESTAQUE == VERMELHO


def test_celula_destacada_tem_marca_de_texto_alem_da_cor():
    html = renderizar_cartao("Título", [LINHA], "maior percentual")
    assert "* 50%" in html  # marcador textual na célula destacada
    assert "30%" in html and "* 30%" not in html  # célula não destacada, sem marcador
    assert 'title="maior percentual"' in html  # lido por leitor de tela
    assert "text-decoration: underline" in html  # reforço visual além da cor


def test_titulo_destaque_padrao_quando_nao_informado():
    html = renderizar_cartao("Título", [LINHA])
    assert 'title="destaque"' in html


def test_tabela_rola_dentro_do_card_em_tela_estreita():
    """O card corta o que sai dele (overflow: hidden, para os cantos); a
    tabela precisa rolar dentro de um contêiner próprio no celular."""
    html = renderizar_cartao("Título", [LINHA])
    assert ".loteca-rolagem { overflow-x: auto;" in html
    assert html.index('<div class="loteca-rolagem"><table>') < html.index("</table></div></div>")
    assert html.count('<th scope="col">') == 5
