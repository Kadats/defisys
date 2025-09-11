from fastapi.testclient import TestClient

from backend.src.api import app


def main():
    client = TestClient(app)
    resp = client.get("/api/v1/run_backtest")
    if resp.status_code == 200:
        print("SUCCESS: /api/v1/run_backtest returned 200")
    else:
        print(f"FAIL: status {resp.status_code}, body: {resp.text}")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
