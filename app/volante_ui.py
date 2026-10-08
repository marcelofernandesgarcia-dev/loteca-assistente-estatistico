"""Volante de leitura (pedido do usuário, 08/10/2026): o bilhete salvo, a versão guardada ou o bilhete conferido
aparecem como o volante da tela, com os quadrados marcados, sem como mudar por engano.

Só HTML/CSS, sem lógica de negócio. A informação nunca depende só da cor (e-MAG): o quadrado marcado leva o "✓" e
um texto para leitor de tela; o resultado vem escrito ("acertou"/"errou") além da borda.
"""
import html

from paleta import VERDE, VERMELHO

COLUNAS = ("1", "X", "2")

_CSS = f"""
<style>
.vl-grade {{ display: flex; flex-wrap: wrap; gap: 12px; margin: 4px 0 12px; font-family: sans-serif; }}
.vl-jogo {{ box-sizing: border-box; width: 320px; max-width: 100%; border: 1px solid #d8dee8; border-radius: 8px;
  padding: 12px 14px; }}
.vl-jogo.vl-acertou {{ border: 2px solid {VERDE}; }}
.vl-jogo.vl-errou {{ border: 2px dashed {VERMELHO}; }}
.vl-titulo {{ margin-bottom: 8px; line-height: 1.4; }}
.vl-colunas {{ display: flex; gap: 8px; }}
.vl-coluna {{ width: 80px; }}
.vl-caixa {{ display: flex; align-items: center; gap: 6px; }}
.vl-quadrado {{ box-sizing: border-box; display: inline-flex; align-items: center; justify-content: center;
  width: 18px; height: 18px; border: 1px solid #8a94a0; border-radius: 4px; font-size: 13px; line-height: 1;
  color: #ffffff; }}
.vl-quadrado.vl-marcado {{ background: {VERMELHO}; border-color: {VERMELHO}; font-weight: bold; }}
.vl-pct {{ color: #5b6770; font-size: 0.85rem; margin-top: 2px; }}
.vl-resultado {{ margin-top: 8px; font-size: 0.85rem; }}
.vl-sr {{ position: absolute; width: 1px; height: 1px; padding: 0; margin: -1px; overflow: hidden;
  clip: rect(0, 0, 0, 0); white-space: nowrap; border: 0; }}
</style>
"""


def _percentual(pct: dict | None, coluna: str) -> str:
    if not pct or pct.get(coluna) is None:
        return "-"
    maior = max(COLUNAS, key=lambda c: (pct.get(c) or 0, -COLUNAS.index(c)))
    texto = f"{pct[coluna]:.0f}%"
    return f"<strong>{texto}</strong> (maior)" if coluna == maior else texto


def _coluna(coluna: str, marcada: bool, pct: dict | None) -> str:
    classe = "vl-quadrado vl-marcado" if marcada else "vl-quadrado"
    simbolo = "✓" if marcada else ""
    estado = "marcado" if marcada else "não marcado"
    return (
        '<div class="vl-coluna"><div class="vl-caixa">'
        f'<span class="{classe}" aria-hidden="true">{simbolo}</span><span>{coluna}</span>'
        f'<span class="vl-sr">, {estado}</span></div>'
        f'<div class="vl-pct">{_percentual(pct, coluna)}</div></div>'
    )


def _bloco(jogo: dict) -> str:
    marcadas = set(jogo["marcacoes"])
    resultado = jogo.get("resultado")
    classe, linha_resultado = "vl-jogo", ""
    if resultado:
        acertou = resultado in marcadas
        classe += " vl-acertou" if acertou else " vl-errou"
        linha_resultado = (f'<div class="vl-resultado">Resultado: <strong>{html.escape(resultado)}</strong> · '
                           + ("✓ acertou" if acertou else "✗ errou") + "</div>")
    titulo = (f'<strong>{jogo["num_jogo"]}.</strong> {html.escape(jogo["casa"])} <strong>x</strong> '
              f'{html.escape(jogo["fora"])}')
    colunas = "".join(_coluna(c, c in marcadas, jogo.get("pct")) for c in COLUNAS)
    return (f'<div class="{classe}" role="listitem"><div class="vl-titulo">{titulo}</div>'
            f'<div class="vl-colunas">{colunas}</div>{linha_resultado}</div>')


def renderizar_volante(jogos: list[dict], rotulo: str) -> str:
    """`jogos`, na ordem do concurso: num_jogo, casa, fora, marcacoes (lista de colunas) e, opcionais, pct
    ({'1','X','2'} em % do momento em que foi salvo) e resultado ('1'/'X'/'2' quando apurado). `rotulo`: nome da
    lista para leitor de tela (ex.: 'Bilhete nº 9'). Sem quebras de linha: o Markdown do Streamlit não mexe no HTML."""
    blocos = "".join(_bloco(j) for j in jogos)
    return _CSS.replace("\n", "") + f'<div class="vl-grade" role="list" aria-label="{html.escape(rotulo)}">{blocos}</div>'


def jogos_para_o_volante(linhas: list[dict]) -> list[dict]:
    """Converte as linhas de stats.bilhetes_salvos.jogos_do_bilhete no formato de renderizar_volante."""
    return [
        {
            "num_jogo": j["num_jogo"], "casa": j["casa"], "fora": j["fora"], "marcacoes": j["marcacoes"],
            "pct": ({"1": j["percentual_1"], "X": j["percentual_x"], "2": j["percentual_2"]}
                    if j.get("percentual_1") is not None else None),
            "resultado": j.get("resultado"),
        }
        for j in linhas
    ]
