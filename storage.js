/**
 * @file storage.js
 * @description localStorageアクセス共通化 ＆ 24会場別学習DB永続化マネージャー (Version 3.0)
 */

const StorageManager = {
  /**
   * @template T
   * @param {string} key
   * @param {T} defaultValue
   * @returns {T}
   */
  get(key, defaultValue = null) {
    try {
      const raw = localStorage.getItem(key);
      if (raw === null || raw === undefined) return defaultValue;
      return JSON.parse(raw);
    } catch (e) {
      console.warn(`[StorageManager] Read error on ${key}:`, e);
      return defaultValue;
    }
  },

  /**
   * @param {string} key
   * @param {any} value
   * @returns {boolean}
   */
  set(key, value) {
    try {
      localStorage.setItem(key, JSON.stringify(value));
      return true;
    } catch (e) {
      console.warn(`[StorageManager] Write error on ${key}:`, e);
      return false;
    }
  },

  remove(key) {
    try {
      localStorage.removeItem(key);
      return true;
    } catch (e) {
      return false;
    }
  },

  /**
   * ⑩ 会場別学習AI: 24場(桐生〜大村、三国含む)それぞれの決まり手率を取得
   * @param {string} venueCode "01"〜"24"
   */
  getVenueStats(venueCode) {
    const vInfo = (typeof VENUE_MASTER !== "undefined" && VENUE_MASTER[venueCode]) ? VENUE_MASTER[venueCode] : { name: "平和島", inNige: 52.0, sashiMod: 2, makuriMod: 2 };
    const key = `${STORAGE_KEYS.VENUE_LEARNING_PREFIX}${venueCode}`;
    const defaultNige = vInfo.inNige || 54.0;
    const defaultSashi = Math.max(8.0, 14.5 + (vInfo.sashiMod || 0) * 0.8);
    const defaultMakuri = Math.max(8.0, 14.5 + (vInfo.makuriMod || 0) * 0.8);
    const defaultMs = Math.max(6.0, 11.5 + (vInfo.sashiMod || 0) * 0.4);
    const defaultNuki = Math.max(3.0, Math.round((100 - defaultNige - defaultSashi - defaultMakuri - defaultMs) * 10) / 10);

    const fallback = {
      venueCode,
      venueName: vInfo.name,
      sampleCount: 0,
      nigeCount: 0,
      sashiCount: 0,
      makuriCount: 0,
      makurisashiCount: 0,
      nukiCount: 0,
      dochuCount: 0,
      nigeRate: Math.round(defaultNige * 10) / 10,
      sashiRate: Math.round(defaultSashi * 10) / 10,
      makuriRate: Math.round(defaultMakuri * 10) / 10,
      makurisashiRate: Math.round(defaultMs * 10) / 10,
      nukiRate: Math.max(2.0, defaultNuki),
      dochuRate: 14.0,
      updatedAt: null
    };
    return this.get(key, fallback);
  },

  saveVenueStats(venueCode, stats) {
    const key = `${STORAGE_KEYS.VENUE_LEARNING_PREFIX}${venueCode}`;
    stats.updatedAt = new Date().toISOString();
    return this.set(key, stats);
  },

  recordVenueRaceResult(venueCode, kimarite, dochuType = "none") {
    const stats = this.getVenueStats(venueCode);
    stats.sampleCount += 1;
    if (kimarite === "nige") stats.nigeCount += 1;
    else if (kimarite === "sashi") stats.sashiCount += 1;
    else if (kimarite === "makuri") stats.makuriCount += 1;
    else if (kimarite === "makurisashi") stats.makurisashiCount += 1;
    else stats.nukiCount += 1;

    if (dochuType && dochuType !== "none") stats.dochuCount += 1;

    const n = stats.sampleCount;
    stats.nigeRate = Math.round((stats.nigeCount / n) * 1000) / 10;
    stats.sashiRate = Math.round((stats.sashiCount / n) * 1000) / 10;
    stats.makuriRate = Math.round((stats.makuriCount / n) * 1000) / 10;
    stats.makurisashiRate = Math.round((stats.makurisashiCount / n) * 1000) / 10;
    stats.nukiRate = Math.round((stats.nukiCount / n) * 1000) / 10;
    stats.dochuRate = Math.round((stats.dochuCount / n) * 1000) / 10;

    this.saveVenueStats(venueCode, stats);
    return stats;
  },

  getAllVenuesSummary() {
    const list = [];
    if (typeof VENUE_MASTER === "undefined") return list;
    Object.keys(VENUE_MASTER).sort().forEach(code => {
      list.push(this.getVenueStats(code));
    });
    return list;
  },

  getReviewLogs() {
    return this.get(STORAGE_KEYS.REVIEW_LOGS, []);
  },

  saveReviewLogs(logs) {
    return this.set(STORAGE_KEYS.REVIEW_LOGS, logs);
  },

  getLearnedParams() {
    return this.get(STORAGE_KEYS.LEARNED_PARAMS, null);
  },

  saveLearnedParams(params) {
    return this.set(STORAGE_KEYS.LEARNED_PARAMS, params);
  },

  getUIMode() {
    return this.get(STORAGE_KEYS.UI_MODE, "pro");
  },

  setUIMode(mode) {
    return this.set(STORAGE_KEYS.UI_MODE, mode);
  }
};
