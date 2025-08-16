# tests/test_auth.py
async def test_telegram_auth(client):
    # Подготовка валидных данных Telegram
    auth_data = {...}

    # Вызов эндпоинта
    response = await client.post("/api/auth/telegram", json=auth_data)

    # Проверки
    assert response.status_code == 200
    assert "access_token" in response.json()