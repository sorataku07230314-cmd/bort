/**
 * @file raceAnalyzer.js
 * @description Version 3.0 展開パターン判定・ST優位指数(stAdvantage)・機力指数V2(SS〜D)・荒れ指数・AI予想理由説明モジュール
 */

const RaceAnalyzer = {
  /**
   * ④ ST優位指数 (stAdvantage)
   * 単純な平均ST評価を廃止し、6艇平均STとの差＆内隣コースとのST差から先攻力を算出
   * @param {Record<number, any>} courseEval
   */
  calculateSTAdvantage(courseEval) {
    const arr = Object.values(courseEval);
    const avgST = arr.reduce((acc, c) => acc + c.expectedSt, 0) / (arr.length || 6);

    const details = {};
    let fastestCourse = 1;
    let minSt = 999;

    for (let c = 1; c <= 6; c++) {
      const cur = courseEval[c];
      if (!cur) continue;
      if (cur.expectedSt < minSt) {
        minSt = cur.expectedSt;
        fastestCourse = c;
      }

      // 全体平均との差 (正の値＝全体平均より早い)
      const diffFromAvg = Math.round((avgST - cur.expectedSt) * 1000) / 1000;
      // 内隣とのST差 (正の値＝内隣より踏み込んで覗く)
      const innerDiff = c >= 2 && courseEval[c - 1]
        ? Math.round((courseEval[c - 1].expectedSt - cur.expectedSt) * 1000) / 1000
        : 0;

      // 新指数 stAdvantage: 平均差・内隣差・カド補正を統合
      let stAdvantage = Math.round((diffFromAvg * 220 + (c >= 2 ? innerDiff * 150 : 0) + (cur.isKado && innerDiff >= 0.02 ? 8 : 0)) * 10) / 10;
      cur.stAdvantage = stAdvantage;

      let badge = "並ST";
      if (diffFromAvg >= 0.04 || innerDiff >= 0.04) badge = "🚀 一撃先攻ST";
      else if (diffFromAvg >= 0.02 || innerDiff >= 0.02) badge = "⚡ ST優位";
      else if (diffFromAvg <= -0.03) badge = "⚠️ ST凹み懸念";

      details[c] = {
        courseNo: c,
        boatId: cur.boatId,
        expectedSt: cur.expectedSt,
        diffFromAvg,
        innerStepAdvantage: innerDiff,
        stAdvantage,
        isFastest: false,
        label: badge
      };
    }

    if (details[fastestCourse]) details[fastestCourse].isFastest = true;
    return { avgST: Math.round(avgST * 1000) / 1000, details };
  },

  /**
   * ⑤ 機力指数V2 (SS / S / A+ / A / B / C / D の7段階評価)
   * モーター2連率依存をやめ、展示順位・展示時計・周回展示・伸び・出足・回り足・部品交換・チルトを統合
   */
  calculateMotorIndexV2(b, exRank = 3, avgExTime = 6.75) {
    const motorBi = Number(b.motorBi ?? 35.0);
    const exTime = Number(b.exTime ?? 6.75);
    const oriRank = Number(b.oriTimeRank ?? 0);
    const visSlit = Number(b.visSlit ?? 0); // 伸び評価 (-1 ~ +2)
    const visTurn = Number(b.visTurn ?? 0); // 回り足・周回評価 (-1 ~ +2)
    const tilt = Number(b.tilt ?? -0.5);
    const parts = b.parts || b.partsReplace || "none";

    // モーター2連率の比重を抑え(20%)、実戦気配・展示時計・周回/出足/回り足・伸び(80%)を主軸化
    const biComponent = (motorBi - 35.0) * 0.55;
    const exRankBonus = [11, 7, 2, -2, -6, -9][Math.max(0, Math.min(5, exRank - 1))] ?? 0;
    const exTimeDelta = (avgExTime - exTime) * 145;
    const nobiScore = visSlit * 6.5 + (tilt >= 0.5 ? 4.5 : tilt === 0.0 ? 1.5 : 0);
    const mawariScore = visTurn * 7.5;
    const deashiScore = (oriRank === 1 ? 8.5 : oriRank === 2 ? 5.0 : oriRank === 5 ? -5.0 : 0) + visTurn * 3.0;

    let partsScore = 0;
    if (parts === "ring" || parts === "ring2") partsScore = 4.5;
    else if (parts === "elec" || parts === "electric" || parts === "piston2") partsScore = 3.5;
    else if (parts === "body" || parts === "carrier") partsScore = 3.0;
    else if (parts === "shaft") partsScore = -10.0;

    const rawIndex = 52.0 + biComponent + exRankBonus + exTimeDelta + nobiScore + mawariScore + deashiScore + partsScore;
    const score = Math.max(20.0, Math.min(99.0, Math.round(rawIndex * 10) / 10));

    let grade = "B";
    let color = "text-sky-300 font-bold";
    let bg = "bg-sky-500/20 border-sky-400/50";

    if (score >= 82.0) {
      grade = "SS";
      color = "text-yellow-300 font-black";
      bg = "bg-yellow-500/25 border-yellow-400";
    } else if (score >= 73.0) {
      grade = "S";
      color = "text-amber-300 font-black";
      bg = "bg-amber-500/20 border-amber-400/60";
    } else if (score >= 65.0) {
      grade = "A+";
      color = "text-rose-300 font-black";
      bg = "bg-rose-500/20 border-rose-400/60";
    } else if (score >= 57.0) {
      grade = "A";
      color = "text-emerald-300 font-bold";
      bg = "bg-emerald-500/20 border-emerald-400/50";
    } else if (score >= 48.0) {
      grade = "B";
      color = "text-sky-300 font-bold";
      bg = "bg-sky-500/20 border-sky-400/40";
    } else if (score >= 39.0) {
      grade = "C";
      color = "text-slate-300";
      bg = "bg-slate-800 border-slate-600";
    } else {
      grade = "D";
      color = "text-slate-400";
      bg = "bg-slate-900 border-slate-700";
    }

    return {
      score,
      grade,
      color,
      bg,
      breakdown: {
        biComponent: Math.round(biComponent * 10) / 10,
        exRankBonus,
        nobiScore: Math.round(nobiScore * 10) / 10,
        mawariScore: Math.round(mawariScore * 10) / 10,
        deashiScore: Math.round(deashiScore * 10) / 10,
        partsScore
      }
    };
  },

  // 後方互換エイリアス
  calculateCompositeMotorIndex(b, exRank = 3, avgExTime = 6.75) {
    return this.calculateMotorIndexV2(b, exRank, avgExTime);
  },

  /**
   * ⑥ 荒れ指数 (0〜100: 20 堅い / 45 普通 / 70 中穴 / 90 大荒れ)
   * 考慮要素: F持ち、進入変化、機力接近度、STばらつき、イン信頼度、会場特性
   */
  calculateUpsetIndex(courseEval, venue, windSpeed, wave, deepIn) {
    let score = 26.0;
    const c1 = courseEval[1];
    const c2 = courseEval[2];
    const factors = [];

    // 1. イン信頼度
    const inWin = c1.effCourseWin || 55.0;
    if (inWin < 50.0) {
      const add = Math.round((50.0 - inWin) * 0.9);
      score += add;
      factors.push(`イン信頼度低(${inWin.toFixed(0)}%): +${add}`);
    } else if (inWin >= 68.0) {
      score -= 8;
      factors.push(`イン盤石(${inWin.toFixed(0)}%): -8`);
    }

    // 2. F持ち
    const fTotal = Object.values(courseEval).reduce((s, x) => s + (x.b.fCount || 0), 0);
    if (c1.b.fCount > 0) {
      score += 14 * c1.b.fCount;
      factors.push(`1C F持ち(F${c1.b.fCount}): +${14 * c1.b.fCount}`);
    }
    if (fTotal > c1.b.fCount) {
      const fAdd = (fTotal - c1.b.fCount) * 5;
      score += fAdd;
      factors.push(`他艇F持ち計${fTotal - c1.b.fCount}本: +${fAdd}`);
    }

    // 3. 進入変化・深イン
    const isChangedEntry = Object.values(courseEval).some(x => x.courseNo !== x.boatId);
    if (isChangedEntry) {
      score += 10;
      factors.push("進入コース変化あり: +10");
    }
    if (deepIn === "deep") {
      score += 15;
      factors.push("深イン(100m以内): +15");
    } else if (deepIn === "semi") {
      score += 7;
      factors.push("やや深イン: +7");
    }

    // 4. STばらつき
    const sts = Object.values(courseEval).map(x => x.expectedSt);
    const meanSt = sts.reduce((a, b) => a + b, 0) / sts.length;
    const stdSt = Math.sqrt(sts.reduce((a, b) => a + Math.pow(b - meanSt, 2), 0) / sts.length);
    const stSpreadAdd = Math.round(stdSt * 320);
    if (stSpreadAdd >= 6) {
      score += stSpreadAdd;
      factors.push(`STばらつき大: +${stSpreadAdd}`);
    }

    // 5. 機力接近度 / 外枠機力優位
    const mScores = Object.values(courseEval).map(x => x.motorV2?.score || 55);
    const maxM = Math.max(...mScores), minM = Math.min(...mScores);
    if (maxM - minM <= 10) {
      score += 8;
      factors.push("機力接近(6艇拮抗): +8");
    }
    const outBestM = Math.max(courseEval[4]?.motorV2?.score || 50, courseEval[5]?.motorV2?.score || 50, courseEval[6]?.motorV2?.score || 50);
    const inM = c1.motorV2?.score || 55;
    if (outBestM - inM >= 10) {
      const mAdd = Math.round((outBestM - inM) * 0.7);
      score += mAdd;
      factors.push(`ダッシュ機力優勢: +${mAdd}`);
    }

    // 6. 会場特性 & 気象
    if (["02", "03", "04", "14"].includes(venue.id)) {
      score += 8;
      factors.push(`${venue.name}難水面特性: +8`);
    } else if (["18", "21", "24"].includes(venue.id)) {
      score -= 8;
      factors.push(`${venue.name}イン安定水面: -8`);
    }
    if (windSpeed >= 5) {
      score += windSpeed * 1.8;
      factors.push(`強風${windSpeed}m: +${Math.round(windSpeed * 1.8)}`);
    }

    const finalScore = Math.max(5, Math.min(98, Math.round(score)));
    let levelObj = UPSET_LEVELS[0];
    for (const lvl of UPSET_LEVELS) {
      if (finalScore <= lvl.max) {
        levelObj = lvl;
        break;
      }
    }

    return { score: finalScore, factors, ...levelObj };
  },

  /**
   * ① 展開パターン判定エンジン (計算開始前に7分類)
   * 分類: イン逃げ戦 / 差し戦 / 2コース差し戦 / まくり戦 / まくり差し戦 / 混戦戦 / 大荒れ戦
   */
  classifyRaceType(courseEval, upsetIndex, kadoCourse, windDir, windSpeed) {
    const c1 = courseEval[1], c2 = courseEval[2], c3 = courseEval[3], c4 = courseEval[4], c5 = courseEval[5];
    const kadoObj = courseEval[kadoCourse] || c4;
    const innerOfKado = courseEval[Math.max(1, kadoCourse - 1)] || c3;

    if (upsetIndex.score >= 76) {
      return {
        ...RACE_TYPE_DEFINITIONS.upset,
        rationale: `荒れ指数${upsetIndex.score}(${upsetIndex.label})。${upsetIndex.factors.slice(0, 3).join("・")}が重なり波乱必至。`
      };
    }

    // まくり戦 (4カドまくり警戒 / センターまくり)
    if (
      kadoObj.attackType === "makuri" ||
      c3.attackType === "makuri" ||
      ((kadoObj.stAdvantage || 0) >= 6.5 && kadoObj.expectedSt <= innerOfKado.expectedSt - 0.025 && kadoObj.effMakuriRate >= 15.0)
    ) {
      const atkC = c3.attackType === "makuri" ? c3 : kadoObj;
      return {
        ...RACE_TYPE_DEFINITIONS.makuri,
        label: `🔥 ${atkC.courseNo === kadoCourse ? `${kadoCourse}カド` : `${atkC.courseNo}コース`}まくり警戒`,
        rationale: `${atkC.courseNo}コース${atkC.b.name}(ST優位+${(atkC.stAdvantage || 0).toFixed(1)}・機力${atkC.motorV2?.grade || "A"})がスリット先攻から一撃まくり強襲。`
      };
    }

    // 2コース差し戦
    if (
      c2.attackType === "sashi" &&
      (c2.effSashiRate >= 21.0 || (windDir === "tail" && windSpeed >= 3 && c2.effSashiRate >= 16.0) || c1.effMakuriRate <= 52.0)
    ) {
      return {
        ...RACE_TYPE_DEFINITIONS.c2_sashi,
        rationale: `2コース${c2.b.name}(差し率${c2.effSashiRate.toFixed(1)}%・機力${c2.motorV2?.grade || "A"})のブイ際差し切りが濃厚。`
      };
    }

    // まくり差し戦
    if (
      c3.attackType === "makurisashi" ||
      c4.attackType === "makurisashi" ||
      (c3.effMsRate >= 19.0 && (c3.motorV2?.score || 55) >= 62)
    ) {
      const msObj = c3.effMsRate >= c4.effMsRate ? c3 : c4;
      return {
        ...RACE_TYPE_DEFINITIONS.makurisashi,
        rationale: `${msObj.courseNo}コース${msObj.b.name}(捲差率${msObj.effMsRate.toFixed(1)}%・機力${msObj.motorV2?.grade || "A"})が1Mでインの懐をシャープに割る展開。`
      };
    }

    // 差し戦 (3C/4C二番差し連動など)
    if (
      c3.attackType === "nibanzashi" ||
      c4.attackType === "nibanzashi" ||
      (c2.effSashiRate + c3.effSashiRate + c4.effSashiRate >= 38.0 && c1.effMakuriRate < 64.0)
    ) {
      return {
        ...RACE_TYPE_DEFINITIONS.sashi,
        rationale: `2C一番差しに加え、3C(${c3.b.name})・4C(${c4.b.name})の二番差しが連動する差し優勢戦。`
      };
    }

    // イン逃げ戦
    if (c1.effMakuriRate >= 58.0 && c1.b.fCount === 0 && upsetIndex.score <= 52) {
      return {
        ...RACE_TYPE_DEFINITIONS.in_nige,
        rationale: `1コース${c1.b.name}(逃げ率${c1.effMakuriRate.toFixed(1)}%・機力${c1.motorV2?.grade || "A"})が2C壁(逃がし${c2.b.nigashi.toFixed(0)}%)を盾に先マイ押し切り。`
      };
    }

    return {
      ...RACE_TYPE_DEFINITIONS.chaos,
      rationale: `荒れ指数${upsetIndex.score}(${upsetIndex.label})。インとセンター・差し勢の評価が伯仲する混戦レース。`
    };
  },

  /**
   * ③ AI予想理由説明機能
   * 各艇ごとに「総合評価 +31 (展示順位 +8 / スリット気配 +7 / ST優位 +5 / コース実績 +6 / 水面補正 +5 / マイナス要素: F持ち -3)」を生成
   */
  buildBoatFactorExplanations(courseEval, venue, windDir, windSpeed, kadoCourse, deepIn) {
    const explanations = {};
    for (let c = 1; c <= 6; c++) {
      const obj = courseEval[c];
      if (!obj) continue;
      const b = obj.b;
      const plusItems = [];
      const minusItems = [];

      // 1. 展示順位
      const exBonus = b.exTimeRank === 1 ? 8 : b.exTimeRank === 2 ? 5 : b.exTimeRank === 5 ? -5 : 1;
      if (exBonus > 0) plusItems.push({ label: `展示${b.exTimeRank}位(${b.exTime.toFixed(2)}s)`, val: exBonus });
      else if (exBonus < 0) minusItems.push({ label: "展示時計劣勢", val: exBonus });

      // 2. スリット・ターン気配 & 機力V2
      const visPts = Math.round((b.visSlit || 0) * 3.5 + (b.visTurn || 0) * 4.0 + ((obj.motorV2?.score || 55) - 52) * 0.25);
      if (visPts > 0) plusItems.push({ label: `気配・機力${obj.motorV2?.grade || "A"}`, val: visPts });
      else if (visPts < 0) minusItems.push({ label: `気配重め(${obj.motorV2?.grade || "C"})`, val: visPts });

      // 3. ST優位 (stAdvantage)
      const stPts = Math.round(obj.stAdvantage || 0);
      if (stPts > 0) plusItems.push({ label: "ST優位", val: stPts });
      else if (stPts < 0) minusItems.push({ label: "ST遅れ懸念", val: stPts });

      // 4. コース実績・決まり手
      const baseCourseBench = [55, 16, 13, 11, 7, 4][c - 1] || 10;
      const cPts = Math.round((obj.effCourseWin - baseCourseBench) * 0.45 + (c >= 2 ? (obj.effMakuriRate + obj.effMsRate + obj.effSashiRate) * 0.18 : 6));
      if (cPts > 0) plusItems.push({ label: `${c}コース実績`, val: cPts });
      else if (cPts < 0) minusItems.push({ label: `${c}コース実績不足`, val: cPts });

      // 5. 会場・水面補正
      let vPts = 0;
      if (c === 1) vPts = venue.inMod + (windDir === "tail" ? 2 : windDir === "head" && windSpeed >= 4 ? -3 : 0);
      else if (obj.attackType === "makuri") vPts = venue.makuriMod + (obj.isKado ? 4 : 0);
      else if (obj.attackType === "sashi" || obj.attackType === "nibanzashi" || obj.attackType === "makurisashi") vPts = venue.sashiMod + 2;
      if (vPts > 0) plusItems.push({ label: `${venue.name}補正`, val: vPts });
      else if (vPts < 0) minusItems.push({ label: `${venue.name}水面減点`, val: vPts });

      // 6. マイナス要素（F持ち・深イン・壁崩壊）
      if (b.fCount > 0) {
        minusItems.push({ label: `F持ち(F${b.fCount})`, val: -4 * b.fCount });
      }
      if (c === 1 && deepIn === "deep") {
        minusItems.push({ label: "深イン起こし", val: -6 });
      }
      if (obj.attackType === "hekomi") {
        minusItems.push({ label: "スリット被弾懸念", val: -8 });
      }

      const netScore = plusItems.reduce((s, x) => s + x.val, 0) + minusItems.reduce((s, x) => s + x.val, 0);
      explanations[c] = {
        courseNo: c,
        boatId: obj.boatId,
        name: b.name,
        netScore,
        plusItems,
        minusItems,
        summaryText: `${obj.boatId}号艇(${b.name.split(" ")[0]}) 総合評価 ${netScore >= 0 ? "+" : ""}${netScore}点`
      };
    }
    return explanations;
  }
};
