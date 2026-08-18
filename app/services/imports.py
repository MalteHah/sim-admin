"""Validation-only CSV import service with no persistence or hardware access."""

import csv
import io

from pydantic import ValidationError

from app.models import CSVImportPreview, CSVImportRow, ProvisioningDraft

REQUIRED_COLUMNS = {"iccid", "imsi", "ki", "opc", "adm"}
SYSMOCOM_COLUMNS = {"pin1", "puk1", "pin2", "puk2", "adm1"} | {
    f"{prefix}{index}" for prefix in ("kic", "kid", "kik") for index in range(1, 4)
}
ALLOWED_COLUMNS = REQUIRED_COLUMNS | {"msisdn", "acc"} | SYSMOCOM_COLUMNS


class CSVImportError(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


class CSVImportPreviewService:
    """Parse and validate CSV text without retaining the source or its values."""

    def create_preview(self, content: str) -> CSVImportPreview:
        preview, _ = self.parse(content)
        return preview

    def parse(self, content: str) -> tuple[CSVImportPreview, list[dict[str, str]]]:
        content = content.lstrip("\ufeff")
        lines = content.splitlines()
        if lines and lines[0].strip().lower().startswith("sep="):
            declared = lines.pop(0).strip()[4:]
            delimiter = "\t" if declared == "\\t" else declared
            content = "\n".join(lines)
        else:
            delimiter = ";"
        header_index = None
        for index, line in enumerate(lines[:20]):
            for candidate in (";", ",", "\t"):
                fields = {field.strip().lower() for field in next(csv.reader([line], delimiter=candidate))}
                if {"iccid", "imsi", "ki", "opc"}.issubset(fields) and ({"adm", "adm1"} & fields):
                    header_index, delimiter = index, candidate
                    break
            if header_index is not None:
                break
        if header_index is not None:
            content = "\n".join(lines[header_index:])
        if not content.strip() or delimiter not in {";", ",", "\t"}:
            raise CSVImportError("invalid_csv", "Die CSV-Datei konnte nicht gelesen werden")
        try:
            reader = csv.DictReader(io.StringIO(content), delimiter=delimiter)
            parsed_rows = list(reader)
        except csv.Error as exc:
            raise CSVImportError("invalid_csv", "Die CSV-Datei konnte nicht gelesen werden") from exc
        headers = {header.strip().lower() for header in (reader.fieldnames or []) if header and header.strip()}
        if "adm1" in headers:
            headers.add("adm")
        missing = REQUIRED_COLUMNS - headers
        unknown = headers - ALLOWED_COLUMNS
        if missing:
            raise CSVImportError("missing_columns", "Pflichtspalten fehlen: " + ", ".join(sorted(missing)))
        if unknown:
            raise CSVImportError("unknown_columns", "Unbekannte Spalten: " + ", ".join(sorted(unknown)))

        rows: list[CSVImportRow] = []
        records: list[dict[str, str]] = []
        seen_iccid: set[str] = set()
        seen_imsi: set[str] = set()
        for row_number, raw in enumerate(parsed_rows, start=2):
            normalized = {str(key).strip().lower(): (value or "").strip() for key, value in raw.items() if key is not None}
            populated = {key: value for key, value in normalized.items() if value}
            if not populated:
                continue
            if (
                not normalized.get("iccid")
                and normalized.get("imsi", "")
                and not normalized["imsi"].isdigit()
                and set(populated) == {"imsi"}
            ):
                continue
            if not normalized.get("adm") and normalized.get("adm1"):
                normalized["adm"] = normalized["adm1"]
            acc = normalized.get("acc", "")
            if acc and len(acc) < 4 and all(character in "0123456789abcdefABCDEF" for character in acc):
                normalized["acc"] = acc.zfill(4)
            errors: list[str] = []
            try:
                ProvisioningDraft.model_validate({
                    "iccid": normalized.get("iccid", ""), "imsi": normalized.get("imsi", ""),
                    "msisdn": normalized.get("msisdn") or None, "acc": normalized.get("acc") or "0001",
                    "ki": normalized.get("ki", ""), "opc": normalized.get("opc", ""), "adm": normalized.get("adm", ""),
                })
            except ValidationError as exc:
                labels = {"iccid": "ICCID", "imsi": "IMSI", "msisdn": "MSISDN", "acc": "ACC", "ki": "Ki", "opc": "OPc", "adm": "ADM1"}
                seen_fields: set[str] = set()
                for issue in exc.errors():
                    field = str(issue["loc"][0]) if issue.get("loc") else "Datensatz"
                    if field in seen_fields:
                        continue
                    seen_fields.add(field)
                    label = labels.get(field, field)
                    if field in {"ki", "opc"}:
                        errors.append(f"{label}: muss aus genau 32 Hex-Zeichen bestehen")
                    elif field == "adm":
                        errors.append("ADM1: fehlt oder hat eine ungültige Länge")
                    else:
                        errors.append(f"{label}: ungültiges Format")
            iccid, imsi = normalized.get("iccid", ""), normalized.get("imsi", "")
            if iccid in seen_iccid or imsi in seen_imsi:
                errors.append("ICCID oder IMSI ist in der Datei doppelt vorhanden")
            seen_iccid.add(iccid); seen_imsi.add(imsi)
            rows.append(CSVImportRow(row_number=row_number, iccid=iccid, imsi=imsi, valid=not errors, errors=errors,
                ki_configured=bool(normalized.get("ki")), opc_configured=bool(normalized.get("opc")), adm_configured=bool(normalized.get("adm"))))
            records.append({key: normalized.get(key, "") for key in sorted(ALLOWED_COLUMNS)})
            if len(rows) > 5000:
                raise CSVImportError("too_many_rows", "Die Datei darf höchstens 5.000 Datensätze enthalten")
        if not rows:
            raise CSVImportError("empty_csv", "Die CSV-Datei enthält keine Datensätze")
        valid = sum(row.valid for row in rows)
        return CSVImportPreview(total_rows=len(rows), valid_rows=valid, invalid_rows=len(rows)-valid, rows=rows), records
