```html
<!doctype html>
<html lang="ja">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>BOAT RACE 展開予想シミュレーター PHASE 2 PRO Complete</title>
    <script src="https://cdn.tailwindcss.com">window.addEventListener("DOMContentLoaded", () => {
        initCourseSelectors();
        loadHeiwajimaPreset();
        renderCourseTacticsGrid();
        applyLearnedFeedbackParams(false);
        if (typeof INITIAL_SERVER_DATA !== "undefined" && INITIAL_SERVER_DATA && INITIAL_SERVER_DATA.status === "ok") {
          applyServerData(INITIAL_SERVER_DATA);
        }
        initAppEventListeners();
      });
    </script>
    <style>
      body { background: #0b1120; color: #f8fafc; font-family: sans-serif; margin: 0; }
      .boat-1 { background: #ffffff; color: #0f172a; border: 1px solid #cbd5e1; }
      .boat-2 { background: #1e293b; color: #ffffff; border: 1px solid #64748b; }
      .boat-3 { background: #ef4444; color: #ffffff; }
      .boat-4 { background: #3b82f6; color: #ffffff; }
      .boat-5 { background: #eab308; color: #0f172a; }
      .boat-6 { background: #22c55e; color: #ffffff; }
      input[type="number"], select, input[type="date"], input[type="text"] {
        background: #1e293b; border: 1px solid #334155; color: #f8fafc;
        border-radius: 0.35rem; padding: 0.2rem 0.35rem; font-size: 0.78rem;
      }
      input[type="range"] { accent-color: #38bdf8; }
      .tactic-select {
        background: #31102f !important; border: 1px solid #ec4899 !important;
        color: #fbcfe8 !important; font-weight: bold;
      }
      .slit-lane {
        position: relative; height: 38px; border-bottom: 1px dashed #334155;
        display: flex; align-items: center;
      }
      .kado-line { border-top: 2px dashed #f43f5e !important; }
    </style>
  </head>
  <body class="pb-12">
    <!-- Top Sticky Navigation Bar -->
    <header class="sticky top-0 z-30 bg-slate-900/95 border-b border-slate-800 px-3 py-2 shadow-lg backdrop-blur">
      <div class="max-w-7xl mx-auto flex flex-wrap items-center justify-between gap-2">
        <div class="flex items-center gap-2">
          <span class="bg-sky-500 text-slate-950 font-black px-2 py-0.5 rounded text-xs">PHASE 2 PRO Complete</span>
          <h1 class="text-sm md:text-base font-bold text-white">
            🎓 ぼーとだいがくせい｜ボートレース展開シミュレーター PHASE 2 PRO
          </h1>
          <span id="g1ActiveHeaderBadge" class="hidden text-[11px] font-black bg-amber-500 text-slate-950 px-2 py-0.5 rounded shadow">
            🏆 G1以上限定成績 適用中
          </span>
          <span id="fetchStatus" class="text-[11px] font-bold text-emerald-300 ml-1"></span>
        </div>

        <div class="flex flex-wrap items-center gap-1.5 text-xs">
          <button onclick="document.getElementById('factorSelectBox').classList.toggle('hidden')" class="bg-indigo-600 hover:bg-indigo-500 text-white font-bold px-2.5 py-1 rounded shadow">
            ✅ 適用データ選択(19項目)
          </button>
          <button onclick="document.getElementById('weightSliderBox').classList.toggle('hidden')" class="bg-sky-700 hover:bg-sky-600 text-white font-bold px-2.5 py-1 rounded shadow">
            ⚙️ 重み付け調整(0〜200%)
          </button>
          <button onclick="applyLearnedFeedbackParams()" class="bg-amber-500 hover:bg-amber-400 text-slate-950 font-black px-2.5 py-1 rounded shadow" title="振り返りサイトの蓄積データから重み付けと水面補正を自動最適化します">
            🧠 振り返り学習反映
          </button>
          <button onclick="document.getElementById('pasteImportBox').classList.toggle('hidden')" class="bg-emerald-700 hover:bg-emerald-600 text-white font-bold px-2.5 py-1 rounded shadow">
            📥 テキスト/JSON取込
          </button>
          <button onclick="toggleAllDetails()" class="bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 px-2 py-1 rounded">
            📂 全詳細開閉
          </button>
          <button onclick="resetAllTactics()" class="bg-pink-950 hover:bg-pink-900 text-pink-300 border border-pink-600/50 px-2 py-1 rounded">
            🎯 戦法リセット
          </button>
          <button onclick="loadHeiwajimaPreset()" class="bg-slate-800 hover:bg-slate-700 text-sky-400 border border-sky-500/40 px-2 py-1 rounded">
            サンプル復元
          </button>
          <a href="?view=reviewer" target="_blank" rel="noopener" class="bg-teal-500 hover:bg-teal-400 text-slate-950 font-black px-2.5 py-1 rounded shadow">
            🔬 結果振り返りサイトへ移動 ↗
          </a>
          <a href="https://x.com/Boatrace__daisu" target="_blank" rel="noopener" class="bg-slate-950 hover:bg-slate-800 text-white border border-slate-600 px-2 py-1 rounded font-bold">
            𝕏 @Boatrace__daisu
          </a>
          <a href="https://note.com/boatrace__daisu" target="_blank" rel="noopener" class="bg-emerald-950 hover:bg-emerald-900 text-emerald-300 border border-emerald-600/50 px-2 py-1 rounded font-bold">
            📓 noteマイページ
          </a>
        </div>
      </div>
    </header>

    <main class="max-w-7xl mx-auto px-3 pt-3 space-y-3">
      <!-- 🧠 振り返りデータの蓄積状況 ＆ シミュレーター自動学習フィードバックパネル -->
      <section id="learningStatusSection" class="bg-slate-900 border-2 border-amber-500/50 rounded-xl p-3 space-y-2">
        <div class="flex flex-wrap items-center justify-between gap-2">
          <div class="flex items-center gap-2">
            <span class="bg-amber-400 text-slate-950 font-black px-2 py-0.5 rounded text-xs">🧠 蓄積学習エンジン</span>
            <h2 class="text-xs font-bold text-amber-300">振り返りデータの蓄積ステータス ＆ シミュレーター自動補正</h2>
            <span id="learnedCountBadge" class="text-[11px] font-mono bg-slate-800 text-emerald-300 px-2 py-0.5 rounded border border-emerald-600/40">蓄積: 0レース (未反映)</span>
          </div>
          <div class="flex flex-wrap items-center gap-1.5 text-xs">
            <button onclick="document.getElementById('quickReviewBox').classList.toggle('hidden')" class="bg-teal-500 hover:bg-teal-400 text-slate-950 font-black px-2.5 py-1 rounded shadow">
              ➕ この場でレース結果を10秒蓄積
            </button>
            <button onclick="applyLearnedFeedbackParams(true)" class="bg-amber-500 hover:bg-amber-400 text-slate-950 font-bold px-2.5 py-1 rounded shadow">
              🔄 蓄積データを再読込・適用
            </button>
            <button onclick="resetLearnedFeedback()" class="bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 px-2 py-1 rounded">
              補正オフ(初期値)
            </button>
          </div>
        </div>
        <div id="learningDetailBar" class="text-[11px] text-slate-300 bg-slate-950/80 border border-slate-800 rounded-lg px-3 py-1.5 leading-relaxed">
          💡 「🔬 結果振り返りサイト」で保存したレース履歴、または右上の「➕ この場でレース結果を10秒蓄積」で登録した確定結果（1Mの攻め方・道中逆転有無）が自動的にここに蓄積され、会場ごとのイン/まくり/差し/展開待ち補正と4大重み付けスライダーを自動進化させます。
        </div>

        <!-- ➕ シミュレーター画面から直接10秒で結果を蓄積できるクイック振り返りフォーム -->
        <div id="quickReviewBox" class="hidden bg-slate-950 border border-teal-500/40 rounded-lg p-2.5 space-y-2 text-xs">
          <div class="flex items-center justify-between border-b border-slate-800 pb-1">
            <span class="font-bold text-teal-300">🏁 レース結果クイック蓄積（保存すると即座に学習DBへ加算＆予想ロジックが進化します）</span>
            <button onclick="document.getElementById('quickReviewBox').classList.add('hidden')" class="text-slate-400 hover:text-white">✕ 閉じる</button>
          </div>
          <div class="grid grid-cols-2 sm:grid-cols-6 gap-2">
            <div>
              <label class="block text-[10px] text-slate-400">確定 1-2-3着</label>
              <div class="flex gap-1">
                <select id="q_fin1" class="w-1/3 font-bold text-amber-300"><option value="1" selected>1</option><option value="2">2</option><option value="3">3</option><option value="4">4</option><option value="5">5</option><option value="6">6</option></select>
                <select id="q_fin2" class="w-1/3 font-bold"><option value="1">1</option><option value="2" selected>2</option><option value="3">3</option><option value="4">4</option><option value="5">5</option><option value="6">6</option></select>
                <select id="q_fin3" class="w-1/3 font-bold"><option value="1">1</option><option value="2">2</option><option value="3">3</option><option value="4" selected>4</option><option value="5">5</option><option value="6">6</option></select>
              </div>
            </div>
            <div>
              <label class="block text-[10px] text-slate-400">決まり手</label>
              <select id="q_kimarite" class="w-full font-bold text-rose-300">
                <option value="nige">🛡️ 逃げ</option><option value="sashi">📐 差し</option>
                <option value="makuri" selected>🔥 まくり</option><option value="makurisashi">⚡ まくり差し</option><option value="nuki">🌀 抜き(道中逆転)</option>
              </select>
            </div>
            <div>
              <label class="block text-[10px] text-slate-400">1Mの実際の攻防(トリガー)</label>
              <select id="q_m1pat" class="w-full font-bold text-amber-200">
                <option value="clean_in">🛡️ イン完璧先マイ</option>
                <option value="in_flow">🌊 イン先マイ膨らみ</option>
                <option value="c2_sashi_atk">📐 2C差し切り</option>
                <option value="c2_makuri_atk">🔥 2Cジカまくり</option>
                <option value="center_makuri_atk" selected>🔥 3・4Cまくり仕掛け</option>
                <option value="center_ms_atk">⚡ 3・4Cまくり差し</option>
                <option value="clash_wait">💥 1Mやり合い→展開待ち浮上</option>
              </select>
            </div>
            <div>
              <label class="block text-[10px] text-slate-400">道中(2M以降)の逆転</label>
              <select id="q_dochu" class="w-full font-bold text-sky-200">
                <option value="none" selected>✅ 道中逆転なし(1M通り)</option>
                <option value="overtake_1st">🔄 1着が道中逆転(抜き)</option>
                <option value="overtake_2nd">🔄 2着が道中逆転(競り)</option>
                <option value="overtake_3rd">🔄 3着が道中追い上げ逆転</option>
              </select>
            </div>
            <div>
              <label class="block text-[10px] text-slate-400">道中逆転の要因</label>
              <select id="q_reason" class="w-full font-bold text-emerald-200">
                <option value="none" selected>ー (1Mスジ通り)</option>
                <option value="turn_power">⚙️ 出足・回り足(機力)差</option>
                <option value="2m_mistake">🌊 2Mツケマイ失敗・流れ</option>
                <option value="racer_skill">🎓 選手の道中さばき差</option>
              </select>
            </div>
            <div class="flex items-end">
              <button onclick="saveQuickReviewFromSimulator()" class="w-full bg-teal-400 hover:bg-teal-300 text-slate-950 font-black py-1.5 rounded shadow">
                💾 蓄積DBに追加して学習
              </button>
            </div>
          </div>
          <div id="quickAccumulatedList" class="text-[11px] text-slate-300 pt-1 border-t border-slate-800 max-h-[120px] overflow-y-auto space-y-1"></div>
        </div>
      </section>

      <!-- パネルA：予想に適用するデータの選択パネル (19項目個別ON/OFF ＆ 4種プリセット) -->
      <section id="factorSelectBox" class="bg-slate-900 border-2 border-indigo-500/40 rounded-xl p-3 space-y-2 ui-mode-pro-only">
        <div class="flex flex-wrap items-center justify-between gap-2 border-b border-slate-800 pb-1.5">
          <h2 class="text-xs font-bold text-indigo-300">✅ 予想計算に適用するデータの選択（チェックを外した項目は計算から除外されます）</h2>
          <div class="flex flex-wrap gap-1 text-[11px]">
            <button onclick="setFactorPreset('all')" class="bg-slate-800 hover:bg-slate-700 text-white px-2 py-0.5 rounded border border-slate-700">🔄 全データ適用</button>
            <button onclick="setFactorPreset('chokuzen')" class="bg-amber-950 hover:bg-amber-900 text-amber-300 px-2 py-0.5 rounded border border-amber-700/50">⚡ 直前展示・気配特化</button>
            <button onclick="setFactorPreset('jizen')" class="bg-sky-950 hover:bg-sky-900 text-sky-300 px-2 py-0.5 rounded border border-sky-700/50">📊 事前データ特化(展示前)</button>
            <button onclick="setFactorPreset('nomotor')" class="bg-emerald-950 hover:bg-emerald-900 text-emerald-300 px-2 py-0.5 rounded border border-emerald-700/50">🛠️ 新モーター期(機力除外)</button>
          </div>
        </div>
        <div class="grid grid-cols-2 sm:grid-cols-4 gap-2 text-[11px] text-slate-200">
          <div class="bg-slate-950/70 p-2 rounded border border-slate-800 space-y-1">
            <div class="font-bold text-sky-400 text-[10px]">【1. 選手実力・グレード基礎】</div>
            <label class="flex items-center gap-1.5 cursor-pointer"><input type="checkbox" id="f_winRate" checked onchange="runSimulation()"> 全国勝率(G1時:G1勝率)</label>
            <label class="flex items-center gap-1.5 cursor-pointer"><input type="checkbox" id="f_localWin" checked onchange="runSimulation()"> 当地勝率(G1時:G1当地)</label>
            <label class="flex items-center gap-1.5 cursor-pointer"><input type="checkbox" id="f_g1OnlyRule" checked onchange="runSimulation()"> 🏆G1以上はG1限定成績適用</label>
            <label class="flex items-center gap-1.5 cursor-pointer font-bold text-pink-300"><input type="checkbox" id="f_ladiesRule" checked onchange="runSimulation()"> 💃女子戦データを入れる/考慮する</label>
            <label class="flex items-center gap-1.5 cursor-pointer"><input type="checkbox" id="f_seriesScore" checked onchange="runSimulation()"> 節間成績点</label>
            <label class="flex items-center gap-1.5 cursor-pointer"><input type="checkbox" id="f_weight" checked onchange="runSimulation()"> 選手体重差</label>
          </div>
          <div class="bg-slate-950/70 p-2 rounded border border-slate-800 space-y-1">
            <div class="font-bold text-emerald-400 text-[10px]">【2. コース実績・攻め成功率】</div>
            <label class="flex items-center gap-1.5 cursor-pointer"><input type="checkbox" id="f_courseWin" checked onchange="runSimulation()"> コース1着率(G1対応)</label>
            <label class="flex items-center gap-1.5 cursor-pointer"><input type="checkbox" id="f_courseTri" checked onchange="runSimulation()"> コース3連率(G1対応)</label>
            <label class="flex items-center gap-1.5 cursor-pointer font-bold text-emerald-300"><input type="checkbox" id="f_courseKimarite" checked onchange="runSimulation()"> ⚔️コース別攻め成功率(差/捲/捲差)</label>
            <label class="flex items-center gap-1.5 cursor-pointer"><input type="checkbox" id="f_nigashi" checked onchange="runSimulation()"> 2C逃がし率</label>
            <label class="flex items-center gap-1.5 cursor-pointer"><input type="checkbox" id="f_nigashiTri" checked onchange="runSimulation()"> 逃がし連対率</label>
          </div>
          <div class="bg-slate-950/70 p-2 rounded border border-slate-800 space-y-1">
            <div class="font-bold text-amber-400 text-[10px]">【3. 機力・直前展示気配】</div>
            <label class="flex items-center gap-1.5 cursor-pointer"><input type="checkbox" id="f_motorBi" checked onchange="runSimulation()"> モーター2連率</label>
            <label class="flex items-center gap-1.5 cursor-pointer"><input type="checkbox" id="f_exTimeRank" checked onchange="runSimulation()"> 展示時計・順位</label>
            <label class="flex items-center gap-1.5 cursor-pointer"><input type="checkbox" id="f_oriTimeRank" checked onchange="runSimulation()"> オリ展順位</label>
            <label class="flex items-center gap-1.5 cursor-pointer"><input type="checkbox" id="f_vis" checked onchange="runSimulation()"> スリット/ターン気配</label>
            <label class="flex items-center gap-1.5 cursor-pointer"><input type="checkbox" id="f_partsTilt" checked onchange="runSimulation()"> 部品交換・チルト</label>
          </div>
          <div class="bg-slate-950/70 p-2 rounded border border-slate-800 space-y-1">
            <div class="font-bold text-rose-400 text-[10px]">【4. ST・水面環境・展開】</div>
            <label class="flex items-center gap-1.5 cursor-pointer"><input type="checkbox" id="f_avgSt" checked onchange="runSimulation()"> 平均ST(G1時:G1平均ST)</label>
            <label class="flex items-center gap-1.5 cursor-pointer"><input type="checkbox" id="f_seriesSt" checked onchange="runSimulation()"> 今節ST/スタ展ST</label>
            <label class="flex items-center gap-1.5 cursor-pointer"><input type="checkbox" id="f_fCount" checked onchange="runSimulation()"> F持ち・深イン補正</label>
            <label class="flex items-center gap-1.5 cursor-pointer"><input type="checkbox" id="f_env" checked onchange="runSimulation()"> 水面・風・波・潮補正</label>
          </div>
        </div>
      </section>

      <!-- パネルB：カテゴリ別 重み付けスライダー (0%〜200%) -->
      <section id="weightSliderBox" class="hidden bg-slate-900 border-2 border-sky-500/40 rounded-xl p-3 space-y-2 ui-mode-pro-only">
        <div class="flex flex-wrap items-center justify-between gap-2 border-b border-slate-800 pb-1.5">
          <h2 class="text-xs font-bold text-sky-300">⚙️ カテゴリ別 重み付けスライダー（0%〜200%で予想ロジックの比重を自在に調整）</h2>
          <div class="flex flex-wrap gap-1 text-[11px]">
            <button onclick="setWeightPreset(100,100,100,100)" class="bg-slate-800 hover:bg-slate-700 text-white px-2 py-0.5 rounded">標準バランス(100%)</button>
            <button onclick="setWeightPreset(80,180,140,130)" class="bg-amber-950 text-amber-300 px-2 py-0.5 rounded">展示・気配重視型</button>
            <button onclick="setWeightPreset(180,90,110,100)" class="bg-sky-950 text-sky-300 px-2 py-0.5 rounded">コース実績・決まり手重視型</button>
            <button onclick="setWeightPreset(80,150,130,190)" class="bg-rose-950 text-rose-300 px-2 py-0.5 rounded">スリット・穴展開重視型</button>
          </div>
        </div>
        <div class="grid grid-cols-1 sm:grid-cols-4 gap-3 text-xs">
          <div class="bg-slate-950/70 p-2.5 rounded border border-slate-800">
            <div class="flex justify-between mb-1"><span>① コース別実績・攻め成功率比重</span><span id="lbl_wCourse" class="font-mono font-bold text-sky-300">100%</span></div>
            <input type="range" id="w_course" min="0" max="200" step="10" value="100" oninput="runSimulation()" class="w-full" />
          </div>
          <div class="bg-slate-950/70 p-2.5 rounded border border-slate-800">
            <div class="flex justify-between mb-1"><span>② 展示・オリ展・気配・部品比重</span><span id="lbl_wEx" class="font-mono font-bold text-amber-300">100%</span></div>
            <input type="range" id="w_exhibit" min="0" max="200" step="10" value="100" oninput="runSimulation()" class="w-full" />
          </div>
          <div class="bg-slate-950/70 p-2.5 rounded border border-slate-800">
            <div class="flex justify-between mb-1"><span>③ 勝率・当地・モーター・体重比重</span><span id="lbl_wMotor" class="font-mono font-bold text-emerald-300">100%</span></div>
            <input type="range" id="w_motor" min="0" max="200" step="10" value="100" oninput="runSimulation()" class="w-full" />
          </div>
          <div class="bg-slate-950/70 p-2.5 rounded border border-slate-800">
            <div class="flex justify-between mb-1"><span>④ スリット＆戦法連動ボーナス比重</span><span id="lbl_wSlit" class="font-mono font-bold text-rose-300">100%</span></div>
            <input type="range" id="w_slit" min="0" max="200" step="10" value="100" oninput="runSimulation()" class="w-full" />
          </div>
        </div>
      </section>

      <!-- パネルC：テキスト / JSON コピペ取込 -->
      <section id="pasteImportBox" class="hidden bg-slate-900 border-2 border-emerald-500/40 rounded-xl p-3 space-y-2">
        <div class="flex items-center justify-between border-b border-slate-800 pb-1">
          <h2 class="text-xs font-bold text-emerald-300">📥 公式ページ全文コピペ または Colab出力JSONの一括取込</h2>
          <button onclick="document.getElementById('pasteImportBox').classList.add('hidden')" class="text-xs text-slate-400 hover:text-white">✕ 閉じる</button>
        </div>
        <textarea id="rawPasteTextarea" rows="4" placeholder="BOAT RACE公式の出走表・直前情報ページを全選択コピー(Ctrl+A → Ctrl+C)して貼り付けるか、JSONを貼り付けてください。" class="w-full bg-slate-950 border border-slate-700 rounded p-2 text-xs font-mono text-slate-200"></textarea>
        <div class="flex justify-end gap-2">
          <button onclick="applyRawPaste()" class="bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-black text-xs px-4 py-1.5 rounded shadow">⚡ 解析して6艇カードに反映する</button>
        </div>
      <