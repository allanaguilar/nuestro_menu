from datetime import date, timedelta

WEEKDAY_LABELS = (
    "Lunes",
    "Martes",
    "Miércoles",
    "Jueves",
    "Viernes",
    "Sábado",
    "Domingo",
)
WEEKDAY_SHORT = ("Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom")


def monday_of(value: date) -> date:
    return value - timedelta(days=value.weekday())


def week_dates(week_start: date) -> list[date]:
    start = monday_of(week_start)
    return [start + timedelta(days=offset) for offset in range(7)]


def weekday_label(value: date) -> str:
    return WEEKDAY_LABELS[value.weekday()]


def weekday_short(value: date) -> str:
    return WEEKDAY_SHORT[value.weekday()]
