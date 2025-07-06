// File: castService.js

const Bonjour = require('bonjour');
const fs = require('fs');
const { Client, DefaultMediaReceiver } = require('castv2-client');

const CACHE_PATH = '/data/cast_devices.json';

class CastService {
  constructor() {
    this.devices = new Map();   // uid → { host, port }
    this.clients = new Map();   // uid → castv2-client instance
    this.bonjour = Bonjour();
  }

  async init() {
    // 1. Load persisted device cache
    try {
      const data = fs.readFileSync(CACHE_PATH, 'utf8');
      const obj = JSON.parse(data);
      for (const uid in obj) {
        this.devices.set(uid, obj[uid]);
      }
      console.log('[CastService] Loaded cache with', this.devices.size, 'devices');
    } catch {
      console.log('[CastService] No cache found, starting fresh');
    }

    // 2. Start mDNS discovery via Bonjour
    this.browser = this.bonjour.find({ type: 'googlecast' });
    this.browser.on('up', service => this._addOrUpdate(service));
    this.browser.on('down', service => this._remove(service));
  }

  _persist() {
    const obj = Object.fromEntries(this.devices);
    fs.writeFileSync(CACHE_PATH, JSON.stringify(obj, null, 2));
  }

  _addOrUpdate(service) {
    const uid = service.txt.id;
    const host = service.addresses[0];
    const port = service.port;
    this.devices.set(uid, { host, port });
    this._persist();
    console.log(`[CastService] Discovered ${service.name} (${uid}) at ${host}:${port}`);
  }

  _remove(service) {
    const uid = service.txt.id;
    if (this.devices.delete(uid)) {
      this._persist();
      console.log(`[CastService] Removed ${service.name} (${uid})`);
    }
  }

  listDevices() {
    return Array.from(this.devices.keys());
  }

  async _getClient(uid) {
    if (this.clients.has(uid)) {
      return this.clients.get(uid);
    }
    const info = this.devices.get(uid);
    if (!info) throw new Error(`Unknown device UID: ${uid}`);

    const client = new Client();
    await new Promise((resolve, reject) => {
      client.connect(info.host, info.port, err => {
        if (err) return reject(err);
        client.launch(DefaultMediaReceiver, (err, player) => {
          if (err) return reject(err);
          client.receiver = player;
          resolve();
        });
      });
    });

    // Auto-reconnect on errors
    client.on('error', err => {
      console.warn(`[CastService] Client error for ${uid}:`, err);
      client.close();
      this.clients.delete(uid);
    });

    this.clients.set(uid, client);
    return client;
  }

  async play(uid) {
    const client = await this._getClient(uid);
    client.receiver.play();
    return 'playing';
  }

  async pause(uid) {
    const client = await this._getClient(uid);
    client.receiver.pause();
    return 'paused';
  }

  async stop(uid) {
    const client = await this._getClient(uid);
    client.receiver.stop();
    return 'stopped';
  }

  async seek(uid, seconds) {
    const client = await this._getClient(uid);
    client.receiver.seek(parseFloat(seconds));
    return `seeked to ${seconds}`;
  }

  async setVolume(uid, level) {
    const client = await this._getClient(uid);
    client.setVolume({ level: parseFloat(level) });
    return `volume set to ${level}`;
  }

  async volumeUp(uid, step = 0.05) {
    const client = await this._getClient(uid);
    const status = await new Promise(res => client.getStatus(res));
    const newLevel = Math.min(1, (status.volume.level || 0) + parseFloat(step));
    client.setVolume({ level: newLevel });
    return `volume up to ${newLevel}`;
  }

  async volumeDown(uid, step = 0.05) {
    const client = await this._getClient(uid);
    const status = await new Promise(res => client.getStatus(res));
    const newLevel = Math.max(0, (status.volume.level || 0) - parseFloat(step));
    client.setVolume({ level: newLevel });
    return `volume down to ${newLevel}`;
  }

  async mute(uid) {
    const client = await this._getClient(uid);
    client.setVolume({ muted: true });
    return 'muted';
  }

