import { run_vscode_regexp_languagedetection } from './helpers.js';
import { WebSocketServer } from 'ws';

const host = process.env.HOST ?? 'localhost';
const port = parseInt(process.env.PORT ?? 15151, 10);

const wss = new WebSocketServer({
  host,
  port,
  perMessageDeflate: {
    zlibDeflateOptions: {
      // See zlib defaults.
      chunkSize: 1024,
      memLevel: 7,
      level: 3,
    },
    zlibInflateOptions: {
      chunkSize: 10 * 1024,
    },
    // Other options settable:
    clientNoContextTakeover: true, // Defaults to negotiated value.
    serverNoContextTakeover: true, // Defaults to negotiated value.
    serverMaxWindowBits: 10, // Defaults to negotiated value.
    // Below options specified as default values.
    concurrencyLimit: 10, // Limits zlib concurrency for perf.
    threshold: 1024, // Size (in bytes) below which messages should not be compressed.
  },
});

wss.on('connection', (ws) => {
  console.log('Connected.');

  ws.on('message', async (message) => {
    // console.log('='.repeat(80));
    // console.log(`received: ${message}`);
    // console.log('='.repeat(80));

    try {
      const { content, ...others } = JSON.parse(message);

      const bias = others['bias'] ?? {}; // how do we construct this?
      const predictions = [...(await run_vscode_regexp_languagedetection(content, bias))];

      ws.send(JSON.stringify({ data: predictions, ...others }));
    } catch (e) {
      ws.send(JSON.stringify({ error: `${e}` }));
    }
  });

  ws.send('Welcome!');
});

console.log('OK');
