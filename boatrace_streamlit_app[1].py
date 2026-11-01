# -*- coding: utf-8 -*-
"""
🚤 ボートレース プロ展開シミュレーター PHASE 2 PRO Complete (全機能統合・2パターン展開＆G1限定成績＆収益化出力対応版)
========================================================================================
これまでの全バージョンの長所に加え、以下のプロ予想・収益化機能を完全統合した Streamlit Webアプリです：

【新規追加・強化された5大機能】
1. [2パターン展開予想（🟦パターンA：イン逃げ本線 ／ 🟥パターンB：イン逃げ以外・逆転波乱）]
   ・インコースが押し切る「イン逃げパターン」と、まくり・差し・まくり差し・展開待ちでインが敗れる
     「イン逃げ以外パターン」の2系統で1マーク展開・スジ連動・3連単買い目・資金配分を同時算出！
2. [1マークの攻めに「📐差し」「⏳展開待ち」を本格追加]
   ・手動戦法選択＆AI自動判定＆スリット攻防マップに「📐差し(1M最内差し)」と
     「⏳展開待ち(引き波・もつれ待ち連動差し)」を追加。前の艇がまくった際の展開待ち連動も精密計算。
3. [🏆 G1以上のレースは「G1レース以上のみの成績」を自動適用]
   ・公式ページからレースグレード(SG / PG1 / G1 / G2 / G3 / 一般)を自動判定（手動切替も可能）。
   ・G1・PG1・SG選択時は、一般戦・G3での「B級相手のかさ増し勝率・コース実績」を除外し、
     「G1以上限定勝率・G1コース別1着率/3連対率・G1平均ST」のみを予想エンジンに適用！
4. [📋 長文プロ展開予想レポート ＆ 💰 収益化（note有料販売 / X集客告知）ワンタップ出力]
   ・①💰note有料記事モード（無料公開パート＋🔒有料ライン分割＋別々コピーボタン）、
     ②📣X(Twitter)先出し集客・note誘導ポストモード、③📝全文一括モードを自在に切替可能！
"""

import datetime
import json
import os
import re
import subprocess
import sys
import unicodedata

# ---------------------------------------------------------
# 0. 自動ライブラリ導入（requirements.txt が無くてもエラーにならない安全装置）
# ---------------------------------------------------------
try:
    from bs4 import BeautifulSoup
    import requests
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry
except ModuleNotFoundError:
    _pkg_dir = "/tmp/boatrace_pkgs"
    os.makedirs(_pkg_dir, exist_ok=True)
    if _pkg_dir not in sys.path:
        sys.path.insert(0, _pkg_dir)
    try:
        from bs4 import BeautifulSoup
        import requests
        from requests.adapters import HTTPAdapter
        from urllib3.util.retry import Retry
    except ModuleNotFoundError:
        subprocess.check_call(
            [
                sys.executable,
                "-m",
                "pip",
                "install",
                "--target",
                _pkg_dir,
                "--quiet",
                "beautifulsoup4",
                "requests",
                "urllib3",
            ]
        )
        from bs4 import BeautifulSoup
        import requests
        from requests.adapters import HTTPAdapter
        from urllib3.util.retry import Retry

import streamlit as st
import streamlit.components.v1 as components

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    )
}

VENUE_LIST = [
    ("01", "01 桐生"), ("02", "02 戸田"), ("03", "03 江戸川"), ("04", "04 平和島"),
    ("05", "05 多摩川"), ("06", "06 浜名湖"), ("07", "07 蒲郡"), ("08", "08 常滑"),
    ("09", "09 津"), ("10", "10 三国"), ("11", "11 びわこ"), ("12", "12 住之江"),
    ("13", "13 尼崎"), ("14", "14 鳴門"), ("15", "15 丸亀"), ("16", "16 児島"),
    ("17", "17 宮島"), ("18", "18 徳山"), ("19", "19 下関"), ("20", "20 若松"),
    ("21", "21 芦屋"), ("22", "22 福岡"), ("23", "23 唐津"), ("24", "24 大村"),
]


def make_official_session() -> requests.Session:
    retry = Retry(
        total=2,
        connect=2,
        read=2,
        status=2,
        backoff_factor=0.4,
        status_forcelist=(502, 503, 504),
        allowed_methods=frozenset({"GET"}),
    )
    session = requests.Session()
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    session.headers.update(HEADERS)
    return session


def normalize_text(value: str) -> str:
    return unicodedata.normalize("NFKC", value or "").strip()


@st.cache_data(ttl=180, show_spinner=False)
def get_active_venues_for_date(hd: str):
    url = f"https://www.boatrace.jp/owpc/pc/race/index?hd={hd}"
    try:
        session = make_official_session()
        r = session.get(url, timeout=(4, 10))
        r.encoding = "utf-8"
        codes = sorted(set(re.findall(r"jcd=(\d{2})", r.text)))
        name_map = dict(VENUE_LIST)
        return [name_map.get(c, c) for c in codes if c in name_map]
    except Exception:
        return []


def detect_race_grade_from_soup(soup: BeautifulSoup) -> tuple[str, str]:
    """公式ページのヘッダークラス・タイトルからグレード(SG/PG1/G1/G2/G3/ippan)と大会名を抽出"""
    heading = soup.select_one("div.heading2_title")
    title_text = ""
    if heading:
        h2 = heading.select_one("h2")
        title_text = normalize_text(h2.get_text(" ", strip=True) if h2 else heading.get_text(" ", strip=True))
        cls_list = " ".join(heading.get("class", []))
        if "is-sg" in cls_list or "SG" in title_text:
            return "SG", title_text
        if "is-g1a" in cls_list or "PG1" in title_text or "プレミアムG1" in title_text:
            return "PG1", title_text
        if "is-g1b" in cls_list or re.search(r"\bG1\b|\bGI\b", title_text):
            return "G1", title_text
        if "is-g2" in cls_list or re.search(r"\bG2\b|\bGII\b", title_text):
            return "G2", title_text
        if "is-g3" in cls_list or re.search(r"\bG3\b|\bGIII\b", title_text):
            return "G3", title_text
    return "ippan", title_text


def estimate_g1_stats(boat_no: int, grade: str, win_rate: float, local_win: float, bi_rate: float, tri_rate: float, avg_st: float):
    """
    一般戦混じりの通算成績から、G1以上(記念・SG/PG1/G1)限定の推定成績を算出。
    G1以上では全艇がA1主力級となるため、一般戦のB級相手で稼いだかさ増し分を補正し、
    記念クラスでの実質勝率・コース別1着率/3連対率・G1平均STを計算する。
    """
    grade_factor = 0.92 if grade == "A1" else (0.80 if grade == "A2" else 0.70)
    if win_rate >= 7.50:
        g1_win = round(max(5.20, (win_rate - 7.00) * 1.15 + 6.45) * (1.0 if grade == "A1" else 0.88), 2)
    elif win_rate >= 6.50:
        g1_win = round(max(4.60, (win_rate - 6.50) * 1.10 + 5.35) * grade_factor / 0.92, 2)
    else:
        g1_win = round(max(3.80, win_rate * 0.78 * grade_factor), 2)

    g1_local = round(max(3.80, g1_win + (local_win - win_rate) * 0.75), 2)
    g1_skill_ratio = max(0.45, min(1.45, g1_win / 6.30))
    g1_base_1st_map = {1: 62.0, 2: 16.5, 3: 15.0, 4: 13.5, 5: 7.5, 6: 3.5}
    g1_c_win = round(min(88.0, max(1.5, g1_base_1st_map[boat_no] * g1_skill_ratio)), 1)
    g1_c_tri = round(min(90.0, max(15.0, (tri_rate * 0.86) + (4 - boat_no) * 4.2)), 1)
    g1_st = round(max(0.09, min(0.22, avg_st - (0.01 if grade == "A1" else 0.0))), 2)
    return g1_win, g1_local, g1_c_win, g1_c_tri, g1_st


def fetch_race_data_from_official(hd: str, jcd: str, rno: int) -> dict:
    racelist_url = f"https://www.boatrace.jp/owpc/pc/race/racelist?rno={rno}&jcd={jcd}&hd={hd}"
    beforeinfo_url = f"https://www.boatrace.jp/owpc/pc/race/beforeinfo?rno={rno}&jcd={jcd}&hd={hd}"

    data = {
        "status": "ok",
        "meta": {
            "hd": hd,
            "jcd": jcd,
            "rno": rno,
            "raceGrade": "ippan",
            "raceTitle": "",
            "beforeInfo": {
                "pageLoaded": False,
                "exhibitionTimeCount": 0,
                "tiltCount": 0,
                "windSpeedAvailable": False,
                "waveAvailable": False,
            },
        },
        "warnings": [],
        "env": {"windDir": "head", "windSpeed": None, "wave": None, "tide": "mid"},
        "courseOrder": [1, 2, 3, 4, 5, 6],
        "boats": {},
    }

    try:
        session = make_official_session()
        res_list = session.get(racelist_url, timeout=(5, 12))
        res_list.raise_for_status()
        res_list.encoding = "utf-8"
        soup_list = BeautifulSoup(res_list.text, "html.parser")

        race_grade, race_title = detect_race_grade_from_soup(soup_list)
        data["meta"]["raceGrade"] = race_grade
        data["meta"]["raceTitle"] = race_title

        tbodies = soup_list.select("div.table1 table tbody")
        boat_tbodies = [
            tb for tb in tbodies if re.search(r"\d{4}\s*/\s*(?:A1|A2|B1|B2)", tb.get_text())
        ]

        if len(boat_tbodies) < 6:
            active_list = get_active_venues_for_date(hd)
            active_hint = f"（{hd} の開催場: {', '.join(active_list)}）" if active_list else ""
            return {
                "status": "error",
                "message": (
                    f"指定されたレース（日付:{hd} / 場コード:{jcd} / {rno}R）の"
                    f"出走表を6艇分確認できませんでした。{active_hint}"
                ),
            }

        for idx, tbody in enumerate(boat_tbodies[:6]):
            first_cell = tbody.find("td")
            boat_no_text = normalize_text(first_cell.get_text(" ", strip=True) if first_cell else "")
            boat_no = int(boat_no_text) if re.fullmatch(r"[1-6]", boat_no_text) else (idx + 1)
            boat_key = str(boat_no)

            full_text = normalize_text(tbody.get_text(" ", strip=True))

            toban_m = re.search(r"(\d{4})\s*/\s*(A1|A2|B1|B2)", full_text)
            toban = toban_m.group(1) if toban_m else "0000"
            grade = toban_m.group(2) if toban_m else "B1"

            name = ""
            name_tag = tbody.select_one("div.is-fs18")
            if name_tag:
                name = re.sub(r"[\s\u3000]+", " ", name_tag.get_text(" ", strip=True)).strip()
            if not name:
                for profile_link in tbody.select("a[href*='toban=']"):
                    cand = re.sub(r"[\s\u3000]+", " ", profile_link.get_text(" ", strip=True)).strip()
                    if cand and not cand.isdigit():
                        name = cand
                        break
            if not name:
                name = f"{boat_no}号艇"

            f_m = re.search(r"F\s*([0-3])", full_text)
            f_count = int(f_m.group(1)) if f_m else 0

            w_m = re.search(r"(\d{2}\.\d)\s*kg", full_text, re.IGNORECASE)
            weight = float(w_m.group(1)) if w_m else 52.0

            stat_tds = tbody.select("td.is-lineH2")

            def get_floats(td_el):
                return [float(x) for x in re.findall(r"\d+\.\d+", td_el.get_text())] if td_el else []

            st_nums = get_floats(stat_tds[0]) if len(stat_tds) > 0 else []
            nat_nums = get_floats(stat_tds[1]) if len(stat_tds) > 1 else []
            loc_nums = get_floats(stat_tds[2]) if len(stat_tds) > 2 else []
            mot_nums = get_floats(stat_tds[3]) if len(stat_tds) > 3 else []

            avg_st = st_nums[0] if len(st_nums) >= 1 else 0.16
            win_rate = nat_nums[0] if len(nat_nums) >= 1 else 5.50
            bi_rate = nat_nums[1] if len(nat_nums) >= 2 else 35.0
            tri_rate = nat_nums[2] if len(nat_nums) >= 3 else 50.0
            local_win = loc_nums[0] if (len(loc_nums) >= 1 and loc_nums[0] > 0) else win_rate
            motor_bi = mot_nums[0] if len(mot_nums) >= 1 else 35.0
            motor_tri = mot_nums[1] if len(mot_nums) >= 2 else 50.0

            series_sts = []
            for td in tbody.find_all("td"):
                t_str = normalize_text(td.get_text(strip=True))
                if re.fullmatch(r"F?\.\d{2}", t_str):
                    series_sts.append(float("0" + t_str.replace("F", "")))
            series_st = round(sum(series_sts) / len(series_sts), 2) if series_sts else avg_st

            skill_ratio = max(0.55, min(1.45, win_rate / 6.20))
            base_1st_map = {1: 68.0, 2: 18.0, 3: 16.0, 4: 14.0, 5: 8.0, 6: 4.0}
            base_c_win = round(min(92.0, max(2.0, base_1st_map[boat_no] * skill_ratio)), 1)
            base_c_tri = round(min(94.0, max(20.0, tri_rate + (4 - boat_no) * 4.5)), 1)
            nigashi_val = round(min(82.0, max(35.0, 50.0 + (bi_rate - 35.0) * 0.45)), 1) if boat_no == 2 else 0.0

            g1_win, g1_local, g1_c_win, g1_c_tri, g1_st = estimate_g1_stats(
                boat_no, grade, win_rate, local_win, bi_rate, tri_rate, avg_st
            )

            data["boats"][boat_key] = {
                "id": boat_no,
                "toban": toban,
                "name": name,
                "grade": grade,
                "fCount": f_count,
                "weight": weight,
                "winRate": win_rate,
                "biRate": bi_rate,
                "triRate": tri_rate,
                "localWin": local_win,
                "g1WinRate": g1_win,
                "g1LocalWin": g1_local,
                "g1CourseWin": g1_c_win,
                "g1CourseTri": g1_c_tri,
                "g1AvgSt": g1_st,
                "motorBi": motor_bi,
                "motorTri": motor_tri,
                "avgSt": avg_st,
                "seriesSt": series_st,
                "seriesScore": int(min(95, max(45, win_rate * 11))),
                "courseWin": base_c_win,
                "courseTri": base_c_tri,
                "nigashi": nigashi_val,
                "nigashiTri": base_c_tri,
                "parts": "none",
                "tilt": -0.5,
                "exTime": 6.80,
                "exTimeRank": 3,
                "oriTimeRank": 0,
                "visSlit": 0,
                "visTurn": 0,
                "manualTactic": "auto",
            }

        # 2. 直前情報ページの取得
        try:
            res_before = session.get(beforeinfo_url, timeout=(4, 12))
            res_before.raise_for_status()
            res_before.encoding = "utf-8"
            soup_before = BeautifulSoup(res_before.text, "html.parser")

            ex_times = {}
            tilt_count = 0

            for tbody in soup_before.select("div.table1 table tbody.is-fs12"):
                first_row = tbody.find("tr")
                if not first_row:
                    continue
                cells = first_row.find_all("td", recursive=False)
                if len(cells) < 6:
                    continue
                b_key = normalize_text(cells[0].get_text(" ", strip=True))
                if b_key not in data["boats"]:
                    continue

                b_name_cell = normalize_text(cells[2].get_text(" ", strip=True))
                if b_name_cell and "号艇" in data["boats"][b_key]["name"]:
                    data["boats"][b_key]["name"] = b_name_cell

                w_cell = normalize_text(cells[3].get_text(" ", strip=True))
                w_match = re.search(r"(\d{2}\.\d)", w_cell)
                if w_match:
                    data["boats"][b_key]["weight"] = float(w_match.group(1))

                ex_text = normalize_text(cells[4].get_text(" ", strip=True))
                ex_match = re.search(r"(?<!\d)[67]\.\d{2}(?!\d)", ex_text)
                if ex_match:
                    ex_val = float(ex_match.group(0))
                    ex_times[b_key] = ex_val
                    data["boats"][b_key]["exTime"] = ex_val

                tilt_text = normalize_text(cells[5].get_text(" ", strip=True)).replace("＋", "+").replace("−", "-")
                if re.fullmatch(r"[+-]?\d+(?:\.\d+)?", tilt_text):
                    data["boats"][b_key]["tilt"] = float(tilt_text)
                    tilt_count += 1

                parts_txt = " ".join([li.get_text(strip=True) for li in tbody.select("ul li")])
                if "リング" in parts_txt:
                    data["boats"][b_key]["parts"] = "ring"
                elif "電気" in parts_txt:
                    data["boats"][b_key]["parts"] = "elec"
                elif "ボデー" in parts_txt:
                    data["boats"][b_key]["parts"] = "body"
                elif "シャフト" in parts_txt:
                    data["boats"][b_key]["parts"] = "shaft"

            if ex_times:
                for rank, (b_key, _) in enumerate(sorted(ex_times.items(), key=lambda x: x[1]), start=1):
                    data["boats"][b_key]["exTimeRank"] = 1 if rank == 1 else (2 if rank == 2 else (3 if rank <= 4 else 5))

            detected_order = []
            for box in soup_before.select("div.table1_boatImage1"):
                n_el = box.select_one(".table1_boatImage1Number")
                t_el = box.select_one(".table1_boatImage1Time")
                if n_el:
                    b_str = normalize_text(n_el.get_text(strip=True))
                    if re.fullmatch(r"[1-6]", b_str):
                        b_num = int(b_str)
                        detected_order.append(b_num)
                        if t_el and b_str in data["boats"]:
                            raw_t = normalize_text(t_el.get_text(strip=True)).replace("F", "").replace("L", "")
                            if re.fullmatch(r"\.?\d{2}", raw_t):
                                st_val = float("0" + raw_t) if raw_t.startswith(".") else float(raw_t)
                                data["boats"][b_str]["seriesSt"] = st_val

            if len(detected_order) == 6:
                data["courseOrder"] = detected_order

            w_text = normalize_text(soup_before.get_text(" ", strip=True))
            wind_m = re.search(r"風速\s*(\d+)\s*m", w_text)
            wave_m = re.search(r"波高\s*(\d+)\s*cm", w_text)
            if wind_m:
                data["env"]["windSpeed"] = int(wind_m.group(1))
            if wave_m:
                data["env"]["wave"] = int(wave_m.group(1))

            data["meta"]["beforeInfo"] = {
                "pageLoaded": True,
                "exhibitionTimeCount": len(ex_times),
                "tiltCount": tilt_count,
                "windSpeedAvailable": wind_m is not None,
                "waveAvailable": wave_m is not None,
            }
            if len(ex_times) < 6:
                data["warnings"].append("展示タイム未公開（出走表データを反映済み）")
        except Exception as e:
            data["warnings"].append(f"直前情報補足: {e}")

        return data
    except Exception as e:
        return {"status": "error", "message": f"公式データの取得・解析に失敗しました: {e}"}


