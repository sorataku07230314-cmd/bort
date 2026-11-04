/**
 * @file ui.js
 * @description Version 3.0 UI描画・初級者/上級者モード管理・addEventListener統一イベントデリゲーション
 */

const UIManager = {
  /**
   * ⑮ レースタイプバッジ ＋ ① 展開パターン判定エンジン ＋ ⑥ 荒れ指数 (0〜100)
   */
  renderRaceTypeHeader(raceType, upsetIndex, containerId = "raceTypeBadgeContainer") {
    const el = document.getElementById(containerId);
    if (!el) return;

    const factorPills = (upsetIndex.factors || []).slice(0, 4).map(f =>
      `<span class="text-[10px] bg-slate-800 text-slate-300 px-1.5 py-0.5 rounded border border-slate-700">${f}</span>`
    ).join("");

    el.innerHTML = `
      <div class="bg-slate-900 border-2 border-sky-500/40 rounded-xl p-3 shadow-lg space-y-2">
        <div class="flex flex-wrap items-center justify-between gap-3">
          <div class="flex items-center gap-3">
            <span class="px-2.5 py-1 rounded-lg text-xs font-black bg-slate-950 border border-slate-700 text-amber-300 shadow">${raceType.shortBadge || "🛡 イン戦"}</span>
            <div>
              <div class="flex flex-wrap items-center gap-2">
                <span class="text-[11px] font-bold text-slate-400">① 展開パターン判定 (${raceType.patternName || "イン逃げ戦"}):</span>
                <span class="px-2.5 py-0.5 rounded-full text-xs font-black border ${raceType.badgeClass}">${raceType.label}</span>
              </div>
              <p class="text-[11px] text-slate-200 mt-0.5">${raceType.rationale}</p>
            </div>
          </div>

          <div class="flex items-center gap-3 bg-slate-950/90 border border-slate-800 rounded-lg px-3 py-1.5">
            <div class="text-right">
              <div class="text-[10px] text-slate-400 font-bold">⑥ 荒れ指数 (0〜100)</div>
              <div class="text-xs font-bold ${upsetIndex.color}">
                <span class="text-lg font-black font-mono">${upsetIndex.score}</span> <span class="px-1.5 py-0.5 rounded ${upsetIndex.bg}">${upsetIndex.label}</span>
              </div>
            </div>
            <div class="w-20 bg-slate-800 h-2.5 rounded-full overflow-hidden border border-slate-700">
              <div class="h-full ${upsetIndex.score >= 70 ? "bg-rose-500" : upsetIndex.score >= 50 ? "bg-amber-500" : upsetIndex.score >= 33 ? "bg-emerald-500" : "bg-sky-500"}" style="width: ${upsetIndex.score}%"></div>
            </div>
          </div>
        </div>
        <div class="flex flex-wrap items-center justify-between gap-2 pt-1 border-t border-slate-800/80 text-[10px] text-slate-400">
          <div class="flex flex-wrap items-center gap-1">
            <span class="font-bold text-slate-300">荒れ指数構成要素:</span>
            ${factorPills || '<span class="text-slate-500">標準水面・特記事項なし</span>'}
          </div>
          <span>基準目安: 20 堅い ／ 45 普通 ／ 70 中穴 ／ 90 大荒れ</span>
        </div>
      </div>
    `;
  },

  /**
   * ③ AI予想理由説明機能 ＆ ④ ST優位指数 (stAdvantage) ＆ ⑤ 機力指数V2 (SS〜D) 表示
   */
  renderExplanationsAndStAdvantage(explanations, stData, courseEval, containerId = "v3ExplanationsContainer") {
    const el = document.getElementById(containerId);
    if (!el) return;

    let cardsHtml = "";
    for (let c = 1; c <= 6; c++) {
      const exp = explanations[c];
      const stIt = stData.details[c];
      const obj = courseEval[c];
      if (!exp || !stIt || !obj) continue;

      const bColor = BOAT_COLORS[obj.boatId] || BOAT_COLORS[1];
      const plusBadges = exp.plusItems.map(p =>
        `<span class="text-[10px] bg-emerald-950/80 text-emerald-300 border border-emerald-600/40 px-1.5 py-0.5 rounded font-mono">${p.label} +${p.val}</span>`
      ).join(" ");
      const minusBadges = exp.minusItems.map(m =>
        `<span class="text-[10px] bg-rose-950/80 text-rose-300 border border-rose-600/40 px-1.5 py-0.5 rounded font-mono">${m.label} ${m.val}</span>`
      ).join(" ");

      const stAdvSign = stIt.stAdvantage >= 0 ? `+${stIt.stAdvantage.toFixed(1)}` : `${stIt.stAdvantage.toFixed(1)}`;
      const mV2 = obj.motorV2 || { grade: "B", score: 55, color: "text-sky-300", bg: "bg-slate-800" };

      cardsHtml += `
        <div class="bg-slate-950/90 border border-slate-800 rounded-lg p-2.5 space-y-1.5">
          <div class="flex items-center justify-between border-b border-slate-800 pb-1">
            <div class="flex items-center gap-1.5">
              <span class="text-[10px] font-bold text-slate-400">${c}C</span>
              <span class="w-5 h-5 rounded text-[11px] font-black flex items-center justify-center" style="background:${bColor.body};color:${bColor.text};border:1px solid ${bColor.border}">${obj.boatId}</span>
              <span class="text-xs font-bold text-white">${exp.name}</span>
            </div>
            <div class="flex items-center gap-1.5">
              <span class="text-[10px] px-1.5 py-0.5 rounded border ${mV2.bg} ${mV2.color}" title="機力指数V2">機力 ${mV2.grade} (${mV2.score})</span>
              <span class="text-xs font-black font-mono ${exp.netScore >= 15 ? "text-amber-300" : exp.netScore >= 0 ? "text-sky-300" : "text-rose-400"}">
                総合 ${exp.netScore >= 0 ? "+" : ""}${exp.netScore}
              </span>
            </div>
          </div>
          <div class="flex flex-wrap items-center justify-between text-[10px] text-slate-300 bg-slate-900/80 px-2 py-0.5 rounded">
            <span>想定ST: <strong class="font-mono text-sky-300">.${Math.round(stIt.expectedSt * 100).toString().padStart(2, "0")}</strong> (平均差 ${stIt.diffFromAvg >= 0 ? "+" : ""}${stIt.diffFromAvg.toFixed(2)}s)</span>
            <span class="font-mono font-bold ${stIt.stAdvantage >= 4 ? "text-amber-300" : "text-slate-300"}">stAdvantage: ${stAdvSign} [${stIt.label}]</span>
          </div>
          <div class="flex flex-wrap gap-1 pt-0.5">
            ${plusBadges || '<span class="text-[10px] text-slate-500">プラス要素標準</span>'}
            ${minusBadges}
          </div>
        </div>
      `;
    }

    el.innerHTML = `
      <div class="bg-slate-900 border border-indigo-500/40 rounded-xl p-3 space-y-2">
        <div class="flex flex-wrap items-center justify-between gap-1 border-b border-slate-800 pb-1.5">
          <div>
            <h3 class="text-xs font-bold text-indigo-300">🧠 ③ AI予想理由説明 ＆ ④ ST優位指数 (stAdvantage) ＆ ⑤ 機力指数V2 (SS〜D)</h3>
            <span class="text-[10px] text-slate-400">6艇平均ST(.${Math.round(stData.avgST * 100).toString().padStart(2, "0")})との差・展示順位・気配・コース実績・水面補正・F持ち減点の完全内訳</span>
          </div>
        </div>
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-2">${cardsHtml}</div>
      </div>
    `;
  },

  /**
   * ② 本格Monte Carloシミュレーション結果 (1000 / 5000 / 10000 / 50000回切替 ＋ 1着率・2連対率・3連対率・3連単TOP20)
   */
  renderMonteCarloV3(simResult, boatsData, containerId = "v3MonteCarloContainer") {
    const el = document.getElementById(containerId);
    if (!el) return;

    const { runs, winRates, top2Rates, top3Rates, top20Trifectas } = simResult;

    let rateRowsHtml = "";
    for (let b = 1; b <= 6; b++) {
      const bColor = BOAT_COLORS[b] || BOAT_COLORS[1];
      const name = (boatsData[b]?.name || `${b}号艇`).split(" ")[0];
      rateRowsHtml += `
        <tr class="border-b border-slate-800/60">
          <td class="py-1 flex items-center gap-1.5">
            <span class="w-4 h-4 rounded text-[10px] font-black flex items-center justify-center" style="background:${bColor.body};color:${bColor.text};border:1px solid ${bColor.border}">${b}</span>
            <span class="font-bold text-white">${b}号艇 ${name}</span>
          </td>
          <td class="py-1 text-right font-mono font-black text-amber-300">${winRates[b].toFixed(1)}%</td>
          <td class="py-1 text-right font-mono font-bold text-sky-300">${top2Rates[b].toFixed(1)}%</td>
          <td class="py-1 text-right font-mono font-bold text-emerald-300">${top3Rates[b].toFixed(1)}%</td>
        </tr>
      `;
    }

    let top20Html = "";
    (top20Trifectas || []).forEach((item, idx) => {
      top20Html += `
        <div class="flex items-center justify-between text-[11px] bg-slate-950 border border-slate-800/80 px-2 py-1 rounded">
          <span class="font-mono ${idx < 4 ? "text-amber-300 font-black" : "text-slate-300"}">#${idx + 1} <strong>${item.combo}</strong></span>
          <span class="font-mono text-emerald-300 font-bold">${item.prob.toFixed(1)}% <span class="text-[9px] text-slate-500">(${item.count}回)</span></span>
        </div>
      `;
    });

    el.innerHTML = `
      <div class="bg-slate-900 border border-emerald-500/40 rounded-xl p-3 space-y-2.5">
        <div class="flex flex-wrap items-center justify-between gap-2 border-b border-slate-800 pb-1.5">
          <div>
            <h3 class="text-xs font-bold text-emerald-400">🎲 ② 本格Monte Carlo勝率シミュレーション（${runs.toLocaleString()}回試行）</h3>
            <span class="text-[10px] text-slate-400">展開予測とST正規乱数・機力V2から【1着率】【2連対率】【3連対率】【3連単出現率 TOP20】を算出</span>
          </div>
          <div class="flex items-center gap-1 text-xs">
            <span class="text-[10px] text-slate-400">試行回数:</span>
            <select id="mcRunsSelect" data-change="changeMcRuns" class="font-bold text-emerald-300">
              <option value="1000" ${runs === 1000 ? "selected" : ""}>1,000回</option>
              <option value="5000" ${runs === 5000 ? "selected" : ""}>5,000回</option>
              <option value="10000" ${runs === 10000 ? "selected" : ""}>10,000回</option>
              <option value="50000" ${runs === 50000 ? "selected" : ""}>50,000回</option>
            </select>
          </div>
        </div>

        <div class="overflow-x-auto">
          <table class="w-full text-xs text-left">
            <thead class="text-[10px] text-slate-400 border-b border-slate-800">
              <tr>
                <th class="py-1">艇番・選手</th>
                <th class="py-1 text-right">【1着率】</th>
                <th class="py-1 text-right">【2連対率】</th>
                <th class="py-1 text-right">【3連対率】</th>
              </tr>
            </thead>
            <tbody>${rateRowsHtml}</tbody>
          </table>
        </div>

        <div class="space-y-1 pt-1">
          <div class="text-[11px] font-bold text-sky-300">📊 【3連単出現率】 TOP20</div>
          <div class="grid grid-cols-2 sm:grid-cols-4 gap-1.5 max-h-[210px] overflow-y-auto pr-1">${top20Html}</div>
        </div>
      </div>
    `;
  },

  /**
   * ⑦ EV(期待値)エンジン ＆ ⑧ AI買い目生成（本線・対抗・穴）＆ ⑨ 資金管理モード
   */
  renderEVAndBettingPanel(evAnalysis, portfolioData, containerId = "v3EvBettingContainer") {
    const el = document.getElementById(containerId);
    if (!el) return;

    const evRows = (evAnalysis?.byEV || []).slice(0, 10).map((it, idx) => `
      <tr class="border-b border-slate-800/60">
        <td class="py-1 font-mono text-slate-400">#${idx + 1}</td>
        <td class="py-1 font-mono font-black text-white">${it.combo}</td>
        <td class="py-1 font-mono text-right text-sky-300">${it.prob.toFixed(1)}%</td>
        <td class="py-1 font-mono text-right text-amber-300">${it.odds.toFixed(1)}倍</td>
        <td class="py-1 font-mono text-right font-black ${it.ev >= 1.35 ? "text-rose-400" : it.ev >= 1.0 ? "text-emerald-400" : "text-slate-400"}">${it.ev.toFixed(2)}</td>
        <td class="py-1 text-center"><span class="text-[10px] px-1.5 py-0.5 rounded ${it.evCategory.badge}">${it.evCategory.label}</span></td>
      </tr>
    `).join("");

    const groupRender = (catName, badgeCls) => {
      const items = (portfolioData?.portfolio || []).filter(x => x.category === catName);
      if (items.length === 0) return "";
      return `
        <div class="space-y-1">
          <div class="text-[11px] font-bold px-2 py-0.5 rounded ${badgeCls}">【${catName}】 (${items.length}点)</div>
          <div class="space-y-1">
            ${items.map(b => `
              <div class="flex items-center justify-between bg-slate-950 border border-slate-800 px-2.5 py-1.5 rounded text-xs">
                <div class="flex items-center gap-2">
                  <span class="font-mono font-black text-sm text-white">${b.combo}</span>
                  <span class="text-[10px] font-mono text-sky-300">確率${b.prob.toFixed(1)}%</span>
                  <span class="text-[10px] font-mono text-amber-300">オッズ${b.odds.toFixed(1)}倍</span>
                  <span class="text-[10px] font-mono px-1.5 py-0.5 rounded ${b.ev >= 1.35 ? "bg-rose-600 text-white font-bold" : b.ev >= 1.0 ? "bg-emerald-900 text-emerald-200" : "bg-slate-800 text-slate-300"}">EV ${b.ev.toFixed(2)}</span>
                </div>
                <div class="text-right font-mono">
                  <span class="text-xs font-black text-emerald-400">${b.allocatedYen.toLocaleString()}円</span>
                  <span class="text-[10px] text-slate-400 ml-1">(払戻 ${b.expectedReturnYen.toLocaleString()}円)</span>
                </div>
              </div>
            `).join("")}
          </div>
        </div>
      `;
    };

    const curBudget = portfolioData?.totalBudget || 5000;
    const curMode = portfolioData?.mode || "ev_focus";

    el.innerHTML = `
      <div class="bg-slate-900 border-2 border-amber-500/40 rounded-xl p-3 space-y-3">
        <div class="flex flex-wrap items-center justify-between gap-2 border-b border-slate-800 pb-2">
          <div>
            <h3 class="text-xs font-bold text-amber-300">💹 ⑦ EV(期待値)エンジン ＆ ⑧ AI買い目生成（本線・対抗・穴）＆ ⑨ 資金管理モード</h3>
            <span class="text-[10px] text-slate-400">EV = 的中確率 × オッズ でランキング化し、軍資金と運用モードに応じて期待値を最大化</span>
          </div>
          <div class="flex flex-wrap items-center gap-1 text-xs">
            <button type="button" data-action="setQuickBudget" data-budget="1000" class="px-2 py-0.5 rounded border ${curBudget === 1000 ? "bg-amber-400 text-slate-950 font-black border-amber-300" : "bg-slate-800 text-slate-300 border-slate-700"}">1000円</button>
            <button type="button" data-action="setQuickBudget" data-budget="3000" class="px-2 py-0.5 rounded border ${curBudget === 3000 ? "bg-amber-400 text-slate-950 font-black border-amber-300" : "bg-slate-800 text-slate-300 border-slate-700"}">3000円</button>
            <button type="button" data-action="setQuickBudget" data-budget="5000" class="px-2 py-0.5 rounded border ${curBudget === 5000 ? "bg-amber-400 text-slate-950 font-black border-amber-300" : "bg-slate-800 text-slate-300 border-slate-700"}">5000円</button>
            <button type="button" data-action="setQuickBudget" data-budget="10000" class="px-2 py-0.5 rounded border ${curBudget === 10000 ? "bg-amber-400 text-slate-950 font-black border-amber-300" : "bg-slate-800 text-slate-300 border-slate-700"}">10000円</button>
            <select id="bankrollModeSelect" data-change="changeBankrollMode" class="font-bold text-emerald-300 ml-1">
              <option value="equal" ${curMode === "equal" ? "selected" : ""}>⑨ 均等買い</option>
              <option value="ev_focus" ${curMode === "ev_focus" ? "selected" : ""}>⑨ 期待値重視</option>
              <option value="kelly" ${curMode === "kelly" ? "selected" : ""}>⑨ ケリー基準</option>
              <option value="conservative" ${curMode === "conservative" ? "selected" : ""}>⑨ 保守運用</option>
              <option value="aggressive" ${curMode === "aggressive" ? "selected" : ""}>⑨ 攻撃運用</option>
            </select>
          </div>
        </div>

        <div class="space-y-2">
          ${groupRender("本線", "bg-sky-950 text-sky-300 border border-sky-600/40")}
          ${groupRender("対抗", "bg-amber-950 text-amber-300 border border-amber-600/40")}
          ${groupRender("穴", "bg-rose-950 text-rose-300 border border-rose-600/40")}
        </div>

        <div class="pt-2 border-t border-slate-800 space-y-1 ui-mode-pro-only">
          <div class="text-[11px] font-bold text-rose-300">🔥 ⑦ EV(期待値)ランキング TOP10（🔥 超期待値 ／ ✅ 買い候補 ／ ⚠ 過剰人気）</div>
          <div class="overflow-x-auto">
            <table class="w-full text-xs text-left">
              <thead class="text-[10px] text-slate-400 border-b border-slate-800">
                <tr>
                  <th class="py-1">順位</th>
                  <th class="py-1">組番</th>
                  <th class="py-1 text-right">的中確率</th>
                  <th class="py-1 text-right">オッズ</th>
                  <th class="py-1 text-right">EV(期待値)</th>
                  <th class="py-1 text-center">判定</th>
                </tr>
              </thead>
              <tbody>${evRows}</tbody>
            </table>
          </div>
        </div>
      </div>
    `;
  },

  /**
   * ⑩ 会場別学習AI ＆ ⑪ 自動重み最適化(現在値 vs 推奨値) ＆ ⑫ ハズレ原因分析・デバッグ情報 (上級者モード用)
   */
  renderLearningAndDebugPanel(venueBias, weightComparison, lastMissReport, debugLog, containerId = "v3LearningComparisonContainer") {
    const el = document.getElementById(containerId);
    if (!el) return;

    const cur = weightComparison.current;
    const rec = weightComparison.recommended;

    const missHtml = lastMissReport
      ? `
        <div class="bg-slate-950 border ${lastMissReport.isHit ? "border-emerald-500/50" : "border-rose-500/50"} rounded-lg p-2.5 space-y-1">
          <div class="flex items-center justify-between text-xs font-bold">
            <span class="${lastMissReport.isHit ? "text-emerald-300" : "text-rose-300"}">⑫ 直近レース ハズレ原因分析 (確定: ${lastMissReport.actualCombo})</span>
            <div class="flex gap-1">
              ${(lastMissReport.reasons || []).map(r => `<span class="px-2 py-0.5 rounded bg-rose-950 text-rose-200 border border-rose-600/40 text-[10px]">${r}</span>`).join("")}
            </div>
          </div>
          <p class="text-[11px] text-slate-300">${lastMissReport.detailText}</p>
        </div>
      `
      : `<div class="text-[11px] text-slate-400 bg-slate-950 p-2 rounded border border-slate-800">💡 上部の「➕ この場でレース結果を10秒蓄積」で確定結果を入力すると、⑫ ハズレ原因分析（ST予測ミス・進入変化・まくり発生・展示過信・道中逆転）が自動診断されます。</div>`;

    el.innerHTML = `
      <div class="bg-slate-900 border border-teal-500/40 rounded-xl p-3 space-y-3 ui-mode-pro-only">
        <div class="flex flex-wrap items-center justify-between gap-2 border-b border-slate-800 pb-1.5">
          <div>
            <h3 class="text-xs font-bold text-teal-300">🧠 ⑩ 会場別学習AI（${venueBias.venueName || "全24場"}）＆ ⑪ 自動重み最適化（現在値 vs 推奨値）</h3>
            <span class="text-[10px] text-slate-400">会場別の決まり手分布（逃げ・差し・まくり・まくり差し・抜き）と4大係数の現在値/推奨値比較</span>
          </div>
          <button type="button" data-action="applyRecommendedWeights" class="bg-amber-400 hover:bg-amber-300 text-slate-950 font-black text-[11px] px-2.5 py-1 rounded shadow">
            ⚡ 推奨重み付けをワンタップ適用
          </button>
        </div>

        <!-- ⑩ 会場別学習DB 5種決まり手率 -->
        <div class="grid grid-cols-5 gap-1.5 text-center text-xs">
          <div class="bg-slate-950 border border-slate-800 rounded p-1.5">
            <div class="text-[10px] text-slate-400">逃げ率</div>
            <div class="font-mono font-bold text-sky-300">${venueBias.nigeRate}%</div>
          </div>
          <div class="bg-slate-950 border border-slate-800 rounded p-1.5">
            <div class="text-[10px] text-slate-400">差し率</div>
            <div class="font-mono font-bold text-emerald-300">${venueBias.sashiRate}%</div>
          </div>
          <div class="bg-slate-950 border border-slate-800 rounded p-1.5">
            <div class="text-[10px] text-slate-400">まくり率</div>
            <div class="font-mono font-bold text-rose-300">${venueBias.makuriRate}%</div>
          </div>
          <div class="bg-slate-950 border border-slate-800 rounded p-1.5">
            <div class="text-[10px] text-slate-400">まくり差し率</div>
            <div class="font-mono font-bold text-amber-300">${venueBias.makurisashiRate}%</div>
          </div>
          <div class="bg-slate-950 border border-slate-800 rounded p-1.5">
            <div class="text-[10px] text-slate-400">抜き率</div>
            <div class="font-mono font-bold text-purple-300">${venueBias.nukiRate}%</div>
          </div>
        </div>

        <!-- ⑪ 自動重み最適化: 現在値 vs 推奨値 比較表 -->
        <div class="overflow-x-auto">
          <table class="w-full text-xs text-left">
            <thead class="text-[10px] text-slate-400 border-b border-slate-800">
              <tr>
                <th class="py-1">重みパラメータ</th>
                <th class="py-1 text-right">現在値</th>
                <th class="py-1 text-right text-amber-300">AI推奨値</th>
                <th class="py-1 text-right">差分</th>
              </tr>
            </thead>
            <tbody>
              <tr class="border-b border-slate-800/50">
                <td class="py-1 font-mono">w_course (コース実績比重)</td>
                <td class="py-1 text-right font-mono">${cur.w_course}%</td>
                <td class="py-1 text-right font-mono font-bold text-amber-300">${rec.w_course}%</td>
                <td class="py-1 text-right font-mono">${rec.w_course - cur.w_course >= 0 ? "+" : ""}${rec.w_course - cur.w_course}%</td>
              </tr>
              <tr class="border-b border-slate-800/50">
                <td class="py-1 font-mono">w_exhibit (展示・気配比重)</td>
                <td class="py-1 text-right font-mono">${cur.w_exhibit}%</td>
                <td class="py-1 text-right font-mono font-bold text-amber-300">${rec.w_exhibit}%</td>
                <td class="py-1 text-right font-mono">${rec.w_exhibit - cur.w_exhibit >= 0 ? "+" : ""}${rec.w_exhibit - cur.w_exhibit}%</td>
              </tr>
              <tr class="border-b border-slate-800/50">
                <td class="py-1 font-mono">w_motor (機力V2・勝率比重)</td>
                <td class="py-1 text-right font-mono">${cur.w_motor}%</td>
                <td class="py-1 text-right font-mono font-bold text-amber-300">${rec.w_motor}%</td>
                <td class="py-1 text-right font-mono">${rec.w_motor - cur.w_motor >= 0 ? "+" : ""}${rec.w_motor - cur.w_motor}%</td>
              </tr>
              <tr>
                <td class="py-1 font-mono">w_slit (ST優位・戦法連動比重)</td>
                <td class="py-1 text-right font-mono">${cur.w_slit}%</td>
                <td class="py-1 text-right font-mono font-bold text-amber-300">${rec.w_slit}%</td>
                <td class="py-1 text-right font-mono">${rec.w_slit - cur.w_slit >= 0 ? "+" : ""}${rec.w_slit - cur.w_slit}%</td>
              </tr>
            </tbody>
          </table>
        </div>

        ${missHtml}

        <!-- ⑭ 上級者モード デバッグ情報＆シミュレーションログ -->
        <details class="bg-slate-950 border border-slate-800 rounded p-2 text-[11px]">
          <summary class="cursor-pointer font-bold text-slate-400">🛠️ ⑭ 上級者モード：シミュレーションログ・詳細係数・デバッグ情報</summary>
          <pre class="mt-2 font-mono text-[10px] text-emerald-300 whitespace-pre-wrap overflow-x-auto">${debugLog || ""}</pre>
        </details>
      </div>
    `;
  },

  /**
   * ⑬ 初級者モード vs ⑭ 上級者モードの表示切替
   */
  applyUIMode(mode = "pro") {
    const proElements = document.querySelectorAll(".ui-mode-pro-only");
    if (mode === "beginner") {
      proElements.forEach(el => el.classList.add("hidden"));
    } else {
      proElements.forEach(el => el.classList.remove("hidden"));
    }
    StorageManager.setUIMode(mode);
  }
};
