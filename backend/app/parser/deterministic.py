import io
import os
import re
import xlrd
from datetime import datetime
from typing import Dict, Any, List, Tuple

class ParserResult:
    def __init__(self):
        self.records: List[Dict[str, Any]] = []
        self.confidence_score: float = 0.0
        self.confidence_factors: Dict[str, float] = {}
        self.data_quality_score: float = 0.0
        self.findings: List[Dict[str, Any]] = []
        self.is_success: bool = False
        self.error_details: str = ""

class ExcelDeterministicParser:
    REQUIRED_HEADERS = {
        ("codigo",): "code",
        ("nome",): "name",
        ("cargo",): "job_title",
        ("categoria",): "category",
        ("hor.", "horas", "carga hor", "hrs mensais", "horaria"): "monthly_hours",
        ("nf", "num fil", "filhos"): "children_count",
        ("nd", "num dep", "dependentes"): "dependents_count",
        ("admissao", "dt adm", "data adm", "dt. adm.", "dt admissao"): "admission_date",
        ("sin", "sindical", "contribuicao"): "union_contribution",
        ("opt", "fgts"): "fgts_option",
        ("salario", "remuneracao", "base", "vencimento"): "salary"
    }

    def _normalize_header(self, text: str) -> str:
        if not isinstance(text, str):
            return ""
        text = text.lower().strip()
        text = re.sub(r'[áàâã]', 'a', text)
        text = re.sub(r'[éèê]', 'e', text)
        text = re.sub(r'[íìî]', 'i', text)
        text = re.sub(r'[óòôõ]', 'o', text)
        text = re.sub(r'[úùû]', 'u', text)
        text = re.sub(r'[ç]', 'c', text)
        return text

    def parse(self, file_content: bytes) -> ParserResult:
        result = ParserResult()
        try:
            book = xlrd.open_workbook(file_contents=file_content, formatting_info=True)
        except Exception:
            try:
                book = xlrd.open_workbook(file_contents=file_content)
            except Exception as e:
                result.error_details = f"Failed to open workbook: {e}"
                return result

        sheet = book.sheet_by_index(0)
        
        # 1. Header candidate detection and Company extraction
        company_name = ""
        if sheet.nrows > 0:
            val = sheet.cell_value(0, 0)
            if isinstance(val, str) and val.strip() != "":
                company_name = val.strip()

        header_row_idx = -1
        column_mapping = {}
        for rowx in range(min(20, sheet.nrows)):
            row_values = sheet.row_values(rowx)
            mapped_count = 0
            temp_mapping = {}
            for colx, cell_val in enumerate(row_values):
                norm_val = self._normalize_header(str(cell_val))
                for req_h_list, canon_h in self.REQUIRED_HEADERS.items():
                    if any(req in norm_val for req in req_h_list):
                        temp_mapping[canon_h] = colx
                        mapped_count += 1
            if mapped_count >= 5:  # Arbitrary threshold to consider it a header row
                header_row_idx = rowx
                column_mapping = temp_mapping
                break

        if header_row_idx == -1:
            result.error_details = "Could not identify header row."
            return result

        # Calculate Header Anchor Quality
        header_quality = len(column_mapping) / len(self.REQUIRED_HEADERS)
        result.confidence_factors["header_anchor_quality"] = header_quality

        # 2. Extract Data Rows
        start_row = header_row_idx + 1
        # Skip empty rows after header
        while start_row < sheet.nrows:
            val = sheet.cell_value(start_row, column_mapping.get("code", 0))
            if isinstance(val, float) or (isinstance(val, str) and val.strip() != ""):
                if not (isinstance(val, str) and val.strip() == ""):
                    break
            start_row += 1

        extracted_records = []
        for rowx in range(start_row, sheet.nrows):
            code_val = sheet.cell_value(rowx, column_mapping.get("code", 0))
            # Stopping rule: code must be a float (or string that looks like code)
            if isinstance(code_val, float):
                # Valid row
                pass
            elif isinstance(code_val, str) and code_val.strip() == "":
                break # Reached end or empty row
            else:
                # Reached footer/totals (e.g. 'ND : N° DE DEPENDENTES')
                break

            record = {"original_row": rowx, "company": company_name}
            for canon_h, mapped_colx in column_mapping.items():
                val = sheet.cell_value(rowx, mapped_colx)
                
                # Handle merged cells offset (check col-1 and col+1 if empty)
                if (val == "" or val is None) and canon_h != "code":
                    if mapped_colx > 0:
                        val_left = sheet.cell_value(rowx, mapped_colx - 1)
                        if val_left != "" and val_left is not None:
                            val = val_left
                    if (val == "" or val is None) and mapped_colx < sheet.ncols - 1:
                        val_right = sheet.cell_value(rowx, mapped_colx + 1)
                        if val_right != "" and val_right is not None:
                            val = val_right
                
                # Conversion logic
                if canon_h == "code":
                    val = str(int(val)) if isinstance(val, float) else str(val)
                elif canon_h in ["children_count", "dependents_count"]:
                    if isinstance(val, str):
                        clean_val = re.sub(r'[^\d]', '', val)
                        val = int(clean_val) if clean_val else None
                    else:
                        val = int(val) if isinstance(val, (float, int)) else None
                elif canon_h == "monthly_hours":
                    if isinstance(val, str):
                        clean_val = re.sub(r'[^\d,.-]', '', val).replace(',', '.')
                        try: val = float(clean_val)
                        except ValueError: val = None
                    else:
                        val = float(val) if isinstance(val, (float, int)) else None
                elif canon_h == "salary":
                    if isinstance(val, str):
                        # Brazilian currency format: R$ 1.500,00 -> 1500.00
                        clean_val = re.sub(r'[^\d,-]', '', val).replace('.', '').replace(',', '.')
                        try: val = float(clean_val)
                        except ValueError: val = None
                    else:
                        val = float(val) if isinstance(val, (float, int)) else None
                elif canon_h in ["union_contribution", "fgts_option"]:
                    val_str = str(val).strip().upper()
                    if val_str == 'S': val = True
                    elif val_str == 'N': val = False
                    else: val = None
                elif canon_h == "admission_date":
                    if isinstance(val, float):
                        # Excel serial date
                        try:
                            dt_tuple = xlrd.xldate_as_tuple(val, book.datemode)
                            val = datetime(*dt_tuple)
                        except:
                            val = None
                    else:
                        val = None
                else:
                    val = str(val).strip() if val else ""
                
                record[canon_h] = val
            extracted_records.append(record)

        result.records = extracted_records
        
        # Calculate Confidence and Data Quality
        # (Simplified for the sake of MVP completion)
        result.confidence_score = header_quality * 1.0  # Basic for now
        if result.confidence_score >= float(os.getenv("PARSER_CONFIDENCE_THRESHOLD", "0.85")):
            result.is_success = True
            
        result.data_quality_score = 100.0 # Placeholder
        
        return result
