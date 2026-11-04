/**
 * @file constants.js
 * @description BOAT RACE 展開予想シミュレーター Version 3.0 定数・マスター定義モジュール
 * TypeScript移行対応 JSDoc型定義付き
 */

/**
 * @typedef {Object} VenueInfo
 * @property {string} id
 * @property {string} code
 * @property {string} name
 * @property {string} water
 * @property {boolean} tide
 * @property {number} inNige
 * @property {string} desc
 * @property {number} inMod
 * @property {number} makuriMod
 * @property {number} sashiMod
 */

/** @type {Record<string, VenueInfo>} */
const VENUE_MASTER = {
  "01": { id: "01", code: "kiryu", name: "桐生", water: "淡水", tide: false, inNige: 52.8, desc: "標高高く気圧低い・ダッシュまくりが決まりやすいナイター水面", inMod: -2, makuriMod: 4, sashiMod: 0 },
  "02": { id: "02", code: "toda", name: "戸田", water: "淡水", tide: false, inNige: 44.5, desc: "日本一狭い1M水面・カドまくり・まくり差し超多発の激戦水面", inMod: -8, makuriMod: 9, sashiMod: 1 },
  "03": { id: "03", code: "edogawa", name: "江戸川", water: "汽水", tide: true, inNige: 46.2, desc: "唯一の河川水面・強風高波と上げ潮下げ潮で波乱必至の超難水面", inMod: -6, makuriMod: 7, sashiMod: 5 },
  "04": { id: "04", code: "heiwajima", name: "平和島", water: "海水", tide: true, inNige: 45.8, desc: "東のメッカ・狭い水面と強烈なビル風で差し・抜き逆転が多発", inMod: -7, makuriMod: 5, sashiMod: 8 },
  "05": { id: "05", code: "tamagawa", name: "多摩川", water: "淡水", tide: false, inNige: 54.2, desc: "日本一の静水面・旋回スピードがフルに生きる全速まくり差し水面", inMod: 1, makuriMod: 3, sashiMod: 2 },
  "06": { id: "06", code: "hamanako", name: "浜名湖", water: "汽水", tide: true, inNige: 53.5, desc: "広大な水面・風の影響が大きくスピード戦と差しがバランス良く決まる", inMod: 0, makuriMod: 2, sashiMod: 2 },
  "07": { id: "07", code: "gamagori", name: "蒲郡", water: "海水", tide: true, inNige: 56.4, desc: "ナイター専用・穏やかな海水面でイン信頼度高め・スピード旋回戦", inMod: 3, makuriMod: 0, sashiMod: -1 },
  "08": { id: "08", code: "tokoname", name: "常滑", water: "海水", tide: true, inNige: 54.0, desc: "伊勢湾の風の影響・基本はイン優勢だが風次第でセンター強襲あり", inMod: 1, makuriMod: 1, sashiMod: 0 },
  "09": { id: "09", code: "tsu", name: "津", water: "海水", tide: true, inNige: 55.2, desc: "鈴鹿おろしの強い向かい風・風速によってダッシュまくり急浮上", inMod: 2, makuriMod: 2, sashiMod: 1 },
  "10": { id: "10", code: "mikuni", name: "三国", water: "淡水", tide: false, inNige: 55.8, desc: "広大な1M・追い風ならイン盤石、向かい風ならカドまくり炸裂", inMod: 2, makuriMod: 1, sashiMod: 0 },
  "11": { id: "11", code: "biwako", name: "びわこ", water: "淡水", tide: false, inNige: 51.5, desc: "1M対岸が狭くインがターン膨らみやすい・2C差し・3Cまくり差し名所", inMod: -3, makuriMod: 3, sashiMod: 4 },
  "12": { id: "12", code: "suminoe", name: "住之江", water: "淡水", tide: false, inNige: 58.5, desc: "ボートレースの聖地・硬い淡水でイン逃げ本線・2コース差しが強い", inMod: 5, makuriMod: -2, sashiMod: 2 },
  "13": { id: "13", code: "amagasaki", name: "尼崎", water: "淡水", tide: false, inNige: 57.2, desc: "センターポール水面・静水面でインが回りやすく逃げ信頼度高い", inMod: 4, makuriMod: -1, sashiMod: 0 },
  "14": { id: "14", code: "naruto", name: "鳴門", water: "海水", tide: true, inNige: 50.8, desc: "狭い水路水面・激しい潮流と風・まくりやまくり差しがよく決まる", inMod: -4, makuriMod: 5, sashiMod: 3 },
  "15": { id: "15", code: "marugame", name: "丸亀", water: "海水", tide: true, inNige: 55.5, desc: "ナイター海水面・潮位差で満潮時はイン有利、干潮時は握りマイ優勢", inMod: 2, makuriMod: 1, sashiMod: 1 },
  "16": { id: "16", code: "kojima", name: "児島", water: "海水", tide: true, inNige: 56.0, desc: "瀬戸内海の潮位差大・満潮はイン先マイ独壇場・干潮はまくり浮上", inMod: 3, makuriMod: 0, sashiMod: 0 },
  "17": { id: "17", code: "miyajima", name: "宮島", water: "海水", tide: true, inNige: 57.0, desc: "日本屈指の干満差・満潮時はイン鉄板、干潮時は2C差し＆カド強襲", inMod: 4, makuriMod: -1, sashiMod: 2 },
  "18": { id: "18", code: "tokuyama", name: "徳山", water: "海水", tide: true, inNige: 64.5, desc: "全国屈指のイン逃げ天国・静かな太華湾で本線1着率ダントツ", inMod: 10, makuriMod: -6, sashiMod: -2 },
  "19": { id: "19", code: "shimonoseki", name: "下関", water: "海水", tide: true, inNige: 60.5, desc: "ナイター海水面・イン逃げ実績高く手堅いレースが多い", inMod: 7, makuriMod: -3, sashiMod: 0 },
  "20": { id: "20", code: "wakamatsu", name: "若松", water: "海水", tide: true, inNige: 56.8, desc: "洞海湾の潮位・ナイター水面でイン逃げ基本、風で差し浮上", inMod: 3, makuriMod: 0, sashiMod: 1 },
  "21": { id: "21", code: "ashiya", name: "芦屋", water: "淡水", tide: false, inNige: 65.2, desc: "全国最強のモーニングイン天国・1枠優遇番組と静水面で逃げ鉄板", inMod: 11, makuriMod: -7, sashiMod: -2 },
  "22": { id: "22", code: "fukuoka", name: "福岡", water: "汽水", tide: true, inNige: 52.0, desc: "独特のうねり・1Mスタンド側が狭くインが張りづらい・2C差し聖地", inMod: -3, makuriMod: 1, sashiMod: 7 },
  "23": { id: "23", code: "karatsu", name: "唐津", water: "淡水", tide: false, inNige: 54.5, desc: "日本一広大なピット〜1M・助走距離長くダッシュ勢の伸びが生きる", inMod: 1, makuriMod: 3, sashiMod: 1 },
  "24": { id: "24", code: "omura", name: "大村", water: "海水", tide: true, inNige: 67.5, desc: "発祥の地・イン天国日本一・1コース1着率約70%の絶対王者水面", inMod: 13, makuriMod: -8, sashiMod: -3 }
};

