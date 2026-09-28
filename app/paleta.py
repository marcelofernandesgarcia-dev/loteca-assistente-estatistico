"""Cores usadas nos gráficos e marcadores da ficha do time, com a conferência
de contraste (WCAG 2.1: texto normal 4,5:1; elementos gráficos 3:1) em um só
lugar para poder ser testada."""

AZUL = "#1a4fa0"
VERMELHO = "#e30613"
VERDE = "#1e6b40"
CINZA = "#6b7785"
BRANCO = "#ffffff"

COR_RESULTADO = {"V": "#1e6b40", "E": "#5b6770", "D": "#b30010"}


def _canal(valor: int) -> float:
    v = valor / 255
    return v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4


def luminancia(cor: str) -> float:
    r, g, b = (int(cor[i:i + 2], 16) for i in (1, 3, 5))
    return 0.2126 * _canal(r) + 0.7152 * _canal(g) + 0.0722 * _canal(b)


def razao_de_contraste(cor_a: str, cor_b: str) -> float:
    la, lb = luminancia(cor_a), luminancia(cor_b)
    claro, escuro = max(la, lb), min(la, lb)
    return (claro + 0.05) / (escuro + 0.05)
