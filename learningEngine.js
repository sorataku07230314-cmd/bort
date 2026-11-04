/**
 * @file learningEngine.js
 * @description Version 3.0 ⑩ 会場別学習AI・⑪ 自動重み最適化(現在値vs推奨値)・⑫ ハズレ原因分析エンジン
 */

const LearningEngine = {
  /**
   * ⑩ 会場別学習AI: 指定会場の決まり手分布と補正値を取得
   */
  getVenueEmpiricalBias(venueCode) {
    const stats = StorageManager.getVenueStats(venueCode);
    const vMaster = (typeof VENUE_MASTER !== "undefined" && VENUE_MASTER[venueCode]) ? VENUE_MASTER[venueCode] : VENUE_MASTER["04"];

    if (!stats || stats.sampleCount < 1) {
      return {
        ...stats,
        inMod: vMaster.inMod,
        makuriMod: vMaster.makuriMod,
        sashiMod: vMaster.sashiMod,
        waitBonus: 0,
        isCustomLearned: false
      };
    }

    const nigeDiff = stats.nigeRate - 54.0;
    const makuriDiff = stats.makuriRate - 14.5;
    const sashiDiff = stats.sashiRate - 14.5;
    const nukiDiff = stats.nukiRate - 5.0;

    return {
      ...stats,
      inMod: Math.round(vMaster.inMod + nigeDiff * 0.35),
      makuriMod: Math.round(vMaster.makuriMod + makuriDiff * 0.45),
      sashiMod: Math.round(vMaster.sashiMod + sashiDiff * 0.45),
      waitBonus: Math.max(0, Math.min(24, Math.round(nukiDiff * 0.8 + stats.dochuRate * 0.3))),
      isCustomLearned: true
    };
  },

  /**
   * ⑪ 自動重み最適化: w_course, w_exhibit, w_motor, w_slit の「現在値」と「推奨値」を比較算出
   */
  compareCurrentAndRecommendedWeights(currentWeights = { w_course: 100, w_exhibit: 100, w_motor: 100, w_slit: 100 }) {
    const logs = StorageManager.getReviewLogs();
    let rec = { w_course: 110, w_exhibit: 115, w_motor: 110, w_slit: 115 };
    let note = "初期標準推奨バランス（直前展示・スリット気配を微増）";

    if (Array.isArray(logs) && logs.length > 0) {
      const total = logs.length;
      const makuriCnt = logs.filter(x => x.kimarite === "makuri" || x.firstMarkPat === "center_makuri_atk" || x.firstMarkPat === "c2_makuri_atk").length;
      const sashiCnt = logs.filter(x => x.kimarite === "sashi" || x.kimarite === "makurisashi").length;
      const dochuCnt = logs.filter(x => x.dochuType && x.dochuType !== "none").length;
      const stMissCnt = logs.filter(x => (x.missReasons || []).includes("ST予測ミス")).length;
      const exOvertrustCnt = logs.filter(x => (x.missReasons || []).includes("展示過信")).length;

      rec.w_course = Math.min(180, Math.max(70, Math.round((105 + (sashiCnt / total) * 45) / 5) * 5));
      rec.w_exhibit = Math.min(190, Math.max(70, Math.round((110 + (dochuCnt / total) * 50 - (exOvertrustCnt / total) * 35) / 5) * 5));
      rec.w_motor = Math.min(190, Math.max(75, Math.round((105 + (dochuCnt / total) * 55) / 5) * 5));
      rec.w_slit = Math.min(195, Math.max(80, Math.round((105 + (makuriCnt / total) * 65 + (stMissCnt / total) * 30) / 5) * 5));
      note = `蓄積${total}レースのハズレ原因・決まり手傾向から自動算出`;
    }

    return {
      current: currentWeights,
      recommended: rec,
      note,
      sampleCount: Array.isArray(logs) ? logs.length : 0
    };
  },

  /**
   * ⑫ ハズレ原因分析: 事前予想と確定結果を比較し、5大ハズレ要因を自動診断
   * 外れ要因: ST予測ミス / 進入変化 / まくり発生 / 展示過信 / 道中逆転
   */
  analyzeMissReasons(simContext, actualResult) {
    const f1 = Number(actualResult.fin1 || 1);
    const f2 = Number(actualResult.fin2 || 2);
    const f3 = Number(actualResult.fin3 || 3);
    const actualCombo = `${f1}-${f2}-${f3}`;
    const kimarite = actualResult.kimarite || "nige";
    const m1Pat = actualResult.firstMarkPat || "clean_in";
    const dochuType = actualResult.dochuType || "none";
    const entryChanged = Boolean(actualResult.entryChanged);

    const predictedBets = (simContext?.selectedBets || []).map(b => b.combo);
    const isHit = predictedBets.includes(actualCombo);

    if (isHit) {
      return {
        isHit: true,
        actualCombo,
        reasons: ["🎯 的中（展開・スジ完全一致）"],
        detailText: `確定【${actualCombo}】(${kimarite})は事前推奨買い目内で的中しました！1Mの攻防読みと連対スジが正確に機能しています。`,
        weightAdjustHint: { w_course: 0, w_exhibit: 0, w_motor: 0, w_slit: 0 }
      };
    }

    const reasons = [];
    const details = [];
    const hint = { w_course: 0, w_exhibit: 0, w_motor: 0, w_slit: 0 };

    const courseEval = simContext?.courseEval || {};
    const winnerEval = Object.values(courseEval).find(x => x.boatId === f1);

    // 1. 進入変化
    if (entryChanged) {
      reasons.push("進入変化");
      details.push("本番で前付け・進入コース変化が発生し、想定起こし位置とスリット隊形が変化しました。");
      hint.w_course += 10;
    }

    // 2. まくり発生
    if (kimarite === "makuri" || m1Pat === "center_makuri_atk" || m1Pat === "c2_makuri_atk") {
      reasons.push("まくり発生");
      details.push(`${f1}号艇のまくり強襲により内枠が引き波に被弾し、イン本線スジが崩壊しました。`);
      hint.w_slit += 15;
    }

    // 3. ST予測ミス
    if (winnerEval && winnerEval.expectedSt >= 0.15 && (kimarite === "makuri" || kimarite === "makurisashi")) {
      reasons.push("ST予測ミス");
      details.push(`想定ST(.${Math.round(winnerEval.expectedSt * 100).toString().padStart(2, "0")})よりも本番で${f1}号艇が鋭く踏み込み、スリット主導権を奪われました。`);
      hint.w_slit += 10;
    }

    // 4. 展示過信
    const ex1stBoat = Object.values(courseEval).find(x => x.b?.exTimeRank === 1);
    if (ex1stBoat && ![f1, f2, f3].includes(ex1stBoat.boatId)) {
      reasons.push("展示過信");
      details.push(`展示1番時計の${ex1stBoat.boatId}号艇(${ex1stBoat.b.name})が直線時計のみでターンマークで流れ、舟券外に敗退しました。`);
      hint.w_exhibit -= 10;
      hint.w_course += 10;
    }

    // 5. 道中逆転
    if (dochuType !== "none" || kimarite === "nuki") {
      reasons.push("道中逆転");
      details.push("1周1マーク出口の隊形から、2マーク以降の周回足・道中さばき差で着順が入れ替わりました。");
      hint.w_motor += 15;
    }

    if (reasons.length === 0) {
      reasons.push("ST予測ミス");
      details.push("スリット隊形の僅かなズレと1マークの引き波連動により、ヒモ順が入れ替わりました。");
    }

    return {
      isHit: false,
      actualCombo,
      reasons,
      detailText: details.join(" ／ "),
      weightAdjustHint: hint
    };
  }
};