const BOAT_COLORS = {
  1: { body: "#ffffff", border: "#94a3b8", innerBorder: "#94a3b8", tip: "#e2e8f0", text: "#0f172a", numText: "#0f172a", line: "#ffffff", name: "白" },
  2: { body: "#111827", border: "#ffffff", innerBorder: "#0f172a", tip: "#ffffff", text: "#ffffff", numText: "#0f172a", line: "#111827", name: "黒" },
  3: { body: "#ef4444", border: "#ffffff", innerBorder: "#b91c1c", tip: "#ffffff", text: "#ffffff", numText: "#dc2626", line: "#ef4444", name: "赤" },
  4: { body: "#2563eb", border: "#ffffff", innerBorder: "#1d4ed8", tip: "#ffffff", text: "#ffffff", numText: "#1d4ed8", line: "#2563eb", name: "青" },
  5: { body: "#facc15", border: "#ffffff", innerBorder: "#ca8a04", tip: "#ffffff", text: "#0f172a", numText: "#a16207", line: "#facc15", name: "黄" },
  6: { body: "#16a34a", border: "#ffffff", innerBorder: "#15803d", tip: "#ffffff", text: "#ffffff", numText: "#15803d", line: "#16a34a", name: "緑" }
};

/**
 * ① 展開パターン判定エンジン（7分類）＋ ⑮ レースタイプバッジ定義
 */