  async unmute(uid) {
    const client = await this._getClient(uid);
    client.setVolume({ muted: false });
    return 'unmuted';
  }

  async loadMedia(uid, url, contentType, title = '', thumb = '') {
    const client = await this._getClient(uid);
    client.receiver.load(
      { contentId: url, contentType, metadata: { title, images: [{ url: thumb }] } },
      { autoplay: true, currentTime: 0 },
      (err) => { if (err) console.error(err); }
    );
    return `loaded ${url}`;
  }

  async getStatus(uid) {
    const client = await this._getClient(uid);
    return await new Promise(res => client.getStatus(res));
  }

  async launchApp(uid, appId) {
    const client = await this._getClient(uid);
    await new Promise((resolve, reject) => {
      client.launch({ appId }, err => err ? reject(err) : resolve());
    });
    return `launched app ${appId}`;
  }

  async launchYouTube(uid, videoId) {
    // YouTube's default receiver appId
    return this.launchApp(uid, '233637DE');
  }

  async ping(uid) {
    // Test connectivity by retrieving status
    await this.getStatus(uid);
    return 'pong';
  }

  async discoverCapabilities(uid) {
    const status = await this.getStatus(uid);
    return {
      supportedMediaCommands: status.supportedMediaCommands,
      volume: status.volume,
      playerState: status.playerState
    };
  }

  async queueLoad(uid, itemsJson, optionsJson = '{}') {
    const client = await this._getClient(uid);
    const items = JSON.parse(itemsJson);
    const options = JSON.parse(optionsJson);
    return await new Promise((resolve, reject) => {
      client.receiver.queueLoad(items, options, (err, status) => err ? reject(err) : resolve(status));
    });
  }

  async queueInsert(uid, itemsJson, beforeItemId, optionsJson = '{}') {
    const client = await this._getClient(uid);
    const items = JSON.parse(itemsJson);
    const options = Object.assign({}, JSON.parse(optionsJson), { insertBefore: beforeItemId });
    return await new Promise((resolve, reject) => {
      client.receiver.queueInsert(items, options, (err, status) => err ? reject(err) : resolve(status));
    });
  }

  async queueRemove(uid, itemIdsJson, optionsJson = '{}') {
    const client = await this._getClient(uid);
    const itemIds = JSON.parse(itemIdsJson);
    const options = JSON.parse(optionsJson);
    return await new Promise((resolve, reject) => {
      client.receiver.queueRemove(itemIds, options, (err, status) => err ? reject(err) : resolve(status));
    });
  }

  async queueReorder(uid, itemIdsJson, insertBeforeId, optionsJson = '{}') {
    const client = await this._getClient(uid);
    const itemIds = JSON.parse(itemIdsJson);
    const options = Object.assign({}, JSON.parse(optionsJson), { insertBefore: insertBeforeId });
    return await new Promise((resolve, reject) => {
      client.receiver.queueReorder(itemIds, options, (err, status) => err ? reject(err) : resolve(status));
    });
  }

  async queueUpdate(uid, itemsJson, optionsJson = '{}') {
    const client = await this._getClient(uid);
    const items = JSON.parse(itemsJson);
    const options = JSON.parse(optionsJson);
    return await new Promise((resolve, reject) => {
      client.receiver.queueUpdate(items, options, (err, status) => err ? reject(err) : resolve(status));
    });
  }

  async setTracks(uid, trackIdsJson) {
    const client = await this._getClient(uid);
    const trackIds = JSON.parse(trackIdsJson);
    return await new Promise((resolve, reject) => {
      client.receiver.setActiveTrackIds(trackIds, (err, status) => err ? reject(err) : resolve(status));
    });
  }

  async joinGroup(uid, groupId) {
    // Group control not implemented yet
    throw new Error('joinGroup not implemented');
  }

  async leaveGroup(uid) {
    // Group control not implemented yet
    throw new Error('leaveGroup not implemented');
  }

  async disconnect(uid) {
    const client = this.clients.get(uid);
    if (client) {
      client.close();
      this.clients.delete(uid);
      return 'disconnected';
    }
    throw new Error(`No active client for UID ${uid}`);
  }
}

module.exports = new CastService();
