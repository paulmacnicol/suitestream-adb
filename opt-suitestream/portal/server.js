// /opt/suitestream/portal/server.js

const express     = require('express');
const { execSync }= require('child_process');
const app         = express();
app.use(express.urlencoded({ extended: true }));

// Redirect captive-portal probes and wrong hosts to suitestream.local
app.use((req, res, next) => {
  const host = (req.headers.host || '').split(':')[0];
  const path = req.url.split('?')[0];
  if (path === '/hotspot-detect.html' || path === '/generate_204') {
    return res.redirect('http://suitestream.local/');
  }
  if (host && host !== 'suitestream.local') {
    return res.redirect(`http://suitestream.local${req.url}`);
  }
  next();
});

// Landing page form
app.get('/', (req, res) => {
  let ssids = [];
  try {
    const data = execSync('cat /opt/suitestream/portal/ssids.txt').toString();
    ssids = data.split('\n').filter(s => s.trim());
  } catch {}
  res.send(`
    <!doctype html>
    <html>
    <head>
      <style>
        body { font-family: sans-serif; background:#f4f4f4; height:100vh;
               display:flex; align-items:center; justify-content:center; }
        .card { background:white; padding:2rem; border-radius:8px;
                box-shadow:0 2px 8px rgba(0,0,0,0.2); width:300px; }
        h1 { margin-top:0; text-align:center; font-size:1.5rem; }
        select, input { width:100%; padding:0.5rem; margin:0.5rem 0;
                        border:1px solid #ccc; border-radius:4px; }
        button { width:100%; padding:0.75rem; margin-top:1rem;
                 background:#007acc; color:white; border:none;
                 border-radius:4px; cursor:pointer; }
        button:hover { background:#005fa3; }
      </style>
    </head>
    <body>
      <div class="card">
        <h1>Suitestream Setup</h1>
        <form method="POST" action="/connect">
          <label for="ssid">SSID</label>
          <select id="ssid" name="ssid" required>
            <option value="" disabled selected>Select network…</option>
            ${ssids.map(s => `<option>${s}</option>`).join('')}
          </select>
          <label for="password">Password</label>
          <input id="password" name="password" type="password" required/>
          <button type="submit">Connect & Reboot</button>
        </form>
      </div>
    </body>
    </html>
  `);
});

// Handle form submit: tear down AP, re-enable NM, join Wi-Fi, then reboot
app.post('/connect', (req, res) => {
  const { ssid, password } = req.body;
  try {
    // 1) Stop AP services
    execSync('systemctl stop hostapd dnsmasq avahi-daemon');

    // 2) Unblock radio and clear wlan0
    execSync('rfkill unblock wifi');
    execSync('ip link set wlan0 down');
    execSync('ip addr flush dev wlan0');
    execSync('ip link set wlan0 up');

    // 3) Restore wpa_supplicant for STA mode
    execSync('systemctl unmask wpa_supplicant.service wpa_supplicant@wlan0.service dbus-fi.w1.wpa_supplicant1.service');
    execSync('systemctl daemon-reload');
    execSync('systemctl enable wpa_supplicant.service');
    execSync('systemctl start wpa_supplicant.service');

    // 4) Hand back to NetworkManager
    execSync('nmcli device set wlan0 managed yes');
    execSync('nmcli networking on');
    execSync('nmcli radio wifi on');

    // 5) Wait & rescan for SSID
    execSync('sleep 3');
    execSync('nmcli device wifi rescan');
    execSync('sleep 2');

    // 6) Connect & save profile
    execSync(`nmcli device wifi connect "${ssid}" password "${password}"`);

    // 7) Feedback + delayed reboot
    res.send(`
      <!doctype html>
      <html><body style="font-family:sans-serif;text-align:center;padding:2rem;">
        <h1>Connected to ${ssid}!</h1>
        <p>Rebooting in 5 seconds…</p>
      </body></html>
    `);
    setTimeout(() => execSync('reboot'), 5000);

  } catch (err) {
    res.send(`
      <!doctype html>
      <html><body style="font-family:sans-serif;padding:2rem;">
        <h1>Connection Failed</h1>
        <pre>${err.message}</pre>
        <p><a href="/">Try again</a></p>
      </body></html>
    `);
  }
});

// Start server
app.listen(80, () => console.log('Captive portal listening on port 80'));
