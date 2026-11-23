"""Where a layout's sheet range and the user's workbook come from in returns that also run against a database."""
import datetime as dt
import os

from backend.error_improvement import cell_locator as cl
from backend.error_improvement import match_upload as mu


def _query(tmp_path, name, rows):
    body = "".join(f'<Row QueryId="1" TemplateId="{tid}"><SelectQuery>{sql}</SelectQuery></Row>' for tid, sql in rows)
    (tmp_path / name).write_text(f'<?xml version="1.0"?><Document>{body}</Document>', encoding="utf-8")


def test_excel_query_file_fills_in_layouts_the_main_query_file_has_no_range_for(tmp_path):
    _query(tmp_path, "XML_Query.xml", [("1", "Select CODE from CIMS_TABLE"), ("2", "Select F1 as D From [Own$A1:B2]")])
    _query(tmp_path, "XML_Query_Excel.xml", [("1", "Select F1 as D From [Sheet1$A3:B9]"), ("2", "Select F1 as D From [Other$A1:A2]")])
    meta = cl.load_form_folder(str(tmp_path), "9999")
    assert meta.sheets["1"] == [("Sheet1", "A3:B9")]          # taken from the Excel file: the main file has only SQL for it
    assert meta.sheets["2"] == [("Own", "A1:B2")]             # the main file already names a range: the Excel file is not consulted


def test_a_return_without_the_excel_query_file_reads_as_before(tmp_path):
    _query(tmp_path, "XML_Query.xml", [("1", "Select F1 as D From [Own$A1:B2]")])
    assert cl.load_form_folder(str(tmp_path), "9999").sheets == {"1": [("Own", "A1:B2")]}


def _upload(tmp_path, folder):
    d = tmp_path / "UploadedFiles" / folder
    d.mkdir(parents=True)
    (d / "Return.xlsx").write_bytes(b"x")
    return str(d / "Return.xlsx")


def test_upload_folders_named_in_either_format_are_matched(tmp_path):
    old = _upload(tmp_path, "05-10-26-18-00-07")
    assert mu.match_upload(str(tmp_path), "X_05-10-26_06-01-25_Instance.html") == old        # 06:01 am/pm both tried: 18:00 is 1 minute before 18:01
    new = tmp_path / "n"
    new.mkdir()
    newer = _upload(new, "20261005180007")
    assert mu.match_upload(str(new), "X_05-10-26_06-01-25_Instance.html") == newer
    assert mu.ranked_uploads(str(new), "X_05-10-26_06-01-25_Instance.html") == [newer]


def test_an_upload_folder_in_neither_format_is_ignored(tmp_path):
    _upload(tmp_path, "backup")
    assert mu.match_upload(str(tmp_path), "X_05-10-26_06-01-25_Instance.html") is None
    assert mu._stamp("20261005180007") == dt.datetime(2026, 10, 5, 18, 0, 7)
    assert os.path.isdir(tmp_path / "UploadedFiles")
