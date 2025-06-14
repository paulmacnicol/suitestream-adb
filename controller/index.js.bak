// /home/gc/suitestream-adb/controller/index.js

const express = require('express');
const axios = require('axios');
const { io } = require('socket.io-client');
const { spawn } = require('child_process');

const app = express();

// Read from env (default to 8080)
const PORT = parseInt(process.env.PORT || '8080', 10);

// CENTRAL_URL should be your base server endpoint (no trailing "/connect")
const CENTRAL_URL = process.env.CENTRAL_URL || 'http://soundscreen.soundcheckvn.com';

// CONNECT_URL can be explicitly set to the full "/connect" path.
// If not provided, we append "/connect" to CENTRAL_URL.
const CONNECT_URL = process.env.CONNECT_URL || `${CENTRAL_URL}/connect`;

const POLL_INTERVAL_MS = parseInt(process.env.POLL_INTERVAL_MS || '3000', 10);

let verificationCode = null;
let token = null;
let socket = null;

/**
 * 1) Fetch the HTML at CONNECT_URL, log the URL being requested,
 *    then parse out <div id="verification-code">XXXXXX</div> via RegExp.
 */
async function fetchVerificationCode() {
  try {
    console.log(`🔍 Attempting to GET: ${CONNECT_URL}`);
    const resp = await axios.get(CONNECT_URL, {
      timeout: 5000,
      headers: {
        // Spoof a browser UA so the server returns full HTML
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/88.0 Safari/537.36'
      }
    });

    const html = resp.data;
    console.log('📄 Fetched HTML (first 500 chars):\n', html.slice(0, 500).replace(/\n/g, '\\n'));

    // Look for <div id="verification-code">  204997  </div>
    const match = html.match(/<div\s+id="verification-code">\s*([\dA-Za-z]+)\s*<\/div>/i);
    if (match && match[1]) {
      verificationCode = match[1].trim();
      console.log('🔑 Extracted verification code:', verificationCode);
      return true;
    } else {
      console.warn('⚠️  RegExp did not match. No verification-code element found. Will retry.');
      return false;
    }
  } catch (err) {
    console.error('❌ Error fetching HTML from CONNECT_URL:', err.message);
    return false;
  }
}

/**
 * 2) Once we have a verificationCode, POST it plus browserDetails to
 *    `${CENTRAL_URL}/api/devices/device-status`, then start polling.
 */
async function registerDevice() {
  if (!verificationCode) {
    console.log('❗ registerDevice called but no verificationCode yet. Retrying...');
    return setTimeout(registerDevice, 2000);
  }

  const browserDetails = {
    userAgent: 'NodeJS/axios',    // not a real browser
    screenWidth: null,
    screenHeight: null,
    language: null,
    timeZone: Intl.DateTimeFormat().resolvedOptions().timeZone || null,
  };

  const statusUrl = `${CENTRAL_URL}/api/devices/device-status`;
  try {
    console.log('📨 Sending initial device-status POST to', statusUrl, 'payload:', {
      code: verificationCode,
      browserDetails,
    });
    const resp = await axios.post(
      statusUrl,
      { code: verificationCode, browserDetails },
      { headers: { 'Content-Type': 'application/json' } }
    );
    console.log('📨 Initial device-status POST response:', resp.data);
  } catch (e) {
    console.error('❌ Error sending initial device-status POST:', e.message);
  }

  // Begin polling for JWT
  pollForJwt();
}

/**
 * 3) Poll `${CENTRAL_URL}/api/devices/device-status` with { code } until
 *    we see { status: 'registered', jwt } in the response.
 */
async function pollForJwt() {
  const statusUrl = `${CENTRAL_URL}/api/devices/device-status`;
  try {
    console.log(`🔄 Polling for JWT by POSTing to ${statusUrl} with code=${verificationCode}`);
    const resp = await axios.post(
      statusUrl,
      { code: verificationCode },
      { headers: { 'Content-Type': 'application/json' } }
    );
    const data = resp.data;
    console.log('🔄 Polling response:', data);

    if (data.status === 'registered' && data.jwt) {
      token = data.jwt;
      console.log('✅ Received JWT:', token);
      startSocketIO();
    } else {
      setTimeout(pollForJwt, POLL_INTERVAL_MS);
    }
  } catch (err) {
    console.error('❌ Error polling for JWT:', err.message);
    setTimeout(pollForJwt, POLL_INTERVAL_MS);
  }
}

