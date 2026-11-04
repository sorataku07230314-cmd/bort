/**
 * @file oddsEngine.js
 * @description Version 3.0 ⑦ EV(期待値)エンジン (EV = 的中確率 × オッズ)
 * 出力: 🔥 超期待値 / ✅ 買い候補 / ⚠ 過剰人気 ランキング
 */

function estimateRealisticTrifectaOdds(combo, rankIdx, b1, b2, b3) {
  if (b1 === 1) {
    if ((b2 === 2 && b3 === 3) || (b2 === 2 && b3 === 4) || (b2 === 3 && b3 === 2) || (b2 === 4 && b3 === 2)) {
      return Math.round((6.8 + rankIdx * 1.4) * 10) / 10;
    }
    if (b2 <= 4) return Math.round((12.0 + rankIdx * 2.1) * 10) / 10;
    return Math.round((21.0 + rankIdx * 3.5) * 10) / 10;
  } else if (b1 === 2 && b2 === 1) {
    return Math.round((15.5 + rankIdx * 2.6) * 10) / 10;
  } else if (b1 === 3 && b2 === 1) {
    return Math.round((18.0 + rankIdx * 3.0) * 10) / 10;
  } else if (b1 === 4 && (b2 === 5 || b2 === 1)) {
    return Math.round((21.5 + rankIdx * 3.6) * 10) / 10;
  }
  return Math.round(Math.min(420.0, 38.0 + rankIdx * 5.8) * 10) / 10;
}

const OddsEngine = {
  /**
   * @param {Array<any>} trifectaList
   * @param {Record<string, number>} liveOddsMap
   */
  calculateExpectedValues(trifectaList, liveOddsMap = {}) {
    const isLiveOdds = Object.keys(liveOddsMap).length >= 6;

    const listWithEV = trifectaList.map((item, idx) => {
      const combo = item.combo;
      let odds = Number(liveOddsMap[combo]);
      if (!Number.isFinite(odds) || odds <= 0) {
        odds = estimateRealisticTrifectaOdds(combo, idx, item.b1, item.b2, item.b3);
      }

      // EV = 的中確率(0~1) × オッズ
      const ev = Math.round((item.probRaw * odds) * 100) / 100;

      let evCategory = EV_LEVELS.overpopular;
      if (ev >= EV_LEVELS.super.min) evCategory = EV_LEVELS.super;
      else if (ev >= EV_LEVELS.candidate.min) evCategory = EV_LEVELS.candidate;

      return {
        ...item,
        odds,
        ev,
        evCategory
      };
    });

    const byEV = [...listWithEV].sort((a, b) => b.ev - a.ev);
    const byProb = [...listWithEV].sort((a, b) => b.probRaw - a.probRaw);

    return {
      all: listWithEV,
      byEV,
      byProb,
      isLiveOdds
    };
  }
};
