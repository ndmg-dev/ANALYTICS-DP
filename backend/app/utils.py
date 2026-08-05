"""Backwards-compatible re-exports.

Company identification now lives in app/services/company_resolver.py, which
handles every export template plus the CNPJ, instead of the single legacy
filename pattern this module used to implement.
"""
from app.services.company_resolver import (  # noqa: F401
    extract_cnpj_from_filename,
    extract_company_from_filename,
)