const RACE_TYPE_DEFINITIONS = {
  in_nige: {
    key: "in_nige",
    patternName: "イン逃げ戦",
    shortBadge: "🛡 イン戦",
    label: "🛡 イン逃げ濃厚",
    icon: "🛡",
    badgeClass: "bg-sky-500/20 text-sky-300 border-sky-500/50",
    desc: "イン艇の実績・ST・2C壁が盤石。1号艇先マイ押し切りが最有力。"
  },
  c2_sashi: {
    key: "c2_sashi",
    patternName: "2コース差し戦",
    shortBadge: "⚡ 差し戦",
    label: "⚡ 差し優勢（2C差し）",
    icon: "⚡",
    badgeClass: "bg-emerald-500/20 text-emerald-300 border-emerald-500/50",
    desc: "2コースの差し率・回り足が強力、またはイン旋回が膨らみやすい水面。"
  },
  sashi: {
    key: "sashi",
    patternName: "差し戦",
    shortBadge: "⚡ 差し戦",
    label: "⚡ 差し優勢",
    icon: "⚡",
    badgeClass: "bg-teal-500/20 text-teal-300 border-teal-500/50",
    desc: "イン先マイに対して2C一番差し・3C/4C二番差しが鋭く入る差し主導展開。"
  },
  makuri: {
    key: "makuri",
    patternName: "まくり戦",
    shortBadge: "🔥 カド戦",
    label: "🔥 4カドまくり警戒",
    icon: "🔥",
    badgeClass: "bg-rose-500/20 text-rose-300 border-rose-500/50",
    desc: "カド・センター勢がST優勢で内隣が凹み気味。一撃まくり強襲に厳重警戒。"
  },
  makurisashi: {
    key: "makurisashi",
    patternName: "まくり差し戦",
    shortBadge: "⚡ 差し戦",
    label: "⚡ まくり差し優勢",
    icon: "⚡",
    badgeClass: "bg-amber-500/20 text-amber-300 border-amber-500/50",
    desc: "3・4・5コースの旋回足・スリット気配が良く、1Mでインの懐を割る展開。"
  },
  chaos: {
    key: "chaos",
    patternName: "混戦戦",
    shortBadge: "💥 荒れ戦",
    label: "🌀 混戦・もつれ警戒",
    icon: "🌀",
    badgeClass: "bg-purple-500/20 text-purple-300 border-purple-500/50",
    desc: "機力・STが接近し複数の攻め手が競合。1Mの初動ひとつで着順が入れ替わる。"
  },
  upset: {
    key: "upset",
    patternName: "大荒れ戦",
    shortBadge: "💥 荒れ戦",
    label: "💥 荒れ警戒",
    icon: "💥",
    badgeClass: "bg-red-600/30 text-red-200 border-red-500 animate-pulse",
    desc: "F持ち・進入乱れ・STばらつき・イン脆弱が重複。高配当・万舟出現率大！"
  }
};

/**
 * ⑥ 荒れ指数 (0〜100) 4段階定義
 * 表示例: 20 堅い / 45 普通 / 70 中穴 / 90 大荒れ
 */
const UPSET_LEVELS = [
  { max: 32, label: "堅い", exampleScore: 20, color: "text-sky-400", bg: "bg-sky-500/20", desc: "イン信頼度が高く波乱要素が小さい堅調レース。" },
  { max: 55, label: "普通", exampleScore: 45, color: "text-emerald-400", bg: "bg-emerald-500/20", desc: "標準的なレースバランス。本線＋対抗スジ押さえ推奨。" },
  { max: 78, label: "中穴", exampleScore: 70, color: "text-amber-400", bg: "bg-amber-500/20", desc: "差し逆転・カド仕掛けの余地あり。中穴・スジ違い警戒。" },
  { max: 100, label: "大荒れ", exampleScore: 90, color: "text-rose-400 font-black", bg: "bg-rose-500/20", desc: "イン崩壊・壁崩壊リスク大。穴目・展開待ち積極狙い推奨。" }
];

/**
 * ⑦ EV(期待値)エンジン判定基準
 * 出力: 🔥 超期待値 / ✅ 買い候補 / ⚠ 過剰人気
 */
const EV_LEVELS = {
  super: { min: 1.35, key: "super", label: "🔥 超期待値", badge: "bg-rose-600 text-white font-black", desc: "的中確率に対してオッズが大幅に甘く、最優先で狙うべき高期待値目" },
  candidate: { min: 1.00, key: "candidate", label: "✅ 買い候補", badge: "bg-emerald-600 text-white font-bold", desc: "EV 1.00以上のプラス期待値が見込める推奨買い候補" },
  overpopular: { max: 1.00, key: "overpopular", label: "⚠ 過剰人気", badge: "bg-amber-900/60 text-amber-300 border border-amber-600/50", desc: "出現率に対してオッズが売れすぎており妙味が薄い目" }
};

/**
 * ⑨ 資金管理モード定義
 */
const BANKROLL_MODES = {
  equal: { key: "equal", label: "均等買い", desc: "全買い目に均等に資金を配分し、どの目が来ても安定回収を狙う方式" },
  ev_focus: { key: "ev_focus", label: "期待値重視", desc: "EV(期待値=確率×オッズ)が高い目ほど厚く傾斜配分する方式" },
  kelly: { key: "kelly", label: "ケリー基準", desc: "f* = (b*p - q)/b に基づき、長期資金成長率を最大化する数学的配分" },
  conservative: { key: "conservative", label: "保守運用", desc: "本線（的中確率上位）に厚く張り、トリガミを防いで的中率を重視する方式" },
  aggressive: { key: "aggressive", label: "攻撃運用", desc: "対抗・穴（高オッズ×プラスEV）の比重を高め、一撃高回収を狙う方式" }
};

const STORAGE_KEYS = {
  VENUE_LEARNING_PREFIX: "BOATRACE_VENUE_DB_",
  LEARNED_PARAMS: "BOATRACE_LEARNED_PARAMS",
  REVIEW_LOGS: "BOATRACE_REVIEW_LOGS",
  MISS_ANALYSIS_LOGS: "BOATRACE_MISS_LOGS",
  UI_MODE: "BOATRACE_UI_MODE",
  USER_BETS: "BOATRACE_USER_BETS",
  SIM_SETTINGS: "BOATRACE_SIM_SETTINGS"
};