/**
 * 4) Once the JWT is obtained, open a Socket.IO connection and handle incoming commands.
 */
function startSocketIO() {
  if (!token) {
    console.warn('⚠️  startSocketIO called without token. Aborting.');
    return;
  }
  console.log('🌐 Connecting to Socket.IO server at', CENTRAL_URL);
  socket = io(CENTRAL_URL, {
    path: '/socket.io',
    auth: { deviceJwt: token },
  });

  socket.on('connect', () => {
    console.log('🟢 Socket.io connected as', socket.id);
  });

  socket.on('disconnect', () => {
    console.warn('🔴 Socket disconnected; attempting reconnect...');
  });

  socket.on('device-command', async (msg) => {
    // msg example: { id, type: 'adb' | 'cec-client', args: [ … ] }
    console.log('⮞ Received device-command:', msg);

    try {
      const output = await runLocal(msg.type, msg.args);
      console.log(`✅ Command succeeded. stdout:\n${output}`);
      socket.emit('device-reply', { id: msg.id, status: 'ok' });
    } catch (err) {
      console.error(`❌ Command failed (type=${msg.type}):`, err.message);
      socket.emit('device-reply', {
        id: msg.id,
        status: 'error',
        error: err.message,
      });
    }
  });
}

/**
 * Helper: spawn a local binary (adb or cec-client). Returns a Promise that resolves on exit code 0.
 */
function runLocal(binary, args) {
  return new Promise((resolve, reject) => {
    console.log(`💻 Spawning local process: ${binary} ${args.join(' ')}`);
    const proc = spawn(binary, args);
    let out = '';
    let err = '';
    proc.stdout.on('data', (b) => {
      out += b.toString();
    });
    proc.stderr.on('data', (b) => {
      err += b.toString();
    });
    proc.on('exit', (code) => {
      if (code === 0) {
        resolve(out);
      } else {
        reject(new Error(err.trim() || `Exit code ${code}`));
      }
    });
  });
}

/**
 * 5) “GET /” endpoint for status checks:
 *    • No code & no token → “Connecting… please wait”
 *    • code but no token → show the numeric code
 *    • token present → “Device Connected”
 */
app.get('/', (req, res) => {
  if (!verificationCode && !token) {
    return res.send(`
      <html>
        <head><meta charset="utf-8"><title>Suitestream Onboard</title></head>
        <body style="background:#222;color:#fff;font-family:sans-serif;text-align:center;padding-top:20vh;">
          <h1>Connecting… please wait</h1>
        </body>
      </html>
    `);
  }
  if (verificationCode && !token) {
    return res.send(`
      <html>
        <head><meta charset="utf-8"><title>Enter Code</title></head>
        <body style="background:#222;color:#fff;font-family:sans-serif;text-align:center;padding-top:15vh;">
          <h1>Your Verification Code:</h1>
          <div style="font-size:4rem;letter-spacing:0.2rem;margin:1rem 0;color:#0f0;">${verificationCode}</div>
          <p>Open your Control Panel<br>and enter this code to register.</p>
        </body>
      </html>
    `);
  }
  return res.send(`
    <html>
      <head><meta charset="utf-8"><title>Connected</title></head>
      <body style="background:#000;color:#0f0;font-family:sans-serif;text-align:center;padding-top:20vh;">
        <h1>Device Connected ✅</h1>
        <p>Waiting for server commands…</p>
      </body>
    </html>
  `);
});

/**
 * 6) Start the HTTP server, then attempt to fetch the verification code.
 *    Once obtained, call registerDevice() which does the initial POST and starts pollForJwt().
 */
app.listen(PORT, () => {
  console.log(`🌐 Onboard HTTP listening on port ${PORT}`);
  (async () => {
    let gotCode = false;
    while (!gotCode) {
      gotCode = await fetchVerificationCode();
      if (!gotCode) {
        console.log('⏳ Waiting 2 seconds before retrying fetchVerificationCode...');
        await new Promise((r) => setTimeout(r, 2000));
      }
    }
    registerDevice();
  })();
});
