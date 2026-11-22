from core.db import bronze_sources, get_conn, latest_raw, save_raw


def test_bronze_roundtrip_and_latest():
    save_raw("s", {"v": 1})
    save_raw("s", {"v": 2})
    save_raw("csv", "a,b\n1,2")  # text payloads (e.g. Traffy CSV) survive as JSON strings
    with get_conn() as conn:
        assert bronze_sources(conn) == ["csv", "s"]
        assert latest_raw(conn, "s")[1] == {"v": 2}
        assert latest_raw(conn, "csv")[1] == "a,b\n1,2"
