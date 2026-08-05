"""Resolution of the owning company for an imported spreadsheet.

Historically the company was a regex over the filename ("Empregados - X -
Ativos"), which silently returned nothing for any other export template — and
imports whose company could not be derived were dropped from every screen.
Companies are now rows in `companies`, keyed by CNPJ whenever the filename
carries one, so a new client is onboarded by importing its file rather than by
changing code.
"""
import re
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import Company

# 14 digits not glued to other digits — the CNPJ in
# "... Apenas Ativos 19842356000109_1785960935078.xls". The trailing timestamp
# is longer than 14 digits, so the boundary assertions keep it from matching.
CNPJ_RE = re.compile(r"(?<!\d)(\d{14})(?!\d)")

# "Empregados - <empresa> - Ativos.xls" (Domínio's older export).
LEGACY_NAME_RE = re.compile(r"Empregados\s*-\s*(.+?)\s*-\s*Ativos", re.IGNORECASE)

# "<empresa> Empregados em Excel - Apenas Ativos ...xls" (current export).
PREFIX_NAME_RE = re.compile(r"^\s*(.+?)\s+Empregados\b", re.IGNORECASE)


def extract_cnpj_from_filename(filename: str) -> Optional[str]:
    match = CNPJ_RE.search(filename or "")
    return match.group(1) if match else None


def extract_company_from_filename(filename: str) -> Optional[str]:
    """Best-effort company display name from the filename, across every export
    template seen so far. Returns None when the filename carries no name."""
    filename = filename or ""
    for pattern in (LEGACY_NAME_RE, PREFIX_NAME_RE):
        match = pattern.search(filename)
        if match:
            name = match.group(1).strip(" -_")
            if name:
                return name
    return None


def format_cnpj(cnpj: str) -> str:
    return f"{cnpj[:2]}.{cnpj[2:5]}.{cnpj[5:8]}/{cnpj[8:12]}-{cnpj[12:]}"


def get_or_create_company(
    db: Session, name: Optional[str] = None, cnpj: Optional[str] = None
) -> Optional[Company]:
    """Find a company by CNPJ (preferred) or by case-insensitive name, creating
    it when neither matches. Flushes so the caller gets an id without having to
    commit."""
    cnpj = re.sub(r"\D", "", cnpj) if cnpj else None
    if cnpj and len(cnpj) != 14:
        cnpj = None
    name = name.strip() if name else None

    company = None
    if cnpj:
        company = db.query(Company).filter(Company.cnpj == cnpj).first()
    if not company and name:
        company = db.query(Company).filter(func.lower(Company.name) == name.lower()).first()

    if company:
        # Late-arriving identity details enrich the existing row rather than
        # creating a near-duplicate.
        if cnpj and not company.cnpj:
            company.cnpj = cnpj
        return company

    if not name and not cnpj:
        return None

    company = Company(name=name or format_cnpj(cnpj), cnpj=cnpj)
    db.add(company)
    db.flush()
    return company


def resolve_company(
    db: Session,
    filename: str,
    sheet_title: Optional[str] = None,
    explicit_company_id: Optional[int] = None,
) -> Optional[Company]:
    """Resolve the company for an import, most trustworthy source first.

    Returns None only when nothing at all identifies the company — the import
    is then flagged in the history so it can be assigned by hand, instead of
    disappearing from the dashboard.
    """
    if explicit_company_id:
        company = db.get(Company, explicit_company_id)
        if company:
            return company

    cnpj = extract_cnpj_from_filename(filename)
    name = extract_company_from_filename(filename)

    if cnpj or name:
        return get_or_create_company(db, name=name, cnpj=cnpj)

    if sheet_title and sheet_title.strip():
        return get_or_create_company(db, name=sheet_title.strip())

    return None
