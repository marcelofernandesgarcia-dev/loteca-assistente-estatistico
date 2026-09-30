#!/usr/bin/env python3
"""Gera app/icone.ico (atalho do lançador): quadrado verde com a letra L branca.
Cores de app/paleta.py (verde com contraste acima de 4,5:1 contra o branco).
Usa o Pillow, que já vem com o Streamlit. Uso: python scripts/gerar_icone.py"""
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "app"))

from paleta import BRANCO, VERDE  # noqa: E402

TAMANHO = 256


def desenhar() -> Image.Image:
    imagem = Image.new("RGBA", (TAMANHO, TAMANHO), (0, 0, 0, 0))
    desenho = ImageDraw.Draw(imagem)
    desenho.rounded_rectangle((8, 8, TAMANHO - 8, TAMANHO - 8), radius=44, fill=VERDE)
    try:
        fonte = ImageFont.truetype("segoeuib.ttf", 170)
    except OSError:
        fonte = ImageFont.load_default(size=170)
    caixa = desenho.textbbox((0, 0), "L", font=fonte)
    largura, altura = caixa[2] - caixa[0], caixa[3] - caixa[1]
    desenho.text(((TAMANHO - largura) / 2 - caixa[0], (TAMANHO - altura) / 2 - caixa[1]), "L", font=fonte, fill=BRANCO)
    return imagem


if __name__ == "__main__":
    destino = RAIZ / "app" / "icone.ico"
    desenhar().save(destino, sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
    print(f"Ícone gravado em {destino}")
