const express = require('express');
const mediasoup = require('mediasoup');
const app = express();
app.use(express.json());

const workers = new Map();
const rooms = new Map();


// Инициализация mediasoup workers
const initWorkers = async () => {
  for (let i = 0; i < 2; i++) {
    const worker = await mediasoup.createWorker();
    workers.set(worker.pid, worker);

    worker.on('died', () => {
      workers.delete(worker.pid);
      setTimeout(() => initWorkers(), 1000);
    });
  }
};


// Создание комнаты
app.post('/room', async (req, res) => {
  const { game_id } = req.body;
  const worker = [...workers.values()][0];

  const router = await worker.createRouter({
    mediaCodecs: [{
      kind: 'audio',
      mimeType: 'audio/opus',
      clockRate: 48000,
      channels: 2
    }]
  });

  rooms.set(game_id, {
    router,
    players: new Map()
  });

  res.json({ room_id: game_id });
});


app.post('/command', (req, res) => {
  const { room_id, player_id, mute } = req.body;
  const room = rooms.get(room_id);
  if (!room) return res.status(404).send('Room not found');

  if (player_id === '*') {
    for (const [, producer] of room.players) {
      mute ? producer.pause() : producer.resume();
    }
    return res.status(200).send('OK');
  }

  const producer = room.players.get(player_id);
  if (producer) {
    mute ? producer.pause() : producer.resume();
    return res.status(200).send('OK');
  }

  return res.status(404).send('Player not found');
});

// Добавляем пакетную версию
app.post('/batch-command', (req, res) => {
  const { room_id, commands } = req.body;
  const room = rooms.get(room_id);
  if (!room) return res.status(404).send('Room not found');

  try {
    for (const cmd of commands) {
      const { player_id, mute } = cmd;
      if (player_id === '*') {
        for (const [, producer] of room.players) {
          mute ? producer.pause() : producer.resume();
        }
      } else {
        const producer = room.players.get(player_id);
        if (producer) {
          mute ? producer.pause() : producer.resume();
        }
      }
    }
    res.status(200).send('OK');
  } catch (e) {
    console.error('Batch command error', e);
    res.status(500).send('Batch command error');
  }
});