"""Renderiza a tabela de jogos no estilo visual do portal da CAIXA
(cabeçalho azul, destaque vermelho na coluna vencedora/sugerida) --
referência visual trazida pelo usuário (print do portal oficial).
Só HTML/CSS, sem lógica de negócio -- recebe os dados já calculados.

Cores vêm de paleta.py (já conferidas quanto a contraste, ver test_paleta.py) --
não duplica os hexadecimais aqui.
"""
from paleta import AZUL, VERMELHO

AZUL_CABECALHO = AZUL
VERMELHO_DESTAQUE = VERMELHO
CINZA_LINHA = "#eef3f8"

_CSS = f"""
<style>
.loteca-card {{ border: 1px solid #d8dee8; border-radius: 6px; overflow: hidden;
  font-family: sans-serif; margin-bottom: 1.5rem; }}
.loteca-rolagem {{ overflow-x: auto; -webkit-overflow-scrolling: touch; }}
.loteca-card table {{ width: 100%; min-width: 460px; border-collapse: collapse; font-size: 0.85rem; }}
.loteca-card td:last-child {{ white-space: nowrap; }}
.loteca-card th {{ background: {AZUL_CABECALHO}; color: white; padding: 8px 10px; text-align: left; }}
.loteca-card td {{ padding: 7px 10px; border-bottom: 1px solid #e2e6ee; }}
.loteca-card tr:nth-child(even) td {{ background: {CINZA_LINHA}; }}
.loteca-badge {{ display: inline-block; min-width: 22px; text-align: center; padding: 2px 7px;
  border-radius: 4px; font-weight: bold; color: #333; }}
.loteca-badge.destaque {{ background: {VERMELHO_DESTAQUE}; color: white; border: 2px solid #7a0410;
  text-decoration: underline; }}
.loteca-titulo {{ font-weight: bold; padding: 8px 10px; background: #f5f7fa; border-bottom: 1px solid #d8dee8; }}
</style>
"""


def _badge(valor: str, destacado: bool, titulo: str = "") -> str:
    """`destacado` nunca é só cor: soma borda, sublinhado e um marcador de
    texto (*) -- e-MAG exige que a informação não dependa só da cor."""
    classe = "loteca-badge destaque" if destacado else "loteca-badge"
    texto = f"* {valor}" if destacado else valor
    atributo_titulo = f' title="{titulo}"' if titulo else ""
    return f'<span class="{classe}"{atributo_titulo}>{texto}</span>'


def renderizar_titulo_cartao(titulo: str) -> str:
    """Só a barra de título do card, para quando o corpo é feito de widgets
    interativos do Streamlit (não dá para colocar widget dentro de HTML
    estático) -- usado no card 3 (bilhete)."""
    return _CSS + '<div class="loteca-card"><div class="loteca-titulo">' + titulo + "</div></div>"


def renderizar_cartao(titulo: str, linhas: list[dict], titulo_destaque: str = "destaque") -> str:
    """`linhas`: cada item precisa de num_jogo, casa, fora, data,
    valor_casa, valor_x, valor_fora (strings a exibir), e
    destaque_casa/destaque_x/destaque_fora (bool, se aquela célula deve
    aparecer marcada). `titulo_destaque`: o que a marca quer dizer nesta
    tabela (ex.: 'resultado vencedor', 'maior percentual') -- vai no atributo
    title de cada célula marcada, lido por leitor de tela."""
    corpo = []
    for linha in linhas:
        corpo.append(
            f"<tr>"
            f"<td>{linha['num_jogo']}</td>"
            f"<td>{_badge(linha['valor_casa'], linha['destaque_casa'], titulo_destaque)} {linha['casa']}</td>"
            f"<td>{_badge(linha['valor_x'], linha['destaque_x'], titulo_destaque)}</td>"
            f"<td>{linha['fora']} {_badge(linha['valor_fora'], linha['destaque_fora'], titulo_destaque)}</td>"
            f"<td>{linha['data']}</td>"
            f"</tr>"
        )
    # O card tem overflow: hidden (cantos arredondados); sem o contêiner de
    # rolagem, a tabela mais larga que a tela do celular era cortada.
    html = (
        _CSS
        + '<div class="loteca-card">'
        + f'<div class="loteca-titulo">{titulo}</div>'
        + '<div class="loteca-rolagem"><table><thead><tr>'
        + '<th scope="col">Jogo</th><th scope="col">Coluna 1</th><th scope="col">X</th>'
        + '<th scope="col">Coluna 2</th><th scope="col">Data</th></tr></thead>'
        + f"<tbody>{''.join(corpo)}</tbody></table></div></div>"
    )
    return html


def renderizar_tabela(titulo: str, cabecalhos: list[str], linhas: list[list[str]]) -> str:
    """Tabela genérica no mesmo card (cabeçalho com scope, rolagem própria no
    celular). As células já chegam escapadas: quem chama é responsável por
    `html.escape` em texto vindo de dado."""
    cabeca = "".join(f'<th scope="col">{c}</th>' for c in cabecalhos)
    corpo = "".join("<tr>" + "".join(f"<td>{celula}</td>" for celula in linha) + "</tr>" for linha in linhas)
    return (
        _CSS
        + '<div class="loteca-card">'
        + f'<div class="loteca-titulo">{titulo}</div>'
        + f'<div class="loteca-rolagem"><table><thead><tr>{cabeca}</tr></thead>'
        + f"<tbody>{corpo}</tbody></table></div></div>"
    )
