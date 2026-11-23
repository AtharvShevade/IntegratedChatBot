"""Read-only lookup of one cell of a data-prep table, for confirming where a failing fact lives.

Connection: the provider named in the fact's XML_Query row (ProviderId) is looked up in the repository's provider files
(XML_Providers.xml, XML_OracleProviderDtl.xml). Those store the Oracle user, password and host AES-GCM encrypted by the
iDEAL application; they are decrypted here with the passphrase from the environment (IDEAL_AES_PASSPHRASE) - it is never
written to a file or a log. When a provider cannot be resolved the cell simply stays unconfirmed: the chatbot's own ORACLE_*
settings are the client's database for the SQL agent and are NEVER used here unless someone sets
EI_DB_USE_CHATBOT_ORACLE=1 on purpose (default: off).

Safety: every connection is made read-only (SET TRANSACTION READ ONLY) and only SELECTs one column from one table; the table and column names must pass db_return.is_identifier and come
from the repository's XML_Query file; every value is a bound parameter; one row fetched at most; a short timeout.
Credentials are never logged or returned.
"""
from __future__ import annotations

import base64
import logging
import os
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass

from .db_return import DbCell, is_identifier

logger = logging.getLogger(__name__)

_CALL_TIMEOUT_MS = 8000


@dataclass
class Reading:
    state: str                  # "value" | "no-row" | "several-rows" | "unavailable"
    value: object = None
    rows: int = 0


def decrypt(token: str, passphrase: str) -> str:
    """AES-GCM as the iDEAL application writes it: base64( iv[12] | ciphertext | tag[16] ), iv = passphrase[:12],
    key = passphrase[12:44]."""
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    if len(passphrase) != 44:
        raise ValueError("passphrase must be 44 characters")
    raw = base64.b64decode(token)
    key = passphrase[12:44].encode("utf-8")
    return AESGCM(key).decrypt(raw[:12], raw[12:], None).decode("utf-8")


def parse_oracle_connection(text: str) -> dict | None:
    """{"user","password","dsn"} from an Oracle connection string such as
    'User Id=x;Password=y;Data Source=(DESCRIPTION=(ADDRESS=...)(CONNECT_DATA=(SID=xe)))', or None."""
    def part(names: str):
        m = re.search(r"(?:^|;)\s*(?:%s)\s*=\s*" % names, text, flags=re.IGNORECASE)
        if not m:
            return None
        i, depth, out = m.end(), 0, []
        while i < len(text):
            ch = text[i]
            if ch == "(":
                depth += 1
            elif ch == ")":
                depth -= 1
            elif ch == ";" and depth <= 0:
                break
            out.append(ch)
            i += 1
        return "".join(out).strip() or None
    user, pwd, dsn = part("user id|uid|user"), part("password|pwd"), part("data source|datasource")
    return {"user": user, "password": pwd, "dsn": dsn} if user and pwd and dsn else None


def provider_connection(db_folder: str, provider_id: str) -> dict | None:
    """{"user","password","dsn"} for a provider id, or None when it cannot be resolved. Never raises.

    The ProviderId of the fact's XML_Query row is looked up in XML_Providers.xml (next to the return folders). A row whose
    ProviderType is Oracle holds the database's connection string, AES-GCM encrypted by the iDEAL application; it is decrypted
    here with IDEAL_AES_PASSPHRASE (environment only) and never written or logged. A provider id whose rows disagree on the type
    (the same id listed for an Oracle and an Excel source) is not resolved: nothing is guessed.

    EI_DB_PROVIDER_<id>="user|password|dsn" (process environment only) names the database for one provider id outright, for a
    machine whose provider file does not carry it.
    """
    override = os.environ.get(f"EI_DB_PROVIDER_{provider_id}", "") if provider_id else ""
    if override.count("|") == 2:
        user, pwd, dsn = override.split("|")
        if user and pwd and dsn:
            return {"user": user, "password": pwd, "dsn": dsn}
    passphrase = os.environ.get("IDEAL_AES_PASSPHRASE", "")
    path = os.path.join(os.path.dirname(db_folder.rstrip("\\/")), "XML_Providers.xml") if db_folder else ""
    if not passphrase or not provider_id or not os.path.isfile(path):
        return None
    try:
        rows = [el for el in ET.parse(path).getroot().iter("Row") if el.get("ProviderId") == provider_id]
        if len({(el.get("ProviderType") or "").lower() for el in rows}) != 1 or (rows[0].get("ProviderType") or "").lower() != "oracle":
            return None
        token = (rows[0].findtext("ConnectionString") or "").strip()
        return parse_oracle_connection(decrypt(token, passphrase)) if token else None
    except Exception as exc:  # noqa: BLE001 - an unreadable provider is just "not resolved"; never expose why in detail
        logger.info("[db_source] provider %s not resolved (%s)", provider_id, type(exc).__name__)
    return None


def environment_connection() -> dict | None:
    """The chatbot's own Oracle settings - the client's database. Off unless EI_DB_USE_CHATBOT_ORACLE=1."""
    if os.environ.get("EI_DB_USE_CHATBOT_ORACLE") != "1":
        return None
    user, pwd = os.environ.get("ORACLE_USER"), os.environ.get("ORACLE_PASSWORD")
    dsn = os.environ.get("ORACLE_DSN")
    if not dsn and os.environ.get("ORACLE_HOST"):
        dsn = f"{os.environ['ORACLE_HOST']}:{os.environ.get('ORACLE_PORT', '1521')}/{os.environ.get('ORACLE_SERVICE', 'XE')}"
    return {"user": user, "password": pwd, "dsn": dsn} if user and pwd and dsn else None


