"""Medição do filtro de notícias contra um gabarito validado pelo usuário (item A3 do plano v2, 07/10/2026).

O gabarito é separado das regras: as 11 manchetes do concurso 1273 (tests/test_gabarito_noticias_1273.py)
serviram para construir as barreiras e não medem a precisão fora da amostra. Este módulo mede em manchetes
novas, a partir do concurso 1274, rotuladas pelo usuário DEPOIS da leitura.

Formato do arquivo (CSV com ';', um por concurso, em data/gabarito-noticias/):
concurso;time;manchete;decisao_app;sinais_app;correto
- `decisao_app`: aplicada, informativa ou descartada (o que o app fez);
- `correto`: "sim" ou "nao", preenchido pelo usuário. Para aplicada/informativa: o sinal é mesmo deste time
  e deste jogo? Para descartada: o descarte estava certo? Linha em branco não entra na conta.
"""
import csv
import math
from pathlib import Path

CAMPOS = ["concurso", "time", "manchete", "decisao_app", "sinais_app", "correto"]
DECISOES_COM_SINAL = ("aplicada", "informativa", "descartada")


def linhas_para_rotular(noticias_lidas: list[dict]) -> list[dict]:
    """Manchetes com palavra de sinal (as sem sinal não têm o que conferir), prontas para o CSV."""
    return [
        {
            "concurso": n["concurso_numero"], "time": n["participante"], "manchete": n["titulo"],
            "decisao_app": n["situacao"], "sinais_app": ",".join(n["aceitos"] or [d["sinal"] for d in n["descartes"]]),
            "correto": "",
        }
        for n in noticias_lidas if n["situacao"] in DECISOES_COM_SINAL
    ]


def gravar_csv(linhas: list[dict], caminho: Path) -> None:
    caminho.parent.mkdir(parents=True, exist_ok=True)
    with open(caminho, "w", encoding="utf-8", newline="") as arquivo:
        escritor = csv.DictWriter(arquivo, fieldnames=CAMPOS, delimiter=";")
        escritor.writeheader()
        escritor.writerows(linhas)


def ler_csv(caminho: Path) -> list[dict]:
    with open(caminho, encoding="utf-8", newline="") as arquivo:
        return list(csv.DictReader(arquivo, delimiter=";"))


def _intervalo_wilson(acertos: int, total: int, z: float = 1.96) -> tuple[float, float] | None:
    """Intervalo de 95% para uma proporção (Wilson): com poucas manchetes, a faixa é larga e diz isso."""
    if total == 0:
        return None
    p = acertos / total
    centro = (p + z * z / (2 * total)) / (1 + z * z / total)
    meia = z * math.sqrt(p * (1 - p) / total + z * z / (4 * total * total)) / (1 + z * z / total)
    return max(0.0, centro - meia), min(1.0, centro + meia)


def medir(linhas: list[dict]) -> dict:
    """Precisão: dos sinais que o app aceitou (aplicada ou informativa), quantos o usuário confirmou.
    Cobertura: dos sinais que deveriam valer (aceitos certos + descartes errados), quantos o app aceitou."""
    rotuladas = [l for l in linhas if (l.get("correto") or "").strip().lower() in ("sim", "nao", "não")]
    certo = lambda l: l["correto"].strip().lower() == "sim"  # noqa: E731
    aceitas = [l for l in rotuladas if l["decisao_app"] in ("aplicada", "informativa")]
    descartadas = [l for l in rotuladas if l["decisao_app"] == "descartada"]
    aceitas_certas = sum(1 for l in aceitas if certo(l))
    descartes_errados = sum(1 for l in descartadas if not certo(l))
    deveriam_valer = aceitas_certas + descartes_errados
    return {
        "rotuladas": len(rotuladas),
        "aceitas": len(aceitas),
        "precisao": aceitas_certas / len(aceitas) if aceitas else None,
        "precisao_ic95": _intervalo_wilson(aceitas_certas, len(aceitas)),
        "cobertura": aceitas_certas / deveriam_valer if deveriam_valer else None,
        "descartes_errados": descartes_errados,
    }
