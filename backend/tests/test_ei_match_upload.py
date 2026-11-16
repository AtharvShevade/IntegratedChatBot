"""Pairing an error file with its upload: the instance log's exact record first, the 30-minute window as the fallback."""
import os
import sys

from backend.error_improvement import match_upload as mu       # noqa: E402

ERR = "APBL250331R09603Q_21-11-25_03-18-00_Instance.html"


def _repo(tmp_path, upload_folder, log_upload_dt=None, with_row=True, form="2036"):
    db = tmp_path / "DataBase"
    folder = db / form
    (folder / "UploadedFiles" / upload_folder).mkdir(parents=True)
    (folder / "UploadedFiles" / upload_folder / "LRBase.xlsx").write_bytes(b"x")
    row = f'<Row Id="1" FormId="{form}" FileUploadDT="{log_upload_dt}" ErrorDocPath="{ERR}"/>' if with_row else ""
    (db / "XML_InstanceLog.xml").write_text(f"<Document>{row}</Document>", encoding="utf-8")
    return str(folder)


def test_the_logged_upload_is_found_however_long_before_the_error_file_it_was_made(tmp_path):
    folder = _repo(tmp_path, "21-11-25-10-02-00", "21-Nov-2025 10:02:00 AM")                  # 5 hours before the error file
    got = mu.match_upload(folder, ERR)
    assert got and got.endswith(os.path.join("21-11-25-10-02-00", "LRBase.xlsx"))
    assert mu.match_upload(folder, ERR.replace("03-18-00", "03-19-00")) is None              # another run: no log row, no upload in the window


def test_the_newer_folder_naming_and_a_pm_time_are_understood(tmp_path):
    folder = _repo(tmp_path, "20251121150212", "21-Nov-2025 03:02:12 PM")
    assert mu.match_upload(folder, ERR).endswith(os.path.join("20251121150212", "LRBase.xlsx"))


def test_without_a_log_row_or_with_the_upload_gone_the_thirty_minute_rule_still_applies(tmp_path):
    folder = _repo(tmp_path, "21-11-25-15-15-12", with_row=False)                              # 3 minutes before, no log row
    assert mu.match_upload(folder, ERR).endswith(os.path.join("21-11-25-15-15-12", "LRBase.xlsx"))
    folder2 = _repo(tmp_path / "b", "21-11-25-15-10-00", "21-Nov-2025 09:00:00 AM")            # the log names an upload that is not there
    assert mu.match_upload(folder2, ERR).endswith(os.path.join("21-11-25-15-10-00", "LRBase.xlsx"))
    folder3 = _repo(tmp_path / "c", "21-11-25-09-00-00", with_row=False)                       # 6 hours before and no row: nothing
    assert mu.match_upload(folder3, ERR) is None


def test_the_6_0_log_names_are_understood(tmp_path):
    err = "RBIN095622820260430F013D_261102122342_Instance.html"                                # no time in the name: only the log can pair it
    db = tmp_path / "DataBase"
    up = db / "2002" / "UploadedFiles" / "02-11-26-12-23-37"
    up.mkdir(parents=True)
    (up / "F013.xlsx").write_bytes(b"x")
    (db / "InstanceLog.xml").write_text(
        f'<Document><Row Id="953" ReturnId="2002" CreateDT="02-Nov-2026 12:23:37 PM" ErrorDoc="{err}"/></Document>', encoding="utf-8")
    assert mu.match_upload(str(db / "2002"), err).endswith(os.path.join("02-11-26-12-23-37", "F013.xlsx"))
    assert mu.log_upload(str(tmp_path / "DataBase" / "2003"), err) is None                     # another form's folder: not used


def test_a_log_row_of_another_form_is_not_used(tmp_path):
    folder = _repo(tmp_path, "21-11-25-10-02-00", "21-Nov-2025 10:02:00 AM", form="2036")
    other = os.path.join(os.path.dirname(folder), "2041")
    os.makedirs(os.path.join(other, "UploadedFiles", "21-11-25-10-02-00"))
    open(os.path.join(other, "UploadedFiles", "21-11-25-10-02-00", "x.xlsx"), "wb").write(b"x")
    assert mu.log_upload(other, ERR) is None
