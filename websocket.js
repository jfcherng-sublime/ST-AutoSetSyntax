import { WebSocketServer } from 'ws';
import vscode_languagedetection from '@vscode/vscode-languagedetection';
import vscode_regexp_languagedetection from './vendor/vscode-regexp-languagedetection/dist/index.js';

const { ModelOperations } = vscode_languagedetection;
const model_operations = new ModelOperations();

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

wss.on('connection', function (ws) {
  console.log('Connected.');

  ws.on('message', async function (message) {
    // console.log('='.repeat(80));
    // console.log(`received: ${message}`);
    // console.log('='.repeat(80));

    try {
      const { content, ...others } = JSON.parse(message);
      const predictions = await model_operations.runModel(content);
      ws.send(JSON.stringify({ data: predictions, ...others }));
    } catch (e) {
      ws.send(JSON.stringify({ error: `${e}` }));
    }
  });

  ws.send('Welcome!');
});

console.log('OK');
