"""Tests for validation-only CSV imports."""

from app.services.imports import CSVImportError, CSVImportPreviewService


CSV = """iccid;imsi;msisdn;acc;ki;opc;adm
8949012345678901234;001010123456789;+491701234567;0001;00112233445566778899AABBCCDDEEFF;FFEEDDCCBBAA99887766554433221100;DEADBEEF
"""


def test_csv_preview_validates_without_exposing_keys() -> None:
    preview = CSVImportPreviewService().create_preview(CSV)

    assert preview.total_rows == 1
    assert preview.valid_rows == 1
    assert preview.stored is False
    assert preview.write_performed is False
    serialized = preview.model_dump_json()
    assert "00112233445566778899AABBCCDDEEFF" not in serialized
    assert "FFEEDDCCBBAA99887766554433221100" not in serialized
    assert "DEADBEEF" not in serialized


def test_csv_preview_marks_duplicate_identifiers() -> None:
    preview = CSVImportPreviewService().create_preview(CSV + CSV.splitlines()[1] + "\n")

    assert preview.invalid_rows == 1
    assert "doppelt" in preview.rows[1].errors[0]


def test_csv_preview_rejects_missing_columns() -> None:
    try:
        CSVImportPreviewService().create_preview("iccid;imsi\n1;2\n")
    except CSVImportError as exc:
        assert exc.code == "missing_columns"
    else:
        raise AssertionError("missing required columns were accepted")


def test_csv_preview_accepts_excel_separator_line_and_bom() -> None:
    content = "\ufeffsep=;\r\n" + CSV

    preview = CSVImportPreviewService().create_preview(content)

    assert preview.valid_rows == 1


def test_csv_preview_accepts_comma_delimiter() -> None:
    preview = CSVImportPreviewService().create_preview(CSV.replace(";", ","))

    assert preview.valid_rows == 1


def test_csv_preview_accepts_numbers_export_of_sysmocom_schema() -> None:
    headers = ",IMSI,ICCID,ACC,PIN1,PUK1,PIN2,PUK2,Ki,OPC,ADM1,KIC1,KID1,KIK1,KIC2,KID2,KIK2,KIC3,KID3,KIK3"
    row = ",001010123456789,8949012345678901234,1,0,12345678,0,12345678,00112233445566778899AABBCCDDEEFF,FFEEDDCCBBAA99887766554433221100,DEADBEEF," + ",".join(["A" * 32] * 9)
    content = "Tabelle 1\n" + "," * 19 + "\n" + headers + "\n" + row + "\n"

    preview = CSVImportPreviewService().create_preview(content)

    assert preview.valid_rows == 1
    assert preview.rows[0].adm_configured is True


def test_csv_preview_reports_fields_without_secret_values() -> None:
    invalid = CSV.replace("00112233445566778899AABBCCDDEEFF", "not-a-key")

    preview = CSVImportPreviewService().create_preview(invalid)

    assert preview.invalid_rows == 1
    assert preview.rows[0].errors == ["Ki: muss aus genau 32 Hex-Zeichen bestehen"]
    assert "not-a-key" not in preview.model_dump_json()


def test_csv_import_accepts_optional_ims_fields() -> None:
    content = CSV.replace(
        "iccid;imsi;msisdn;acc;ki;opc;adm",
        "iccid;imsi;msisdn;acc;ki;opc;adm;impi;impu;domain;ist",
    ).replace(
        ";DEADBEEF\n",
        ";DEADBEEF;user@ims.example;sip:user@ims.example;ims.example;03FF\n",
    )

    preview, records = CSVImportPreviewService().parse(content)

    assert preview.valid_rows == 1
    assert records[0]["impi"] == "user@ims.example"
    assert records[0]["impu"] == "sip:user@ims.example"
    assert records[0]["ims_domain"] == "ims.example"
    assert records[0]["ist"] == "03FF"


def test_csv_import_rejects_invalid_ims_field_without_echoing_value() -> None:
    content = CSV.replace(";adm\n", ";adm;impi\n").replace(";DEADBEEF\n", ";DEADBEEF;invalid identity\n")

    preview = CSVImportPreviewService().create_preview(content)

    assert preview.invalid_rows == 1
    assert preview.rows[0].errors == ["IMPI: ungültiges Format"]
    assert "invalid identity" not in preview.model_dump_json()
