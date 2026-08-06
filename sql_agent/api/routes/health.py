from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
def health_check():
    return {"status": "ok"}


@router.get("/test-db")
def test_db():
    """
    Diagnostic endpoint — checks Oracle connectivity, NLS settings,
    and whether the CIMS tables are accessible.
    Call this first when queries return no data.
    """
    from src.executor import get_connection

    try:
        conn = get_connection()
    except Exception as e:
        return {"step": "connect", "ok": False, "error": str(e)}

    results = {}
    cursor = None
    try:
        cursor = conn.cursor()

        # 1 — NLS before fix
        cursor.execute("SELECT VALUE FROM NLS_SESSION_PARAMETERS WHERE PARAMETER = 'NLS_DATE_LANGUAGE'")
        results["nls_date_language_before"] = cursor.fetchone()[0]

        # 2 — Apply NLS fix
        cursor.execute("ALTER SESSION SET NLS_DATE_LANGUAGE = 'AMERICAN'")
        cursor.execute("SELECT VALUE FROM NLS_SESSION_PARAMETERS WHERE PARAMETER = 'NLS_DATE_LANGUAGE'")
        results["nls_date_language_after"] = cursor.fetchone()[0]

        # 3 — Row count on a key CIMS table
        cursor.execute("SELECT COUNT(*) FROM CIMS_RAQ_Q_SEC2_PART_A")
        results["cims_raq_q_sec2_part_a_count"] = cursor.fetchone()[0]

        # 4 — Distinct RDATEs available
        cursor.execute(
            "SELECT RDATE FROM "
            "(SELECT DISTINCT RDATE FROM CIMS_RAQ_Q_SEC2_PART_A ORDER BY RDATE DESC) "
            "WHERE ROWNUM <= 5"
        )
        results["latest_rdates"] = [str(r[0]) for r in cursor.fetchall()]

        # 5 — Distinct CODEs available
        cursor.execute(
            "SELECT CODE FROM "
            "(SELECT DISTINCT CODE FROM CIMS_RAQ_Q_SEC2_PART_A ORDER BY CODE) "
            "WHERE ROWNUM <= 10"
        )
        results["available_codes"] = [str(r[0]) for r in cursor.fetchall()]

        results["ok"] = True
        return results

    except Exception as e:
        results["ok"] = False
        results["error"] = str(e)
        return results
    finally:
        if cursor:
            cursor.close()
        conn.close()
