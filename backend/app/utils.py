import re
from typing import Optional


def extract_company_from_filename(filename: str) -> Optional[str]:
    """Extract the company name from filenames like
    "Empregados - <empresa> - Ativos.xls" — a far more reliable source than
    sniffing spreadsheet cells, which varies by template."""
    match = re.search(r"Empregados\s*-\s*(.+?)\s*-\s*Ativos", filename or "", re.IGNORECASE)
    return match.group(1).strip() if match else None
