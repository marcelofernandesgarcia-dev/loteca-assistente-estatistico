"""Prazo de apostas de um concurso -- regra pura, sem I/O."""
import datetime as dt


def situacao_do_prazo(
    data_limite_iso: str | None, horario_fim: int | None, agora: dt.datetime | None = None
) -> dict:
    """`horario_fim` é a hora cheia do encerramento (ex.: 15). Sem horário, o
    prazo é só aproximado (dia do primeiro jogo) e tratado até o fim do dia.
    Retorna {'exato', 'aberto', 'limite', 'restante'}; sem data, tudo None."""
    agora = agora or dt.datetime.now()
    if not data_limite_iso:
        return {"exato": False, "aberto": None, "limite": None, "restante": None}
    data = dt.date.fromisoformat(data_limite_iso)
    exato = horario_fim is not None
    limite = dt.datetime.combine(data, dt.time(horario_fim if exato else 23, 0 if exato else 59))
    restante = limite - agora
    return {"exato": exato, "aberto": restante.total_seconds() > 0, "limite": limite, "restante": restante}


def formatar_restante(restante: dt.timedelta) -> str:
    total = int(restante.total_seconds())
    if total <= 0:
        return "encerradas"
    dias, resto = divmod(total, 86400)
    horas, resto = divmod(resto, 3600)
    minutos = resto // 60
    if dias:
        return f"faltam {dias} d {horas} h"
    return f"faltam {horas} h {minutos} min"
