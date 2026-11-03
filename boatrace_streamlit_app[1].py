```python
# -*- coding: utf-8 -*-
"""
🚤 ボートレース プロ展開シミュレーター PHASE 2 PRO Complete
========================================================================================
🎓 ぼーとだいがくせい｜全機能統合・コース別攻め成功率・最大24点対応・My予想AI採点チェッカー搭載版

【搭載機能一覧】
1. [⚔️ コース別の攻め方 ＆ 決まり手成功率（2Cまくり率/差し率、3〜6Cまくり/まくり差し/差し/展開待ち率）]
   ・各コース(1C〜6C)ごとの「逃げ率・差し率・まくり率・まくり差し率・展開待ち連対率」を選手データから自動算出＆手動調整可能。
   ・当日の風向・風速・潮位・ST差・カド位置を加味した「コース別 1M攻め方＆リアルタイム成功率マトリクス」を表示。
2. [🎯 推奨買い目点数を4点〜最大24点まで大幅拡充（6点上限を完全撤廃）]
   ・パターンA（イン逃げ：最大20通り）とパターンB（イン逃げ以外：最大30通り）の全組み合わせを確率順に生成。
   ・4点 / 6点 / 8点 / 10点 / 12点 / 14点 / 16点 / 18点 / 20点 / 24点（＋任意の自由点数入力）に完全対応。
3. [🧐 自分の予想を入力してAIが100点満点で採点・スジ診断する「My予想AI評価チェッカー」]
   ・自分の買い目（単発 `1-2-3` やフォーメーション `1-23-2345`、ボタン選択）と想定展開を入力すると、
     AIが「総合ランク(S〜D)・100点満点スコア」「1点ごとのスジ整合性＆推定確率」「抜けている危険な死角買い目（抜け目警告）」を即座に診断！
4. [🏆 G1以上はG1限定成績のみ適用 ＆ 🟦イン逃げ vs 🟥イン逃げ以外の2パターン予想 ＆ 💰note/X収益化出力]
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


def fetch_latest_odds_only(hd: str, jcd: str, rno: int) -> dict:
    """出走表設定を保ったまま、公式の最新3連単オッズ(全120通り)と確定配当だけを再取得する"""
    odds_map = {}
    settled_info = None
    session = make_official_session()
    try:
        odds_url = f"https://www.boatrace.jp/owpc/pc/race/odds3t?rno={rno}&jcd={jcd}&hd={hd}"
        res_odds = session.get(odds_url, timeout=(4, 10))
        res_odds.encoding = "utf-8"
        soup_odds = BeautifulSoup(res_odds.text, "html.parser")
        odds_cells = [normalize_text(td.get_text(strip=True)) for td in soup_odds.select("td.oddsPoint")]
        if len(odds_cells) == 120:
            for col in range(6):
                fst = col + 1
                col_vals = [odds_cells[row * 6 + col] for row in range(20)]
                idx_v = 0
                for snd in range(1, 7):
                    if snd == fst:
                        continue
                    for trd in range(1, 7):
                        if trd == fst or trd == snd:
                            continue
                        val_str = col_vals[idx_v]
                        idx_v += 1
                        if re.fullmatch(r"\d+(?:\.\d+)?", val_str):
                            odds_map[f"{fst}-{snd}-{trd}"] = float(val_str)
    except Exception:
        pass

    try:
        rres_url = f"https://www.boatrace.jp/owpc/pc/race/raceresult?rno={rno}&jcd={jcd}&hd={hd}"
        res_rres = session.get(rres_url, timeout=(4, 10))
        res_rres.encoding = "utf-8"
        soup_rres = BeautifulSoup(res_rres.text, "html.parser")
        rres_txt = normalize_text(soup_rres.get_text(" ", strip=True))
        if "データがありません" not in rres_txt:
            pay_spans = [
                int(re.sub(r"[^\d]", "", sp.get_text()))
                for sp in soup_rres.select("span.is-payout1")
                if re.sub(r"[^\d]", "", sp.get_text())
            ]
            if pay_spans:
                settled_info = {"payout3t": pay_spans[0]}
    except Exception:
        pass

    return {"odds3t": odds_map, "settledResult": settled_info}


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
    """一般戦混じりの通算成績から、G1以上(記念・SG/PG1/G1)限定の推定成績を算出"""
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


def estimate_course_attack_rates(boat_no: int, win_rate: float, bi_rate: float, tri_rate: float, avg_st: float):
    """
    コース別の攻め方ごとの基本成功率（％）を算出：
    ・sashiRate: 差し成功率(%)（例：2コース差し率、3〜6コース最内差し率）
    ・makuriRate: まくり成功率(%)（例：2コースジカまくり率、3・4コースまくり率）
    ・makurisashiRate: まくり差し成功率(%)（例：3・4・5コースまくり差し率）
    ・waitRentaiRate: 展開待ちからの2・3着連対率(%)
    """
    skill = max(0.55, min(1.45, win_rate / 6.10))
    st_boost = max(0.75, min(1.35, (0.17 - avg_st) * 8.0 + 1.0))

    base_sashi = {1: 3.5, 2: 14.2, 3: 3.8, 4: 3.2, 5: 1.6, 6: 1.0}[boat_no]
    base_makuri = {1: 68.0, 2: 5.4, 3: 8.2, 4: 7.8, 5: 2.4, 6: 1.0}[boat_no]
    base_ms = {1: 0.5, 2: 1.2, 3: 7.2, 4: 6.4, 5: 6.8, 6: 2.6}[boat_no]
    base_wait = {1: 18.0, 2: 46.0, 3: 44.0, 4: 45.0, 5: 42.0, 6: 31.0}[boat_no]

    sashi_r = round(min(45.0, max(0.5, base_sashi * skill)), 1)
    makuri_r = round(min(92.0 if boat_no == 1 else 38.0, max(0.5, base_makuri * skill * (1.0 if boat_no == 1 else st_boost))), 1)
    ms_r = round(min(38.0, max(0.5, base_ms * skill * st_boost)), 1)
    wait_r = round(min(85.0, max(12.0, base_wait * (0.65 + (tri_rate / 140.0)))), 1)
    return sashi_r, makuri_r, ms_r, wait_r


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
            sashi_r, makuri_r, ms_r, wait_r = estimate_course_attack_rates(
                boat_no, win_rate, bi_rate, tri_rate, avg_st
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
                "sashiRate": sashi_r,
                "makuriRate": makuri_r,
                "makurisashiRate": ms_r,
                "waitRentaiRate": wait_r,
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
                data["env"]["wave"]