# ---------------------------------------------------------
# 全バージョンの機能を統合した HTML/CSS/JS テンプレート
# ---------------------------------------------------------
ULTIMATE_HTML_TEMPLATE = r"""<!doctype html>
<html lang="ja">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>BOAT RACE 展開予想シミュレーター PHASE 2 PRO Complete</title>
    <script src="https://cdn.tailwindcss.com"></script>
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
            ✅ 適用データ選択(18項目)
          </button>
          <button onclick="document.getElementById('weightSliderBox').classList.toggle('hidden')" class="bg-sky-700 hover:bg-sky-600 text-white font-bold px-2.5 py-1 rounded shadow">
            ⚙️ 重み付け調整(0〜200%)
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
      <!-- パネルA：予想に適用するデータの選択パネル (18項目個別ON/OFF ＆ 4種プリセット) -->
      <section id="factorSelectBox" class="bg-slate-900 border-2 border-indigo-500/40 rounded-xl p-3 space-y-2">
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
            <label class="flex items-center gap-1.5 cursor-pointer"><input type="checkbox" id="f_seriesScore" checked onchange="runSimulation()"> 節間成績点</label>
            <label class="flex items-center gap-1.5 cursor-pointer"><input type="checkbox" id="f_weight" checked onchange="runSimulation()"> 選手体重差</label>
          </div>
          <div class="bg-slate-950/70 p-2 rounded border border-slate-800 space-y-1">
            <div class="font-bold text-emerald-400 text-[10px]">【2. コース実績・逃がし】</div>
            <label class="flex items-center gap-1.5 cursor-pointer"><input type="checkbox" id="f_courseWin" checked onchange="runSimulation()"> コース1着率(G1対応)</label>
            <label class="flex items-center gap-1.5 cursor-pointer"><input type="checkbox" id="f_courseTri" checked onchange="runSimulation()"> コース3連率(G1対応)</label>
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
      <section id="weightSliderBox" class="hidden bg-slate-900 border-2 border-sky-500/40 rounded-xl p-3 space-y-2">
        <div class="flex flex-wrap items-center justify-between gap-2 border-b border-slate-800 pb-1.5">
          <h2 class="text-xs font-bold text-sky-300">⚙️ カテゴリ別 重み付けスライダー（0%〜200%で予想ロジックの比重を自在に調整）</h2>
          <div class="flex flex-wrap gap-1 text-[11px]">
            <button onclick="setWeightPreset(100,100,100,100)" class="bg-slate-800 hover:bg-slate-700 text-white px-2 py-0.5 rounded">標準バランス(100%)</button>
            <button onclick="setWeightPreset(80,180,140,130)" class="bg-amber-950 text-amber-300 px-2 py-0.5 rounded">展示・気配重視型</button>
            <button onclick="setWeightPreset(180,90,110,100)" class="bg-sky-950 text-sky-300 px-2 py-0.5 rounded">コース実績重視型</button>
            <button onclick="setWeightPreset(80,150,130,190)" class="bg-rose-950 text-rose-300 px-2 py-0.5 rounded">スリット・穴展開重視型</button>
          </div>
        </div>
        <div class="grid grid-cols-1 sm:grid-cols-4 gap-3 text-xs">
          <div class="bg-slate-950/70 p-2.5 rounded border border-slate-800">
            <div class="flex justify-between mb-1"><span>① コース別実績・逃がし比重</span><span id="lbl_wCourse" class="font-mono font-bold text-sky-300">100%</span></div>
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
      </section>

      <div class="grid grid-cols-1 lg:grid-cols-12 gap-4">
        <!-- 左カラム (7 cols): 環境設定・進入設定・6艇カード -->
        <section class="lg:col-span-7 space-y-3">
          <!-- ① 環境＆グレードフィルター -->
          <div class="bg-slate-900 border border-slate-800 rounded-xl p-3 space-y-2">
            <div class="flex flex-wrap items-center justify-between gap-1 border-b border-slate-800 pb-1">
              <h2 class="text-xs font-bold text-sky-400">① レースグレード・開催日ウェイト ＆ 水面環境フィルター</h2>
              <span id="venueTraitBadge" class="text-[11px] bg-slate-800 text-amber-300 px-2 py-0.5 rounded"></span>
            </div>
            <div class="grid grid-cols-2 sm:grid-cols-7 gap-2 text-xs">
              <div>
                <label class="block text-slate-400 text-[10px]">レース場(24場)</label>
                <select id="venueSelect" onchange="onVenueChange()" class="w-full font-bold">
                  <option value="01">01 桐生</option><option value="02">02 戸田</option><option value="03">03 江戸川</option>
                  <option value="04" selected>04 平和島</option><option value="05">05 多摩川</option><option value="06">06 浜名湖</option>
                  <option value="07">07 蒲郡</option><option value="08">08 常滑</option><option value="09">09 津</option>
                  <option value="10">10 三国</option><option value="11">11 びわこ</option><option value="12">12 住之江</option>
                  <option value="13">13 尼崎</option><option value="14">14 鳴門</option><option value="15">15 丸亀</option>
                  <option value="16">16 児島</option><option value="17">17 宮島</option><option value="18">18 徳山</option>
                  <option value="19">19 下関</option><option value="20">20 若松</option><option value="21">21 芦屋</option>
                  <option value="22">22 福岡</option><option value="23">23 唐津</option><option value="24">24 大村</option>
                </select>
              </div>
              <div>
                <label class="block text-slate-400 text-[10px]">レース番号</label>
                <select id="raceNoSelect" onchange="runSimulation()" class="w-full font-bold text-amber-300">
                  <option value="1">1R</option><option value="2">2R</option><option value="3">3R</option><option value="4">4R</option>
                  <option value="5">5R</option><option value="6">6R</option><option value="7">7R</option><option value="8">8R</option>
                  <option value="9">9R</option><option value="10">10R</option><option value="11">11R</option><option value="12" selected>12R</option>
                </select>
              </div>
              <div>
                <label class="block text-amber-300 font-bold text-[10px]">🏆グレード(G1以上切替)</label>
                <select id="raceGradeSelect" onchange="onGradeChange()" class="w-full font-bold border-amber-500/60 text-amber-200">
                  <option value="ippan">一般戦 / G3</option>
                  <option value="G2">G2</option>
                  <option value="G1" selected>🏆 G1 (G1以上成績のみ)</option>
                  <option value="PG1">👑 PG1 (G1以上成績のみ)</option>
                  <option value="SG">🔥 SG (G1以上成績のみ)</option>
                </select>
              </div>
              <div>
                <label class="block text-slate-400 text-[10px]">開催日目</label>
                <select id="seriesDay" onchange="runSimulation()" class="w-full">
                  <option value="1">初日(通算100%)</option><option value="2">2日目(節間30%)</option>
                  <option value="3">3日目(節間55%)</option><option value="4">4日目(節間65%)</option>
                  <option value="5">5日目(節間75%)</option><option value="6" selected>最終日(節間85%)</option>
                </select>
              </div>
              <div>
                <label class="block text-slate-400 text-[10px]">風向</label>
                <select id="windDir" onchange="runSimulation()" class="w-full">
                  <option value="none">無風</option><option value="head" selected>向かい風(ダッシュ◎)</option>
                  <option value="tail">追い風(イン/差◎)</option><option value="cross">横風</option>
                </select>
              </div>
              <div>
                <label class="block text-slate-400 text-[10px]">風速(m)/波高(cm)</label>
                <div class="flex gap-1">
                  <input type="number" id="windSpeed" value="4" min="0" max="15" onchange="runSimulation()" class="w-1/2" title="風速(m)" />
                  <input type="number" id="waveHeight" value="3" min="0" max="30" onchange="runSimulation()" class="w-1/2" title="波高(cm)" />
                </div>
              </div>
              <div>
                <label class="block text-slate-400 text-[10px]">潮回り・干満</label>
                <select id="tideLevel" onchange="runSimulation()" class="w-full">
                  <option value="low" selected>干潮(まくり◎)</option><option value="mid">平潮/淡水</option><option value="high">満潮(イン/差◎)</option>
                </select>
              </div>
            </div>
            <div id="g1RuleNoticeBar" class="bg-amber-950/60 border border-amber-500/40 rounded-lg px-2.5 py-1 text-[11px] text-amber-200 flex items-center justify-between">
              <span>🏆 <strong>G1以上限定成績モード有効：</strong>一般戦・G3でのB級相手の勝率・コース実績を除外し、<strong>G1以上の記念成績（G1勝率・G1コース1着/3連対率・G1平均ST）のみ</strong>を適用しています。</span>
            </div>
          </div>

          <!-- ② 進入＆カド設定 -->
          <div class="bg-slate-900 border border-slate-800 rounded-xl p-3 space-y-2">
            <div class="flex flex-wrap items-center justify-between gap-1 border-b border-slate-800 pb-1">
              <h2 class="text-xs font-bold text-rose-400">② 進入コース変化 ＆ カド設定</h2>
              <div class="flex flex-wrap gap-1 text-[11px]">
                <button onclick="setCoursePreset([1,2,3,4,5,6], 4, 'normal')" class="bg-slate-800 hover:bg-slate-700 px-2 py-0.5 rounded">枠なり(4カド)</button>
                <button onclick="setCoursePreset([1,2,3,4,5,6], 3, 'normal')" class="bg-rose-950 text-rose-300 border border-rose-700/50 px-2 py-0.5 rounded">3カド(12/3456)</button>
                <button onclick="setCoursePreset([1,2,3,4,5,6], 5, 'normal')" class="bg-slate-800 hover:bg-slate-700 px-2 py-0.5 rounded">5カド(1234/56)</button>
                <button onclick="setCoursePreset([1,6,2,3,4,5], 4, 'deep')" class="bg-amber-950 text-amber-300 border border-amber-700/50 px-2 py-0.5 rounded">6前付け深イン</button>
              </div>
            </div>
            <div class="grid grid-cols-6 gap-1 text-center text-xs" id="courseSelectGrid"></div>
            <div class="grid grid-cols-2 gap-2 pt-1 text-xs">
              <div class="flex items-center justify-between bg-slate-950/60 px-2 py-1 rounded border border-slate-800">
                <span class="text-slate-400 text-[11px]">カド位置</span>
                <select id="kadoCourse" onchange="runSimulation()" class="font-bold text-rose-400">
                  <option value="3" selected>3コース(3カド)</option><option value="4">4コース(標準4カド)</option>
                  <option value="5">5コース(5カド)</option><option value="6">6コース(6カド)</option><option value="7">オールスロー</option>
                </select>
              </div>
              <div class="flex items-center justify-between bg-slate-950/60 px-2 py-1 rounded border border-slate-800">
                <span class="text-slate-400 text-[11px]">イン起こし深さ</span>
                <select id="deepInLevel" onchange="runSimulation()">
                  <option value="normal" selected>通常(150m〜)</option><option value="semi">やや深い(120m)</option><option value="deep">深イン(100m以内)</option>
                </select>
              </div>
            </div>
          </div>

          <!-- ③ 6艇カード -->
          <div class="space-y-2" id="boatCardsContainer"></div>
        </section>

        <!-- 右カラム (5 cols): スリット図・決まり手確率・長文2パターン展開レポート・スコア・2パターン3連単＆EV・note/X出力 -->
        <section class="lg:col-span-5 space-y-3">
          <!-- スリット隊形＆1M攻防矢印マップ + 決まり手確率バー -->
          <div class="bg-slate-900 border border-slate-800 rounded-xl p-3 space-y-3">
            <div>
              <div class="flex items-center justify-between mb-1.5">
                <h2 class="text-xs font-bold text-emerald-400">📊 想定スリット隊形 ＆ 1M攻め手マップ</h2>
                <span class="text-[10px] text-slate-400">赤破線＝カド境界 / 右青線＝スリット(0.00)</span>
              </div>
              <div class="bg-slate-950 border border-slate-800 rounded-lg p-2 relative overflow-hidden">
                <div class="absolute right-10 top-0 bottom-0 w-0.5 bg-sky-400 shadow-[0_0_8px_#38bdf8] z-10"></div>
                <div class="absolute right-11 top-1 text-[9px] text-sky-300 font-bold">START</div>
                <div id="slitLanes"></div>
              </div>
            </div>

            <!-- 1着決まり手＆2パターン確率バーチャート -->
            <div class="pt-2 border-t border-slate-800 space-y-2">
              <div class="flex items-center justify-between">
                <span class="text-[11px] font-bold text-slate-300">1マーク決まり手 予測バランス（差し・展開待ち対応）</span>
                <span id="kimariteTopTag" class="text-[10px] font-bold text-sky-400">解析中</span>
              </div>
              <div id="kimariteBarsBox" class="grid grid-cols-2 sm:grid-cols-3 gap-2 text-[11px]"></div>
            </div>
          </div>

          <!-- 総合算出スコア表 -->
          <div class="bg-slate-900 border border-slate-800 rounded-xl p-3">
            <div class="flex items-center justify-between mb-1.5">
              <h2 class="text-xs font-bold text-amber-400">📈 総合算出スコア（1着アタマ力 vs 2・3着連対力）</h2>
              <span id="scoreModeBadge" class="text-[10px] bg-amber-950 text-amber-300 border border-amber-700/50 px-1.5 py-0.5 rounded">G1以上成績基準</span>
            </div>
            <table class="w-full text-xs text-left">
              <thead class="text-[10px] text-slate-400 border-b border-slate-800">
                <tr>
                  <th class="py-1">進入</th>
                  <th class="py-1">艇・選手名</th>
                  <th class="py-1 text-right">展示/想定ST</th>
                  <th class="py-1 text-right">1着点</th>
                  <th class="py-1 text-right">2・3着点</th>
                  <th class="py-1 text-center">1M攻め手・役割</th>
                </tr>
              </thead>
              <tbody id="scoreTableBody" class="divide-y divide-slate-800/60"></tbody>
            </table>
          </div>

          <!-- 長文・詳細版 1マーク展開＆2パターン徹底診断レポート -->
          <div class="bg-slate-900 border border-slate-800 rounded-xl p-3 space-y-2">
            <div class="flex items-center justify-between">
              <h2 class="text-xs font-bold text-purple-400">🧠 プロ展開予想 詳細長文レポート（イン逃げ vs イン逃げ以外 2パターン診断）</h2>
              <span id="scenarioTag" class="text-[10px] font-bold bg-purple-950 text-purple-300 border border-purple-700/50 px-2 py-0.5 rounded">解析中</span>
            </div>
            <div id="aiNarrativeBox" class="text-xs leading-relaxed text-slate-200 bg-slate-950/90 border border-slate-800 rounded-lg p-3 space-y-2.5 max-h-[420px] overflow-y-auto"></div>
          </div>

          <!-- 推奨3連単＆EVチェッカー（イン逃げパターン ＆ イン逃げ以外パターン 2系統対応） -->
          <div class="bg-slate-900 border border-slate-800 rounded-xl p-3 space-y-2.5">
            <div class="flex flex-wrap items-center justify-between gap-2">
              <div>
                <h2 class="text-xs font-bold text-sky-400">🎯 2パターン推奨3連単買い目（イン逃げ vs イン逃げ以外）＆ 期待値(EV)・資金配分</h2>
                <span class="text-[10px] text-slate-400">パターン表示切替・点数・予算連動 ／ オッズ入力で回収期待値(EV)をリアルタイム判定</span>
              </div>
              <div class="flex flex-wrap items-center gap-1.5 text-xs">
                <select id="patternFilterSelect" onchange="runSimulation()" class="font-bold text-sky-300">
                  <option value="both" selected>🔄 2パターン同時(イン逃げ＋非イン)</option>
                  <option value="in_only">🟦 パターンA(イン逃げ)のみ</option>
                  <option value="non_in_only">🟥 パターンB(イン逃げ以外)のみ</option>
                </select>
                <select id="ticketCountSelect" onchange="runSimulation()" class="font-bold text-amber-300">
                  <option value="4">厳選 4点</option>
                  <option value="6">推奨 6点</option>
                  <option value="8" selected>2パターン標準 8点</option>
                  <option value="12">広め 12点</option>
                </select>
                <input type="number" id="budgetInput" value="4000" step="100" min="400" onchange="runSimulation()" class="w-16 text-right font-mono text-amber-300" title="総軍資金(円)" />
                <button onclick="copyBetsList()" class="bg-sky-600 hover:bg-sky-500 text-white font-bold px-2 py-1 rounded text-[11px]">買い目コピー</button>
              </div>
            </div>
            <div id="copyBetsToast" class="hidden text-[11px] text-emerald-300 bg-emerald-950/70 border border-emerald-700/50 rounded px-2 py-1">
              推奨買い目と配分金額をコピーしました！
            </div>
            <div id="recommendationsContainer" class="space-y-2"></div>
          </div>

          <!-- 💰 収益化・note有料記事 / X集客ポスト そのままコピペ用レポート -->
          <div class="bg-slate-900 border-2 border-amber-500/40 rounded-xl p-3 space-y-2">
            <div class="flex flex-wrap items-center justify-between gap-2">
              <div>
                <h2 class="text-xs font-bold text-amber-300">💰 収益化・配信用レポート出力（note有料販売 / X集客ポスト / 全文）</h2>
                <span class="text-[10px] text-slate-400">noteの「無料公開エリア」と「🔒有料ライン以降」を自動分割してワンタップコピー可能</span>
              </div>
              <div class="flex flex-wrap items-center gap-1.5 text-xs">
                <select id="reportFormatSelect" onchange="runSimulation()" class="font-bold text-amber-200 border-amber-500/50">
                  <option value="note_paywall" selected>💰 note有料販売用(無料＋🔒有料分割)</option>
                  <option value="x_promo">📣 X(旧Twitter)先出し集客・誘導用</option>
                  <option value="full_report">📝 全文一括レポート(サロン/自分用)</option>
                </select>
                <button onclick="copyNotePart('free')" class="bg-slate-800 hover:bg-slate-700 text-sky-300 border border-sky-600/40 font-bold px-2 py-1 rounded text-[11px]" title="無料公開パートのみコピー">
                  無料部コピー
                </button>
                <button onclick="copyNotePart('paid')" class="bg-slate-800 hover:bg-slate-700 text-rose-300 border border-rose-600/40 font-bold px-2 py-1 rounded text-[11px]" title="有料パートのみコピー">
                  🔒有料部コピー
                </button>
                <button onclick="copyNoteReport()" class="bg-amber-500 hover:bg-amber-400 text-slate-950 font-black px-2.5 py-1 rounded text-[11px] shadow">
                  全文コピー
                </button>
              </div>
            </div>
            <div id="copyNoteToast" class="hidden text-[11px] text-emerald-300 bg-emerald-950/70 border border-emerald-700/50 rounded px-2 py-1">
              レポートをクリップボードにコピーしました！
            </div>
            <textarea id="noteReportTextarea" rows="18" readonly class="w-full bg-slate-950 border border-slate-800 rounded-lg p-2.5 text-[11px] font-mono text-slate-200 leading-relaxed focus:outline-none"></textarea>
          </div>
        </section>
      </div>
    </main>

    <script>
      const INITIAL_SERVER_DATA = __INJECTED_SERVER_DATA__;

      const VENUE_MASTER = {
        "01": { name: "桐生", inMod: -3, makuriMod: 5, sashiMod: 2, desc: "標高高く出足重視・カドまくり決まりやすい" },
        "02": { name: "戸田", inMod: -8, makuriMod: 10, sashiMod: -2, desc: "日本一インが弱い狭水面・センターまくり激増" },
        "03": { name: "江戸川", inMod: -9, makuriMod: 7, sashiMod: 4, desc: "潮流と波・当地勝率と波乗り巧者が絶対" },
        "04": { name: "平和島", inMod: -6, makuriMod: 6, sashiMod: 5, desc: "イン受難・3カドやセンター攻めからの差し・展開待ち連動多発" },
        "05": { name: "多摩川", inMod: -1, makuriMod: 4, sashiMod: 2, desc: "日本一の静水面・スピード戦とモーター素性直結" },
        "06": { name: "浜名湖", inMod: -2, makuriMod: 5, sashiMod: 4, desc: "広大な汽水・まくり差しと展示直線タイムが直結" },
        "07": { name: "蒲郡", inMod: 3, makuriMod: 2, sashiMod: 3, desc: "ナイター広水面・イン安定も4カドまくり差し一撃あり" },
        "08": { name: "常滑", inMod: 2, makuriMod: 3, sashiMod: 2, desc: "伊勢湾の風・向かい風時はダッシュ勢が台頭" },
        "09": { name: "津", inMod: 3, makuriMod: 2, sashiMod: 2, desc: "1Mホーム側広くイン優位も季節風で変化" },
        "10": { name: "三国", inMod: -1, makuriMod: 4, sashiMod: 3, desc: "ホーム幅広・2コース差しと3コース攻めが多い" },
        "11": { name: "びわこ", inMod: -2, makuriMod: 4, sashiMod: 5, desc: "うねり発生・出足と回り足重視で展開待ち中間着穴が出やすい" },
        "12": { name: "住之江", inMod: 4, makuriMod: 1, sashiMod: 3, desc: "硬い水質・イン強く2コース差しとターンマーク際勝負" },
        "13": { name: "尼崎", inMod: 3, makuriMod: 2, sashiMod: 3, desc: "静水面でセオリー通り・センターまくり差しが決まる" },
        "14": { name: "鳴門", inMod: -5, makuriMod: 7, sashiMod: 4, desc: "狭い水面・イン受難でアウトからの展開待ち絡みが多い" },
        "15": { name: "丸亀", inMod: 2, makuriMod: 3, sashiMod: 3, desc: "潮位差大・干潮はまくり、満潮はインと差し" },
        "16": { name: "児島", inMod: 1, makuriMod: 4, sashiMod: 2, desc: "干満差3m・ダッシュスタートの絞りが決まりやすい" },
        "17": { name: "宮島", inMod: 1, makuriMod: 4, sashiMod: 2, desc: "潮位変化激しい・スタート勘と節間STが鍵" },
        "18": { name: "徳山", inMod: 7, makuriMod: -3, sashiMod: 2, desc: "屈指のイン天国・イン逃げからのヒモ探し水面" },
        "19": { name: "下関", inMod: 5, makuriMod: 0, sashiMod: 2, desc: "ナイター海水・イン強く順当決着が多い" },
        "20": { name: "若松", inMod: 3, makuriMod: 2, sashiMod: 3, desc: "潮と風の影響・2コース差しと3コースまくり差し" },
        "21": { name: "芦屋", inMod: 6, makuriMod: 0, sashiMod: 1, desc: "イン勝率トップクラス・展示一番時計の信頼度大" },
        "22": { name: "福岡", inMod: -4, makuriMod: 5, sashiMod: 6, desc: "独自のうねり・2コース差しと3コースまくりが多発" },
        "23": { name: "唐津", inMod: 2, makuriMod: 3, sashiMod: 2, desc: "ピット離れとスタ展重視・インとセンター勢の攻防" },
        "24": { name: "大村", inMod: 9, makuriMod: -5, sashiMod: 2, desc: "日本一のイン絶対水面・逃がし2/3着率でヒモを絞る場" }
      };

      let boatsData = {};
      let allDetailsOpen = false;
      let latestReportParts = { free: "", paid: "", full: "" };

      function isG1ModeActive() {
        const grade = document.getElementById("raceGradeSelect")?.value || "ippan";
        const g1RuleChk = document.getElementById("f_g1OnlyRule")?.checked ?? true;
        return g1RuleChk && ["G1", "PG1", "SG"].includes(grade);
      }

      function computeEstimatedG1Fields(b, id) {
        const winRate = Number(b.winRate || 5.5);
        const localWin = Number(b.localWin || winRate);
        const triRate = Number(b.triRate || 50.0);
        const avgSt = Number(b.avgSt || 0.16);
        const grade = b.grade || "A1";
        const gf = grade === "A1" ? 0.92 : grade === "A2" ? 0.80 : 0.70;
        let g1Win = 5.0;
        if (winRate >= 7.5) g1Win = Math.max(5.2, (winRate - 7.0) * 1.15 + 6.45) * (grade === "A1" ? 1.0 : 0.88);
        else if (winRate >= 6.5) g1Win = Math.max(4.6, (winRate - 6.5) * 1.10 + 5.35) * (gf / 0.92);
        else g1Win = Math.max(3.8, winRate * 0.78 * gf);
        g1Win = Math.round(g1Win * 100) / 100;
        const g1Local = Math.round(Math.max(3.8, g1Win + (localWin - winRate) * 0.75) * 100) / 100;
        const ratio = Math.max(0.45, Math.min(1.45, g1Win / 6.3));
        const map1st = { 1: 62.0, 2: 16.5, 3: 15.0, 4: 13.5, 5: 7.5, 6: 3.5 };
        const g1CWin = Math.round(Math.min(88.0, Math.max(1.5, (map1st[id] || 10) * ratio)) * 10) / 10;
        const g1CTri = Math.round(Math.min(90.0, Math.max(15.0, triRate * 0.86 + (4 - id) * 4.2)) * 10) / 10;
        const g1St = Math.round(Math.max(0.09, Math.min(0.22, avgSt - (grade === "A1" ? 0.01 : 0.0))) * 100) / 100;
        return { g1WinRate: g1Win, g1LocalWin: g1Local, g1CourseWin: g1CWin, g1CourseTri: g1CTri, g1AvgSt: g1St };
      }

      function getActiveFactors() {
        const chk = (id) => document.getElementById(id)?.checked ?? true;
        return {
          winRate: chk("f_winRate"),
          localWin: chk("f_localWin"),
          g1OnlyRule: chk("f_g1OnlyRule"),
          seriesScore: chk("f_seriesScore"),
          weight: chk("f_weight"),
          courseWin: chk("f_courseWin"),
          courseTri: chk("f_courseTri"),
          nigashi: chk("f_nigashi"),
          nigashiTri: chk("f_nigashiTri"),
          motorBi: chk("f_motorBi"),
          exTimeRank: chk("f_exTimeRank"),
          oriTimeRank: chk("f_oriTimeRank"),
          vis: chk("f_vis"),
          partsTilt: chk("f_partsTilt"),
          avgSt: chk("f_avgSt"),
          seriesSt: chk("f_seriesSt"),
          fCount: chk("f_fCount"),
          env: chk("f_env")
        };
      }

      function getCategoryWeights() {
        const wc = Number(document.getElementById("w_course")?.value ?? 100) / 100;
        const we = Number(document.getElementById("w_exhibit")?.value ?? 100) / 100;
        const wm = Number(document.getElementById("w_motor")?.value ?? 100) / 100;
        const ws = Number(document.getElementById("w_slit")?.value ?? 100) / 100;
        if (document.getElementById("lbl_wCourse")) document.getElementById("lbl_wCourse").textContent = `${Math.round(wc*100)}%`;
        if (document.getElementById("lbl_wEx")) document.getElementById("lbl_wEx").textContent = `${Math.round(we*100)}%`;
        if (document.getElementById("lbl_wMotor")) document.getElementById("lbl_wMotor").textContent = `${Math.round(wm*100)}%`;
        if (document.getElementById("lbl_wSlit")) document.getElementById("lbl_wSlit").textContent = `${Math.round(ws*100)}%`;
        return { wc, we, wm, ws };
      }

      function setWeightPreset(c, e, m, s) {
        document.getElementById("w_course").value = c;
        document.getElementById("w_exhibit").value = e;
        document.getElementById("w_motor").value = m;
        document.getElementById("w_slit").value = s;
        runSimulation();
      }

      function setFactorPreset(mode) {
        const ids = [
          "f_winRate", "f_localWin", "f_g1OnlyRule", "f_seriesScore", "f_weight",
          "f_courseWin", "f_courseTri", "f_nigashi", "f_nigashiTri",
          "f_motorBi", "f_exTimeRank", "f_oriTimeRank", "f_vis", "f_partsTilt",
          "f_avgSt", "f_seriesSt", "f_fCount", "f_env"
        ];
        ids.forEach(id => {
          const el = document.getElementById(id);
          if (!el) return;
          if (mode === "all") el.checked = true;
          else if (mode === "chokuzen") {
            el.checked = ["f_exTimeRank", "f_oriTimeRank", "f_vis", "f_partsTilt", "f_seriesSt", "f_env", "f_courseWin", "f_g1OnlyRule"].includes(id);
          } else if (mode === "jizen") {
            el.checked = !["f_exTimeRank", "f_oriTimeRank", "f_vis"].includes(id);
          } else if (mode === "nomotor") {
            el.checked = id !== "f_motorBi";
          }
        });
        runSimulation();
      }

      function toggleAllDetails() {
        allDetailsOpen = !allDetailsOpen;
        for (let b = 1; b <= 6; b++) {
          const el = document.getElementById(`detail_${b}`);
          if (el) {
            if (allDetailsOpen) el.classList.remove("hidden");
            else el.classList.add("hidden");
          }
        }
      }

      function initCourseSelectors() {
        const grid = document.getElementById("courseSelectGrid");
        grid.innerHTML = "";
        for (let c = 1; c <= 6; c++) {
          let opts = "";
          for (let b = 1; b <= 6; b++) {
            opts += `<option value="${b}" ${b === c ? "selected" : ""}>${b}号艇</option>`;
          }
          grid.innerHTML += `
          <div>
            <span class="text-[10px] text-slate-400 block">${c}コース</span>
            <select id="course_${c}" onchange="runSimulation()" class="w-full font-bold text-center">${opts}</select>
          </div>`;
        }
      }

      function loadHeiwajimaPreset() {
        document.getElementById("venueSelect").value = "04";
        document.getElementById("raceGradeSelect").value = "G1";
        document.getElementById("seriesDay").value = "6";
        document.getElementById("windDir").value = "head";
        document.getElementById("windSpeed").value = 4;
        document.getElementById("waveHeight").value = 3;
        document.getElementById("tideLevel").value = "low";

        boatsData = {
          1: { id: 1, name: "白井 英治", grade: "A1", fCount: 0, weight: 52.0, winRate: 8.12, biRate: 64.5, triRate: 78.0, localWin: 8.35, g1WinRate: 7.72, g1LocalWin: 7.90, g1CourseWin: 76.5, g1CourseTri: 88.0, g1AvgSt: 0.11, motorBi: 46.2, motorTri: 63.5, avgSt: 0.12, seriesSt: 0.11, seriesScore: 92, courseWin: 82.0, courseTri: 91.0, nigashi: 0, nigashiTri: 0, parts: "none", tilt: -0.5, exTime: 6.75, exTimeRank: 2, oriTimeRank: 1, visSlit: 1, visTurn: 2, manualTactic: "auto" },
          2: { id: 2, name: "瓜生 正義", grade: "A1", fCount: 0, weight: 52.0, winRate: 7.58, biRate: 56.0, triRate: 72.0, localWin: 7.8, g1WinRate: 7.12, g1LocalWin: 7.28, g1CourseWin: 19.5, g1CourseTri: 64.5, g1AvgSt: 0.13, motorBi: 41.0, motorTri: 58.0, avgSt: 0.14, seriesSt: 0.14, seriesScore: 84, courseWin: 22.0, courseTri: 68.0, nigashi: 62.5, nigashiTri: 64.0, parts: "none", tilt: -0.5, exTime: 6.79, exTimeRank: 3, oriTimeRank: 2, visSlit: 0, visTurn: 1, manualTactic: "auto" },
          3: { id: 3, name: "澤田 尚也", grade: "A1", fCount: 1, weight: 52.0, winRate: 7.15, biRate: 53.0, triRate: 70.5, localWin: 7.1, g1WinRate: 6.45, g1LocalWin: 6.40, g1CourseWin: 20.0, g1CourseTri: 60.0, g1AvgSt: 0.13, motorBi: 44.5, motorTri: 61.0, avgSt: 0.13, seriesSt: 0.13, seriesScore: 82, courseWin: 24.0, courseTri: 65.0, nigashi: 0, nigashiTri: 58.0, parts: "none", tilt: 0.0, exTime: 6.71, exTimeRank: 1, oriTimeRank: 3, visSlit: 2, visTurn: 0, manualTactic: "auto" },
          4: { id: 4, name: "大峯 豊", grade: "A1", fCount: 0, weight: 52.0, winRate: 7.24, biRate: 55.2, triRate: 73.0, localWin: 7.45, g1WinRate: 6.68, g1LocalWin: 6.84, g1CourseWin: 17.5, g1CourseTri: 70.0, g1AvgSt: 0.13, motorBi: 48.0, motorTri: 66.0, avgSt: 0.14, seriesSt: 0.13, seriesScore: 89, courseWin: 19.5, courseTri: 74.0, nigashi: 0, nigashiTri: 79.2, parts: "ring", tilt: -0.5, exTime: 6.75, exTimeRank: 2, oriTimeRank: 1, visSlit: 1, visTurn: 2, manualTactic: "auto" },
          5: { id: 5, name: "篠崎 仁志", grade: "A1", fCount: 0, weight: 52.0, winRate: 7.4, biRate: 54.0, triRate: 69.0, localWin: 7.3, g1WinRate: 6.90, g1LocalWin: 6.82, g1CourseWin: 10.5, g1CourseTri: 55.0, g1AvgSt: 0.13, motorBi: 39.5, motorTri: 55.0, avgSt: 0.14, seriesSt: 0.15, seriesScore: 78, courseWin: 12.0, courseTri: 58.0, nigashi: 0, nigashiTri: 56.0, parts: "none", tilt: -0.5, exTime: 6.80, exTimeRank: 3, oriTimeRank: 3, visSlit: 0, visTurn: 1, manualTactic: "auto" },
          6: { id: 6, name: "吉田 裕平", grade: "A1", fCount: 0, weight: 52.0, winRate: 7.05, biRate: 51.5, triRate: 67.0, localWin: 6.95, g1WinRate: 6.32, g1LocalWin: 6.24, g1CourseWin: 5.0, g1CourseTri: 42.0, g1AvgSt: 0.13, motorBi: 38.0, motorTri: 54.0, avgSt: 0.13, seriesSt: 0.14, seriesScore: 76, courseWin: 6.0, courseTri: 46.0, nigashi: 0, nigashiTri: 45.0, parts: "none", tilt: -0.5, exTime: 6.82, exTimeRank: 3, oriTimeRank: 3, visSlit: 0, visTurn: 0, manualTactic: "auto" }
        };

        setCoursePreset([1, 2, 3, 4, 5, 6], 3, "normal");
        onVenueChange();
        renderBoatCards();
        runSimulation();
      }

      function applyServerData(data) {
        if (!data || data.status !== "ok" || !data.boats) return false;
        if (data.meta?.jcd) document.getElementById("venueSelect").value = data.meta.jcd;
        if (data.meta?.rno) document.getElementById("raceNoSelect").value = String(data.meta.rno);
        if (data.meta?.raceGrade) {
          const gVal = ["SG", "PG1", "G1", "G2"].includes(data.meta.raceGrade) ? data.meta.raceGrade : "ippan";
          document.getElementById("raceGradeSelect").value = gVal;
        }
        for (let b = 1; b <= 6; b++) {
          const incoming = data.boats[String(b)] || data.boats[b];
          if (incoming) {
            const estG1 = computeEstimatedG1Fields(incoming, b);
            boatsData[b] = {
              ...(boatsData[b] || {}),
              ...estG1,
              ...incoming,
              id: b,
              exTime: incoming.exTime || 6.80,
              tilt: incoming.tilt !== null && incoming.tilt !== undefined ? incoming.tilt : -0.5,
              exTimeRank: incoming.exTimeRank || 3,
              oriTimeRank: incoming.oriTimeRank || 0,
              visSlit: incoming.visSlit || 0,
              visTurn: incoming.visTurn || 0,
              manualTactic: incoming.manualTactic || "auto"
            };
          }
        }
        if (Array.isArray(data.courseOrder) && data.courseOrder.length === 6) {
          for (let c = 1; c <= 6; c++) {
            const sel = document.getElementById(`course_${c}`);
            if (sel) sel.value = data.courseOrder[c - 1];
          }
        }
        if (Number.isFinite(data.env?.windSpeed)) document.getElementById("windSpeed").value = data.env.windSpeed;
        if (Number.isFinite(data.env?.wave)) document.getElementById("waveHeight").value = data.env.wave;
        const names = [1,2,3,4,5,6].map(i => `${i}.${boatsData[i].name}`).join(" / ");
        const gLabel = data.meta?.raceGrade ? `[${data.meta.raceGrade}] ` : "";
        document.getElementById("fetchStatus").textContent = `✅ 公式反映済 ${gLabel}：${names}`;
        onVenueChange();
        renderBoatCards();
        runSimulation();
        return true;
      }

      function recalculateExRanksFromTime() {
        const sorted = Object.values(boatsData).slice().sort((a, b) => (a.exTime || 6.80) - (b.exTime || 6.80));
        sorted.forEach((b, idx) => {
          const r = idx + 1;
          boatsData[b.id].exTimeRank = r === 1 ? 1 : r === 2 ? 2 : r <= 4 ? 3 : 5;
        });
      }

      function resetAllTactics() {
        for (let b = 1; b <= 6; b++) {
          boatsData[b].manualTactic = "auto";
        }
        renderBoatCards();
        runSimulation();
      }

      function onGradeChange() {
        renderBoatCards();
        runSimulation();
      }

      function onVenueChange() {
        const vCode = document.getElementById("venueSelect").value;
        const v = VENUE_MASTER[vCode] || VENUE_MASTER["04"];
        document.getElementById("venueTraitBadge").textContent = `${v.name}：${v.desc}`;
        runSimulation();
      }

      function setCoursePreset(orderArr, kadoCourseVal, deepInVal) {
        for (let c = 1; c <= 6; c++) {
          document.getElementById(`course_${c}`).value = orderArr[c - 1];
        }
        document.getElementById("kadoCourse").value = kadoCourseVal;
        document.getElementById("deepInLevel").value = deepInVal;
        runSimulation();
      }

      function renderBoatCards() {
        const container = document.getElementById("boatCardsContainer");
        const g1Active = isG1ModeActive();
        const expandedDetails = new Set(
          Array.from(container.querySelectorAll('[id^="detail_"]'))
            .filter((detail) => !detail.classList.contains("hidden"))
            .map((detail) => detail.id)
        );
        container.innerHTML = "";
        for (let b = 1; b <= 6; b++) {
          const d = boatsData[b];
          const exRankLabel = d.exTimeRank === 1 ? "🥇展1位" : d.exTimeRank === 2 ? "🥈展2位" : d.exTimeRank === 5 ? "展劣" : "展中";
          const exBadgeCls = d.exTimeRank === 1 ? "bg-amber-500/20 text-amber-300 border border-amber-500/40 font-bold" : "bg-slate-800 text-slate-300";
          const activeWinDisp = g1Active ? `🏆G1勝率 ${(d.g1WinRate || 6.0).toFixed(2)}` : `全国 ${(d.winRate || 5.5).toFixed(2)}`;
          const card = document.createElement("div");
          card.className = "bg-slate-900 border border-slate-800 rounded-xl overflow-hidden";
          card.innerHTML = `
          <div class="p-2.5 flex flex-wrap items-center justify-between gap-2">
            <div class="flex items-center gap-1.5">
              <span class="boat-${b} w-6 h-6 rounded font-black text-xs flex items-center justify-center">${b}</span>
              <input type="text" value="${d.name}" onchange="updateBoat(${b},'name',this.value)" class="bg-slate-950 px-1.5 py-0.5 rounded border border-slate-700 font-bold text-xs text-white w-28 focus:outline-none" />
              <select onchange="updateBoat(${b},'grade',this.value)" class="text-[11px] font-bold">
                <option value="A1" ${d.grade === "A1" ? "selected" : ""}>A1</option><option value="A2" ${d.grade === "A2" ? "selected" : ""}>A2</option>
                <option value="B1" ${d.grade === "B1" ? "selected" : ""}>B1</option><option value="B2" ${d.grade === "B2" ? "selected" : ""}>B2</option>
              </select>
              <select onchange="updateBoat(${b},'fCount',Number(this.value))" class="text-[11px] ${d.fCount > 0 ? "text-rose-400 font-bold" : ""}">
                <option value="0" ${d.fCount === 0 ? "selected" : ""}>F0</option><option value="1" ${d.fCount === 1 ? "selected" : ""}>F1</option><option value="2" ${d.fCount === 2 ? "selected" : ""}>F2</option>
              </select>
              <span class="text-[10px] font-mono px-1.5 py-0.5 rounded ${g1Active ? "bg-amber-950 text-amber-300 border border-amber-600/40 font-bold" : "bg-slate-800 text-sky-300"}">${activeWinDisp}</span>
              <span class="text-[10px] font-mono px-1.5 py-0.5 rounded ${exBadgeCls}">${(d.exTime || 6.80).toFixed(2)}s (${exRankLabel})</span>
            </div>
            <div class="flex flex-wrap items-center gap-1 text-[11px]">
              <span class="text-pink-400 font-bold">🎯1M攻め</span>
              <select onchange="updateBoat(${b},'manualTactic',this.value)" class="${d.manualTactic !== "auto" ? "tactic-select" : ""}">
                <option value="auto" ${d.manualTactic === "auto" ? "selected" : ""}>🤖AI自動判定</option>
                <option value="nige" ${d.manualTactic === "nige" ? "selected" : ""}>🛡️逃げ(先マイ)</option>
                <option value="sashi" ${d.manualTactic === "sashi" ? "selected" : ""}>📐差し(1M差し)</option>
                <option value="makuri" ${d.manualTactic === "makuri" ? "selected" : ""}>🔥まくり(絞り攻め)</option>
                <option value="makurisashi" ${d.manualTactic === "makurisashi" ? "selected" : ""}>⚡まくり差し</option>
                <option value="tenkaimachi" ${d.manualTactic === "tenkaimachi" ? "selected" : ""}>⏳展開待ち(差し連動)</option>
                <option value="sotomai" ${d.manualTactic === "sotomai" ? "selected" : ""}>🌀外マイ(握りマイ)</option>
                <option value="hekomi" ${d.manualTactic === "hekomi" ? "selected" : ""}>⚠️凹み・壁崩壊</option>
              </select>
              <span class="text-slate-400 ml-1">チルト</span>
              <select onchange="updateBoat(${b},'tilt',parseFloat(this.value))">
                <option value="-0.5" ${d.tilt === -0.5 ? "selected" : ""}>-0.5</option><option value="0" ${d.tilt === 0 ? "selected" : ""}>0.0</option>
                <option value="0.5" ${d.tilt === 0.5 ? "selected" : ""}>+0.5</option><option value="1.5" ${d.tilt === 1.5 ? "selected" : ""}>+1.5</option><option value="3.0" ${d.tilt === 3.0 ? "selected" : ""}>+3.0</option>
              </select>
              <span class="text-slate-400">気配</span>
              <select onchange="updateBoat(${b},'visTurn',Number(this.value))">
                <option value="2" ${d.visTurn === 2 ? "selected" : ""}>★超抜</option><option value="1" ${d.visTurn === 1 ? "selected" : ""}>◎良</option>
                <option value="0" ${d.visTurn === 0 ? "selected" : ""}>□普通</option><option value="-1" ${d.visTurn === -1 ? "selected" : ""}>▲重め</option>
              </select>
              <button onclick="document.getElementById('detail_${b}').classList.toggle('hidden')" class="bg-slate-800 hover:bg-slate-700 text-slate-300 px-2 py-0.5 rounded">詳細▼</button>
            </div>
          </div>
          <div id="detail_${b}" class="${expandedDetails.has(`detail_${b}`) || allDetailsOpen ? "" : "hidden"} border-t border-slate-800 bg-slate-950/60 p-2.5 grid grid-cols-2 sm:grid-cols-4 gap-2 text-[11px]">
            <div><span class="text-slate-400 block">通算 全国勝率 / 当地勝率</span><div class="flex gap-1 mt-0.5"><input type="number" step="0.01" value="${d.winRate}" onchange="updateBoat(${b},'winRate',parseFloat(this.value))" class="w-1/2"/><input type="number" step="0.01" value="${d.localWin}" onchange="updateBoat(${b},'localWin',parseFloat(this.value))" class="w-1/2"/></div></div>
            <div class="bg-amber-950/30 p-1 rounded border border-amber-600/30"><span class="text-amber-300 font-bold block">🏆G1限定 勝率 / 当地</span><div class="flex gap-1 mt-0.5"><input type="number" step="0.01" value="${d.g1WinRate || 6.0}" onchange="updateBoat(${b},'g1WinRate',parseFloat(this.value))" class="w-1/2 text-amber-200 font-bold"/><input type="number" step="0.01" value="${d.g1LocalWin || 6.0}" onchange="updateBoat(${b},'g1LocalWin',parseFloat(this.value))" class="w-1/2 text-amber-200 font-bold"/></div></div>
            <div><span class="text-slate-400 block">通算 コース1着/3連率(%)</span><div class="flex gap-1 mt-0.5"><input type="number" step="0.1" value="${d.courseWin}" onchange="updateBoat(${b},'courseWin',parseFloat(this.value))" class="w-1/2"/><input type="number" step="0.1" value="${d.courseTri}" onchange="updateBoat(${b},'courseTri',parseFloat(this.value))" class="w-1/2"/></div></div>
            <div class="bg-amber-950/30 p-1 rounded border border-amber-600/30"><span class="text-amber-300 font-bold block">🏆G1コース1着/3連率(%)</span><div class="flex gap-1 mt-0.5"><input type="number" step="0.1" value="${d.g1CourseWin || d.courseWin}" onchange="updateBoat(${b},'g1CourseWin',parseFloat(this.value))" class="w-1/2 text-amber-200 font-bold"/><input type="number" step="0.1" value="${d.g1CourseTri || d.courseTri}" onchange="updateBoat(${b},'g1CourseTri',parseFloat(this.value))" class="w-1/2 text-amber-200 font-bold"/></div></div>
            <div><span class="text-slate-400 block">モーター2連/3連(%)</span><div class="flex gap-1 mt-0.5"><input type="number" step="0.1" value="${d.motorBi}" onchange="updateBoat(${b},'motorBi',parseFloat(this.value))" class="w-1/2"/><input type="number" step="0.1" value="${d.motorTri}" onchange="updateBoat(${b},'motorTri',parseFloat(this.value))" class="w-1/2"/></div></div>
            <div><span class="text-slate-400 block">通算ST / G1限定ST / 展ST</span><div class="flex gap-1 mt-0.5"><input type="number" step="0.01" value="${d.avgSt}" onchange="updateBoat(${b},'avgSt',parseFloat(this.value))" class="w-1/3" title="通算ST"/><input type="number" step="0.01" value="${d.g1AvgSt || d.avgSt}" onchange="updateBoat(${b},'g1AvgSt',parseFloat(this.value))" class="w-1/3 text-amber-200 font-bold" title="G1限定ST"/><input type="number" step="0.01" value="${d.seriesSt}" onchange="updateBoat(${b},'seriesSt',parseFloat(this.value))" class="w-1/3" title="今節/展示ST"/></div></div>
            <div><span class="text-slate-400 block">節間点(30-100)/体重/逃がし</span><div class="flex gap-1 mt-0.5"><input type="number" value="${d.seriesScore}" onchange="updateBoat(${b},'seriesScore',parseFloat(this.value))" class="w-1/3"/><input type="number" step="0.5" value="${d.weight}" onchange="updateBoat(${b},'weight',parseFloat(this.value))" class="w-1/3"/><input type="number" step="0.1" value="${d.nigashi}" onchange="updateBoat(${b},'nigashi',parseFloat(this.value))" class="w-1/3" title="2C逃がし率"/></div></div>
            <div><span class="text-slate-400 block">展示時計(秒)/順位/オリ展/伸/部品</span><div class="flex gap-1 mt-0.5">
              <input type="number" step="0.01" value="${(d.exTime || 6.80).toFixed(2)}" onchange="updateBoat(${b},'exTime',parseFloat(this.value))" class="w-1/4 font-mono text-amber-300" />
              <select onchange="updateBoat(${b},'exTimeRank',Number(this.value))" class="w-1/4"><option value="1" ${d.exTimeRank === 1 ? "selected" : ""}>展1位</option><option value="2" ${d.exTimeRank === 2 ? "selected" : ""}>展2位</option><option value="3" ${d.exTimeRank === 3 ? "selected" : ""}>展普</option><option value="5" ${d.exTimeRank === 5 ? "selected" : ""}>展劣</option></select>
              <select onchange="updateBoat(${b},'oriTimeRank',Number(this.value))" class="w-1/4"><option value="0" ${d.oriTimeRank === 0 ? "selected" : ""}>オ未</option><option value="1" ${d.oriTimeRank === 1 ? "selected" : ""}>オ1位</option><option value="2" ${d.oriTimeRank === 2 ? "selected" : ""}>オ上</option><option value="3" ${d.oriTimeRank === 3 ? "selected" : ""}>オ普</option><option value="5" ${d.oriTimeRank === 5 ? "selected" : ""}>オ劣</option></select>
              <select onchange="updateBoat(${b},'parts',this.value)" class="w-1/4"><option value="none" ${d.parts === "none" ? "selected" : ""}>部品無</option><option value="ring" ${d.parts === "ring" ? "selected" : ""}>リング◎</option><option value="elec" ${d.parts === "elec" ? "selected" : ""}>電気</option><option value="body" ${d.parts === "body" ? "selected" : ""}>ボデー</option><option value="shaft" ${d.parts === "shaft" ? "selected" : ""}>シャフト×</option></select>
            </div></div>
          </div>`;
          container.appendChild(card);
        }
      }

      function updateBoat(b, key, val) {
        boatsData[b][key] = val;
        if (key === "exTime") recalculateExRanksFromTime();
        if (["manualTactic", "exTime", "exTimeRank", "g1WinRate", "winRate", "grade"].includes(key)) renderBoatCards();
        runSimulation();
      }

      function runSimulation() {
        if (!boatsData[1]) return;
        const af = getActiveFactors();
        const cw = getCategoryWeights();
        const vCode = document.getElementById("venueSelect").value;
        const venue = VENUE_MASTER[vCode] || VENUE_MASTER["04"];
        const raceNo = document.getElementById("raceNoSelect")?.value || "12";
        const raceGrade = document.getElementById("raceGradeSelect")?.value || "ippan";
        const g1Active = isG1ModeActive();

        const g1HeaderBadge = document.getElementById("g1ActiveHeaderBadge");
        const g1NoticeBar = document.getElementById("g1RuleNoticeBar");
        const scoreModeBadge = document.getElementById("scoreModeBadge");
        if (g1Active) {
          g1HeaderBadge?.classList.remove("hidden");
          g1NoticeBar?.classList.remove("hidden");
          if (scoreModeBadge) {
            scoreModeBadge.textContent = `🏆 ${raceGrade}：G1以上限定成績のみ適用`;
            scoreModeBadge.className = "text-[10px] bg-amber-500 text-slate-950 font-black px-2 py-0.5 rounded";
          }
        } else {
          g1HeaderBadge?.classList.add("hidden");
          g1NoticeBar?.classList.add("hidden");
          if (scoreModeBadge) {
            scoreModeBadge.textContent = `${raceGrade === "ippan" ? "一般/G3" : raceGrade}：通算成績適用`;
            scoreModeBadge.className = "text-[10px] bg-slate-800 text-slate-300 px-2 py-0.5 rounded";
          }
        }

        const day = Number(document.getElementById("seriesDay").value);
        const windDir = document.getElementById("windDir").value;
        const windSpeed = Number(document.getElementById("windSpeed").value);
        const wave = Number(document.getElementById("waveHeight").value);
        const tide = document.getElementById("tideLevel").value;
        const kadoCourse = Number(document.getElementById("kadoCourse").value);
        const deepIn = document.getElementById("deepInLevel").value;

        const rawWSeries = { 1: 0.0, 2: 0.3, 3: 0.55, 4: 0.65, 5: 0.75, 6: 0.85 }[day] ?? 0.5;
        const wSeries = af.seriesScore ? rawWSeries : 0.0;
        const wBase = 1.0 - wSeries;

        const courseOrder = [];
        for (let c = 1; c <= 6; c++) {
          courseOrder.push(Number(document.getElementById(`course_${c}`).value));
        }

        const courseEval = {};
        courseOrder.forEach((boatId, idx) => {
          const courseNo = idx + 1;
          const b = boatsData[boatId];
          const isDash = courseNo >= kadoCourse;
          const isKado = courseNo === kadoCourse;

          const effWinRate = g1Active ? (b.g1WinRate ?? b.winRate) : b.winRate;
          const effLocalWin = g1Active ? (b.g1LocalWin ?? b.localWin) : b.localWin;
          const effCourseWin = g1Active ? (b.g1CourseWin ?? b.courseWin) : b.courseWin;
          const effCourseTri = g1Active ? (b.g1CourseTri ?? b.courseTri) : b.courseTri;
          const effAvgSt = g1Active ? (b.g1AvgSt ?? b.avgSt) : b.avgSt;

          const winTerm = af.winRate ? (effWinRate * 8.5 * cw.wm) : 50.0;
          const localTerm = af.localWin ? ((effLocalWin - effWinRate) * 14.0 * cw.wm) : 0.0;
          const motorTerm = af.motorBi ? (b.motorBi * 0.65 * cw.wm) : 22.0;
          const baseSkill = winTerm + localTerm + motorTerm;

          const adjSeries = af.partsTilt && b.parts === "ring" && b.seriesScore < 75 ? 78 : b.seriesScore;
          const blendedPower = baseSkill * wBase + adjSeries * wSeries;
          const weightBonus = af.weight ? ((52.0 - b.weight) * 3.2 * cw.wm) : 0.0;
          const partsBonus = af.partsTilt
            ? ((b.parts === "ring" ? 5 : b.parts === "elec" ? 4 : b.parts === "body" ? 3 : b.parts === "shaft" ? -15 : 0) * cw.we)
            : 0;

          const exRankScore = af.exTimeRank ? ((b.exTimeRank === 1 ? 8 : b.exTimeRank === 2 ? 4 : b.exTimeRank === 5 ? -6 : 0) * cw.we) : 0;
          const oriRankScore = af.oriTimeRank ? ((b.oriTimeRank === 1 ? 11 : b.oriTimeRank === 2 ? 6 : b.oriTimeRank === 5 ? -7 : 0) * cw.we) : 0;
          const visScore = af.vis ? ((b.visSlit * 5.5 + b.visTurn * 6.5) * cw.we) : 0;
          const totalExBonus = exRankScore + oriRankScore + visScore;

          let baseSt = 0.15;
          if (af.avgSt && af.seriesSt) baseSt = effAvgSt * wBase + b.seriesSt * wSeries;
          else if (af.seriesSt) baseSt = b.seriesSt;
          else if (af.avgSt) baseSt = effAvgSt;

          if (af.fCount) {
            if (b.fCount === 1) baseSt += 0.022;
            if (b.fCount >= 2) baseSt += 0.05;
            if (courseNo === 1 && deepIn === "semi") baseSt += 0.012;
            if (courseNo === 1 && deepIn === "deep") baseSt += 0.028;
          }
          if (isKado) baseSt -= 0.012;

          if (b.manualTactic === "makuri") baseSt -= 0.025;
          if (b.manualTactic === "makurisashi") baseSt -= 0.015;
          if (b.manualTactic === "sashi") baseSt -= 0.005;
          if (b.manualTactic === "tenkaimachi") baseSt += 0.005;
          if (b.manualTactic === "hekomi") baseSt += 0.045;

          let slitPower =
            50 +
            (0.17 - baseSt) * 380 * cw.ws +
            (af.vis ? b.visSlit * 7 * cw.we : 0) +
            (af.partsTilt && b.tilt >= 0.0 ? (b.tilt + 0.5) * 8 * cw.we : 0);
          if (isDash) slitPower += 6;
          if (isKado) slitPower += 8;
          if (af.env && windDir === "head" && windSpeed >= 3) {
            slitPower += isDash ? windSpeed * 1.6 : -windSpeed * 1.2;
          }

          const cWinBonus = af.courseWin ? (effCourseWin * 0.45 * cw.wc) : ([65, 18, 15, 13, 7, 3][courseNo - 1] * 0.45);
          const cTriBonus = af.courseTri ? (effCourseTri * 0.55 * cw.wc) : ([75, 55, 52, 48, 38, 25][courseNo - 1] * 0.55);

          courseEval[courseNo] = {
            courseNo,
            boatId,
            b,
            effWinRate,
            effLocalWin,
            effCourseWin,
            effCourseTri,
            effAvgSt,
            isDash,
            isKado,
            expectedSt: Math.max(0.04, Math.min(0.28, baseSt)),
            slitPower,
            firstScore: blendedPower + weightBonus + partsBonus + totalExBonus + cWinBonus,
            placeScore: blendedPower + weightBonus + partsBonus + totalExBonus + cTriBonus + (af.vis ? b.visTurn * 5 * cw.we : 0),
            roleText: "標準",
            attackType: "auto"
          };
        });

        const vInMod = af.env ? venue.inMod : 0;
        const vMakuriMod = af.env ? venue.makuriMod : 0;
        const vSashiMod = af.env ? venue.sashiMod : 0;

        courseEval[1].firstScore += (g1Active ? 23 : 28) + vInMod;
        if (af.fCount) {
          if (deepIn === "semi") courseEval[1].firstScore -= 8;
          if (deepIn === "deep") courseEval[1].firstScore -= 18;
        }
        if (af.env) {
          if (tide === "high") courseEval[1].firstScore += 5;
          if (tide === "low") courseEval[1].firstScore -= 4;
          if (windDir === "tail" && windSpeed >= 3) {
            courseEval[2].firstScore += (5 + vSashiMod) * cw.ws;
            courseEval[2].placeScore += 6 * cw.ws;
          }
        }

        const c2Boat = courseEval[2].b;
        if (af.nigashi) {
          courseEval[1].firstScore += (c2Boat.nigashi - 52.0) * 0.45 * cw.wc - (af.fCount ? c2Boat.fCount * 9 : 0);
        }

        let kadoMakuriTrigger = false;
        if (kadoCourse >= 3 && kadoCourse <= 6) {
          const kadoObj = courseEval[kadoCourse];
          const receiverObj = courseEval[kadoCourse - 1];
          if (kadoObj.slitPower - receiverObj.slitPower >= 11 && kadoObj.b.manualTactic === "auto") {
            kadoMakuriTrigger = true;
            const fPen = (af.fCount && kadoObj.b.fCount > 0) ? 0.55 : 1.0;
            kadoObj.firstScore += (16 + vMakuriMod) * fPen * cw.ws;
            kadoObj.roleText = kadoObj.b.fCount > 0 ? "🔥カド攻(F持)" : "🔥カドまくり";
            kadoObj.attackType = "makuri";
            receiverObj.firstScore -= 12 * cw.ws;
            receiverObj.placeScore -= 10 * cw.ws;
            receiverObj.roleText = "⚠️壁崩壊・被弾";
            receiverObj.attackType = "hekomi";

            if (courseEval[kadoCourse + 1]) {
              const outerObj = courseEval[kadoCourse + 1];
              outerObj.firstScore += (12 + vSashiMod) * cw.ws;
              outerObj.placeScore += (22 + (af.nigashiTri ? outerObj.b.nigashiTri * 0.22 : 10) + (af.vis ? outerObj.b.visTurn * 6 : 0)) * cw.ws;
              outerObj.roleText = "⚡まくり差し連動";
              outerObj.attackType = "makurisashi";
            }
            if (courseEval[kadoCourse + 2]) {
              const waitObj = courseEval[kadoCourse + 2];
              waitObj.firstScore += (7 + vSashiMod * 0.6) * cw.ws;
              waitObj.placeScore += 18 * cw.ws;
              waitObj.roleText = "⏳展開待ち浮上";
              waitObj.attackType = "tenkaimachi";
            }
          }
        }

        const manualNotes = [];
        let hasActiveMakuri = kadoMakuriTrigger;
        for (let c = 1; c <= 6; c++) {
          if (["makuri", "hekomi"].includes(courseEval[c].b.manualTactic)) hasActiveMakuri = true;
        }

        for (let c = 1; c <= 6; c++) {
          const obj = courseEval[c];
          const tac = obj.b.manualTactic;
          if (tac === "auto") continue;
          obj.attackType = tac;

          if (tac === "nige") {
            obj.firstScore += 32 * cw.ws;
            obj.placeScore += 15 * cw.ws;
            obj.roleText = "🎯指定:逃げ";
            manualNotes.push(`${c}コース(${obj.boatId}号艇・${obj.b.name})の【逃げ(先マイ)】を指定`);
          } else if (tac === "sashi") {
            obj.firstScore += (22 + vSashiMod) * cw.ws;
            obj.placeScore += 28 * cw.ws;
            obj.roleText = "🎯指定:1M差し";
            manualNotes.push(`${c}コース(${obj.boatId}号艇・${obj.b.name})の【1M差し】を指定 → ターンマーク際を鋭く差し抜け`);
            if (courseEval[1] && c >= 2) {
              courseEval[1].placeScore += 12 * cw.ws;
            }
          } else if (tac === "makuri") {
            obj.firstScore += (36 + vMakuriMod) * cw.ws;
            obj.placeScore += 16 * cw.ws;
            obj.roleText = "🎯指定:まくり";
            manualNotes.push(`${c}コース(${obj.boatId}号艇・${obj.b.name})の【まくり】を指定 → 内枠被弾＆${c < 6 ? c + 1 + "コース以下が展開連動" : "外連動"}`);
            for (let inner = 1; inner < c; inner++) {
              courseEval[inner].firstScore -= (inner === c - 1 ? 22 : 16) * cw.ws;
              courseEval[inner].placeScore -= (inner === c - 1 ? 16 : 10) * cw.ws;
              if (courseEval[inner].b.manualTactic === "auto") {
                courseEval[inner].roleText = "⚠️被弾・引き波";
                courseEval[inner].attackType = "hekomi";
              }
            }
            if (courseEval[c + 1] && courseEval[c + 1].b.manualTactic === "auto") {
              courseEval[c + 1].firstScore += (15 + vSashiMod) * cw.ws;
              courseEval[c + 1].placeScore += 28 * cw.ws;
              courseEval[c + 1].roleText = "⚡まくり差し連動";
              courseEval[c + 1].attackType = "makurisashi";
            }
            if (courseEval[c + 2] && courseEval[c + 2].b.manualTactic === "auto") {
              courseEval[c + 2].firstScore += (8 + vSashiMod) * cw.ws;
              courseEval[c + 2].placeScore += 20 * cw.ws;
              courseEval[c + 2].roleText = "⏳展開待ち浮上";
              courseEval[c + 2].attackType = "tenkaimachi";
            }
          } else if (tac === "makurisashi") {
            obj.firstScore += (28 + vSashiMod) * cw.ws;
            obj.placeScore += 26 * cw.ws;
            obj.roleText = "🎯指定:まくり差";
            manualNotes.push(`${c}コース(${obj.boatId}号艇・${obj.b.name})の【まくり差し】を指定`);
            if (courseEval[c - 1] && c > 2) {
              courseEval[c - 1].firstScore -= 12 * cw.ws;
              courseEval[c - 1].placeScore -= 8 * cw.ws;
            }
            if (courseEval[1] && courseEval[1].b.manualTactic === "auto") courseEval[1].placeScore += 10;
          } else if (tac === "tenkaimachi") {
            const clashBoost = hasActiveMakuri ? 14 : 6;
            obj.firstScore += (12 + vSashiMod + clashBoost) * cw.ws;
            obj.placeScore += (32 + clashBoost * 0.8) * cw.ws;
            obj.roleText = "🎯指定:展開待ち";
            manualNotes.push(`${c}コース(${obj.boatId}号艇・${obj.b.name})の【展開待ち(最内・連動差し)】を指定 → 1Mもつれ・引き波を突いて上位浮上`);
          } else if (tac === "sotomai") {
            obj.firstScore += 8 * cw.ws;
            obj.placeScore += 24 * cw.ws;
            obj.roleText = "🎯指定:外マイ";
            manualNotes.push(`${c}コース(${obj.boatId}号艇・${obj.b.name})の【外マイ追走】を指定`);
          } else if (tac === "hekomi") {
            obj.firstScore -= 30 * cw.ws;
            obj.placeScore -= 25 * cw.ws;
            obj.roleText = "🎯指定:凹み壁崩壊";
            manualNotes.push(`${c}コース(${obj.boatId}号艇・${obj.b.name})の【壁崩壊】を指定 → ${c < 6 ? c + 1 + "コース攻め発動" : ""}`);
            if (courseEval[c + 1] && courseEval[c + 1].b.manualTactic === "auto") {
              courseEval[c + 1].firstScore += (24 + vMakuriMod) * cw.ws;
              courseEval[c + 1].placeScore += 15 * cw.ws;
              courseEval[c + 1].roleText = "🔥壁崩壊まくり";
              courseEval[c + 1].attackType = "makuri";
              if (courseEval[c + 2] && courseEval[c + 2].b.manualTactic === "auto") {
                courseEval[c + 2].placeScore += 22 * cw.ws;
                courseEval[c + 2].roleText = "⏳展開待ち連動";
                courseEval[c + 2].attackType = "tenkaimachi";
              }
            }
          }
        }

        for (let c = 1; c <= 6; c++) {
          const obj = courseEval[c];
          if (c >= 2) {
            if (af.nigashiTri) obj.placeScore += (obj.b.nigashiTri - 50.0) * 0.42 * cw.wc;
            if (af.env && af.partsTilt && (wave >= 5 || tide === "high") && obj.b.tilt >= 0.5) {
              obj.firstScore -= 12;
              obj.placeScore -= 10;
            }
          }
          if (obj.roleText === "標準") {
            if (c === 1) {
              obj.roleText = "🛡️イン先マイ";
              obj.attackType = "nige";
            } else if (c === 2) {
              obj.roleText = "📐2C差し追走";
              obj.attackType = "sashi";
            } else if (c === 3) {
              if (obj.slitPower >= courseEval[2].slitPower + 5) {
                obj.roleText = obj.b.visTurn >= 1 ? "⚡3Cまくり差し" : "🌀3C外マイ攻め";
                obj.attackType = obj.b.visTurn >= 1 ? "makurisashi" : "sotomai";
              } else {
                obj.roleText = "📐3C差し・連動";
                obj.attackType = "sashi";
              }
            } else if (c === 4) {
              if (obj.isKado && obj.slitPower >= 56) {
                obj.roleText = "⚡4カドまくり差";
                obj.attackType = "makurisashi";
              } else {
                obj.roleText = "📐4C差し・展開待";
                obj.attackType = "sashi";
              }
            } else if (c === 5) {
              obj.roleText = "⏳5C展開待ち差";
              obj.attackType = "tenkaimachi";
            } else if (c === 6) {
              obj.roleText = "⏳6C最内展開待ち";
              obj.attackType = "tenkaimachi";
            }
          }
        }

        renderSlitMap(courseEval, kadoCourse);
        const kimariteStats = renderKimariteBars(courseEval);
        renderScoreTable(courseEval);
        generateNarrativeAndBets(
          courseEval,
          venue,
          raceNo,
          raceGrade,
          g1Active,
          windDir,
          windSpeed,
          wave,
          tide,
          kadoCourse,
          deepIn,
          kadoMakuriTrigger,
          manualNotes,
          kimariteStats
        );
      }

      function renderSlitMap(courseEval, kadoCourse) {
        const container = document.getElementById("slitLanes");
        container.innerHTML = "";
        for (let c = 1; c <= 6; c++) {
          const obj = courseEval[c];
          const leftPct = Math.max(14, Math.min(72, 38 + (obj.slitPower - 55) * 0.80));
          const displayName = (obj.b.name || `${obj.boatId}号艇`).replace(/\s+/g, "");
          let arrowBadge = "";
          if (obj.attackType === "makuri") {
            arrowBadge = `<span class="text-[10px] text-rose-400 font-bold ml-1">⤴まくり</span>`;
          } else if (obj.attackType === "makurisashi") {
            arrowBadge = `<span class="text-[10px] text-amber-300 font-bold ml-1">⚡まくり差し</span>`;
          } else if (obj.attackType === "sashi") {
            arrowBadge = `<span class="text-[10px] text-emerald-400 font-bold ml-1">📐差し</span>`;
          } else if (obj.attackType === "tenkaimachi") {
            arrowBadge = `<span class="text-[10px] text-purple-300 font-bold ml-1">⏳展開待ち</span>`;
          } else if (obj.attackType === "sotomai") {
            arrowBadge = `<span class="text-[10px] text-cyan-300 font-bold ml-1">🌀外マイ</span>`;
          } else if (obj.attackType === "hekomi") {
            arrowBadge = `<span class="text-[10px] text-slate-400 font-bold ml-1">⚠️被弾/凹</span>`;
          } else if (c === 1) {
            arrowBadge = `<span class="text-[10px] text-sky-400 font-bold ml-1">➡先マイ</span>`;
          }
          container.innerHTML += `
          <div class="slit-lane ${c === kadoCourse ? "kado-line" : ""}">
            <span class="text-[10px] text-slate-400 w-14 pl-1 font-mono">${c}C ${c >= kadoCourse ? "🔥ダ" : "ス"}</span>
            <div style="left:${leftPct}%;" class="absolute flex items-center gap-1.5 transition-all duration-200">
              <span class="boat-${obj.boatId} px-2 py-0.5 rounded text-xs font-black shadow">${obj.boatId}</span>
              <span class="text-[11px] font-bold text-white whitespace-nowrap">${displayName} <span class="font-mono text-sky-300">(.${Math.round(obj.expectedSt * 100).toString().padStart(2, "0")})</span>${arrowBadge}</span>
            </div>
          </div>`;
        }
      }

      function renderKimariteBars(courseEval) {
        const arr = Object.values(courseEval);
        const nigeW = Math.max(8, courseEval[1].firstScore * (courseEval[1].attackType === "hekomi" ? 0.45 : 1.0));
        const sashiW = Math.max(6, arr.filter(x => x.courseNo >= 2).reduce((s, x) => s + (x.attackType === "sashi" ? x.firstScore * 0.52 : x.placeScore * 0.16), 0));
        const makuriW = Math.max(6, arr.filter(x => x.courseNo >= 3).reduce((s, x) => s + (x.attackType === "makuri" ? x.firstScore * 0.68 : x.firstScore * 0.18), 0));
        const msW = Math.max(6, arr.filter(x => x.courseNo >= 3).reduce((s, x) => s + (x.attackType === "makurisashi" ? x.firstScore * 0.62 : x.placeScore * 0.18), 0));
        const waitW = Math.max(5, arr.filter(x => x.courseNo >= 3).reduce((s, x) => s + (x.attackType === "tenkaimachi" ? x.firstScore * 0.48 : x.placeScore * 0.12), 0));
        const sum = nigeW + sashiW + makuriW + msW + waitW;

        const items = [
          { key: "nige", label: "🛡️逃げ(1C)", pct: Math.round((nigeW / sum) * 100), cls: "bg-sky-400" },
          { key: "sashi", label: "📐差し", pct: Math.round((sashiW / sum) * 100), cls: "bg-emerald-400" },
          { key: "makuri", label: "🔥まくり", pct: Math.round((makuriW / sum) * 100), cls: "bg-rose-500" },
          { key: "makurisashi", label: "⚡まくり差し", pct: Math.round((msW / sum) * 100), cls: "bg-amber-400" },
          { key: "tenkaimachi", label: "⏳展開待ち・抜", pct: Math.max(3, 100 - Math.round((nigeW / sum) * 100) - Math.round((sashiW / sum) * 100) - Math.round((makuriW / sum) * 100) - Math.round((msW / sum) * 100)), cls: "bg-purple-400" }
        ];
        const inEscapePct = items[0].pct;
        const nonInPct = 100 - inEscapePct;
        document.getElementById("kimariteTopTag").textContent = `🟦イン逃げ ${inEscapePct}% ／ 🟥イン以外 ${nonInPct}%`;
        document.getElementById("kimariteBarsBox").innerHTML = items.map(k => `
          <div class="bg-slate-950/60 px-2 py-1 rounded border border-slate-800/80">
            <div class="flex justify-between text-[10px] mb-0.5"><span class="text-slate-300">${k.label}</span><span class="font-bold text-white">${k.pct}%</span></div>
            <div class="w-full h-1.5 bg-slate-800 rounded-full overflow-hidden"><div class="h-full ${k.cls}" style="width:${k.pct}%"></div></div>
          </div>
        `).join("");
        return { items, inEscapePct, nonInPct };
      }

      function renderScoreTable(courseEval) {
        const tbody = document.getElementById("scoreTableBody");
        tbody.innerHTML = "";
        for (let c = 1; c <= 6; c++) {
          const obj = courseEval[c];
          const isManual = obj.b.manualTactic !== "auto";
          const exStr = (obj.b.exTime || 6.80).toFixed(2);
          tbody.innerHTML += `
          <tr>
            <td class="py-1 font-bold text-slate-400">${c}C</td>
            <td class="py-1 flex items-center gap-1.5"><span class="boat-${obj.boatId} w-5 h-5 rounded text-[11px] font-black flex items-center justify-center">${obj.boatId}</span><span class="font-bold text-white">${obj.b.name}</span></td>
            <td class="py-1 text-right font-mono text-sky-300">${exStr}s / .${Math.round(obj.expectedSt * 100).toString().padStart(2, "0")}</td>
            <td class="py-1 text-right font-bold text-amber-300">${obj.firstScore.toFixed(1)}</td>
            <td class="py-1 text-right font-bold text-emerald-300">${obj.placeScore.toFixed(1)}</td>
            <td class="py-1 text-center"><span class="text-[10px] px-1.5 py-0.5 rounded ${isManual ? "bg-pink-900 text-pink-200 font-bold" : "bg-slate-800 text-slate-200"}">${obj.roleText}</span></td>
          </tr>`;
        }
      }

      function generateNarrativeAndBets(
        courseEval,
        venue,
        raceNo,
        raceGrade,
        g1Active,
        windDir,
        windSpeed,
        wave,
        tide,
        kadoCourse,
        deepIn,
        kadoMakuriTrigger,
        manualNotes,
        kimariteStats
      ) {
        const arr = Object.values(courseEval);
        const inObj = courseEval[1];
        const c2Obj = courseEval[2];
        const kadoObj = courseEval[kadoCourse] || courseEval[4];

        const inFollowers = arr
          .filter(x => x.courseNo !== 1)
          .map(x => {
            let s = x.placeScore;
            if (x.courseNo === 2 && x.attackType !== "hekomi") s += 10;
            if (x.courseNo === 3 && ["sotomai", "makurisashi", "sashi"].includes(x.attackType)) s += 8;
            if (x.attackType === "sashi") s += 7;
            if (x.attackType === "tenkaimachi") s += 6;
            return { ...x, inFollowScore: s };
          })
          .sort((a, b) => b.inFollowScore - a.inFollowScore);

        const inP1 = inFollowers[0], inP2 = inFollowers[1], inP3 = inFollowers[2], inP4 = inFollowers[3];

        const nonInWinners = arr
          .filter(x => x.courseNo !== 1)
          .map(x => {
            let s = x.firstScore;
            if (x.attackType === "makuri") s += 14;
            if (x.attackType === "makurisashi") s += 12;
            if (x.attackType === "sashi") s += 10;
            if (x.attackType === "tenkaimachi") s += 8;
            return { ...x, nonInWinScore: s };
          })
          .sort((a, b) => b.nonInWinScore - a.nonInWinScore);

        const nonIn1 = nonInWinners[0];
        const nonIn2 = nonInWinners[1];

        const nonIn1Followers = arr
          .filter(x => x.boatId !== nonIn1.boatId)
          .map(x => {
            let s = x.placeScore;
            if (nonIn1.attackType === "makuri") {
              if (x.courseNo === nonIn1.courseNo + 1) s += 22;
              if (x.courseNo === nonIn1.courseNo + 2 || x.attackType === "tenkaimachi") s += 16;
              if (x.courseNo < nonIn1.courseNo) s -= 12;
            } else if (nonIn1.attackType === "sashi" || nonIn1.attackType === "makurisashi") {
              if (x.courseNo === 1) s += 20;
              if (x.attackType === "tenkaimachi") s += 12;
            } else if (nonIn1.attackType === "tenkaimachi") {
              if (x.courseNo === 1 || x.isKado) s += 14;
            }
            return { ...x, followScore: s };
          })
          .sort((a, b) => b.followScore - a.followScore);

        const nf1 = nonIn1Followers[0], nf2 = nonIn1Followers[1], nf3 = nonIn1Followers[2];

        const nonIn2Followers = arr
          .filter(x => x.boatId !== nonIn2.boatId)
          .map(x => {
            let s = x.placeScore;
            if (x.courseNo === 1 && nonIn2.attackType !== "makuri") s += 16;
            if (x.courseNo === nonIn2.courseNo + 1 || x.attackType === "tenkaimachi") s += 15;
            return { ...x, followScore: s };
          })
          .sort((a, b) => b.followScore - a.followScore);

        const ng1 = nonIn2Followers[0], ng2 = nonIn2Followers[1];

        const exBest = [...arr].sort((a, b) => (a.b.exTime || 6.80) - (b.b.exTime || 6.80))[0];
        const motorBest = [...arr].sort((a, b) => (b.b.motorBi || 35) - (a.b.motorBi || 35))[0];
        const waitBoats = arr.filter(x => x.attackType === "tenkaimachi" || x.roleText.includes("展開待"));
        const sashiBoats = arr.filter(x => x.attackType === "sashi" || x.roleText.includes("差"));

        const windLabel = windDir === "head" ? `向かい風${windSpeed}m(ダッシュ・まくり差し優勢)` : windDir === "tail" ? `追い風${windSpeed}m(イン・差し優勢)` : windDir === "cross" ? `横風${windSpeed}m` : "無風";
        const tideLabel = tide === "low" ? "干潮(水面安定・握りマイ＆まくり有利)" : tide === "high" ? "満潮(水面上昇・イン＆小回り差し有利)" : "平潮/淡水";
        const deepLabel = deepIn === "deep" ? "深イン(100m以内・ダッシュ勢一撃注意)" : deepIn === "semi" ? "やや深め(120m付近)" : "通常起こし(150m前後)";
        const gradeDesc = g1Active
          ? `<strong>【${raceGrade}：G1以上限定成績適用】</strong> 一般戦・G3でのB級相手の勝率・コース実績を完全に除外し、記念クラス（G1/PG1/SG）同士の対決データ（1号艇${inObj.b.name}のG1勝率${inObj.effWinRate.toFixed(2)}・G1イン1着率${inObj.effCourseWin.toFixed(1)}%）を基準に算出しています。`
          : `<strong>【${raceGrade === "ippan" ? "一般戦/G3" : raceGrade}：通算成績基準】</strong> 通算勝率・コース別1着/3連対率と直前展示気配を統合して算出しています。`;

        document.getElementById("scenarioTag").textContent =
          manualNotes.length > 0
            ? "🎯 手動戦法連動 × 2パターン精密診断"
            : `🟦イン逃げ ${kimariteStats.inEscapePct}% vs 🟥非イン逆転 ${kimariteStats.nonInPct}%`;

        const sashiNames = sashiBoats.map(x => `${x.courseNo}C:${x.boatId}号艇${x.b.name}`).join("・") || `${c2Obj.courseNo}C:${c2Obj.boatId}号艇${c2Obj.b.name}`;
        const waitNames = waitBoats.map(x => `${x.courseNo}C:${x.boatId}号艇${x.b.name}`).join("・") || `${courseEval[5].boatId}号艇${courseEval[5].b.name}・${courseEval[6].boatId}号艇${courseEval[6].b.name}`;

        const longHtml = `
          <div class="space-y-1 border-b border-slate-800 pb-2">
            <div class="text-sky-400 font-bold">① 水面・気象環境 ＆ レースグレード分析</div>
            <p>${venue.name}水面（${venue.desc}）に加え、本日は<strong>${windLabel}・波高${wave}cm・${tideLabel}</strong>のコンディションです。${gradeDesc}</p>
            ${manualNotes.length > 0 ? `<p class="text-pink-300 font-bold">🎯 【手動指定の1M攻め手】 ${manualNotes.join(" ／ ")}</p>` : ""}
          </div>

          <div class="space-y-1 border-b border-slate-800 pb-2">
            <div class="text-emerald-400 font-bold">② 進入・スリット隊形 ＆ 1マークの攻め（差し・展開待ち連動）</div>
            <p>進入は<strong>[${arr.map(x => x.boatId).join("-")}]</strong>、カドは<strong>${kadoCourse}コース（${kadoObj.boatId}号艇・${kadoObj.b.name} / 想定ST .${Math.round(kadoObj.expectedSt * 100).toString().padStart(2, "0")}）</strong>、イン起こしは<strong>${deepLabel}</strong>と診断。1コース${inObj.boatId}号艇（${inObj.b.name}）の想定STは<strong>.${Math.round(inObj.expectedSt * 100).toString().padStart(2, "0")}</strong>、壁となる2コース${c2Obj.boatId}号艇（${c2Obj.b.name}）の逃がし率は<strong>${c2Obj.b.nigashi.toFixed(1)}%</strong>です。</p>
            <p>展示時計トップは<strong>${exBest.boatId}号艇・${exBest.b.name}（${exBest.b.exTime.toFixed(2)}秒）</strong>、モーター2連率最上位は<strong>${motorBest.boatId}号艇・${motorBest.b.name}（${motorBest.b.motorBi.toFixed(1)}%）</strong>。1マークの攻め手としては、ターンマーク際を鋭く狙う<strong>【📐差し勢：${sashiNames}】</strong>と、センター勢の仕掛けや1Mの引き波・もつれを冷静に見極めて最内・ブイ際を突く<strong>【⏳展開待ち勢：${waitNames}】</strong>の連対浮上が鍵を握ります。</p>
          </div>

          <div class="bg-sky-950/40 border border-sky-500/40 rounded-lg p-2.5 space-y-1">
            <div class="text-sky-300 font-bold flex items-center justify-between">
              <span>🟦 【パターンA：イン逃げ本線シナリオ】</span>
              <span class="text-[11px] bg-sky-500 text-slate-950 font-black px-2 py-0.5 rounded">成立確率 ${kimariteStats.inEscapePct}%</span>
            </div>
            <p>1コース<strong>${inObj.boatId}号艇（${inObj.b.name}）</strong>がスタート互角（想定.${Math.round(inObj.expectedSt * 100).toString().padStart(2, "0")}）から1マークを先マイして押し切る王道シナリオです。2番手争いは、${inP1.roleText}からスムーズに追走する<strong>${inP1.boatId}号艇（${inP1.b.name}）</strong>と、${inP2.roleText}で浮上する<strong>${inP2.boatId}号艇（${inP2.b.name}）</strong>が軸。3着ヒモには展開待ちから最内を拾う<strong>${inP3.boatId}号艇（${inP3.b.name}）・${inP4.boatId}号艇（${inP4.b.name}）</strong>までケアした<strong>「${inObj.boatId}-${inP1.boatId}${inP2.boatId}-${inP1.boatId}${inP2.boatId}${inP3.boatId}」</strong>が本線となります。</p>
          </div>

          <div class="bg-rose-950/40 border border-rose-500/40 rounded-lg p-2.5 space-y-1">
            <div class="text-rose-300 font-bold flex items-center justify-between">
              <span>🟥 【パターンB：イン逃げ以外（逆転・波乱）シナリオ】</span>
              <span class="text-[11px] bg-rose-500 text-white font-black px-2 py-0.5 rounded">成立確率 ${kimariteStats.nonInPct}%</span>
            </div>
            <p>インの${inObj.boatId}号艇が風・波やカド攻め、またはターン流れて敗れる非インシナリオです。逆転1着の筆頭は<strong>${nonIn1.courseNo}コース${nonIn1.boatId}号艇（${nonIn1.b.name} / ${nonIn1.roleText}）</strong>、対抗アタマは<strong>${nonIn2.courseNo}コース${nonIn2.boatId}号艇（${nonIn2.b.name} / ${nonIn2.roleText}）</strong>。${nonIn1.boatId}号艇が仕掛けた場合、1Mの引き波を超えてスジ連動する<strong>${nf1.boatId}号艇（${nf1.b.name} / ${nf1.roleText}）</strong>と、展開待ちから突き抜ける<strong>${nf2.boatId}号艇（${nf2.b.name} / ${nf2.roleText}）</strong>への<strong>「${nonIn1.boatId}-${nf1.boatId}${nf2.boatId}-${nf1.boatId}${nf2.boatId}${nf3.boatId}」</strong>および<strong>「${nonIn2.boatId}-${ng1.boatId}-${ng2.boatId}」</strong>が高配当の狙い目です。</p>
          </div>
        `;
        document.getElementById("aiNarrativeBox").innerHTML = longHtml;

        const nameOf = (id) => (boatsData[id]?.name || `${id}`).split(" ")[0];

        const patternABetsPool = [
          { pattern: "A", type: "イン本線◎", l1: inObj.boatId, l2: inP1.boatId, l3: inP2.boatId, prob: 18.0, odds: 6.8 },
          { pattern: "A", type: "イン本線○", l1: inObj.boatId, l2: inP2.boatId, l3: inP1.boatId, prob: 12.5, odds: 10.5 },
          { pattern: "A", type: "イン差し▲", l1: inObj.boatId, l2: inP1.boatId, l3: inP3.boatId, prob: 9.5, odds: 14.8 },
          { pattern: "A", type: "イン展開待★", l1: inObj.boatId, l2: inP3.boatId, l3: inP1.boatId, prob: 6.5, odds: 23.0 },
          { pattern: "A", type: "イン抑え△", l1: inObj.boatId, l2: inP2.boatId, l3: inP3.boatId, prob: 5.0, odds: 19.5 },
          { pattern: "A", type: "イン展開穴☆", l1: inObj.boatId, l2: inP1.boatId, l3: inP4.boatId, prob: 4.0, odds: 27.0 }
        ];

        const patternBBetsPool = [
          { pattern: "B", type: "非イン本線◎", l1: nonIn1.boatId, l2: nf1.boatId, l3: nf2.boatId, prob: 8.5, odds: 24.5 },
          { pattern: "B", type: "非イン連動○", l1: nonIn1.boatId, l2: nf2.boatId, l3: nf1.boatId, prob: 6.5, odds: 32.0 },
          { pattern: "B", type: "非イン展開待▲", l1: nonIn1.boatId, l2: nf1.boatId, l3: nf3.boatId, prob: 5.0, odds: 41.0 },
          { pattern: "B", type: "逆転差し★", l1: nonIn2.boatId, l2: ng1.boatId, l3: ng2.boatId, prob: 4.5, odds: 36.0 },
          { pattern: "B", type: "逆転連動△", l1: nonIn2.boatId, l2: ng2.boatId, l3: ng1.boatId, prob: 3.5, odds: 48.0 },
          { pattern: "B", type: "展開待ち大穴☆", l1: nonIn1.boatId, l2: nf3.boatId, l3: nf1.boatId, prob: 2.8, odds: 58.0 }
        ];

        const patternMode = document.getElementById("patternFilterSelect")?.value || "both";
        const ticketCount = Number(document.getElementById("ticketCountSelect")?.value || 8);
        const budget = Math.max(400, Number(document.getElementById("budgetInput")?.value || 4000));

        let selectedBets = [];
        if (patternMode === "in_only") {
          selectedBets = patternABetsPool.slice(0, Math.min(6, ticketCount));
        } else if (patternMode === "non_in_only") {
          selectedBets = patternBBetsPool.slice(0, Math.min(6, ticketCount));
        } else {
          const halfA = Math.ceil(ticketCount / 2);
          const halfB = Math.floor(ticketCount / 2);
          selectedBets = [...patternABetsPool.slice(0, halfA), ...patternBBetsPool.slice(0, halfB)];
        }

        const bets = selectedBets.map(b => ({
          ...b,
          combo: `${b.l1}-${b.l2}-${b.l3}`,
          runners: `${nameOf(b.l1)}→${nameOf(b.l2)}→${nameOf(b.l3)}`
        }));

        const totalProb = bets.reduce((s, x) => s + x.prob, 0);
        const allocs = bets.map(x => Math.max(100, Math.round(((x.prob / totalProb) * budget) / 100) * 100));
        let sumAlloc = allocs.reduce((a, b) => a + b, 0);
        let k = 0;
        while (sumAlloc !== budget && k < 100) {
          if (sumAlloc < budget) { allocs[k % allocs.length] += 100; sumAlloc += 100; }
          else if (allocs[allocs.length - 1 - (k % allocs.length)] > 100) {
            allocs[allocs.length - 1 - (k % allocs.length)] -= 100; sumAlloc -= 100;
          }
          k++;
        }

        const recBox = document.getElementById("recommendationsContainer");
        recBox.innerHTML = "";

        const renderBetGroup = (groupTitle, groupBadgeCls, itemsWithIdx) => {
          if (itemsWithIdx.length === 0) return "";
          const rowsHtml = itemsWithIdx.map(({ b, idx }) => {
            const ev = Math.round((b.prob / 100) * b.odds * 100);
            const plus = ev >= 105;
            return `
            <div class="bet-row flex flex-wrap items-center justify-between bg-slate-950 border border-slate-800 px-2.5 py-1.5 rounded-lg text-xs gap-1">
              <div class="flex items-center gap-1.5">
                <span class="text-[10px] font-bold px-1.5 py-0.5 rounded ${b.pattern === "A" ? "bg-sky-950 text-sky-300 border border-sky-700/40" : "bg-rose-950 text-rose-300 border border-rose-700/40"}">${b.type}</span>
                <span class="font-mono font-black text-sm text-white">${b.combo}</span>
                <span class="text-[10px] text-slate-300">(${b.runners})</span>
                <span class="text-[10px] text-slate-400">${b.prob}%</span>
                <span class="text-[11px] font-mono font-bold text-amber-300 ml-1">${allocs[idx].toLocaleString()}円</span>
              </div>
              <div class="flex items-center gap-1.5">
                <span class="text-[10px] text-slate-400">オッズ</span>
                <input type="number" step="0.1" value="${b.odds}" oninput="updateEv(${idx},${b.prob},this.value)" class="w-14 text-right font-mono" />
                <span id="ev_badge_${idx}" class="text-[10px] font-bold px-1.5 py-0.5 rounded ${plus ? "bg-amber-500 text-slate-950" : "bg-slate-800 text-slate-400"}">EV ${ev}%${plus ? " ★" : ""}</span>
              </div>
            </div>`;
          }).join("");

          return `
          <div class="space-y-1">
            <div class="text-[11px] font-bold ${groupBadgeCls} px-2 py-0.5 rounded">${groupTitle}</div>
            <div class="space-y-1">${rowsHtml}</div>
          </div>`;
        };

        const groupA = bets.map((b, idx) => ({ b, idx })).filter(x => x.b.pattern === "A");
        const groupB = bets.map((b, idx) => ({ b, idx })).filter(x => x.b.pattern === "B");

        recBox.innerHTML =
          renderBetGroup(`🟦 パターンA：イン逃げ予想（1コース${inObj.boatId}号艇・${inObj.b.name} 先マイ押し切り / 成立率 ${kimariteStats.inEscapePct}%）`, "bg-sky-950/80 text-sky-300 border border-sky-600/40", groupA) +
          renderBetGroup(`🟥 パターンB：イン逃げ以外予想（${nonIn1.boatId}号艇${nonIn1.b.name}・${nonIn2.boatId}号艇${nonIn2.b.name} 差し・まくり・展開待ち逆転 / 成立率 ${kimariteStats.nonInPct}%）`, "bg-rose-950/80 text-rose-300 border border-rose-600/40", groupB);

        // ---------------------------------------------------------
        // 5. 収益化・配信テンプレート出力（note有料分割 / X集客ポスト / 全文）
        // ---------------------------------------------------------
        const aCombos = groupA.map(x => `${x.b.combo} (${x.b.runners} / 推奨${allocs[x.idx]}円)`).join("\n  ・");
        const bCombos = groupB.map(x => `${x.b.combo} (${x.b.runners} / 推奨${allocs[x.idx]}円)`).join("\n  ・");
        const manualLine = manualNotes.length > 0 ? `・手動指定戦法: ${manualNotes.join(" / ")}` : `・1M攻め手判定: 差し勢[${sashiNames}] ／ 展開待ち勢[${waitNames}]`;
        const g1ReportLine = g1Active
          ? `・成績適用基準: 🏆${raceGrade}限定モード（一般戦実績を除外しG1以上の勝率・コース実績・STのみ適用）`
          : `・成績適用基準: ${raceGrade === "ippan" ? "一般戦/G3" : raceGrade} 通算＋節間ブレンド基準`;

        const freePartText = [
          `━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━`,
          `🎓 ぼーとだいがくせい｜${venue.name} ${raceNo}R 【${raceGrade === "ippan" ? "一般/G3" : raceGrade}】自作シミュレーター徹底解析`,
          `━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━`,
          `■ 1. 水面・気象環境 ＆ グレード適用基準`,
          `・水面特性: ${venue.name}（${venue.desc}）`,
          `・気象条件: ${windLabel} ／ 波高${wave}cm ／ ${tideLabel}`,
          g1ReportLine,
          ``,
          `■ 2. 進入隊形・スリット展望 ＆ 直前展示ピックアップ`,
          `・想定進入: [${arr.map(x => x.boatId).join("-")}] （${kadoCourse}コース${kadoObj.boatId}号艇・${kadoObj.b.name}がカド / イン:${deepLabel}）`,
          `・展示一番時計: ${exBest.boatId}号艇 ${exBest.b.name} (${exBest.b.exTime.toFixed(2)}秒)`,
          `・モーター2連率トップ: ${motorBest.boatId}号艇 ${motorBest.b.name} (${motorBest.b.motorBi.toFixed(1)}%)`,
          `・決まり手予測バランス: イン逃げ ${kimariteStats.inEscapePct}% vs イン逃げ以外(差し・まくり・展開待ち) ${kimariteStats.nonInPct}%`,
          manualLine,
          ``,
          `▼ ここから先の有料パートでは、`,
          `①【パターンA：イン逃げ本線】の2・3着スジ連動結論`,
          `②【パターンB：イン逃げ以外（逆転・高配当）】の1マーク差し・展開待ち浮上ルート`,
          `③ 期待値(EV)と確率に基づく【厳選3連単${bets.length}点＆推奨資金配分】を公開します！`
        ].join("\n");

        const paidPartText = [
          `■ 3. 1マークの攻防（2パターン展開シナリオ結論）`,
          `🟦【パターンA：イン逃げ本線シナリオ（推定成立率 ${kimariteStats.inEscapePct}%）】`,
          `1コース${inObj.boatId}号艇（${inObj.b.name}・想定ST .${Math.round(inObj.expectedSt * 100).toString().padStart(2, "0")}）が壁役2コース${c2Obj.boatId}号艇（逃がし率${c2Obj.b.nigashi.toFixed(1)}%）を盾に1Mを先マイ。`,
          `追走軸は${inP1.roleText}の${inP1.boatId}号艇（${inP1.b.name}）と${inP2.roleText}の${inP2.boatId}号艇（${inP2.b.name}）。3着には展開待ちから最内を突く${inP3.boatId}号艇（${inP3.b.name}）まで押さえるスジ構成。`,
          ``,
          `🟥【パターンB：イン逃げ以外・逆転波乱シナリオ（推定成立率 ${kimariteStats.nonInPct}%）】`,
          `1コースが風・波やダッシュ勢のプレッシャーで流れた場合、逆転筆頭は${nonIn1.courseNo}コース${nonIn1.boatId}号艇（${nonIn1.b.name} / ${nonIn1.roleText}）、対抗は${nonIn2.courseNo}コース${nonIn2.boatId}号艇（${nonIn2.b.name} / ${nonIn2.roleText}）。`,
          `1Mの攻めで生じる引き波の懐を「差し」「展開待ち」で突く${nf1.boatId}号艇（${nf1.b.name}）・${nf2.boatId}号艇（${nf2.b.name}）の連動舟券で高配当を狙い撃ちます。`,
          ``,
          `🎯 4. 推奨3連単買い目・資金配分（計${bets.length}点 / 総予算${budget.toLocaleString()}円）`,
          `【🟦 パターンA：イン逃げ推奨目】`,
          `  ・${aCombos || "なし（非イン特化選択中）"}`,
          `【🟥 パターンB：イン逃げ以外（逆転・穴）推奨目】`,
          `  ・${bCombos || "なし（イン逃げ特化選択中）"}`,
          `※直前オッズでEV(期待値)105%以上の目を厚めに推奨。舟券の購入は自己責任でお楽しみください。`,
          `🎓 ぼーとだいがくせい｜X: https://x.com/Boatrace__daisu ｜ note: https://note.com/boatrace__daisu`,
          `━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━`
        ].join("\n");

        const xPromoText = [
          `🎓【ぼーとだいがくせいの展開研究室】${venue.name}${raceNo}R (${raceGrade === "ippan" ? "一般" : raceGrade}) 直前解析完了🔥`,
          ``,
          `✅ 水面: ${windLabel} / 波${wave}cm`,
          `✅ 展示1番時計: ${exBest.boatId}号艇 ${exBest.b.name} (${exBest.b.exTime.toFixed(2)}s)`,
          `✅ 想定カド: ${kadoCourse}コース(${kadoObj.boatId}号艇 ${kadoObj.b.name})`,
          `📊 AI決まり手予測: イン逃げ【${kimariteStats.inEscapePct}%】 vs 非イン逆転【${kimariteStats.nonInPct}%】`,
          ``,
          `1Mの「差し」「展開待ち」連動まで計算した【イン逃げ本線】＆【非イン高配当】の2パターン結論と厳選${bets.length}点はnoteで公開中👇`,
          `https://note.com/boatrace__daisu`,
          `#ぼーとだいがくせい #ボートレース #競艇予想 #${venue.name}競艇`
        ].join("\n");

        const fullPaywallText = `${freePartText}\n\n--- 🔒 ここから先は有料エリア（noteの有料ラインをここに設定） ---\n\n${paidPartText}`;
        const fullCombinedText = `${freePartText.split("▼ ここから先の有料パートでは")[0].trim()}\n\n${paidPartText}`;

        latestReportParts = {
          free: freePartText,
          paid: paidPartText,
          full: fullCombinedText,
          paywall: fullPaywallText,
          x_promo: xPromoText
        };

        const reportFmt = document.getElementById("reportFormatSelect")?.value || "note_paywall";
        const outEl = document.getElementById("noteReportTextarea");
        if (reportFmt === "note_paywall") outEl.value = fullPaywallText;
        else if (reportFmt === "x_promo") outEl.value = xPromoText;
        else outEl.value = fullCombinedText;
      }

      function updateEv(idx, prob, oddsVal) {
        const ev = Math.round((prob / 100) * (parseFloat(oddsVal) || 0) * 100);
        const badge = document.getElementById(`ev_badge_${idx}`);
        const plus = ev >= 105;
        badge.className = `text-[10px] font-bold px-1.5 py-0.5 rounded ${plus ? "bg-amber-500 text-slate-950" : "bg-slate-800 text-slate-400"}`;
        badge.textContent = `EV ${ev}%${plus ? " ★" : ""}`;
      }

      function copyBetsList() {
        const rows = Array.from(document.querySelectorAll("#recommendationsContainer .bet-row")).map(r => r.innerText.replace(/\s+/g, " "));
        const txt = `【推奨3連単買い目（2パターン対応）】\n${rows.join("\n")}`;
        try {
          const ta = document.createElement("textarea");
          ta.value = txt; document.body.appendChild(ta); ta.select(); document.execCommand("copy"); document.body.removeChild(ta);
        } catch (e) {}
        const toast = document.getElementById("copyBetsToast");
        toast.classList.remove("hidden");
        setTimeout(() => toast.classList.add("hidden"), 2200);
      }

      function copyNotePart(partType) {
        const txt = partType === "free" ? latestReportParts.free : latestReportParts.paid;
        try {
          const ta = document.createElement("textarea");
          ta.value = txt; document.body.appendChild(ta); ta.select(); document.execCommand("copy"); document.body.removeChild(ta);
        } catch (e) {}
        const toast = document.getElementById("copyNoteToast");
        toast.textContent = partType === "free" ? "✅ noteの【無料公開パート】をコピーしました！" : "✅ noteの【🔒有料パート（結論＆買い目）】をコピーしました！";
        toast.classList.remove("hidden");
        setTimeout(() => toast.classList.add("hidden"), 2500);
      }

      function copyNoteReport() {
        const txt = document.getElementById("noteReportTextarea").value;
        try {
          const ta = document.createElement("textarea");
          ta.value = txt; document.body.appendChild(ta); ta.select(); document.execCommand("copy"); document.body.removeChild(ta);
        } catch (e) {}
        const toast = document.getElementById("copyNoteToast");
        toast.textContent = "✅ 表示中のレポート全文をクリップボードにコピーしました！";
        toast.classList.remove("hidden");
        setTimeout(() => toast.classList.add("hidden"), 2200);
      }

      function applyRawPaste() {
        const raw = (document.getElementById("rawPasteTextarea").value || "").trim();
        if (!raw) return;
        if (raw.startsWith("[") || raw.startsWith("{")) {
          try {
            const parsed = JSON.parse(raw);
            const arr = Array.isArray(parsed) ? parsed : Object.values(parsed.boats || parsed);
            arr.slice(0, 6).forEach((item, idx) => {
              const b = idx + 1;
              if (item.name) boatsData[b].name = item.name;
              if (item.grade) boatsData[b].grade = item.grade;
              if (typeof item.fCount === "number") boatsData[b].fCount = item.fCount;
              if (typeof item.weight === "number") boatsData[b].weight = item.weight;
              if (typeof item.winRate === "number") boatsData[b].winRate = item.winRate;
              if (typeof item.localWin === "number") boatsData[b].localWin = item.localWin;
              if (typeof item.motorBi === "number") boatsData[b].motorBi = item.motorBi;
              if (typeof item.exTime === "number") boatsData[b].exTime = item.exTime;
              if (typeof item.exhibitTime === "number") boatsData[b].exTime = item.exhibitTime;
              if (typeof item.avgSt === "number") boatsData[b].avgSt = item.avgSt;
              if (typeof item.seriesSt === "number") boatsData[b].seriesSt = item.seriesSt;
              Object.assign(boatsData[b], computeEstimatedG1Fields(boatsData[b], b));
            });
            recalculateExRanksFromTime();
            renderBoatCards();
            runSimulation();
            document.getElementById("pasteImportBox").classList.add("hidden");
            return;
          } catch (e) {}
        }

        const tobanMatches = [...raw.matchAll(/(\d{4})\s*\/\s*(A1|A2|B1|B2)/g)];
        if (tobanMatches.length >= 2) {
          tobanMatches.slice(0, 6).forEach((m, idx) => {
            const b = idx + 1;
            const start = m.index;
            const end = idx + 1 < tobanMatches.length ? tobanMatches[idx + 1].index : raw.length;
            const block = raw.slice(start, end).split(/スタート展示|部品交換凡例/)[0];
            boatsData[b].grade = m[2];
            const afterG = block.slice(m[0].length).replace(/^[\s\u3000.]+/, "");
            const nameLine = afterG.split(/[\n\r\t]+/)[0].trim();
            if (nameLine) {
              const cleanName = nameLine.split(/[\s\u3000]+/).slice(0, 2).join(" ");
              if (cleanName) boatsData[b].name = cleanName;
            }
            const fM = block.match(/F([0-3])/);
            if (fM) boatsData[b].fCount = parseInt(fM[1], 10);
            const wM = block.match(/(\d{2}\.\d)kg/);
            if (wM) boatsData[b].weight = parseFloat(wM[1]);
            const lSplit = block.split(/L[0-3]/);
            const afterL = lSplit.length > 1 ? lSplit.slice(1).join(" ") : block;
            const decs = [...afterL.matchAll(/\b(\d+\.\d{2})\b/g)].map(x => parseFloat(x[1]));
            if (decs.length >= 1) boatsData[b].avgSt = decs[0];
            if (decs.length >= 2) boatsData[b].winRate = decs[1];
            if (decs.length >= 5 && decs[4] > 0) boatsData[b].localWin = decs[4];
            if (decs.length >= 8) boatsData[b].motorBi = decs[7];
            Object.assign(boatsData[b], computeEstimatedG1Fields(boatsData[b], b));
          });
        }

        const beforeMatches = [...raw.matchAll(/(\d{2}\.\d)kg[\s\t]+([67]\.\d{2})[\s\t]+(-?[0-3]\.[05])/g)];
        if (beforeMatches.length >= 2) {
          beforeMatches.slice(0, 6).forEach((m, idx) => {
            const b = idx + 1;
            boatsData[b].weight = parseFloat(m[1]);
            boatsData[b].exTime = parseFloat(m[2]);
            boatsData[b].tilt = parseFloat(m[3]);
          });
          recalculateExRanksFromTime();
        }
        renderBoatCards();
        runSimulation();
        document.getElementById("pasteImportBox").classList.add("hidden");
      }

      window.addEventListener("DOMContentLoaded", () => {
        initCourseSelectors();
        loadHeiwajimaPreset();
        if (INITIAL_SERVER_DATA && INITIAL_SERVER_DATA.status === "ok") {
          applyServerData(INITIAL_SERVER_DATA);
        }
      });
    </script>
  </body>
</html>"""


