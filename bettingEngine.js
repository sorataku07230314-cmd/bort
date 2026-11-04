/**
 * @file bettingEngine.js
 * @description Version 3.0 ⑧ AI買い目生成（【本線】【対抗】【穴】）＆ ⑨ 資金管理モード（均等買い・期待値重視・ケリー基準・保守運用・攻撃運用）
 */

const BettingEngine = {
  /**
   * ⑨ 5種の資金管理モードに対応した最適配分計算
   * @param {Array<any>} tickets
   * @param {number} totalBudget 1000 / 3000 / 5000 / 10000 等
   * @param {string} mode 'equal' | 'ev_focus' | 'kelly' | 'conservative' | 'aggressive'
   */
  allocateBudgetByMode(tickets, totalBudget = 5000, mode = "ev_focus") {
    const budget = Math.max(400, Math.floor(Number(totalBudget) / 100) * 100);
    if (!Array.isArray(tickets) || tickets.length === 0) return [];

    const rawWeights = tickets.map((t, idx) => {
      const p = Math.max(0.005, (Number(t.prob) || 4.0) / 100);
      const odds = Math.max(1.2, Number(t.odds) || 10.0);
      const ev = p * odds;
      const b = odds - 1.0;
      const q = 1.0 - p;

      if (mode === "equal") {
        return 1.0;
      } else if (mode === "kelly") {
        // ケリー基準: f* = (b*p - q) / b (ハーフケリー安全制約付き)
        const kellyF = (b * p - q) / b;
        return Math.max(0.08, kellyF > 0 ? kellyF * 12 : p * 1.5);
      } else if (mode === "conservative") {
        // 保守運用: 本線・高確率目に厚く、トリガミ防止下限を考慮
        const catMult = t.category === "本線" ? 2.2 : t.category === "対抗" ? 1.1 : 0.6;
        return Math.max(0.15, p * 15 * catMult);
      } else if (mode === "aggressive") {
        // 攻撃運用: 対抗・穴かつプラスEV目に大きく傾斜
        const catMult = t.category === "穴" ? 2.0 : t.category === "対抗" ? 1.7 : 0.85;
        return Math.max(0.15, Math.pow(Math.max(0.6, ev), 1.6) * catMult);
      } else {
        // 期待値重視 (ev_focus)
        const evBoost = ev >= 1.35 ? 2.1 : ev >= 1.0 ? 1.4 : 0.65;
        return Math.max(0.1, p * 10 * evBoost);
      }
    });

    const sumW = rawWeights.reduce((a, b) => a + b, 0) || 1;
    let remaining = budget;
    const allocated = tickets.map((t, i) => {
      const yen = Math.max(100, Math.floor(((budget * rawWeights[i]) / sumW) / 100) * 100);
      remaining -= yen;
      return { ...t, allocatedYen: yen };
    });

    let cursor = 0;
    while (remaining >= 100 && cursor < 300) {
      allocated[cursor % allocated.length].allocatedYen += 100;
      remaining -= 100;
      cursor++;
    }
    while (remaining < 0 && cursor < 300) {
      const idx = allocated.length - 1 - (cursor % allocated.length);
      if (allocated[idx].allocatedYen > 100) {
        allocated[idx].allocatedYen -= 100;
        remaining += 100;
      }
      cursor++;
    }

    allocated.forEach(item => {
      item.expectedReturnYen = Math.round(item.allocatedYen * (Number(item.odds) || 10));
      item.ev = Math.round(((Number(item.prob) || 4) / 100) * (Number(item.odds) || 10) * 100) / 100;
    });

    return allocated;
  },

  /**
   * ⑧ AI買い目生成: 【本線】【対抗】【穴】を自動構築し、指定した資金管理モードで配分
   */
  generateAIBetsPortfolio(evAnalysis, patternABets = [], patternBBets = [], totalBudget = 5000, mode = "ev_focus", targetCount = 10) {
    const probMap = {};
    (evAnalysis?.all || []).forEach(x => { probMap[x.combo] = x; });

    const normalizeTicket = (it, defaultCat, catClass) => {
      const combo = it.combo || `${it.l1}-${it.l2}-${it.l3}`;
      const m = probMap[combo] || {};
      const prob = Number(m.prob ?? it.prob ?? 4.5);
      const odds = Number(m.odds ?? it.odds ?? 12.0);
      const ev = Math.round(((prob / 100) * odds) * 100) / 100;
      return {
        ...it,
        ...m,
        combo,
        prob,
        odds,
        ev,
        category: defaultCat,
        catClass
      };
    };

    const mainCount = Math.max(2, Math.round(targetCount * 0.4));
    const counterCount = Math.max(2, Math.round(targetCount * 0.35));
    const upsetCount = Math.max(1, targetCount - mainCount - counterCount);

    const used = new Set();
    const list = [];

    // 【本線】
    patternABets.slice(0, mainCount).forEach(it => {
      const t = normalizeTicket(it, "本線", "bg-sky-500/20 text-sky-300 border border-sky-500/40");
      if (!used.has(t.combo)) {
        used.add(t.combo);
        t.rationale = `【本線】イン先マイ王道スジ (確率${t.prob.toFixed(1)}% / EV:${t.ev.toFixed(2)})`;
        list.push(t);
      }
    });

    // 【対抗】
    patternBBets.slice(0, counterCount + 2).forEach(it => {
      if (list.filter(x => x.category === "対抗").length >= counterCount) return;
      const t = normalizeTicket(it, "対抗", "bg-amber-500/20 text-amber-300 border border-amber-500/40");
      if (!used.has(t.combo)) {
        used.add(t.combo);
        t.rationale = `【対抗】非イン逆転・差し/まくりスジ (オッズ${t.odds.toFixed(1)}倍 / EV:${t.ev.toFixed(2)})`;
        list.push(t);
      }
    });

    // 【穴】 (EV上位の高配当目)
    const evPool = [...(evAnalysis?.byEV || []), ...patternBBets];
    evPool.forEach(it => {
      if (list.filter(x => x.category === "穴").length >= upsetCount) return;
      const t = normalizeTicket(it, "穴", "bg-rose-500/20 text-rose-300 border border-rose-500/40");
      if (!used.has(t.combo) && t.odds >= 18.0) {
        used.add(t.combo);
        t.rationale = `【穴】🔥超期待値・展開待ち連動目 (オッズ${t.odds.toFixed(1)}倍 / EV:${t.ev.toFixed(2)})`;
        list.push(t);
      }
    });

    const allocated = this.allocateBudgetByMode(list, totalBudget, mode);
    const totalExpectedVal = allocated.reduce((s, x) => s + (x.prob / 100) * x.expectedReturnYen, 0);

    return {
      totalBudget: Math.max(400, Math.floor(Number(totalBudget) / 100) * 100),
      mode,
      modeInfo: BANKROLL_MODES[mode] || BANKROLL_MODES.ev_focus,
      portfolio: allocated,
      expectedRoiPct: Math.round((totalExpectedVal / Math.max(1, totalBudget)) * 100),
      summary: {
        mainCount: allocated.filter(x => x.category === "本線").length,
        counterCount: allocated.filter(x => x.category === "対抗").length,
        upsetCount: allocated.filter(x => x.category === "穴").length
      }
    };
  }
};