class DbReader:
    """One connection per reader, opened lazily. Use as a context manager."""

    def __init__(self, db_folder: str = "", provider_id: str = ""):
        self._folder, self._provider = db_folder, provider_id
        self._conns: dict = {}
        self._failed: set = set()
        self._rows: dict = {}          # one lookup per (database, table, key, date, columns): many facts share a row
        self.source = ""          # "provider" | "environment" | ""

    def _connect(self, provider_id: str = ""):
        provider_id = provider_id or self._provider
        if provider_id in self._conns:
            return self._conns[provider_id]
        if provider_id in self._failed:
            return None
        self._failed.add(provider_id)
        try:
            import oracledb
        except ImportError:
            return None
        for label, cfg in (("provider", provider_connection(self._folder, provider_id)),
                           ("environment", environment_connection())):
            if not cfg:
                continue
            try:
                conn = oracledb.connect(user=cfg["user"], password=cfg["password"], dsn=cfg["dsn"])
                conn.call_timeout = _CALL_TIMEOUT_MS
                conn.cursor().execute("SET TRANSACTION READ ONLY")      # nothing this connection runs can change data
                self._conns[provider_id], self.source = conn, label
                self._failed.discard(provider_id)
                return conn
            except Exception as exc:  # noqa: BLE001
                logger.info("[db_source] %s connection failed (%s)", label, type(exc).__name__)
        return None

    def __del__(self):
        try:
            self.close()
        except Exception:  # noqa: BLE001
            pass

    def close(self):
        for conn in list(self._conns.values()):
            try:
                conn.close()
            except Exception:  # noqa: BLE001
                pass
        self._conns.clear()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()

    def read_row(self, cell: DbCell, columns: list[str], reporting_date: str) -> tuple[str, dict]:
        """("ok", {column: value}) for several columns of the ONE row the cell's key names; ("no-row", {}) when the database has no
        such row; ("several", {}) for more than one; ("unavailable", {}) for no connection or a failed lookup. Same safety rules as
        read(): identifier-checked names, bound values, read-only."""
        names = [cell.table, cell.date_column, *columns, *cell.key.keys()]
        if not reporting_date or not columns or not all(is_identifier(n) for n in names):
            return "unavailable", {}
        ck = (cell.provider_id or self._provider, cell.table, tuple(cell.key.items()), reporting_date, tuple(columns))
        if ck in self._rows:
            return self._rows[ck]
        conn = self._connect(cell.provider_id)
        if conn is None:
            return "unavailable", {}
        where = " AND ".join(f"TRIM({c}) = :k{i}" for i, c in enumerate(cell.key))
        sql = (f"SELECT {', '.join(columns)} FROM {cell.table} "
               f"WHERE TRUNC({cell.date_column}) = TO_DATE(:d, 'YYYY-MM-DD') AND {where} FETCH FIRST 2 ROWS ONLY")
        binds = {"d": reporting_date, **{f"k{i}": str(v).strip() for i, v in enumerate(cell.key.values())}}
        try:
            cur = conn.cursor()
            cur.execute(sql, binds)
            rows = cur.fetchall()
        except Exception as exc:  # noqa: BLE001
            logger.info("[db_source] row lookup failed (%s)", type(exc).__name__)
            return "unavailable", {}
        result = ("no-row", {}) if not rows else ("several", {}) if len(rows) > 1 else ("ok", dict(zip(columns, rows[0])))
        self._rows[ck] = result
        return result

    def read(self, cell: DbCell, reporting_date: str) -> Reading:
        names = [cell.table, cell.column, cell.date_column, *cell.key.keys()]
        if not reporting_date or not all(is_identifier(n) for n in names):
            return Reading("unavailable")
        conn = self._connect(cell.provider_id)
        if conn is None:
            return Reading("unavailable")
        where = " AND ".join(f"TRIM({c}) = :k{i}" for i, c in enumerate(cell.key))
        sql = (f"SELECT {cell.column} FROM {cell.table} "
               f"WHERE TRUNC({cell.date_column}) = TO_DATE(:d, 'YYYY-MM-DD') AND {where} FETCH FIRST 2 ROWS ONLY")
        binds = {"d": reporting_date, **{f"k{i}": str(v).strip() for i, v in enumerate(cell.key.values())}}
        try:
            cur = conn.cursor()
            cur.execute(sql, binds)
            rows = cur.fetchall()
        except Exception as exc:  # noqa: BLE001 - e.g. the date column is text; try the text form once
            try:
                sql2 = sql.replace(f"TRUNC({cell.date_column}) = TO_DATE(:d, 'YYYY-MM-DD')",
                                   f"TO_DATE({cell.date_column}, 'DD-MON-RR') = TO_DATE(:d, 'YYYY-MM-DD')")
                cur = conn.cursor()
                cur.execute(sql2, binds)
                rows = cur.fetchall()
            except Exception:  # noqa: BLE001
                logger.info("[db_source] lookup failed (%s)", type(exc).__name__)
                return Reading("unavailable")
        if not rows:
            return Reading("no-row")
        if len(rows) > 1:
            return Reading("several-rows", rows[0][0], len(rows))
        return Reading("value", rows[0][0], 1)