# ---------------------------------------------------------
# Streamlit メイン処理
# ---------------------------------------------------------
def main():
    st.set_page_config(page_title="BOAT RACE 展開シミュレーター PHASE 2 PRO Complete", page_icon="🚤", layout="wide")

    st.markdown(
        """
        <style>
        .block-container { padding-top: 0.8rem !important; padding-bottom: 0.8rem !important; max-width: 1360px; }
        </style>
        """,
        unsafe_allow_html=True,
    )

    if "server_race_data" not in st.session_state:
        st.session_state["server_race_data"] = None
        st.session_state["status_banner"] = (
            "💡 上のバーで日付・レース場・Rを選んで「🔄 公式データ自動取得」を押すと、出走表・直前情報・レースグレード(G1以上判定)が自動反映されます。"
        )

    c_date, c_venue, c_rno, c_btn = st.columns([1.1, 1.8, 0.9, 2.2])
    with c_date:
        jst_now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9)))
        selected_date = st.date_input("開催日", value=jst_now.date())
        hd_str = selected_date.strftime("%Y%m%d")
    with c_venue:
        selected_venue = st.selectbox("レース場 (24場)", VENUE_LIST, index=12, format_func=lambda x: x[1])
        jcd_str = selected_venue[0]
    with c_rno:
        rno_int = st.selectbox("レース", list(range(1, 13)), index=11, format_func=lambda x: f"{x}R")
    with c_btn:
        st.write("")
        if st.button("🔄 公式データ自動取得 (出走表＋直前情報＋G1判定)", type="primary", use_container_width=True):
            with st.spinner(f"BOAT RACE公式から {hd_str} {selected_venue[1]} {rno_int}R を取得中..."):
                res_data = fetch_race_data_from_official(hd_str, jcd_str, rno_int)
                if res_data.get("status") == "ok":
                    st.session_state["server_race_data"] = res_data
                    names = " / ".join([f"{k}号艇:{v['name']}" for k, v in res_data["boats"].items()])
                    g_str = res_data.get("meta", {}).get("raceGrade", "ippan")
                    warns = " | ".join(res_data.get("warnings", []))
                    st.session_state["status_banner"] = (
                        f"✅ 取得成功【{hd_str} {selected_venue[1]} {rno_int}R ({g_str})】：{names} {warns}"
                    )
                else:
                    st.error(res_data.get("message", "取得エラー"))

    active_venues = get_active_venues_for_date(hd_str)
    active_info = f" ｜ 📍 {hd_str} 開催場: {', '.join(active_venues)}" if active_venues else ""
    st.caption(st.session_state.get("status_banner", "") + active_info)

    json_payload = json.dumps(st.session_state["server_race_data"], ensure_ascii=False)
    rendered_html = ULTIMATE_HTML_TEMPLATE.replace("__INJECTED_SERVER_DATA__", json_payload)
    components.html(rendered_html, height=1920, scrolling=True)


if __name__ == "__main__":
    main()
