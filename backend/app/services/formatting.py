"""Formatação compartilhada — extraído depois de duplicar em decisions_engine.py e
audit_engine.py. Python's f"{v:,.2f}" é formato americano (1,234.56); a plataforma toda usa
formato brasileiro (1.234,56), igual ao toLocaleString('pt-BR') do frontend."""


def brl(valor: float) -> str:
    inteiro, decimal = f"{valor:,.2f}".split(".")
    return inteiro.replace(",", ".") + "," + decimal
