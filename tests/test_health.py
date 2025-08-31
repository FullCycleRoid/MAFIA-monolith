from fastapi.testclient import TestClient
from app.main import app

def test_health_shape(monkeypatch):
    from app.domains.economy.ton_service import ton_service
    class Dummy:
        async def get_ton_balance(self, addr): return 0.0
    monkeypatch.setattr(ton_service, "get_ton_balance", Dummy().get_ton_balance)
    client = TestClient(app)
    r = client.get('/health')
    assert r.status_code == 200
    body = r.json()
    assert 'status' in body and 'services' in body and 'token_ticker' in body

def test_health_ton_down(monkeypatch):
    from app.domains.economy.ton_service import ton_service
    async def boom(addr): raise RuntimeError('down')
    monkeypatch.setattr(ton_service, "get_ton_balance", boom)
    client = TestClient(app)
    r = client.get('/health')
    assert r.status_code == 200
    assert r.json()['services']['ton_blockchain'] is False
