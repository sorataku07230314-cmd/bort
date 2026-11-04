/**
 * @file simulation.js
 * @description Version 3.0 本格Monte Carloシミュレーションエンジン (1000 / 5000 / 10000 / 50000回試行対応)
 * 出力: 【1着率】【2連対率】【3連対率】【3連単出現率 TOP20】
 */

function randnBoxMuller() {
  let u = 0, v = 0;
  while (u === 0) u = Math.random();
  while (v === 0) v = Math.random();
  return Math.sqrt(-2.0 * Math.log(u)) * Math.cos(2.0 * Math.PI * v);
}

const SimulationEngine = {
  /**
   * @param {Record<number, any>} courseEval
   * @param {Object} options
   */
  runMonteCarlo(courseEval, options = {}) {
    const runs = Number(options.runs) || 5000;
    const inEscapePct = Math.max(20, Math.min(90, Number(options.inEscapePct || 56))) / 100;
    const windDir = options.windDir || "cross";
    const windSpeed = Number(options.windSpeed) || 2;
    const deepIn = options.deepIn || "normal";

    const winCounts = { 1: 0, 2: 0, 3: 0, 4: 0, 5: 0, 6: 0 };
    const top2Counts = { 1: 0, 2: 0, 3: 0, 4: 0, 5: 0, 6: 0 };
    const top3Counts = { 1: 0, 2: 0, 3: 0, 4: 0, 5: 0, 6: 0 };
    const trifectaCounts = {};

    const c1 = courseEval[1], c2 = courseEval[2], c3 = courseEval[3], c4 = courseEval[4], c5 = courseEval[5], c6 = courseEval[6];

    // 展開別スジ理論ウェイト (二番差し連動含む)
    const attackerWeights = [
      {
        type: "c2_sashi",
        name: "2コース差し",
        winner: c2.boatId,
        weight: Math.max(3.0, (c2.effSashiRate || 16.0) * 1.5 + (windDir === "tail" ? windSpeed * 1.8 : 0) + ((c2.stAdvantage || 0) * 0.5)),
        lines: [
          { b2: c1.boatId, b3s: [c3.boatId, c4.boatId, c5.boatId, c6.boatId], w: 54 },
          { b2: c3.boatId, b3s: [c1.boatId, c4.boatId, c5.boatId], w: 23 },
          { b2: c4.boatId, b3s: [c1.boatId, c3.boatId, c5.boatId], w: 15 },
          { b2: c5.boatId, b3s: [c1.boatId, c3.boatId, c4.boatId], w: 8 }
        ]
      },
      {
        type: "c2_makuri",
        name: "2コースジカまくり",
        winner: c2.boatId,
        weight: Math.max(1.0, (c2.effMakuriRate || 5.0) * 1.1 + (c2.attackType === "makuri" ? 18 : 0)),
        lines: [
          { b2: c3.boatId, b3s: [c4.boatId, c5.boatId, c6.boatId], w: 44 },
          { b2: c4.boatId, b3s: [c3.boatId, c5.boatId, c6.boatId], w: 32 },
          { b2: c1.boatId, b3s: [c3.boatId, c4.boatId, c5.boatId], w: 16 }
        ]
      },
      {
        type: "c3_makurisashi",
        name: "3コースまくり差し/二番差し",
        winner: c3.boatId,
        weight: Math.max(3.0, (c3.effMsRate || 14.0) * 1.5 + (c3.effSashiRate || 5.0) * 0.8 + (["makurisashi", "nibanzashi", "sashi"].includes(c3.attackType) ? 14 : 0)),
        lines: [
          { b2: c1.boatId, b3s: [c4.boatId, c5.boatId, c2.boatId, c6.boatId], w: 50 },
          { b2: c4.boatId, b3s: [c1.boatId, c5.boatId, c2.boatId], w: 28 },
          { b2: c5.boatId, b3s: [c1.boatId, c4.boatId, c6.boatId], w: 15 }
        ]
      },
      {
        type: "c3_makuri",
        name: "3コースまくり",
        winner: c3.boatId,
        weight: Math.max(2.0, (c3.effMakuriRate || 10.0) * 1.35 + (c3.attackType === "makuri" ? 20 : 0)),
        lines: [
          { b2: c4.boatId, b3s: [c5.boatId, c6.boatId, c1.boatId, c2.boatId], w: 48 },
          { b2: c1.boatId, b3s: [c4.boatId, c5.boatId, c6.boatId], w: 28 },
          { b2: c5.boatId, b3s: [c4.boatId, c6.boatId, c1.boatId], w: 18 }
        ]
      },
      {
        type: "c4_makuri",
        name: "4カドまくり",
        winner: c4.boatId,
        weight: Math.max(4.0, (c4.effMakuriRate || 15.0) * 1.8 + (c4.attackType === "makuri" ? 24 : 0) + Math.max(0, (c4.stAdvantage || 0) * 1.4)),
        lines: [
          { b2: c5.boatId, b3s: [c1.boatId, c6.boatId, c2.boatId, c3.boatId], w: 48 },
          { b2: c1.boatId, b3s: [c5.boatId, c6.boatId, c2.boatId], w: 30 },
          { b2: c6.boatId, b3s: [c5.boatId, c1.boatId, c2.boatId], w: 22 }
        ]
      },
      {
        type: "c4_sashi_ms",
        name: "4コースまくり差し・二番差し",
        winner: c4.boatId,
        weight: Math.max(2.5, (c4.effMsRate || 11.0) * 1.35 + (c4.effSashiRate || 7.0) * 1.1 + (["makurisashi", "nibanzashi", "sashi"].includes(c4.attackType) ? 16 : 0)),
        lines: [
          { b2: c1.boatId, b3s: [c2.boatId, c5.boatId, c3.boatId, c6.boatId], w: 48 },
          { b2: c5.boatId, b3s: [c1.boatId, c6.boatId, c2.boatId], w: 30 },
          { b2: c2.boatId, b3s: [c1.boatId, c5.boatId, c3.boatId], w: 16 }
        ]
      },
      {
        type: "c5_attack",
        name: "5コースまくり差し",
        winner: c5.boatId,
        weight: Math.max(1.5, (c5.effMsRate || 8.0) * 1.4 + (c5.attackType === "makurisashi" ? 18 : 0)),
        lines: [
          { b2: c1.boatId, b3s: [c4.boatId, c6.boatId, c2.boatId], w: 45 },
          { b2: c4.boatId, b3s: [c1.boatId, c6.boatId, c2.boatId], w: 35 },
          { b2: c6.boatId, b3s: [c1.boatId, c4.boatId, c2.boatId], w: 16 }
        ]
      },
      {
        type: "out_wait",
        name: "展開待ち最内差し",
        winner: c6.boatId,
        weight: Math.max(1.0, (c6.effWaitRate || 38.0) * 0.08 + (c6.attackType === "tenkaimachi" ? 6 : 0)),
        lines: [
          { b2: c1.boatId, b3s: [c4.boatId, c5.boatId, c2.boatId], w: 42 },
          { b2: c4.boatId, b3s: [c1.boatId, c5.boatId, c2.boatId], w: 32 },
          { b2: c5.boatId, b3s: [c1.boatId, c4.boatId, c2.boatId], w: 26 }
        ]
      }
    ];
    const totalNonInWeight = attackerWeights.reduce((a, b) => a + b.weight, 0);

    for (let r = 0; r < runs; r++) {
      const st1 = c1.expectedSt + randnBoxMuller() * 0.026;
      const st4 = c4.expectedSt + randnBoxMuller() * 0.030;

      let pIn = inEscapePct;
      if (st1 <= 0.10) pIn += 0.09;
      else if (st1 >= 0.19) pIn -= 0.17;
      if (st4 <= st1 - 0.04) pIn -= 0.14;
      if (c2.attackType === "makuri") pIn -= 0.18;
      if (deepIn === "deep") pIn -= 0.11;

      pIn = Math.max(0.14, Math.min(0.91, pIn));
      let b1, b2, b3;

      if (Math.random() < pIn) {
        b1 = c1.boatId;
        const cand2 = [
          { id: c2.boatId, w: 38 + (c2.placeScore || 70) * 0.32 + (c2.attackType === "sashi" ? 10 : 0) },
          { id: c3.boatId, w: 34 + (c3.placeScore || 70) * 0.34 + (c3.attackType === "nibanzashi" ? 9 : 0) },
          { id: c4.boatId, w: 29 + (c4.placeScore || 70) * 0.30 + (c4.attackType === "nibanzashi" ? 9 : 0) },
          { id: c5.boatId, w: 15 + (c5.placeScore || 60) * 0.20 },
          { id: c6.boatId, w: 10 + (c6.placeScore || 50) * 0.15 }
        ];
        const sum2 = cand2.reduce((s, x) => s + x.w, 0);
        let rnd2 = Math.random() * sum2;
        for (const it of cand2) {
          if (rnd2 <= it.w) { b2 = it.id; break; }
          rnd2 -= it.w;
        }
        if (!b2) b2 = cand2[0].id;

        const cand3 = [c2, c3, c4, c5, c6]
          .filter(x => x.boatId !== b2)
          .map(x => ({
            id: x.boatId,
            w: 18 + (x.effWaitRate || 45) * 0.35 + ((x.motorV2?.score || 55) - 50) * 0.5 + (x.attackType === "nibanzashi" ? 8 : 0)
          }));
        const sum3 = cand3.reduce((s, x) => s + x.w, 0);
        let rnd3 = Math.random() * sum3;
        for (const it of cand3) {
          if (rnd3 <= it.w) { b3 = it.id; break; }
          rnd3 -= it.w;
        }
        if (!b3) b3 = cand3[0].id;
      } else {
        let rndT = Math.random() * totalNonInWeight;
        let tac = attackerWeights[0];
        for (const t of attackerWeights) {
          if (rndT <= t.weight) { tac = t; break; }
          rndT -= t.weight;
        }
        b1 = tac.winner;
        const sumL = tac.lines.reduce((s, x) => s + x.w, 0);
        let rndL = Math.random() * sumL;
        let line = tac.lines[0];
        for (const l of tac.lines) {
          if (rndL <= l.w) { line = l; break; }
          rndL -= l.w;
        }
        b2 = line.b2;
        const valid3 = line.b3s.filter(id => id !== b1 && id !== b2);
        b3 = valid3[Math.floor(Math.random() * valid3.length)] || c1.boatId;
      }

      // 道中機力V2差による2・3着入れ替わり
      if (Math.random() < 0.15) {
        const o2 = Object.values(courseEval).find(x => x.boatId === b2);
        const o3 = Object.values(courseEval).find(x => x.boatId === b3);
        if ((o3?.motorV2?.score || 50) >= (o2?.motorV2?.score || 50) + 7) {
          const tmp = b2; b2 = b3; b3 = tmp;
        }
      }

      winCounts[b1]++;
      top2Counts[b1]++; top2Counts[b2]++;
      top3Counts[b1]++; top3Counts[b2]++; top3Counts[b3]++;

      const combo = `${b1}-${b2}-${b3}`;
      trifectaCounts[combo] = (trifectaCounts[combo] || 0) + 1;
    }

    const winRates = {}, top2Rates = {}, top3Rates = {};
    for (let b = 1; b <= 6; b++) {
      winRates[b] = Math.round((winCounts[b] / runs) * 1000) / 10;
      top2Rates[b] = Math.round((top2Counts[b] / runs) * 1000) / 10;
      top3Rates[b] = Math.round((top3Counts[b] / runs) * 1000) / 10;
    }

    const trifectaList = Object.keys(trifectaCounts).map(combo => {
      const cnt = trifectaCounts[combo];
      const prob = Math.round((cnt / runs) * 1000) / 10;
      const [b1, b2, b3] = combo.split("-").map(Number);
      return { combo, b1, b2, b3, count: cnt, prob, probRaw: cnt / runs };
    }).sort((a, b) => b.probRaw - a.probRaw);

    return {
      runs,
      winRates,
      top2Rates,
      top3Rates,
      trifectaList,
      top20Trifectas: trifectaList.slice(0, 20),
      trifectaMap: trifectaCounts
    };
  }
};
