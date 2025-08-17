# DEPLOYMENT GUIDE
"""
# TON JETTON $MAFIA DEPLOYMENT GUIDE

## Prerequisites
1. TON Wallet with TON for gas fees
2. Deployed $MAFIA jetton smart contract
3. PostgreSQL, Redis, RabbitMQ running
4. Python 3.11+

## Step 1: Deploy Jetton Contract
1. Use TON blueprint or tonscan to deploy jetton
2. Set minter address to service wallet
3. Note the jetton master address

## Step 2: Environment Setup
```bash
# Create .env file
cp .env.example .env

# Edit .env with your values:
- MAFIA_JETTON_MASTER_ADDRESS=<your-jetton-address>
- SERVICE_WALLET_MNEMONIC=<24-word-mnemonic>
- TELEGRAM_BOT_TOKEN=<from-botfather>
- JWT_SECRET=<generate-secure-key>
- WALLET_ENCRYPTION_KEY=<32-byte-key>
```

## Step 3: Database Setup
```bash
# Run migrations
alembic upgrade head

# Create initial data
python scripts/init_data.py
```

## Step 4: Docker Deployment
```bash
# Development
docker-compose up -d

# Production
docker-compose -f docker-compose.prod.yml up -d
```

## Step 5: Initialize Jetton
```python
# scripts/init_jetton.py
import asyncio
from app.domains.economy.ton_service import ton_service

async def init():
    await ton_service.initialize()
    # Mint initial supply if needed
    # Set up liquidity pools
    
asyncio.run(init())
```

## Step 6: Telegram Bot Setup
1. Create bot with BotFather
2. Set webhook: https://api.telegram.org/bot<token>/setWebhook?url=<your-domain>/api/auth/telegram
3. Enable inline mode
4. Set up Web App

## Step 7: Monitoring
```bash
# Celery monitoring
celery -A app.core.celery flower

# Logs
docker-compose logs -f backend

# Database monitoring
pgAdmin or DBeaver
```

## Production Checklist
- [ ] SSL certificates configured
- [ ] Environment variables secured
- [ ] Database backups configured
- [ ] Redis persistence enabled
- [ ] Rate limiting configured
- [ ] Monitoring alerts set up
- [ ] TON wallet funded for gas
- [ ] Jetton liquidity provided
- [ ] Security audit completed

## Common Issues & Solutions

### Issue: TON connection fails
Solution: Check TON_NETWORK and ensure mainnet/testnet config matches

### Issue: Transactions fail
Solution: Ensure service wallet has TON for gas fees

### Issue: WebSocket disconnects
Solution: Configure nginx for WebSocket upgrade headers

### Issue: High memory usage
Solution: Adjust Celery worker pool size and Redis maxmemory

## Testing
```bash
# Run tests
pytest tests/ -v

# Test TON integration
python scripts/test_ton.py

# Load testing
locust -f tests/load_test.py