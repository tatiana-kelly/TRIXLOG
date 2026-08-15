"""Utilitários compartilhados pelos 3 importadores — tratam os riscos de dado reais documentados
em docs/COST_ALLOCATION.md#6 (CNPJ como float, Número como float).

Todas as funções usam pd.isna() como guarda universal primeiro: cobre None, float('nan'),
np.nan E pd.NaT numa só checagem. Checagem por isinstance(value, float)/isinstance(value,
datetime) sozinha NÃO basta — pd.NaT faz duck-typing como datetime.datetime e escapa por ali
("dt_pagamento": NaT sobrevivendo até o INSERT, descoberto rodando o import contra os 3
arquivos reais)."""

from datetime import date, datetime

import pandas as pd


def _is_missing(value) -> bool:
    try:
        result = pd.isna(value)
    except (TypeError, ValueError):
        return False
    return bool(result) if not hasattr(result, "__len__") else False


def float_id_to_str(value) -> str | None:
    """CNPJ/CPF/Número chegam do Excel como float (perda potencial de zero à esquerda ANTES de
    chegarmos ao dado — não recuperável aqui). Nosso trabalho é não piorar: nunca deixar
    '6.348688e+12' ou '384.0' sobreviver como chave."""
    if _is_missing(value):
        return None
    if isinstance(value, float):
        return str(int(value))
    return str(value).strip() or None


def to_date(value) -> date | None:
    if _is_missing(value):
        return None
    if isinstance(value, pd.Timestamp):
        return value.date()
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return None


def to_float(value, default: float = 0.0) -> float:
    if _is_missing(value):
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def clean_str(value) -> str | None:
    if _is_missing(value):
        return None
    text = str(value).strip()
    return text or None
