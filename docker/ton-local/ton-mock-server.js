const express = require('express');
const app = express();
app.use(express.json());

// Store mock data
const wallets = new Map();
const transactions = [];
let blockHeight = 1000;

// Mock endpoints
app.get('/status', (req, res) => {
  res.json({
    ok: true,
    network: 'sandbox',
    blockHeight: blockHeight,
    timestamp: Date.now()
  });
});

app.post('/api/v2/jsonRPC', (req, res) => {
  const { method, params } = req.body;

  switch(method) {
    case 'getAddressInformation':
      const address = params.address;
      if (!wallets.has(address)) {
        wallets.set(address, {
          balance: '1000000000', // 1000 TON
          state: 'active'
        });
      }
      res.json({
        ok: true,
        result: wallets.get(address)
      });
      break;

    case 'sendBoc':
      // Mock transaction
      const txHash = 'mock_' + Math.random().toString(36).substr(2, 9);
      transactions.push({
        hash: txHash,
        timestamp: Date.now(),
        boc: params.boc
      });
      res.json({
        ok: true,
        result: { hash: txHash }
      });
      break;

    default:
      res.json({
        ok: true,
        result: {}
      });
  }
});

// Mock explorer
app.get('/explorer', (req, res) => {
  res.send(`
    <html>
      <head><title>TON Local Explorer</title></head>
      <body>
        <h1>TON Local Explorer (Mock)</h1>
        <p>Block Height: ${blockHeight}</p>
        <p>Wallets: ${wallets.size}</p>
        <p>Transactions: ${transactions.length}</p>
      </body>
    </html>
  `);
});

// Increment block height every 5 seconds
setInterval(() => {
  blockHeight++;
}, 5000);

app.listen(8081, () => {
  console.log('TON mock server running on port 8081');
});

app.listen(8082, () => {
  console.log('TON explorer running on port 8082');
});
