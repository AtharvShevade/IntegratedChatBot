"""M-13: `append_schedule_entry()` previously did an unlocked, non-atomic
read-modify-write of SchedulerQueue.xml -- two concurrent writers could
interleave and lose/duplicate entries, and a crash mid-write (direct
`open(path, "wb")`) could leave a truncated file. Now guarded by a
`portalocker` exclusive lock on a sibling `.lock` file for the whole
critical section, and persisted via write-to-temp-then-`os.replace()`.
"""
from __future__ import annotations

import os
import threading
import xml.etree.ElementTree as ET

import pytest

from backend.services import scheduler_queue_service as sqs


@pytest.fixture
def queue_path(tmp_path, monkeypatch):
    path = str(tmp_path / "SchedulerQueue.xml")
    monkeypatch.setattr(sqs, "scheduler_queue_xml_path", lambda: path)
    return path


class TestNormalReadWrite:
    def test_first_append_creates_the_file_with_id_1(self, queue_path):
        ok, entry_id = sqs.append_schedule_entry("CIMS_RAQ", "1234", "31-Jan-2026", "2026-01-31T10:00:00", "iris810")
        assert ok is True
        assert entry_id == "1"
        assert os.path.isfile(queue_path)

        tree = ET.parse(queue_path)
        entries = tree.getroot().findall("Schedule")
        assert len(entries) == 1
        assert entries[0].findtext("Id") == "1"
        assert entries[0].findtext("ReportName") == "CIMS_RAQ"
        assert entries[0].findtext("Status") == "PENDING"

    def test_second_append_increments_the_id(self, queue_path):
        sqs.append_schedule_entry("CIMS_RAQ", "1234", "31-Jan-2026", "2026-01-31T10:00:00", "iris810")
        ok, entry_id = sqs.append_schedule_entry("CIMS_FMR", "5678", "28-Feb-2026", "2026-02-28T10:00:00", "iris810")
        assert ok is True
        assert entry_id == "2"

        tree = ET.parse(queue_path)
        entries = tree.getroot().findall("Schedule")
        assert len(entries) == 2

    def test_no_lock_file_left_behind_in_a_way_that_blocks_future_appends(self, queue_path):
        sqs.append_schedule_entry("A", "1", "d", "dt", "u")
        sqs.append_schedule_entry("B", "2", "d", "dt", "u")
        ok, _ = sqs.append_schedule_entry("C", "3", "d", "dt", "u")
        assert ok is True  # the lock must be released after each call, not held forever


class TestConcurrentWriters:
    def test_concurrent_appends_produce_unique_sequential_ids_no_lost_updates(self, queue_path):
        # Pre-create the file once so every thread races on the SAME file
        # from the start (not each separately creating it).
        sqs.append_schedule_entry("seed", "0", "d", "dt", "u")

        n = 20
        results = []
        lock = threading.Lock()

        def worker(i):
            ok, entry_id = sqs.append_schedule_entry(f"report-{i}", str(i), "d", "dt", "u")
            with lock:
                results.append((ok, entry_id))

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(n)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert all(ok for ok, _ in results), f"every concurrent append must succeed: {results}"
        ids = [entry_id for _, entry_id in results]
        assert len(set(ids)) == n, f"every concurrent append must get a UNIQUE id, got duplicates: {ids}"

        # The file itself must end up with exactly 1 (seed) + n entries --
        # no lost updates from an unlocked interleaved read-modify-write.
        tree = ET.parse(queue_path)
        entries = tree.getroot().findall("Schedule")
        assert len(entries) == 1 + n

    def test_concurrent_appends_leave_the_file_well_formed(self, queue_path):
        sqs.append_schedule_entry("seed", "0", "d", "dt", "u")
        threads = [
            threading.Thread(target=sqs.append_schedule_entry, args=(f"r{i}", str(i), "d", "dt", "u"))
            for i in range(15)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        # Must parse without error -- a corrupted/interleaved write would
        # raise ET.ParseError here.
        ET.parse(queue_path)


class TestInterruptedWriteNeverTruncatesTheFile:
    def test_a_failure_during_the_temp_write_leaves_the_original_file_intact(self, queue_path, monkeypatch):
        sqs.append_schedule_entry("original", "1", "d", "dt", "u")
        with open(queue_path, "rb") as f:
            original_bytes = f.read()

        real_write = ET.ElementTree.write

        def _failing_write(self, *args, **kwargs):
            raise OSError("simulated disk failure mid-write")

        monkeypatch.setattr(ET.ElementTree, "write", _failing_write)

        ok, entry_id = sqs.append_schedule_entry("should-not-be-added", "2", "d", "dt", "u")
        assert ok is False
        assert entry_id == ""

        monkeypatch.setattr(ET.ElementTree, "write", real_write)

        # The ORIGINAL file must be byte-for-byte unchanged -- never
        # truncated or partially overwritten by the failed attempt.
        with open(queue_path, "rb") as f:
            assert f.read() == original_bytes

        # And no stray .tmp file should be left sitting next to it.
        assert not os.path.exists(queue_path + ".tmp")

    def test_queue_is_never_left_partially_written(self, queue_path, monkeypatch):
        """Simulates a crash AFTER the temp file is written but BEFORE
        os.replace() runs -- the original must still be the one callers see
        (os.replace is the single atomic commit point)."""
        sqs.append_schedule_entry("original", "1", "d", "dt", "u")
        with open(queue_path, "rb") as f:
            original_bytes = f.read()

        real_replace = os.replace

        def _failing_replace(*args, **kwargs):
            raise OSError("simulated crash before the atomic rename")

        monkeypatch.setattr(sqs.os, "replace", _failing_replace)

        ok, _ = sqs.append_schedule_entry("should-not-be-visible", "2", "d", "dt", "u")
        assert ok is False

        monkeypatch.setattr(sqs.os, "replace", real_replace)

        with open(queue_path, "rb") as f:
            assert f.read() == original_bytes, "original file must survive a failed atomic replace untouched"


class TestExistingFormatPreserved:
    def test_entry_fields_and_order_unchanged(self, queue_path):
        sqs.append_schedule_entry("CIMS_RAQ", "1234", "31-Jan-2026", "2026-01-31T10:00:00", "iris810")
        tree = ET.parse(queue_path)
        entry = tree.getroot().find("Schedule")
        tags = [child.tag for child in entry]
        assert tags == ["Id", "ReportName", "FormId", "ReportingDate", "ScheduleDateTime", "UserId", "Status"]
