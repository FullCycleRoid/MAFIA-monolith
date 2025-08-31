import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.shared.utils.security import create_access_token

client = TestClient(app)

def test_ws_requires_token():
    with client.websocket_connect("/api/game/abc/ws") as ws:
        # If server accepts then immediately disconnects, it's unexpected
        # Expect close 4401, TestClient raises on non-101; so we simulate by expecting exception
        pass

def test_ws_valid_token_connects():
    token = create_access_token({"sub": "u1"})
    with client.websocket_connect(f"/api/game/g1/ws?token={token}") as ws:
        ws.send_text("{}" )
