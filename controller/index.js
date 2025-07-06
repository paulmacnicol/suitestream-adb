// File: index.js

require('dotenv').config();

const express = require('express');
const axios = require('axios');
const { io } = require('socket.io-client');
const { spawn } = require('child_process');
const fs = require('fs');

const castService = require('./castService');

const app = express();

const PORT = parseInt(process.env.PORT || '8080', 10);
const CENTRAL_URL = process.env.CENTRAL_URL || 'https://soundscreen.soundcheckvn.com';
const CONNECT_URL = process.env.CONNECT_URL || `${CENTRAL_URL}/connect`;
const POLL_INTERVAL_MS = parseInt(process.env.POLL_INTERVAL_MS || '3000', 10);
const JWT_PATH = '/data/device_jwt.txt';

let verificationCode = null;
let token = null;
let socket = null;

app.get('/', (req, res) => {
  if (!verificationCode && !token) {
    return res.send('<h1>Connecting… please wait</h1>');
  }
  if (verificationCode && !token) {
    return res.send(`<h1>Code: ${verificationCode}</h1>`);
  }
  return res.send('<h1>Device Connected ✅</h1>');
});

app.listen(PORT, async () => {
  // Initialize Cast discovery & clients
  await castService.init();
  console.log('[index] CastService initialized');
  console.log(`🌐 HTTP listening on ${PORT}`);

  // Attempt to reuse existing JWT
  if (fs.existsSync(JWT_PATH)) {
    try {
      const saved = fs.readFileSync(JWT_PATH, 'utf8').trim();
      if (saved) {
        token = saved;
        console.log('🔄 Using saved JWT');
        startSocketIO();
        return;
      }
    } catch (e) {
      console.error('❌ JWT read error:', e.message);
    }
  }

  // Otherwise, fetch onboarding code and register
  while (!await fetchVerificationCode()) {
    await new Promise(r => setTimeout(r, 2000));
  }
  registerDevice();
});

// Fetch the one-time onboarding code
async function fetchVerificationCode() {
  try {
    console.log(`🔍 Attempting GET ${CONNECT_URL}`);
    const resp = await axios.get(CONNECT_URL, {
      timeout: 5000,
      headers: { 'User-Agent': 'Mozilla/5.0' }
    });
    const html = resp.data;
    console.log('📄 Fetched HTML snippet:', html.slice(0, 200).replace(/\n/g, '\\n'));
    const match = html.match(/<div\s+id="verification-code">\s*([\dA-Za-z]+)\s*<\/div>/i);
    if (match && match[1]) {
      verificationCode = match[1].trim();
      console.log('🔑 Extracted verification code:', verificationCode);
      return true;
    }
    console.warn('⚠️ No verification-code found; retrying');
    return false;
  } catch (err) {
    console.error('❌ Error fetching verification code:', err.message);
    return false;
  }
}

// Register the device with the central server
async function registerDevice() {
  if (!verificationCode) {
    setTimeout(registerDevice, 2000);
    return;
  }
  const statusUrl = `${CENTRAL_URL}/api/devices/device-status`;
  try {
    console.log('📨 Registering device with code', verificationCode);
    await axios.post(statusUrl, { code: verificationCode }, {
      headers: { 'Content-Type': 'application/json' }
    });
  } catch (err) {
    console.error('❌ Error on registerDevice:', err.message);
  }
  pollForJwt();
}

// Poll until a JWT is issued for this device
async function pollForJwt() {
  const statusUrl = `${CENTRAL_URL}/api/devices/device-status`;
  try {
    console.log('🔄 Polling for JWT');
    const { data } = await axios.post(statusUrl, { code: verificationCode }, {
      headers: { 'Content-Type': 'application/json' }
    });
    console.log('🔄 Poll response:', data);
    if (data.status === 'registered' && data.jwt) {
      token = data.jwt;
      try {
        fs.writeFileSync(JWT_PATH, token, 'utf8');
        console.log('💾 JWT saved');
      } catch (e) {
        console.error('❌ JWT write error:', e.message);
      }
      startSocketIO();
    } else {
      setTimeout(pollForJwt, POLL_INTERVAL_MS);
    }
  } catch (err) {
    console.error('❌ Error polling for JWT:', err.message);
    setTimeout(pollForJwt, POLL_INTERVAL_MS);
  }
}

// Establish and handle the Socket.IO connection
function startSocketIO() {
  if (!token) {
    console.warn('⚠️ No token; aborting startSocketIO');
    return;
  }
  console.log('🌐 Connecting Socket.IO to', CENTRAL_URL);
  socket = io(CENTRAL_URL, {
    path: '/controllers/socket.io',
    transports: ['websocket'],
    auth: { deviceJwt: token },
    reconnection: true
  });

  socket.on('connect', () => console.log('🟢 Connected as', socket.id));
  socket.on('disconnect', () => console.warn('🔴 Disconnected; retrying'));
  socket.on('connect_error', async (err) => {
    console.error('🔴 Connect error:', err.message);
    if (/invalid token|Authentication error/i.test(err.message)) {
      console.warn('🗑️ Clearing token & restarting onboarding');
      try { fs.unlinkSync(JWT_PATH); } catch {}
      token = null;
      verificationCode = null;
      while (!await fetchVerificationCode()) {
        await new Promise(r => setTimeout(r, 2000));
      }
      registerDevice();
    }
  });

  socket.on('device-command', async (msg, ack) => {
    console.log('⮞ Received device-command:', msg);
    const { type, targetDeviceId, args = [] } = msg;

    if (type.startsWith('cast:')) {
      // Handle Cast commands via our CastService
      const action = type.split(':')[1];
      try {
        const result = await castService[action](targetDeviceId, ...args);
        return ack({ status: 'ok', result });
      } catch (err) {
        return ack({ status: 'error', error: err.message });
      }
    }

    // Fallback: spawn a local process for other commands
    try {
      const output = await runLocal(type, args);
      return ack({ status: 'ok', stdout: output });
    } catch (err) {
      return ack({ status: 'error', error: err.message });
    }
  });
}

// Helper: spawn a local binary with arguments
function runLocal(binary, args) {
  return new Promise((resolve, reject) => {
    console.log(`💻 Spawning ${binary} ${args.join(' ')}`);
    const proc = spawn(binary, args);
    let out = '', err = '';
    proc.stdout.on('data', b => out += b.toString());
    proc.stderr.on('data', b => err += b.toString());
    proc.on('exit', code =>
      code === 0 ? resolve(out) : reject(new Error(err.trim() || `Exit ${code}`))
    );
  });
}
