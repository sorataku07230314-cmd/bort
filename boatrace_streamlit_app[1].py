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

    base_sashi = {1: 3.5, 2: 15.6, 3: 4.8, 4: 6.5, 5: 2.2, 6: 1.5}[boat_no]
    base_makuri = {1: 68.0, 2: 5.2, 3: 8.4, 4: 9.2, 5: 2.6, 6: 1.2}[boat_no]
    base_ms = {1: 0.5, 2: 1.5, 3: 9.6, 4: 8.8, 5: 8.5, 6: 3.4}[boat_no]
    base_wait = {1: 18.0, 2: 48.0, 3: 46.0, 4: 48.0, 5: 46.0, 6: 36.0}[boat_no]

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

        # 3. 3連単リアルタイムオッズ(odds3t) ＆ 確定配当(raceresult) の自動取得
        data["odds3t"] = {}
        data["settledResult"] = None
        try:
            odds_url = f"https://www.boatrace.jp/owpc/pc/race/odds3t?rno={rno}&jcd={jcd}&hd={hd}"
            res_odds = session.get(odds_url, timeout=(4, 10))
            res_odds.encoding = "utf-8"
            soup_odds = BeautifulSoup(res_odds.text, "html.parser")
            odds_Cells = [normalize_text(td.get_text(strip=True)) for td in soup_odds.select("td.oddsPoint")]
            if len(odds_Cells) == 120:
                # 20 rows x 6 cols matrix -> transpose by 1st boat (col 0..5)
                for col in range(6):
                    fst = col + 1
                    col_vals = [odds_Cells[row * 6 + col] for row in range(20)]
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
                                data["odds3t"][f"{fst}-{snd}-{trd}"] = float(val_str)
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
                    data["settledResult"] = {"payout3t": pay_spans[0]}
        except Exception:
            pass

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
          <span class="bg-sky-500 text-slate-950 font-black px-2 py-0.5 rounded text-xs">Version 3.0 Complete</span>
          <div class="inline-flex rounded-lg bg-slate-950 p-0.5 border border-slate-700 ml-1">
            <button id="btnModeBeginner" type="button" data-action="setUIMode" data-mode="beginner" class="px-2.5 py-0.5 text-[11px] font-bold rounded-md text-slate-400 hover:text-white">🔰 初級者モード</button>
            <button id="btnModePro" type="button" data-action="setUIMode" data-mode="pro" class="px-2.5 py-0.5 text-[11px] font-black rounded-md bg-sky-600 text-white shadow">🔬 上級者モード</button>
          </div>
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
      </section>

      
      

      <!-- ⑬ レースタイプバッジ ＆ ⑨ 荒れ指数コンテナ -->
      <div id="raceTypeBadgeContainer" class="mb-3"></div>

      <div class="grid grid-cols-1 lg:grid-cols-12 gap-4">
        <!-- 左カラム (7 cols): 環境設定・進入設定・6艇カード・コース別攻め成功率マトリクス -->
        <section class="lg:col-span-7 space-y-3">
          <!-- ① 環境＆グレードフィルター -->
          <div class="bg-slate-900 border border-slate-800 rounded-xl p-3 space-y-2">
            <div class="flex flex-wrap items-center justify-between gap-1 border-b border-slate-800 pb-1">
              <h2 class="text-xs font-bold text-sky-400">① レースグレード・開催日ウェイト ＆ 水面環境フィルター</h2>
              <span id="venueTraitBadge" class="text-[11px] bg-slate-800 text-amber-300 px-2 py-0.5 rounded"></span>
            </div>
            <div class="grid grid-cols-2 sm:grid-cols-8 gap-2 text-xs">
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
                <label class="block text-pink-300 font-bold text-[10px]">💃女子戦データ適用</label>
                <select id="ladiesModeSelect" onchange="onGradeChange()" class="w-full font-bold border-pink-500/60 text-pink-200">
                  <option value="exclude" selected>🚫 入れない(女子戦かさ増し除外)</option>
                  <option value="include">💃 入れる(女子戦モード・まくり/抜増)</option>
                  <option value="raw">📊 通算そのまま(補正なし)</option>
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
                  <option value="3">3コース(3カド)</option><option value="4" selected>4コース(標準4カド)</option>
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

          
          <!-- 🎯 ③ 過去レース展開分析 ＆ 6コース連動戦術パネル -->
          <div class="bg-slate-900 border-2 border-pink-500/50 rounded-xl p-3 space-y-2.5 shadow-lg">
            <div class="flex flex-wrap items-center justify-between gap-1 border-b border-slate-800 pb-1.5">
              <div class="flex items-center gap-2">
                <span class="text-base">🎯</span>
                <div>
                  <h2 class="text-xs font-bold text-pink-300">③ 過去レース展開分析 ＆ 6コース連動戦術パネル</h2>
                  <span class="text-[10px] text-slate-400">過去レース統計（会場×風×ST段差×選手決まり手履歴）から6艇が矛盾なく連動する1M展開を分析・指定</span>
                </div>
              </div>
              <label class="flex items-center gap-1.5 text-[11px] bg-slate-950 border border-pink-500/40 px-2 py-1 rounded cursor-pointer text-pink-200 font-bold">
                <input type="checkbox" id="chkAutoCoupleTactics" checked />
                🔗 1艇変更時に他艇もセオリー連動
              </label>
            </div>

            <!-- 📊 過去レース分析から導いた推奨展開シナリオ TOP3 -->
            <div id="pastRaceScenarioTop3Box" class="bg-slate-950/90 border border-slate-800 rounded-lg p-2 space-y-1.5 text-xs"></div>

            <!-- ワンクリック6艇完全連動プリセット -->
            <div class="flex flex-wrap gap-1 text-[11px]">
              <button type="button" onclick="setTacticsPreset('in_nige')" class="bg-sky-950 hover:bg-sky-900 text-sky-300 border border-sky-700/60 px-2 py-0.5 rounded font-bold">🛡️ イン先マイ王道</button>
              <button type="button" onclick="setTacticsPreset('c2_sashi')" class="bg-emerald-950 hover:bg-emerald-900 text-emerald-300 border border-emerald-700/60 px-2 py-0.5 rounded font-bold">📐 2C差し切り逆転</button>
              <button type="button" onclick="setTacticsPreset('c2_makuri')" class="bg-amber-950 hover:bg-amber-900 text-amber-300 border border-amber-700/60 px-2 py-0.5 rounded font-bold">🔥 2Cジカまくり</button>
              <button type="button" onclick="setTacticsPreset('c3_attack')" class="bg-purple-950 hover:bg-purple-900 text-purple-300 border border-purple-700/60 px-2 py-0.5 rounded font-bold">⚡ 3Cまくり差し</button>
              <button type="button" onclick="setTacticsPreset('c3_makuri')" class="bg-orange-950 hover:bg-orange-900 text-orange-300 border border-orange-700/60 px-2 py-0.5 rounded font-bold">🔥 3Cツケマイ攻め</button>
              <button type="button" onclick="setTacticsPreset('c4_makuri')" class="bg-rose-950 hover:bg-rose-900 text-rose-300 border border-rose-700/60 px-2 py-0.5 rounded font-bold">🔥 4カドまくり一撃</button>
              <button type="button" onclick="setTacticsPreset('out_wait')" class="bg-teal-950 hover:bg-teal-900 text-teal-300 border border-teal-700/60 px-2 py-0.5 rounded font-bold">💥 1Mやり合い展開待ち</button>
              <button type="button" onclick="setTacticsPreset('reset')" class="bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 px-2 py-0.5 rounded">🔄 過去レースAI自動に戻す</button>
            </div>

            <!-- コース別戦術セレクター（1C〜6C） -->
            <div class="grid grid-cols-2 sm:grid-cols-6 gap-2" id="courseTacticsControlGrid"></div>
          </div>

          <!-- ③ 6艇カード -->
          <div class="space-y-2" id="boatCardsContainer"></div>

          
          <!-- ④ コース別 1M攻め方＆決まり手成功率マトリクス (2Cまくり率/差し率など) -->
          <div class="bg-slate-900 border border-emerald-500/40 rounded-xl p-3 space-y-2">
            <div class="flex flex-wrap items-center justify-between gap-1 border-b border-slate-800 pb-1.5">
              <div>
                <h2 class="text-xs font-bold text-emerald-400">⚔️ ④ コース別 1M攻め方 ＆ 決まり手成功率マトリクス（当日水面・風・ST補正後）</h2>
                <span class="text-[10px] text-slate-400">2コースの「差し率・まくり率」やセンター・アウトの「まくり・まくり差し・展開待ち連対率」をコース別に算出（各艇の「詳細▼」で基礎率も変更可能）</span>
              </div>
            </div>
            <div class="overflow-x-auto">
              <table class="w-full text-xs text-left">
                <thead class="text-[10px] text-slate-400 border-b border-slate-800">
                  <tr>
                    <th class="py-1">コース</th>
                    <th class="py-1">艇・選手</th>
                    <th class="py-1">主戦法(1M攻め)</th>
                    <th class="py-1 text-right">📐差し率</th>
                    <th class="py-1 text-right">🔥まくり/逃げ率</th>
                    <th class="py-1 text-right">⚡まくり差し率</th>
                    <th class="py-1 text-right">⏳展開待ち率</th>
                    <th class="py-1 pl-2">🔄他艇展開連動による動的補正理由</th>
                  </tr>
                </thead>
                <tbody id="courseAttackMatrixBody" class="divide-y divide-slate-800/60"></tbody>
              </table>
            </div>
          </div>

          <!-- 🧠 Version 3.0: ③ AI予想理由説明 ＆ ④ ST優位指数(stAdvantage) ＆ ⑤ 機力指数V2 (SS〜D) -->
          <div id="v3ExplanationsContainer"></div>

          <!-- 🧠 Version 3.0: ⑩ 会場別学習AI ＆ ⑪ 自動重み最適化(現在値 vs 推奨値) ＆ ⑫ ハズレ原因分析 -->
          <div id="v3LearningComparisonContainer"></div>
        </section>

        <!-- 右カラム (5 cols): スリット図・決まり手確率・スコア・長文2パターン展開レポート・最大24点3連単＆EV・My予想AI採点チェッカー・note/X出力 -->
        <section class="lg:col-span-5 space-y-3">
          <!-- 🖼️ 高精細スリット隊形画像 ＆ 1マーク展開画像ジェネレーター（ワンタップ画像コピー＆PNG保存対応） -->
          <div class="bg-slate-900 border-2 border-emerald-500/40 rounded-xl p-3 space-y-3">
            <div class="flex flex-wrap items-center justify-between gap-1.5 border-b border-slate-800 pb-2">
              <div>
                <h2 class="text-xs font-bold text-emerald-300">🖼️ 想定スリット隊形画像 ＆ 1マーク展開軌道画像（X / note コピペ対応）</h2>
                <span class="text-[10px] text-slate-400">ボタンを押すと画像としてクリップボードにコピーされ、Xやnoteにそのまま貼り付け(Ctrl+V)できます</span>
              </div>
              <div class="flex flex-wrap gap-1 text-[11px]">
                <button onclick="copyCanvasToClipboard('slitCanvas', 'スリット隊形画像')" class="bg-sky-500 hover:bg-sky-400 text-slate-950 font-black px-2 py-1 rounded shadow">
                  📋 スリット画像をコピー
                </button>
                <button onclick="copyCanvasToClipboard('firstMarkCanvas', '1マーク展開画像')" class="bg-amber-400 hover:bg-amber-300 text-slate-950 font-black px-2 py-1 rounded shadow">
                  📋 1マーク画像をコピー
                </button>
                <button onclick="copyCombinedSnsImage()" class="bg-pink-500 hover:bg-pink-400 text-white font-black px-2 py-1 rounded shadow">
                  🖼️ 2枚合体画像をコピー
                </button>
                <button onclick="downloadCombinedSnsImage()" class="bg-slate-800 hover:bg-slate-700 text-emerald-300 border border-emerald-500/40 font-bold px-2 py-1 rounded">
                  💾 PNG保存
                </button>
              </div>
            </div>

            <div id="imageCopyToast" class="hidden text-[11px] font-bold text-emerald-300 bg-emerald-950/80 border border-emerald-500/50 rounded px-2.5 py-1.5"></div>

            <!-- 画像①：高精細スリット隊形キャンバス -->
            <div class="space-y-1">
              <div class="flex items-center justify-between text-[11px]">
                <span class="font-bold text-sky-300">① 想定スリット隊形図（艇身目盛り・スロー/ダッシュ境界・ST差）</span>
                <span class="text-[10px] text-slate-400">右端黄金ライン＝START(0.00) ／ 緑帯＝好STゾーン(.05〜.13)</span>
              </div>
              <div class="bg-slate-950 border border-slate-800 rounded-lg p-1 overflow-x-auto">
                <canvas id="slitCanvas" width="900" height="420" class="w-full h-auto rounded"></canvas>
              </div>
              <div id="slitLanes" class="hidden"></div>
            </div>

            <!-- 画像②：1マーク（第1ターンマーク）旋回・展開軌道キャンバス -->
            <div class="space-y-1 pt-1 border-t border-slate-800">
              <div class="flex items-center justify-between text-[11px]">
                <span class="font-bold text-amber-300">② 1マーク（第1ターンマーク）攻防・旋回ルート展開図</span>
                <span class="text-[10px] text-slate-400">実線矢印＝先マイ・まくり・差し・展開待ち軌道 ／ 白波＝引き波ゾーン</span>
              </div>
              <div class="bg-slate-950 border border-slate-800 rounded-lg p-1 overflow-x-auto">
                <canvas id="firstMarkCanvas" width="900" height="560" class="w-full h-auto rounded"></canvas>
              </div>
            </div>

            <!-- スマホ・長押しコピー用プレビューモーダル -->
            <div id="copyPreviewModal" class="hidden bg-slate-950 border-2 border-amber-400 rounded-lg p-2.5 space-y-1.5">
              <div class="flex items-center justify-between text-xs">
                <span class="font-bold text-amber-300">📸 下の画像を右クリック「画像をコピー」またはスマホ長押しで保存・コピーできます</span>
                <button onclick="document.getElementById('copyPreviewModal').classList.add('hidden')" class="text-slate-400 hover:text-white font-bold">✕ 閉じる</button>
              </div>
              <img id="copyPreviewImg" src="" alt="生成画像プレビュー" class="w-full rounded border border-slate-700" />
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

          <!-- 🎬 Version 3.0: ⑯ レースリプレイ Canvasアニメーション (スリット → 1M → バック → 2M → ゴール) -->
          <div class="bg-slate-900 border-2 border-cyan-500/40 rounded-xl p-3 space-y-2">
            <div class="flex flex-wrap items-center justify-between gap-1.5 border-b border-slate-800 pb-1.5">
              <div>
                <h2 class="text-xs font-bold text-cyan-300">🎬 ⑯ 展開シミュレーション レースリプレイ（スリット ➔ 1M ➔ バック ➔ 2M ➔ ゴール）</h2>
                <span class="text-[10px] text-slate-400">二番差し・まくり・展開待ちの航走軌道をリアルタイム再生</span>
              </div>
              <div class="flex flex-wrap items-center gap-1 text-[11px]">
                <button id="btnReplayPlay" type="button" data-action="replayToggle" class="bg-cyan-400 hover:bg-cyan-300 text-slate-950 font-black px-2.5 py-0.5 rounded shadow">▶️ 再生</button>
                <button type="button" data-action="replayStage" data-pct="12" class="btn-replay-stage bg-slate-800 hover:bg-slate-700 text-slate-200 px-1.5 py-0.5 rounded">①スリット</button>
                <button type="button" data-action="replayStage" data-pct="34" class="btn-replay-stage bg-slate-800 hover:bg-slate-700 text-amber-300 px-1.5 py-0.5 rounded">②1M旋回</button>
                <button type="button" data-action="replayStage" data-pct="56" class="btn-replay-stage bg-slate-800 hover:bg-slate-700 text-sky-300 px-1.5 py-0.5 rounded">③バック</button>
                <button type="button" data-action="replayStage" data-pct="76" class="btn-replay-stage bg-slate-800 hover:bg-slate-700 text-emerald-300 px-1.5 py-0.5 rounded">④2M</button>
                <button type="button" data-action="replayStage" data-pct="98" class="btn-replay-stage bg-slate-800 hover:bg-slate-700 text-rose-300 px-1.5 py-0.5 rounded">⑤ゴール</button>
                <button id="btnSpeed1" type="button" data-action="replaySpeed" data-speed="1" class="px-1.5 py-0.5 rounded bg-slate-800 text-sky-300 font-bold">1x</button>
                <button id="btnSpeed15" type="button" data-action="replaySpeed" data-speed="1.5" class="px-1.5 py-0.5 rounded text-slate-400 hover:text-white">1.5x</button>
                <button id="btnSpeed2" type="button" data-action="replaySpeed" data-speed="2" class="px-1.5 py-0.5 rounded text-slate-400 hover:text-white">2x</button>
              </div>
            </div>
            <div class="bg-slate-950 border border-slate-800 rounded-lg p-1 overflow-x-auto">
              <canvas id="raceReplayCanvas" width="920" height="380" class="w-full h-auto rounded"></canvas>
            </div>
            <div class="flex items-center gap-2 text-xs">
              <input type="range" id="replayProgressSlider" data-input="replaySeek" min="0" max="100" step="1" value="0" class="w-full" />
              <span id="replayProgressLabel" class="font-mono text-[11px] text-cyan-300 w-10 text-right">0%</span>
            </div>
          </div>

          <!-- 🎲 Version 3.0: ② 本格Monte Carloシミュレーション (1000〜50000回 & 3連単TOP20) -->
          <div id="v3MonteCarloContainer"></div>

          <!-- 💹 Version 3.0: ⑦ EVエンジン ＆ ⑧ AI買い目生成(本線・対抗・穴) ＆ ⑨ 資金管理モード -->
          <div id="v3EvBettingContainer"></div>

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
                  <th class="py-1 text-center">機力評価</th>
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

          <!-- 推奨3連単＆EVチェッカー（4点〜最大24点＆自由点数指定・2パターン対応） -->
          <div class="bg-slate-900 border border-slate-800 rounded-xl p-3 space-y-2.5">
            <div class="flex flex-wrap items-center justify-between gap-2">
              <div>
                <h2 class="text-xs font-bold text-sky-400">🎯 2パターン推奨3連単買い目（4点〜最大24点対応）＆ 期待値(EV)・資金配分</h2>
                <span class="text-[10px] text-slate-400">イン逃げのみ・非インのみ選択時も指定した点数をフル出力 ／ オッズ入力でEV判定</span>
              </div>
              <div class="flex flex-wrap items-center gap-1.5 text-xs">
                <select id="patternFilterSelect" onchange="runSimulation()" class="font-bold text-sky-300">
                  <option value="both" selected>🔄 2パターン同時(イン＋非イン)</option>
                  <option value="in_only">🟦 パターンA(イン逃げ)のみ</option>
                  <option value="non_in_only">🟥 パターンB(イン逃げ以外)のみ</option>
                </select>
                <select id="ticketCountSelect" onchange="runSimulation()" class="font-bold text-amber-300">
                  <option value="4">厳選 4点</option>
                  <option value="6">推奨 6点</option>
                  <option value="8">標準 8点</option>
                  <option value="10">中穴 10点</option>
                  <option value="12" selected>充実 12点</option>
                  <option value="14">広め 14点</option>
                  <option value="16">網羅 16点</option>
                  <option value="18">多点 18点</option>
                  <option value="20">フォーメーション 20点</option>
                  <option value="24">フルカバー 24点</option>
                </select>
                <select id="allocStrategySelect" onchange="runSimulation()" class="font-bold text-emerald-300" title="資金配分方式">
                  <option value="prob" selected>配分:確率比例</option>
                  <option value="ev">配分:期待値(EV)重視</option>
                  <option value="equal_return">配分:均等払戻(ガミ防止)</option>
                </select>
                <input type="number" id="budgetInput" value="5000" step="100" min="400" onchange="runSimulation()" class="w-16 text-right font-mono text-amber-300" title="総軍資金(円)" />
                <button onclick="refreshLiveOddsInBrowser()" class="bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-black px-2 py-1 rounded text-[11px] shadow" title="現在の戦法・気配設定を保ったまま最新3連単オッズのみを再取得します">
                  💹 オッズ更新
                </button>
                <button onclick="document.getElementById('oddsPasteBox').classList.toggle('hidden')" class="bg-slate-800 hover:bg-slate-700 text-amber-300 border border-amber-500/40 px-2 py-1 rounded text-[11px]" title="公式オッズ表をコピペして一括更新">
                  📋 オッズ貼付
                </button>
                <button onclick="copyBetsList()" class="bg-sky-600 hover:bg-sky-500 text-white font-bold px-2 py-1 rounded text-[11px]">買い目コピー</button>
              </div>
            </div>
            <div id="oddsUpdateStatus" class="hidden text-[11px] text-amber-300 bg-amber-950/60 border border-amber-600/40 rounded px-2.5 py-1"></div>
            <div id="oddsPasteBox" class="hidden bg-slate-950 border border-amber-500/40 rounded-lg p-2 space-y-1.5 text-xs">
              <div class="flex items-center justify-between">
                <span class="font-bold text-amber-300 text-[11px]">📋 公式3連単オッズ表 または「1-2-3 6.8」形式のコピペ一括更新</span>
                <button onclick="document.getElementById('oddsPasteBox').classList.add('hidden')" class="text-slate-400 hover:text-white">✕</button>
              </div>
              <textarea id="rawOddsPasteInput" rows="3" placeholder="BOAT RACE公式の「3連単オッズ」ページを全選択コピーして貼り付けるか、『1-2-4 8.5, 3-4-5 32.0』のように入力してください。" class="w-full bg-slate-900 border border-slate-700 rounded p-1.5 text-xs font-mono text-white"></textarea>
              <div class="flex justify-end">
                <button onclick="applyPastedOdds()" class="bg-amber-400 hover:bg-amber-300 text-slate-950 font-black px-3 py-1 rounded text-[11px]">⚡ オッズを一括反映してEV・配分を再計算</button>
              </div>
            </div>
            <div id="copyBetsToast" class="hidden text-[11px] text-emerald-300 bg-emerald-950/70 border border-emerald-700/50 rounded px-2 py-1">
              推奨買い目と配分金額をコピーしました！
            </div>
            <div id="recommendationsContainer" class="space-y-2 max-h-[460px] overflow-y-auto pr-1"></div>
          </div>

          <!-- 🧐 新機能：自分の予想を入力してAIが採点・スジ評価するチェッカー -->
          <div class="bg-slate-900 border-2 border-pink-500/50 rounded-xl p-3 space-y-2.5">
            <div class="flex flex-wrap items-center justify-between gap-2 border-b border-slate-800 pb-1.5">
              <div>
                <h2 class="text-xs font-bold text-pink-300">🧐 あなたの予想・買い目 AI採点＆スジ評価チェッカー（My予想ジャッジ）</h2>
                <span class="text-[10px] text-slate-400">自分の買い目（単発 `1-2-3` やフォーメーション `1-23-2345`、`3-4-全`）を入力すると、100点満点スコア・スジ整合性・抜け目（死角）を診断します</span>
              </div>
              <div class="flex gap-1 text-[11px]">
                <button onclick="loadAiBetsToUserInput()" class="bg-slate-800 hover:bg-slate-700 text-sky-300 border border-sky-600/40 px-2 py-0.5 rounded">🔄 AI上位目を入力</button>
                <button onclick="clearUserBetsInput()" class="bg-slate-800 hover:bg-slate-700 text-slate-300 px-2 py-0.5 rounded">クリア</button>
              </div>
            </div>

            <!-- クイックフォーメーション追加＆テキスト入力 -->
            <div class="bg-slate-950/80 border border-slate-800 rounded-lg p-2 space-y-2 text-xs">
              <div class="flex flex-wrap items-center justify-between gap-2">
                <div class="flex items-center gap-1.5">
                  <span class="text-[11px] text-slate-300 font-bold">あなたの想定展開:</span>
                  <select id="userScenarioSelect" onchange="evaluateUserPredictions()" class="text-[11px] font-bold text-pink-200">
                    <option value="auto" selected>🤖 買い目から自動逆算</option>
                    <option value="in_nige">🛡️ 1コース逃げ本線</option>
                    <option value="c2_sashi">📐 2コース差し逆転</option>
                    <option value="c2_makuri">🔥 2コースまくり(ジカまくり)</option>
                    <option value="c3_attack">⚡ 3コースまくり/まくり差し</option>
                    <option value="c4_kado">🔥 4カドまくり/まくり差し</option>
                    <option value="out_wait">⏳ 5・6コース展開待ち高配当</option>
                  </select>
                </div>
                <div class="flex flex-wrap gap-1 text-[10px]">
                  <button onclick="addPresetUserFormation('1-23-2345')" class="bg-slate-800 hover:bg-slate-700 text-sky-300 px-1.5 py-0.5 rounded">例: 1-23-2345</button>
                  <button onclick="addPresetUserFormation('2-1-345, 3-14-145')" class="bg-slate-800 hover:bg-slate-700 text-emerald-300 px-1.5 py-0.5 rounded">例: 2差＆3攻め</button>
                  <button onclick="addPresetUserFormation('4-51-1256')" class="bg-slate-800 hover:bg-slate-700 text-rose-300 px-1.5 py-0.5 rounded">例: 4カド連動</button>
                </div>
              </div>

              <div>
                <label class="block text-[10px] text-slate-400 mb-0.5">① あなたの3連単買い目入力（単発 `1-2-3` / フォーメーション `1-23-2345` / `3-4-全` 対応）</label>
                <textarea id="userBetsInput" rows="2" oninput="evaluateUserPredictions()" placeholder="例: 1-2-3, 1-2-4, 3-4-5 またはフォーメーション表記 1-23-2345 / 3-4-全" class="w-full bg-slate-900 border border-pink-500/40 rounded p-2 text-xs font-mono text-white focus:outline-none">1-2-4, 1-4-2, 4-5-1, 4-1-5</textarea>
              </div>

              <div class="pt-1 border-t border-slate-800 space-y-1">
                <div class="flex flex-wrap items-center justify-between gap-1">
                  <label class="text-[11px] font-bold text-pink-300">✍️ ② この買い目の展開シナリオ・根拠を書く（AI整合性チェック＆note/X出力連動）</label>
                  <div class="flex flex-wrap gap-1 text-[10px]">
                    <button onclick="insertScenarioTemplate('in_escape')" class="bg-slate-800 hover:bg-slate-700 text-sky-300 px-1.5 py-0.5 rounded">+イン先マイ定型</button>
                    <button onclick="insertScenarioTemplate('kado_makuri')" class="bg-slate-800 hover:bg-slate-700 text-rose-300 px-1.5 py-0.5 rounded">+カド捲り連動定型</button>
                    <button onclick="insertScenarioTemplate('sashi_wait')" class="bg-slate-800 hover:bg-slate-700 text-emerald-300 px-1.5 py-0.5 rounded">+差し＆展開待ち定型</button>
                    <button onclick="applyUserScenarioToReport()" class="bg-amber-400 hover:bg-amber-300 text-slate-950 font-black px-2 py-0.5 rounded shadow">📝 このシナリオ＆買い目をnote/Xレポートに反映</button>
                  </div>
                </div>
                <textarea id="userScenarioMemo" rows="3" oninput="evaluateUserPredictions()" placeholder="あなたが考えた1マークの展開ストーリーや狙い目の根拠を自由に書いてください（例：4カド大峯がスリット覗いてまくり仕掛け。外の5号艇がまくり差し連動し、展開待ちの1号艇が残る4-5-1を勝負目に指定！）" class="w-full bg-slate-900 border border-pink-500/40 rounded p-2 text-xs text-slate-100 leading-relaxed focus:outline-none">1コース白井の先マイ本線（1-24）を押さえつつ、カド4号艇大峯がスリット踏み込んでまくり仕掛けた際に外5号艇篠崎が連動する「4-5-1」「4-1-5」を逆転勝負目として狙う。</textarea>
              </div>
            </div>

            <!-- 評価結果表示ボックス -->
            <div id="userEvalResultBox" class="space-y-2"></div>
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
      // =========================================================
      // BOAT RACE 展開予想シミュレーター PHASE 2 PRO Complete v2.5
      // BUNDLED PREDICTION & LEARNING MODULES
      // =========================================================

      // --- MODULE: src/constants.js ---
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


// --- MODULE: src/storage.js ---
/**
 * @file storage.js
 * @description localStorageアクセス共通化 ＆ 24会場別学習DB永続化マネージャー (Version 3.0)
 */

const StorageManager = {
  /**
   * @template T
   * @param {string} key
   * @param {T} defaultValue
   * @returns {T}
   */
  get(key, defaultValue = null) {
    try {
      const raw = localStorage.getItem(key);
      if (raw === null || raw === undefined) return defaultValue;
      return JSON.parse(raw);
    } catch (e) {
      console.warn(`[StorageManager] Read error on ${key}:`, e);
      return defaultValue;
    }
  },

  /**
   * @param {string} key
   * @param {any} value
   * @returns {boolean}
   */
  set(key, value) {
    try {
      localStorage.setItem(key, JSON.stringify(value));
      return true;
    } catch (e) {
      console.warn(`[StorageManager] Write error on ${key}:`, e);
      return false;
    }
  },

  remove(key) {
    try {
      localStorage.removeItem(key);
      return true;
    } catch (e) {
      return false;
    }
  },

  /**
   * ⑩ 会場別学習AI: 24場(桐生〜大村、三国含む)それぞれの決まり手率を取得
   * @param {string} venueCode "01"〜"24"
   */
  getVenueStats(venueCode) {
    const vInfo = (typeof VENUE_MASTER !== "undefined" && VENUE_MASTER[venueCode]) ? VENUE_MASTER[venueCode] : { name: "平和島", inNige: 52.0, sashiMod: 2, makuriMod: 2 };
    const key = `${STORAGE_KEYS.VENUE_LEARNING_PREFIX}${venueCode}`;
    const defaultNige = vInfo.inNige || 54.0;
    const defaultSashi = Math.max(8.0, 14.5 + (vInfo.sashiMod || 0) * 0.8);
    const defaultMakuri = Math.max(8.0, 14.5 + (vInfo.makuriMod || 0) * 0.8);
    const defaultMs = Math.max(6.0, 11.5 + (vInfo.sashiMod || 0) * 0.4);
    const defaultNuki = Math.max(3.0, Math.round((100 - defaultNige - defaultSashi - defaultMakuri - defaultMs) * 10) / 10);

    const fallback = {
      venueCode,
      venueName: vInfo.name,
      sampleCount: 0,
      nigeCount: 0,
      sashiCount: 0,
      makuriCount: 0,
      makurisashiCount: 0,
      nukiCount: 0,
      dochuCount: 0,
      nigeRate: Math.round(defaultNige * 10) / 10,
      sashiRate: Math.round(defaultSashi * 10) / 10,
      makuriRate: Math.round(defaultMakuri * 10) / 10,
      makurisashiRate: Math.round(defaultMs * 10) / 10,
      nukiRate: Math.max(2.0, defaultNuki),
      dochuRate: 14.0,
      updatedAt: null
    };
    return this.get(key, fallback);
  },

  saveVenueStats(venueCode, stats) {
    const key = `${STORAGE_KEYS.VENUE_LEARNING_PREFIX}${venueCode}`;
    stats.updatedAt = new Date().toISOString();
    return this.set(key, stats);
  },

  recordVenueRaceResult(venueCode, kimarite, dochuType = "none") {
    const stats = this.getVenueStats(venueCode);
    stats.sampleCount += 1;
    if (kimarite === "nige") stats.nigeCount += 1;
    else if (kimarite === "sashi") stats.sashiCount += 1;
    else if (kimarite === "makuri") stats.makuriCount += 1;
    else if (kimarite === "makurisashi") stats.makurisashiCount += 1;
    else stats.nukiCount += 1;

    if (dochuType && dochuType !== "none") stats.dochuCount += 1;

    const n = stats.sampleCount;
    stats.nigeRate = Math.round((stats.nigeCount / n) * 1000) / 10;
    stats.sashiRate = Math.round((stats.sashiCount / n) * 1000) / 10;
    stats.makuriRate = Math.round((stats.makuriCount / n) * 1000) / 10;
    stats.makurisashiRate = Math.round((stats.makurisashiCount / n) * 1000) / 10;
    stats.nukiRate = Math.round((stats.nukiCount / n) * 1000) / 10;
    stats.dochuRate = Math.round((stats.dochuCount / n) * 1000) / 10;

    this.saveVenueStats(venueCode, stats);
    return stats;
  },

  getAllVenuesSummary() {
    const list = [];
    if (typeof VENUE_MASTER === "undefined") return list;
    Object.keys(VENUE_MASTER).sort().forEach(code => {
      list.push(this.getVenueStats(code));
    });
    return list;
  },

  getReviewLogs() {
    return this.get(STORAGE_KEYS.REVIEW_LOGS, []);
  },

  saveReviewLogs(logs) {
    return this.set(STORAGE_KEYS.REVIEW_LOGS, logs);
  },

  getLearnedParams() {
    return this.get(STORAGE_KEYS.LEARNED_PARAMS, null);
  },

  saveLearnedParams(params) {
    return this.set(STORAGE_KEYS.LEARNED_PARAMS, params);
  },

  getUIMode() {
    return this.get(STORAGE_KEYS.UI_MODE, "pro");
  },

  setUIMode(mode) {
    return this.set(STORAGE_KEYS.UI_MODE, mode);
  }
};


// --- MODULE: src/raceAnalyzer.js ---
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


// --- MODULE: src/simulation.js ---
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


// --- MODULE: src/oddsEngine.js ---
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


// --- MODULE: src/bettingEngine.js ---
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


// --- MODULE: src/learningEngine.js ---
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


// --- MODULE: src/replay.js ---
/**
 * @file replay.js
 * @description Version 3.0 ⑯ レースリプレイ Canvasアニメーションモジュール
 * スリット ➔ 1M ➔ バック ➔ 2M ➔ ゴール を滑らかに描画
 */

const ReplayEngine = {
  renderFrame(canvasId, progress = 0, courseEval = {}, simResult = null) {
    const canvas = document.getElementById(canvasId);
    if (!canvas) return;
    const W = 920;
    const H = 380;
    if (canvas.width !== W * 2 || canvas.height !== H * 2) {
      canvas.width = W * 2;
      canvas.height = H * 2;
    }
    const ctx = canvas.getContext("2d");
    ctx.save();
    ctx.scale(2, 2);

    ctx.fillStyle = "#14b8d4";
    ctx.fillRect(0, 0, W, H);

    // 1マーク & 2マーク ブイ
    const buoys = [
      { x: 220, y: 195, name: "1マーク" },
      { x: 700, y: 195, name: "2マーク" }
    ];
    buoys.forEach(b => {
      ctx.save();
      ctx.translate(b.x, b.y);
      ctx.fillStyle = "#ffffff";
      ctx.beginPath(); ctx.arc(0, 0, 16, 0, Math.PI * 2); ctx.fill();
      ctx.fillStyle = "#ef4444";
      ctx.beginPath(); ctx.moveTo(0, 0); ctx.arc(0, 0, 16, -Math.PI * 0.75, -Math.PI * 0.25); ctx.closePath(); ctx.fill();
      ctx.beginPath(); ctx.moveTo(0, 0); ctx.arc(0, 0, 16, Math.PI * 0.25, Math.PI * 0.75); ctx.closePath(); ctx.fill();
      ctx.strokeStyle = "#0f172a"; ctx.lineWidth = 2;
      ctx.beginPath(); ctx.arc(0, 0, 16, 0, Math.PI * 2); ctx.stroke();
      ctx.fillStyle = "#0f172a"; ctx.font = "900 12px sans-serif"; ctx.textAlign = "center";
      ctx.fillText(b.name, 0, 30);
      ctx.restore();
    });

    // スリットライン & ゴールライン
    ctx.strokeStyle = "#dc2626"; ctx.lineWidth = 2.5;
    ctx.beginPath(); ctx.moveTo(470, 245); ctx.lineTo(470, 360); ctx.stroke();
    ctx.fillStyle = "#dc2626"; ctx.font = "bold 10px sans-serif"; ctx.textAlign = "center";
    ctx.fillText("START (スリット)", 470, 372);

    ctx.strokeStyle = "#0f172a"; ctx.lineWidth = 2; ctx.setLineDash([4, 4]);
    ctx.beginPath(); ctx.moveTo(410, 245); ctx.lineTo(410, 360); ctx.stroke();
    ctx.setLineDash([]);
    ctx.fillStyle = "#0f172a"; ctx.fillText("GOAL", 410, 372);

    const topCombo = (simResult?.trifectaList?.[0]?.combo || "1-2-4").split("-").map(Number);
    const finishOrder = [...topCombo];
    for (let b = 1; b <= 6; b++) {
      if (!finishOrder.includes(b)) finishOrder.push(b);
    }

    const p = Math.max(0, Math.min(100, Number(progress) || 0));

    for (let c = 1; c <= 6; c++) {
      const obj = courseEval[c] || { boatId: c, expectedSt: 0.14, attackType: "sashi" };
      const bId = obj.boatId || c;
      const bColor = BOAT_COLORS[bId] || BOAT_COLORS[1];
      const rankIdx = finishOrder.indexOf(bId);
      const st = obj.expectedSt || 0.14;

      let x = 470, y = 300, angle = Math.PI;
      if (p <= 20) {
        // ① スリット
        const t = p / 20;
        const stAdv = (0.15 - st) * 320;
        x = 750 - t * 280 - stAdv;
        y = 262 + (c - 1) * 16;
        angle = Math.PI;
      } else if (p <= 45) {
        // ② 1M旋回
        const t = (p - 20) / 25;
        let turnR = 36 + c * 8;
        if (obj.attackType === "sashi" || obj.attackType === "nibanzashi") turnR = 28 + c * 4;
        else if (obj.attackType === "makuri") turnR = 68;
        else if (obj.attackType === "tenkaimachi") turnR = 34;
        const theta = -Math.PI * 0.5 + t * Math.PI;
        x = 220 - Math.cos(theta) * turnR;
        y = 195 + Math.sin(theta) * turnR;
        angle = Math.PI - (theta + Math.PI * 0.5);
      } else if (p <= 68) {
        // ③ バックストレッチ
        const t = (p - 45) / 23;
        const lead = (5 - rankIdx) * 24;
        x = 220 + t * 470 + lead;
        y = 68 + rankIdx * 14;
        angle = 0;
      } else if (p <= 86) {
        // ④ 2M旋回
        const t = (p - 68) / 18;
        const turnR = 34 + rankIdx * 8;
        const theta = Math.PI * 0.5 + t * Math.PI;
        x = 700 + Math.cos(theta) * turnR;
        y = 195 - Math.sin(theta) * turnR;
        angle = theta + Math.PI * 0.5;
      } else {
        // ⑤ ゴール
        const t = (p - 86) / 14;
        const lead = (5 - rankIdx) * 32;
        x = 700 - t * 290 - lead;
        y = 262 + rankIdx * 16;
        angle = Math.PI;
      }

      ctx.save();
      ctx.translate(x, y);
      ctx.rotate(angle);
      ctx.fillStyle = "rgba(255,255,255,0.45)";
      ctx.beginPath(); ctx.moveTo(-16, -5); ctx.lineTo(-40, -10); ctx.lineTo(-40, 10); ctx.lineTo(-16, 5); ctx.closePath(); ctx.fill();
      ctx.fillStyle = bColor.body; ctx.strokeStyle = "#0f172a"; ctx.lineWidth = 1.5;
      ctx.beginPath(); ctx.moveTo(-20, -9); ctx.lineTo(10, -9); ctx.lineTo(22, 0); ctx.lineTo(10, 9); ctx.lineTo(-20, 9); ctx.closePath(); ctx.fill(); ctx.stroke();
      ctx.fillStyle = "#ffffff";
      ctx.beginPath(); ctx.arc(-4, 0, 7.5, 0, Math.PI * 2); ctx.fill(); ctx.stroke();
      ctx.save();
      ctx.translate(-4, 0);
      ctx.rotate(-angle);
      ctx.fillStyle = bColor.numText; ctx.font = "900 11px sans-serif"; ctx.textAlign = "center"; ctx.textBaseline = "middle";
      ctx.fillText(String(bId), 0, 1);
      ctx.restore();
      ctx.restore();
    }

    // 上部ステータスバー
    ctx.fillStyle = "#0f172a";
    ctx.fillRect(0, 0, W, 28);
    ctx.fillStyle = "#ffffff";
    ctx.font = "bold 12px sans-serif";
    ctx.textAlign = "left";
    const stageText = p <= 20
      ? "① スリット（スタート踏み込み）"
      : p <= 45
        ? "② 1マーク旋回（先マイ・差し・二番差し・まくり攻防）"
        : p <= 68
          ? "③ バックストレッチ（直線伸び比べ）"
          : p <= 86
            ? "④ 2マーク旋回（道中さばき・逆転攻防）"
            : `⑤ ゴールイン（想定決着: ${topCombo.join("-")}）`;
    ctx.fillText(`🎬 展開リプレイ: ${stageText}`, 12, 18);
    ctx.fillStyle = "#38bdf8";
    ctx.textAlign = "right";
    ctx.fillText(`進行: ${Math.round(p)}%`, W - 12, 18);

    ctx.restore();
  }
};


// --- MODULE: src/ui.js ---
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


const DEFAULT_BOATS_DATA = {
  1: { id: 1, name: "毒島 誠", branch: "群馬", rank: "A1", winRate: 7.82, localWin: 7.95, g1Win: 7.74, g1CourseWin: 76.5, courseWin: 74.2, courseTri: 88.5, avgSt: 0.12, seriesSt: 0.11, seriesScore: 8.5, fCount: 0, weight: 51.5, motorNo: 42, motorBi: 46.8, exTime: 6.71, oriExTime: 6.64, visSlit: 4, visTurn: 4, partsReplace: "none", tilt: -0.5, sashiRate: 8.0, makuriRate: 74.2, makurisashiRate: 0.0, waitRentaiRate: 91.0, nigashi: 52.0, nigashiTri: 72.0, manualTactic: "auto" },
  2: { id: 2, name: "馬場 貴也", branch: "滋賀", rank: "A1", winRate: 7.98, localWin: 8.10, g1Win: 7.88, g1CourseWin: 24.5, courseWin: 26.8, courseTri: 78.4, avgSt: 0.13, seriesSt: 0.14, seriesScore: 7.8, fCount: 0, weight: 51.0, motorNo: 15, motorBi: 41.2, exTime: 6.74, oriExTime: 6.68, visSlit: 3, visTurn: 5, partsReplace: "none", tilt: -0.5, sashiRate: 24.5, makuriRate: 6.2, makurisashiRate: 0.0, waitRentaiRate: 78.0, nigashi: 62.5, nigashiTri: 84.0, manualTactic: "auto" },
  3: { id: 3, name: "峰 竜太", branch: "佐賀", rank: "A1", winRate: 8.45, localWin: 8.60, g1Win: 8.32, g1CourseWin: 28.0, courseWin: 29.5, courseTri: 82.0, avgSt: 0.11, seriesSt: 0.12, seriesScore: 9.1, fCount: 0, weight: 51.2, motorNo: 63, motorBi: 48.5, exTime: 6.69, oriExTime: 6.61, visSlit: 4, visTurn: 5, partsReplace: "ring2", tilt: -0.5, sashiRate: 10.5, makuriRate: 15.2, makurisashiRate: 22.8, waitRentaiRate: 82.0, nigashi: 48.0, nigashiTri: 68.0, manualTactic: "auto" },
  4: { id: 4, name: "菊地 孝平", branch: "静岡", rank: "A1", winRate: 7.55, localWin: 7.62, g1Win: 7.42, g1CourseWin: 22.0, courseWin: 24.0, courseTri: 72.5, avgSt: 0.09, seriesSt: 0.08, seriesScore: 7.2, fCount: 0, weight: 52.0, motorNo: 28, motorBi: 43.0, exTime: 6.72, oriExTime: 6.66, visSlit: 5, visTurn: 3, partsReplace: "carrier", tilt: 0.0, sashiRate: 6.0, makuriRate: 24.5, makurisashiRate: 16.5, waitRentaiRate: 72.0, nigashi: 45.0, nigashiTri: 65.0, manualTactic: "auto" },
  5: { id: 5, name: "池田 浩二", branch: "愛知", rank: "A1", winRate: 7.76, localWin: 7.85, g1Win: 7.68, g1CourseWin: 12.5, courseWin: 14.2, courseTri: 68.0, avgSt: 0.14, seriesSt: 0.13, seriesScore: 7.5, fCount: 0, weight: 52.5, motorNo: 51, motorBi: 39.5, exTime: 6.75, oriExTime: 6.70, visSlit: 3, visTurn: 4, partsReplace: "none", tilt: -0.5, sashiRate: 5.5, makuriRate: 4.0, makurisashiRate: 16.0, waitRentaiRate: 68.0, nigashi: 50.0, nigashiTri: 70.0, manualTactic: "auto" },
  6: { id: 6, name: "茅原 悠紀", branch: "岡山", rank: "A1", winRate: 7.88, localWin: 7.92, g1Win: 7.75, g1CourseWin: 6.8, courseWin: 8.5, courseTri: 62.0, avgSt: 0.13, seriesSt: 0.15, seriesScore: 8.0, fCount: 0, weight: 51.8, motorNo: 34, motorBi: 42.8, exTime: 6.77, oriExTime: 6.71, visSlit: 3, visTurn: 5, partsReplace: "piston2", tilt: -0.5, sashiRate: 4.0, makuriRate: 3.5, makurisashiRate: 8.0, waitRentaiRate: 62.0, nigashi: 46.0, nigashiTri: 66.0, manualTactic: "auto" }
};

      window.VENUE_MASTER = VENUE_MASTER;
      window.BOAT_COLORS = BOAT_COLORS;
      window.StorageManager = StorageManager;
      window.RaceAnalyzer = RaceAnalyzer;
      window.SimulationEngine = SimulationEngine;
      window.OddsEngine = OddsEngine;
      window.BettingEngine = BettingEngine;
      window.LearningEngine = LearningEngine;
      window.ReplayEngine = ReplayEngine;
      window.UIManager = UIManager;

      const AppStateV3 = {
        mcRuns: 5000,
        budget: 5000,
        bankrollMode: "ev_focus",
        uiMode: "pro",
        lastMissReport: null
      };

      let replayProgress = 0;
      let replayRunning = false;
      let replaySpeed = 1.0;
      let replayAnimFrameId = null;
      let latestMonteCarloResult = null;
      let latestEVAnalysis = null;
      let latestSmartPortfolio = null;

      const INITIAL_SERVER_DATA = __INJECTED_SERVER_DATA__;

      

      let boatsData = (typeof DEFAULT_BOATS_DATA !== 'undefined' && DEFAULT_BOATS_DATA) ? JSON.parse(JSON.stringify(DEFAULT_BOATS_DATA)) : {};
      let liveOddsMap = {};
      let settledPayoutInfo = null;
      let learnedBias = { inModAdj: 0, makuriModAdj: 0, sashiModAdj: 0, waitBonusAdj: 0, sampleCount: 0 };
      let allDetailsOpen = false;
      let latestReportParts = { free: "", paid: "", full: "" };
      let latestSimContext = null;

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

        // コース別攻め方成功率（差し率・まくり率・まくり差し率・展開待ち連対率）
        const skill = Math.max(0.55, Math.min(1.45, winRate / 6.1));
        const stBoost = Math.max(0.75, Math.min(1.35, (0.17 - avgSt) * 8.0 + 1.0));
        const baseSashi = { 1: 3.5, 2: 15.6, 3: 4.8, 4: 6.5, 5: 2.2, 6: 1.5 }[id] || 3.0;
        const baseMakuri = { 1: 68.0, 2: 5.2, 3: 8.4, 4: 9.2, 5: 2.6, 6: 1.2 }[id] || 4.0;
        const baseMs = { 1: 0.5, 2: 1.5, 3: 9.6, 4: 8.8, 5: 8.5, 6: 3.4 }[id] || 3.0;
        const baseWait = { 1: 18.0, 2: 48.0, 3: 46.0, 4: 48.0, 5: 46.0, 6: 36.0 }[id] || 35.0;

        const sashiRate = Math.round(Math.min(45.0, Math.max(0.5, baseSashi * skill)) * 10) / 10;
        const makuriRate = Math.round(Math.min(id === 1 ? 92.0 : 38.0, Math.max(0.5, baseMakuri * skill * (id === 1 ? 1.0 : stBoost))) * 10) / 10;
        const makurisashiRate = Math.round(Math.min(38.0, Math.max(0.5, baseMs * skill * stBoost)) * 10) / 10;
        const waitRentaiRate = Math.round(Math.min(85.0, Math.max(12.0, baseWait * (0.65 + triRate / 140.0))) * 10) / 10;

        return {
          g1WinRate: g1Win,
          g1LocalWin: g1Local,
          g1CourseWin: g1CWin,
          g1CourseTri: g1CTri,
          g1AvgSt: g1St,
          sashiRate: b.sashiRate ?? sashiRate,
          makuriRate: b.makuriRate ?? makuriRate,
          makurisashiRate: b.makurisashiRate ?? makurisashiRate,
          waitRentaiRate: b.waitRentaiRate ?? waitRentaiRate
        };
      }

      function getActiveFactors() {
        const chk = (id) => document.getElementById(id)?.checked ?? true;
        return {
          winRate: chk("f_winRate"),
          localWin: chk("f_localWin"),
          g1OnlyRule: chk("f_g1OnlyRule"),
          ladiesRule: chk("f_ladiesRule"),
          seriesScore: chk("f_seriesScore"),
          weight: chk("f_weight"),
          courseWin: chk("f_courseWin"),
          courseTri: chk("f_courseTri"),
          courseKimarite: chk("f_courseKimarite"),
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


      function rebuildLearnedParamsFromLogs(logs) {
        if (!Array.isArray(logs) || logs.length === 0) return null;
        const total = logs.length;
        const nigeCnt = logs.filter(x => x.kimarite === "nige").length;
        const m1MakuriAtkCnt = logs.filter(x => ["center_makuri_atk", "c2_makuri_atk", "clash_wait"].includes(x.firstMarkPat) || x.kimarite === "makuri").length;
        const sashiCnt = logs.filter(x => x.kimarite === "sashi" || x.kimarite === "makurisashi").length;
        const dochuOvertakeCnt = logs.filter(x => x.dochuType && x.dochuType !== "none").length;
        const turnPowerCnt = logs.filter(x => x.dochuReason === "turn_power" || x.dochuReason === "racer_skill").length;
        const clashWaitCnt = logs.filter(x => x.firstMarkPat === "clash_wait").length;
        const thirdMissCnt = logs.filter(x => x.missedThirdOnly).length;

        const nigeRatio = nigeCnt / total;
        const makuriRatio = m1MakuriAtkCnt / total;
        const sashiRatio = sashiCnt / total;
        const dochuRatio = dochuOvertakeCnt / total;

        const w_course = Math.min(180, Math.max(70, Math.round((100 + (sashiRatio - 0.25) * 85 + (nigeRatio - 0.50) * 35) / 5) * 5));
        const w_exhibit = Math.min(190, Math.max(80, Math.round((105 + dochuRatio * 55 + (turnPowerCnt / total) * 45) / 5) * 5));
        const w_motor = Math.min(190, Math.max(80, Math.round((100 + dochuRatio * 60 + sashiRatio * 35) / 5) * 5));
        const w_slit = Math.min(190, Math.max(80, Math.round((100 + (makuriRatio - 0.20) * 130) / 5) * 5));

        const inModAdj = Math.round((nigeRatio - 0.52) * 24);
        const makuriModAdj = Math.round((makuriRatio - 0.22) * 28);
        const sashiModAdj = Math.round((sashiRatio - 0.24) * 26);
        const waitBonusAdj = Math.min(22, thirdMissCnt * 5 + clashWaitCnt * 6 + dochuOvertakeCnt * 3);

        const venueBiases = {};
        const byVenue = {};
        logs.forEach(item => {
          const v = item.venue || "平和島";
          if (!byVenue[v]) byVenue[v] = [];
          byVenue[v].push(item);
        });
        Object.keys(byVenue).forEach(v => {
          const list = byVenue[v];
          const vc = list.length;
          const vNige = list.filter(x => x.kimarite === "nige").length / vc;
          const vMak = list.filter(x => ["center_makuri_atk", "c2_makuri_atk", "clash_wait"].includes(x.firstMarkPat) || x.kimarite === "makuri").length / vc;
          const vSas = list.filter(x => x.kimarite === "sashi" || x.kimarite === "makurisashi").length / vc;
          const vWait = list.filter(x => x.missedThirdOnly || x.firstMarkPat === "clash_wait" || (x.dochuType && x.dochuType !== "none")).length;
          venueBiases[v] = {
            count: vc,
            inModAdj: Math.round((vNige - 0.52) * 24),
            makuriModAdj: Math.round((vMak - 0.22) * 28),
            sashiModAdj: Math.round((vSas - 0.24) * 26),
            waitBonusAdj: Math.min(22, vWait * 5)
          };
        });

        const learnedObj = {
          type: "BOATRACE_LEARNED_PARAMS",
          sampleCount: total,
          hitRate: Math.round((logs.filter(x => x.isHit).length / total) * 100),
          dochuRate: Math.round(dochuRatio * 100),
          weights: { w_course, w_exhibit, w_motor, w_slit },
          bias: { inModAdj, makuriModAdj, sashiModAdj, waitBonusAdj },
          venueBiases,
          recentLogs: logs.slice(0, 20),
          updatedAt: new Date().toLocaleTimeString()
        };
        try {
          localStorage.setItem("BOATRACE_LEARNED_PARAMS", JSON.stringify(learnedObj));
        } catch (e) {}
        return learnedObj;
      }

      function saveQuickReviewFromSimulator() {
        const vCode = document.getElementById("venueSelect").value;
        const venue = (VENUE_MASTER[vCode] || VENUE_MASTER["04"]).name;
        const raceNo = document.getElementById("raceNoSelect")?.value || "12";
        const grade = document.getElementById("raceGradeSelect")?.value || "G1";
        const f1 = Number(document.getElementById("q_fin1").value);
        const f2 = Number(document.getElementById("q_fin2").value);
        const f3 = Number(document.getElementById("q_fin3").value);
        const actualCombo = `${f1}-${f2}-${f3}`;
        const kimarite = document.getElementById("q_kimarite").value;
        const firstMarkPat = document.getElementById("q_m1pat").value;
        const dochuType = document.getElementById("q_dochu").value;
        const dochuReason = document.getElementById("q_reason").value;

        const aiBets = (latestSimContext?.selectedBets || []).map(b => b.combo);
        const isHit = aiBets.includes(actualCombo);
        const has1st2nd = aiBets.some(c => {
          const [a, b] = c.split("-").map(Number);
          return a === f1 && b === f2;
        });

        let logs = [];
        try {
          const raw = localStorage.getItem("BOATRACE_REVIEW_LOGS");
          if (raw) logs = JSON.parse(raw);
        } catch (e) {}
        if (!Array.isArray(logs)) logs = [];

        const kimMap = { nige: "逃げ", sashi: "差し", makuri: "まくり", makurisashi: "まくり差し", nuki: "抜き" };
        logs.unshift({
          venue,
          raceNo,
          grade,
          actualCombo,
          kimarite,
          kimariteName: kimMap[kimarite] || "逃げ",
          firstMarkPat,
          dochuType,
          dochuReason,
          payout: 0,
          invest: 4000,
          returnYen: isHit ? 6000 : 0,
          isHit,
          missedThirdOnly: !isHit && has1st2nd
        });

        try {
          localStorage.setItem("BOATRACE_REVIEW_LOGS", JSON.stringify(logs));
        } catch (e) {}

        StorageManager.recordVenueRaceResult(vCode, kimarite, dochuType);
        AppStateV3.lastMissReport = LearningEngine.analyzeMissReasons(latestSimContext, {
          fin1: f1, fin2: f2, fin3: f3, kimarite, firstMarkPat, dochuType
        });
        rebuildLearnedParamsFromLogs(logs);
        applyLearnedFeedbackParams(false);
      }

      function resetLearnedFeedback() {
        learnedBias = { inModAdj: 0, makuriModAdj: 0, sashiModAdj: 0, waitBonusAdj: 0, sampleCount: 0 };
        setWeightPreset(100, 100, 100, 100);
        const badge = document.getElementById("learnedCountBadge");
        if (badge) badge.textContent = "補正オフ (標準100%)";
        const bar = document.getElementById("learningDetailBar");
        if (bar) bar.innerHTML = "現在は振り返り学習補正をオフ（初期値100%）にしています。「🔄 蓄積データを再読込・適用」を押すと再度反映されます。";
      }

      function applyLearnedFeedbackParams(promptIfMissing = false) {
        let parsed = null;
        try {
          const rawLogs = localStorage.getItem("BOATRACE_REVIEW_LOGS");
          if (rawLogs) {
            const logsArr = JSON.parse(rawLogs);
            if (Array.isArray(logsArr) && logsArr.length > 0) {
              parsed = rebuildLearnedParamsFromLogs(logsArr);
            }
          }
          if (!parsed) {
            const saved = localStorage.getItem("BOATRACE_LEARNED_PARAMS");
            if (saved) parsed = JSON.parse(saved);
          }
        } catch (e) {}

        if ((!parsed || parsed.type !== "BOATRACE_LEARNED_PARAMS") && promptIfMissing) {
          const raw = prompt("振り返りサイトの「🧠 蓄積データから学習パラメータを生成・コピー」でコピーした学習データ(JSON)を貼り付けてください：");
          if (raw) {
            try {
              parsed = JSON.parse(raw.trim());
              localStorage.setItem("BOATRACE_LEARNED_PARAMS", JSON.stringify(parsed));
            } catch (e) {}
          }
        }

        if (parsed && parsed.weights) {
          document.getElementById("w_course").value = parsed.weights.w_course ?? 100;
          document.getElementById("w_exhibit").value = parsed.weights.w_exhibit ?? 100;
          document.getElementById("w_motor").value = parsed.weights.w_motor ?? 100;
          document.getElementById("w_slit").value = parsed.weights.w_slit ?? 100;

          const vCode = document.getElementById("venueSelect").value;
          const vName = (VENUE_MASTER[vCode] || VENUE_MASTER["04"]).name;
          const vSpecific = parsed.venueBiases && parsed.venueBiases[vName];

          if (vSpecific && vSpecific.count >= 1) {
            learnedBias = { ...vSpecific, sampleCount: parsed.sampleCount || vSpecific.count, venueCount: vSpecific.count };
          } else if (parsed.bias) {
            learnedBias = { ...parsed.bias, sampleCount: parsed.sampleCount || 1, venueCount: 0 };
          }

          const badge = document.getElementById("learnedCountBadge");
          if (badge) {
            badge.textContent = `✅ 蓄積: 全${parsed.sampleCount || 1}R (${vName}:${learnedBias.venueCount || 0}R) 自動反映中`;
          }
          const bar = document.getElementById("learningDetailBar");
          if (bar) {
            bar.innerHTML = `🧠 <strong>全${parsed.sampleCount || 1}レースの振り返りデータ（道中逆転率 ${parsed.dochuRate || 0}%）を自動学習・適用中！</strong><br>` +
              `・自動最適化された重み付け：<strong>[①コース実績:${parsed.weights.w_course}% ／ ②展示気配:${parsed.weights.w_exhibit}% ／ ③勝率・機力:${parsed.weights.w_motor}% ／ ④スリット連動:${parsed.weights.w_slit}%]</strong><br>` +
              `・現在の水面・展開バイアス補正（${vName}）：<strong>[イン補正 ${learnedBias.inModAdj >= 0 ? "+" : ""}${learnedBias.inModAdj} ／ まくり補正 ${learnedBias.makuriModAdj >= 0 ? "+" : ""}${learnedBias.makuriModAdj} ／ 差し補正 ${learnedBias.sashiModAdj >= 0 ? "+" : ""}${learnedBias.sashiModAdj} ／ 3着展開待ち・道中浮上ボーナス +${learnedBias.waitBonusAdj}]</strong>`;
          }

          const qList = document.getElementById("quickAccumulatedList");
          if (qList && Array.isArray(parsed.recentLogs)) {
            qList.innerHTML = parsed.recentLogs.slice(0, 8).map((item, idx) =>
              `<div class="flex items-center justify-between bg-slate-900 px-2 py-1 rounded border border-slate-800">` +
              `<span>#${parsed.sampleCount - idx} <strong>${item.venue}${item.raceNo}R</strong> 確定:<strong class="text-teal-300 font-mono">${item.actualCombo}</strong> (${item.kimariteName})</span>` +
              `<span class="text-[10px] text-amber-300">1M:${item.firstMarkPat || "-"} ／ 道中:${item.dochuType === "none" ? "1M通り" : item.dochuType}</span>` +
              `</div>`
            ).join("");
          }

          runSimulation();
        }
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
          "f_winRate", "f_localWin", "f_g1OnlyRule", "f_ladiesRule", "f_seriesScore", "f_weight",
          "f_courseWin", "f_courseTri", "f_courseKimarite", "f_nigashi", "f_nigashiTri",
          "f_motorBi", "f_exTimeRank", "f_oriTimeRank", "f_vis", "f_partsTilt",
          "f_avgSt", "f_seriesSt", "f_fCount", "f_env"
        ];
        ids.forEach(id => {
          const el = document.getElementById(id);
          if (!el) return;
          if (mode === "all") el.checked = true;
          else if (mode === "chokuzen") {
            el.checked = ["f_exTimeRank", "f_oriTimeRank", "f_vis", "f_partsTilt", "f_seriesSt", "f_env", "f_courseWin", "f_courseKimarite", "f_g1OnlyRule"].includes(id);
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
          1: { id: 1, name: "白井 英治", grade: "A1", fCount: 0, weight: 52.0, winRate: 8.12, biRate: 64.5, triRate: 78.0, localWin: 8.35, g1WinRate: 7.72, g1LocalWin: 7.90, g1CourseWin: 76.5, g1CourseTri: 88.0, g1AvgSt: 0.11, sashiRate: 4.0, makuriRate: 76.5, makurisashiRate: 1.0, waitRentaiRate: 25.0, motorBi: 46.2, motorTri: 63.5, avgSt: 0.12, seriesSt: 0.11, seriesScore: 92, courseWin: 82.0, courseTri: 91.0, nigashi: 0, nigashiTri: 0, parts: "none", tilt: -0.5, exTime: 6.75, exTimeRank: 2, oriTimeRank: 1, visSlit: 1, visTurn: 2, manualTactic: "auto" },
          2: { id: 2, name: "瓜生 正義", grade: "A1", fCount: 0, weight: 52.0, winRate: 7.58, biRate: 56.0, triRate: 72.0, localWin: 7.8, g1WinRate: 7.12, g1LocalWin: 7.28, g1CourseWin: 19.5, g1CourseTri: 64.5, g1AvgSt: 0.13, sashiRate: 16.8, makuriRate: 6.2, makurisashiRate: 1.5, waitRentaiRate: 54.0, motorBi: 41.0, motorTri: 58.0, avgSt: 0.14, seriesSt: 0.14, seriesScore: 84, courseWin: 22.0, courseTri: 68.0, nigashi: 62.5, nigashiTri: 64.0, parts: "none", tilt: -0.5, exTime: 6.79, exTimeRank: 3, oriTimeRank: 2, visSlit: 0, visTurn: 1, manualTactic: "auto" },
          3: { id: 3, name: "澤田 尚也", grade: "A1", fCount: 1, weight: 52.0, winRate: 7.15, biRate: 53.0, triRate: 70.5, localWin: 7.1, g1WinRate: 6.45, g1LocalWin: 6.40, g1CourseWin: 20.0, g1CourseTri: 60.0, g1AvgSt: 0.13, sashiRate: 4.2, makuriRate: 13.5, makurisashiRate: 9.8, waitRentaiRate: 48.0, motorBi: 44.5, motorTri: 61.0, avgSt: 0.13, seriesSt: 0.13, seriesScore: 82, courseWin: 24.0, courseTri: 65.0, nigashi: 0, nigashiTri: 58.0, parts: "none", tilt: 0.0, exTime: 6.71, exTimeRank: 1, oriTimeRank: 3, visSlit: 2, visTurn: 0, manualTactic: "auto" },
          4: { id: 4, name: "大峯 豊", grade: "A1", fCount: 0, weight: 52.0, winRate: 7.24, biRate: 55.2, triRate: 73.0, localWin: 7.45, g1WinRate: 6.68, g1LocalWin: 6.84, g1CourseWin: 17.5, g1CourseTri: 70.0, g1AvgSt: 0.13, sashiRate: 5.5, makuriRate: 9.2, makurisashiRate: 11.4, waitRentaiRate: 58.0, motorBi: 48.0, motorTri: 66.0, avgSt: 0.14, seriesSt: 0.13, seriesScore: 89, courseWin: 19.5, courseTri: 74.0, nigashi: 0, nigashiTri: 79.2, parts: "ring", tilt: -0.5, exTime: 6.75, exTimeRank: 2, oriTimeRank: 1, visSlit: 1, visTurn: 2, manualTactic: "auto" },
          5: { id: 5, name: "篠崎 仁志", grade: "A1", fCount: 0, weight: 52.0, winRate: 7.4, biRate: 54.0, triRate: 69.0, localWin: 7.3, g1WinRate: 6.90, g1LocalWin: 6.82, g1CourseWin: 10.5, g1CourseTri: 55.0, g1AvgSt: 0.13, sashiRate: 2.8, makuriRate: 3.2, makurisashiRate: 8.6, waitRentaiRate: 52.0, motorBi: 39.5, motorTri: 55.0, avgSt: 0.14, seriesSt: 0.15, seriesScore: 78, courseWin: 12.0, courseTri: 58.0, nigashi: 0, nigashiTri: 56.0, parts: "none", tilt: -0.5, exTime: 6.80, exTimeRank: 3, oriTimeRank: 3, visSlit: 0, visTurn: 1, manualTactic: "auto" },
          6: { id: 6, name: "吉田 裕平", grade: "A1", fCount: 0, weight: 52.0, winRate: 7.05, biRate: 51.5, triRate: 67.0, localWin: 6.95, g1WinRate: 6.32, g1LocalWin: 6.24, g1CourseWin: 5.0, g1CourseTri: 42.0, g1AvgSt: 0.13, sashiRate: 1.8, makuriRate: 1.2, makurisashiRate: 3.4, waitRentaiRate: 41.0, motorBi: 38.0, motorTri: 54.0, avgSt: 0.13, seriesSt: 0.14, seriesScore: 76, courseWin: 6.0, courseTri: 46.0, nigashi: 0, nigashiTri: 45.0, parts: "none", tilt: -0.5, exTime: 6.82, exTimeRank: 3, oriTimeRank: 3, visSlit: 0, visTurn: 0, manualTactic: "auto" }
        };

        setCoursePreset([1, 2, 3, 4, 5, 6], 4, "normal");
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
        if (data.odds3t && Object.keys(data.odds3t).length > 0) {
          liveOddsMap = data.odds3t;
        }
        if (data.settledResult) {
          settledPayoutInfo = data.settledResult;
        }
        const oddsCount = Object.keys(liveOddsMap).length;
        const payStr = settledPayoutInfo?.payout3t ? ` ｜ 確定3連単配当: ${settledPayoutInfo.payout3t.toLocaleString()}円` : (oddsCount > 0 ? ` ｜ 3連単オッズ${oddsCount}通り自動取得済` : "");
        const names = [1,2,3,4,5,6].map(i => `${i}.${boatsData[i].name}`).join(" / ");
        const gLabel = data.meta?.raceGrade ? `[${data.meta.raceGrade}] ` : "";
        document.getElementById("fetchStatus").textContent = `✅ 公式反映済 ${gLabel}：${names}${payStr}`;
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
          const attackSummary = b === 1
            ? `逃${(d.makuriRate || d.courseWin || 70).toFixed(0)}%`
            : b === 2
              ? `差${(d.sashiRate || 14).toFixed(1)}% / 捲${(d.makuriRate || 5).toFixed(1)}%`
              : `捲${(d.makuriRate || 7).toFixed(1)}% / 捲差${(d.makurisashiRate || 6).toFixed(1)}% / 差${(d.sashiRate || 3).toFixed(1)}%`;

          const card = document.createElement("div");
          card.className = "bg-slate-900 border border-slate-800 rounded-xl overflow-hidden";
          card.innerHTML = `
          <div class="p-2.5 flex flex-wrap items-center justify-between gap-2">
            <div class="flex items-center gap-1.5 flex-wrap">
              <span class="boat-${b} w-6 h-6 rounded font-black text-xs flex items-center justify-center">${b}</span>
              <input type="text" value="${d.name}" onchange="updateBoat(${b},'name',this.value)" class="bg-slate-950 px-1.5 py-0.5 rounded border border-slate-700 font-bold text-xs text-white w-28 focus:outline-none" />
              <select onchange="updateBoat(${b},'grade',this.value)" class="text-[11px] font-bold">
                <option value="A1" ${d.grade === "A1" ? "selected" : ""}>A1</option><option value="A2" ${d.grade === "A2" ? "selected" : ""}>A2</option>
                <option value="B1" ${d.grade === "B1" ? "selected" : ""}>B1</option><option value="B2" ${d.grade === "B2" ? "selected" : ""}>B2</option>
              </select>
              <select onchange="updateBoat(${b},'fCount',Number(this.value))" class="text-[11px] ${d.fCount > 0 ? "text-rose-400 font-bold" : ""}">
                <option value="0" ${d.fCount === 0 ? "selected" : ""}>F0</option><option value="1" ${d.fCount === 1 ? "selected" : ""}>F1</option><option value="2" ${d.fCount === 2 ? "selected" : ""}>F2</option>
              </select>
              <select onchange="updateBoat(${b},'isLady',this.value==='true')" class="text-[11px] ${(d.isLady || d.weight <= 49.0) ? "text-pink-300 font-bold border-pink-500/50" : "text-slate-400"}" title="男子選手 / 女子選手">
                <option value="false" ${!(d.isLady || d.weight <= 49.0) ? "selected" : ""}>♂男</option>
                <option value="true" ${(d.isLady || d.weight <= 49.0) ? "selected" : ""}>💃女</option>
              </select>
              <span class="text-[10px] font-mono px-1.5 py-0.5 rounded ${g1Active ? "bg-amber-950 text-amber-300 border border-amber-600/40 font-bold" : "bg-slate-800 text-sky-300"}">${activeWinDisp}</span>
              <span class="text-[10px] font-mono px-1.5 py-0.5 rounded bg-emerald-950/70 text-emerald-300 border border-emerald-700/40">${attackSummary}</span>
              <span class="text-[10px] font-mono px-1.5 py-0.5 rounded ${exBadgeCls}">${(d.exTime || 6.80).toFixed(2)}s (${exRankLabel})</span>
            </div>
            <div class="flex flex-wrap items-center gap-1 text-[11px]">
              <span class="text-pink-400 font-bold">🎯1M攻め</span>
              <select onchange="updateBoat(${b},'manualTactic',this.value)" class="${d.manualTactic !== "auto" ? "tactic-select" : ""}">
                <option value="auto" ${d.manualTactic === "auto" ? "selected" : ""}>🤖AI自動判定</option>
                <option value="nige" ${d.manualTactic === "nige" ? "selected" : ""}>🛡️逃げ(先マイ)</option>
                <option value="sashi" ${d.manualTactic === "sashi" ? "selected" : ""}>📐差し(1M差し)</option>
                <option value="nibanzashi" ${d.manualTactic === "nibanzashi" ? "selected" : ""}>📐二番差し(連動差)</option>
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
          <div id="detail_${b}" class="${expandedDetails.has(`detail_${b}`) || allDetailsOpen ? "" : "hidden"} border-t border-slate-800 bg-slate-950/60 p-2.5 grid grid-cols-2 sm:grid-cols-3 gap-2 text-[11px]">
            <div><span class="text-slate-400 block">通算 全国勝率 / 当地勝率</span><div class="flex gap-1 mt-0.5"><input type="number" step="0.01" value="${d.winRate}" onchange="updateBoat(${b},'winRate',parseFloat(this.value))" class="w-1/2"/><input type="number" step="0.01" value="${d.localWin}" onchange="updateBoat(${b},'localWin',parseFloat(this.value))" class="w-1/2"/></div></div>
            <div class="bg-amber-950/30 p-1 rounded border border-amber-600/30"><span class="text-amber-300 font-bold block">🏆G1限定 勝率 / 当地</span><div class="flex gap-1 mt-0.5"><input type="number" step="0.01" value="${d.g1WinRate || 6.0}" onchange="updateBoat(${b},'g1WinRate',parseFloat(this.value))" class="w-1/2 text-amber-200 font-bold"/><input type="number" step="0.01" value="${d.g1LocalWin || 6.0}" onchange="updateBoat(${b},'g1LocalWin',parseFloat(this.value))" class="w-1/2 text-amber-200 font-bold"/></div></div>
            <div><span class="text-slate-400 block">通算 コース1着/3連率(%)</span><div class="flex gap-1 mt-0.5"><input type="number" step="0.1" value="${d.courseWin}" onchange="updateBoat(${b},'courseWin',parseFloat(this.value))" class="w-1/2"/><input type="number" step="0.1" value="${d.courseTri}" onchange="updateBoat(${b},'courseTri',parseFloat(this.value))" class="w-1/2"/></div></div>
            <div class="bg-amber-950/30 p-1 rounded border border-amber-600/30"><span class="text-amber-300 font-bold block">🏆G1コース1着/3連率(%)</span><div class="flex gap-1 mt-0.5"><input type="number" step="0.1" value="${d.g1CourseWin || d.courseWin}" onchange="updateBoat(${b},'g1CourseWin',parseFloat(this.value))" class="w-1/2 text-amber-200 font-bold"/><input type="number" step="0.1" value="${d.g1CourseTri || d.courseTri}" onchange="updateBoat(${b},'g1CourseTri',parseFloat(this.value))" class="w-1/2 text-amber-200 font-bold"/></div></div>
            <div class="bg-emerald-950/30 p-1 rounded border border-emerald-600/30 col-span-2 sm:col-span-2">
              <span class="text-emerald-300 font-bold block">⚔️ コース別 攻め成功率(%) [📐差し率 / 🔥まくり率 / ⚡まくり差し率 / ⏳展開待ち連対率]</span>
              <div class="grid grid-cols-4 gap-1 mt-0.5">
                <input type="number" step="0.1" value="${d.sashiRate ?? 10.0}" onchange="updateBoat(${b},'sashiRate',parseFloat(this.value))" class="text-emerald-200 font-bold" title="差し率(%)" />
                <input type="number" step="0.1" value="${d.makuriRate ?? 8.0}" onchange="updateBoat(${b},'makuriRate',parseFloat(this.value))" class="text-rose-200 font-bold" title="まくり率(%)" />
                <input type="number" step="0.1" value="${d.makurisashiRate ?? 6.0}" onchange="updateBoat(${b},'makurisashiRate',parseFloat(this.value))" class="text-amber-200 font-bold" title="まくり差し率(%)" />
                <input type="number" step="0.1" value="${d.waitRentaiRate ?? 45.0}" onchange="updateBoat(${b},'waitRentaiRate',parseFloat(this.value))" class="text-purple-200 font-bold" title="展開待ち連対率(%)" />
              </div>
            </div>
            <div><span class="text-slate-400 block">モーター2連/3連(%)</span><div class="flex gap-1 mt-0.5"><input type="number" step="0.1" value="${d.motorBi}" onchange="updateBoat(${b},'motorBi',parseFloat(this.value))" class="w-1/2"/><input type="number" step="0.1" value="${d.motorTri}" onchange="updateBoat(${b},'motorTri',parseFloat(this.value))" class="w-1/2"/></div></div>
            <div><span class="text-slate-400 block">通算ST / G1限定ST / 展ST</span><div class="flex gap-1 mt-0.5"><input type="number" step="0.01" value="${d.avgSt}" onchange="updateBoat(${b},'avgSt',parseFloat(this.value))" class="w-1/3" title="通算ST"/><input type="number" step="0.01" value="${d.g1AvgSt || d.avgSt}" onchange="updateBoat(${b},'g1AvgSt',parseFloat(this.value))" class="w-1/3 text-amber-200 font-bold" title="G1限定ST"/><input type="number" step="0.01" value="${d.seriesSt}" onchange="updateBoat(${b},'seriesSt',parseFloat(this.value))" class="w-1/3" title="今節/展示ST"/></div></div>
            <div><span class="text-slate-400 block">節間点/体重/2C逃がし率</span><div class="flex gap-1 mt-0.5"><input type="number" value="${d.seriesScore}" onchange="updateBoat(${b},'seriesScore',parseFloat(this.value))" class="w-1/3"/><input type="number" step="0.5" value="${d.weight}" onchange="updateBoat(${b},'weight',parseFloat(this.value))" class="w-1/3"/><input type="number" step="0.1" value="${d.nigashi}" onchange="updateBoat(${b},'nigashi',parseFloat(this.value))" class="w-1/3" title="2C逃がし率"/></div></div>
            <div class="col-span-2 sm:col-span-3"><span class="text-slate-400 block">展示時計(秒) / 展示順位 / オリ展順位 / スリット伸気配 / 部品交換</span><div class="grid grid-cols-5 gap-1 mt-0.5">
              <input type="number" step="0.01" value="${(d.exTime || 6.80).toFixed(2)}" onchange="updateBoat(${b},'exTime',parseFloat(this.value))" class="font-mono text-amber-300" />
              <select onchange="updateBoat(${b},'exTimeRank',Number(this.value))"><option value="1" ${d.exTimeRank === 1 ? "selected" : ""}>展1位</option><option value="2" ${d.exTimeRank === 2 ? "selected" : ""}>展2位</option><option value="3" ${d.exTimeRank === 3 ? "selected" : ""}>展普</option><option value="5" ${d.exTimeRank === 5 ? "selected" : ""}>展劣</option></select>
              <select onchange="updateBoat(${b},'oriTimeRank',Number(this.value))"><option value="0" ${d.oriTimeRank === 0 ? "selected" : ""}>オ未</option><option value="1" ${d.oriTimeRank === 1 ? "selected" : ""}>オ1位</option><option value="2" ${d.oriTimeRank === 2 ? "selected" : ""}>オ上</option><option value="3" ${d.oriTimeRank === 3 ? "selected" : ""}>オ普</option><option value="5" ${d.oriTimeRank === 5 ? "selected" : ""}>オ劣</option></select>
              <select onchange="updateBoat(${b},'visSlit',Number(this.value))"><option value="2" ${d.visSlit === 2 ? "selected" : ""}>★伸◎</option><option value="1" ${d.visSlit === 1 ? "selected" : ""}>◎良</option><option value="0" ${d.visSlit === 0 ? "selected" : ""}>□普</option><option value="-1" ${d.visSlit === -1 ? "selected" : ""}>▲劣</option></select>
              <select onchange="updateBoat(${b},'parts',this.value)"><option value="none" ${d.parts === "none" ? "selected" : ""}>部品無</option><option value="ring" ${d.parts === "ring" ? "selected" : ""}>リング◎</option><option value="elec" ${d.parts === "elec" ? "selected" : ""}>電気</option><option value="body" ${d.parts === "body" ? "selected" : ""}>ボデー</option><option value="shaft" ${d.parts === "shaft" ? "selected" : ""}>シャフト×</option></select>
            </div></div>
          </div>`;
          container.appendChild(card);
        }
      }

      function updateBoat(b, key, val) {
        boatsData[b][key] = val;
        if (key === "exTime") recalculateExRanksFromTime();
        if (["manualTactic", "exTime", "exTimeRank", "g1WinRate", "winRate", "grade", "sashiRate", "makuriRate", "makurisashiRate"].includes(key)) {
          renderBoatCards();
        }
        runSimulation();
      }

      
      // =========================================================
      // 他艇展開連動・動的相関エンジン (Inter-Boat Tactical Coupling Engine)
      // 単純な個人成績率だけでなく、他艇の攻め手（内壁の有無・凹み・2C挙動・センター仕掛け・イン信頼度）
      // に連動して、各艇の「まくり率」「まくり差し率」「差し率」「展開待ち率」を動的にリアルタイム補正！
      // =========================================================
      function applyInterBoatCoupling(courseEval, kadoCourse, deepIn, windDir, windSpeed, vSashiMod, vMakuriMod, cw) {
        const couplingNotes = [];
        const c1 = courseEval[1];
        const c2 = courseEval[2];
        const c3 = courseEval[3];
        const c4 = courseEval[4];

        // 1. 各艇の理由タグ初期化
        for (let c = 1; c <= 6; c++) {
          courseEval[c].couplingReason = "";
        }

        // ---------------------------------------------------------
        // Step 1: 隣接艇のスリット比較（内壁の厚さ vs 凹みによる壁崩壊）
        // ---------------------------------------------------------
        for (let c = 2; c <= 6; c++) {
          const cur = courseEval[c];
          const inner = courseEval[c - 1];
          const stDiff = Math.round((inner.expectedSt - cur.expectedSt) * 100) / 100; // >0: 内隣が遅れ(凹み), <0: 内隣が先行(壁)

          if (stDiff >= 0.02) {
            // 内隣が凹んだ場合：外のまくりを遮る壁が崩壊！
            const makuriBoost = Math.min(22.0, Math.round(stDiff * 280 * 10) / 10);
            const msBoost = Math.min(15.0, Math.round(stDiff * 180 * 10) / 10);
            cur.effMakuriRate = Math.min(68.0, cur.effMakuriRate + makuriBoost);
            cur.effMsRate = Math.min(55.0, cur.effMsRate + msBoost);
            cur.couplingReason = `⚠️${c-1}C凹み(ST差+${stDiff.toFixed(2)}s)で壁崩壊 ➔ まくり率+${makuriBoost}%／捲差+${msBoost}%`;
            couplingNotes.push(`${c}コース: ${cur.couplingReason}`);
          } else if (stDiff <= -0.02) {
            // 内隣が同体以上で先に出ている場合：強固な壁！
            const wallPenalty = Math.min(18.0, Math.round(Math.abs(stDiff) * 200 * 10) / 10);
            cur.effMakuriRate = Math.max(1.0, cur.effMakuriRate - wallPenalty);
            cur.couplingReason = `🛡️${c-1}C壁厚くST先行 ➔ まくり率-${wallPenalty}%(外マイ抑制)`;
            couplingNotes.push(`${c}コース: ${cur.couplingReason}`);
          }
        }

        // ---------------------------------------------------------
        // Step 2: 2コースの攻め手連動（差し構え vs ジカまくり）
        // ---------------------------------------------------------
        if (c2.b.manualTactic === "makuri" || (c2.b.manualTactic === "auto" && (c2.effMakuriRate >= c2.effSashiRate + 2.0 || c2.slitPower - c1.slitPower >= 10))) {
          // 2コースがジカまくりに行く場合：1Cと2Cが1Mで競り合ってイン共倒れリスク激増！
          c1.effMakuriRate = Math.max(12.0, c1.effMakuriRate - 18.0);
          c3.effSashiRate = Math.min(65.0, c3.effSashiRate + 18.0); // 3Cの「2Cまくり連動差し」が極大化
          c3.couplingReason = (c3.couplingReason ? c3.couplingReason + " ／ " : "") + "🔥2Cジカまくり競り合い ➔ 3C最内差し場急拡大(+18%)";
          courseEval[5].effWaitRate = Math.min(90.0, courseEval[5].effWaitRate + 14.0);
          courseEval[6].effWaitRate = Math.min(92.0, courseEval[6].effWaitRate + 16.0);
          couplingNotes.push("2コース: ジカまくり攻め予測 ➔ イン逃げ率急落＆3C連動差し・外枠展開待ちが急浮上");
        } else {
          // 2コースが差し構え（逃がし率が高い場合）：1Cが安心して先マイできる
          if (c2.b.nigashi >= 54.0) {
            c1.effMakuriRate = Math.min(92.0, c1.effMakuriRate + 4.5);
            c1.couplingReason = "🛡️2C壁厚く逃がし率高(+4.5%)";
          }
        }

        // ---------------------------------------------------------
        // Step 3: カド受け（3コース）とカド（4コース）の攻防連動
        // ---------------------------------------------------------
        if (kadoCourse === 4) {
          const kadoStDiff = Math.round((c3.expectedSt - c4.expectedSt) * 100) / 100;
          if (kadoStDiff >= 0.02) {
            c4.effMakuriRate = Math.min(70.0, c4.effMakuriRate + 14.0);
            c4.couplingReason = (c4.couplingReason ? c4.couplingReason + " ／ " : "") + "🔥3Cカド受け凹み ➔ カドまくり率+14%";
            couplingNotes.push("4カド: 3Cカド受け崩壊によりカドまくり成功率が急上昇");
          } else if (kadoStDiff <= -0.02) {
            c4.effMakuriRate = Math.max(2.0, c4.effMakuriRate - 12.0);
            c4.effMsRate = Math.min(55.0, c4.effMsRate + 6.0);
            c4.couplingReason = (c4.couplingReason ? c4.couplingReason + " ／ " : "") + "🛡️3Cカド受け強固 ➔ カドまくり率-12%(捲差へシフト)";
            couplingNotes.push("4カド: 3Cがカド受けの壁となり、カドまくり封じ(まくり差しへ)");
          }
        }

        // ---------------------------------------------------------
        // Step 4: センター（3C/4C）のまくり強襲連動（外枠の展開待ち最内差し＆まくり差し場発生）
        // ---------------------------------------------------------
        let centerMakuriCourse = null;
        if (c3.b.manualTactic === "makuri" || (c3.b.manualTactic === "auto" && c3.effMakuriRate >= 24.0)) centerMakuriCourse = 3;
        if (c4.b.manualTactic === "makuri" || (c4.b.manualTactic === "auto" && c4.effMakuriRate >= 26.0)) centerMakuriCourse = 4;

        if (centerMakuriCourse) {
          const nextC = centerMakuriCourse + 1;
          if (courseEval[nextC]) {
            // まくり艇の外隣：インとまくりの間にぽっかり空いた「まくり差し場」を突く
            const msBoost = 15.0;
            courseEval[nextC].effMsRate = Math.min(60.0, courseEval[nextC].effMsRate + msBoost);
            courseEval[nextC].couplingReason = (courseEval[nextC].couplingReason ? courseEval[nextC].couplingReason + " ／ " : "") + `⚡${centerMakuriCourse}C強襲連動 ➔ まくり差し場発生(+${msBoost}%)`;
          }
          // 5コース・6コース：センターがまくって大外へ流れた内側のガラ空き水面（最内・内切り込み）を突く！
          for (let c = Math.max(5, nextC); c <= 6; c++) {
            const waitBoost = c === 5 ? 16.0 : 22.0;
            courseEval[c].effWaitRate = Math.min(94.0, courseEval[c].effWaitRate + waitBoost);
            courseEval[c].couplingReason = (courseEval[c].couplingReason ? courseEval[c].couplingReason + " ／ " : "") + `⏳${centerMakuriCourse}C仕掛けの1Mもつれ ➔ 展開待ち(最内差し)連対率+${waitBoost}%`;
          }
          couplingNotes.push(`${centerMakuriCourse}コースのまくり仕掛け予測 ➔ イン抵抗で大外もつれ、5Cまくり差し＆6C展開待ち(最内差し)成功率が急上昇`);
        }

        // ---------------------------------------------------------
        // Step 5: 1コース（イン）信頼度連動
        // ---------------------------------------------------------
        if (c1.effMakuriRate >= 68.0) {
          // 強固なイン逃げ水準：外枠の強引なまくり成功率は抑制
          for (let c = 2; c <= 6; c++) {
            courseEval[c].effMakuriRate = Math.max(1.0, courseEval[c].effMakuriRate - 5.0);
          }
        } else if (c1.effMakuriRate <= 42.0 || deepIn === "deep") {
          // 脆いイン（逃げ率42%未満または深イン）：1Mでターンが膨らみ、差し・まくり差しが連動急上昇！
          c2.effSashiRate = Math.min(60.0, c2.effSashiRate + 9.0);
          c3.effMsRate = Math.min(58.0, c3.effMsRate + 9.0);
          c1.couplingReason = (c1.couplingReason ? c1.couplingReason + " ／ " : "") + "⚠️イン逃げ脆弱(逃げ率42%未満/深イン)";
          c2.couplingReason = (c2.couplingReason ? c2.couplingReason + " ／ " : "") + "📐インターン流れ予測 ➔ 2C差し率+9%";
          c3.couplingReason = (c3.couplingReason ? c3.couplingReason + " ／ " : "") + "⚡インターン流れ予測 ➔ 3Cまくり差し率+9%";
          couplingNotes.push("1コース: イン信頼度低下 ➔ 2C差し・3Cまくり差し成功率が連動上昇(+9%)");
        }

        // クランプ処理（0.5%〜95.0%）
        for (let c = 1; c <= 6; c++) {
          const obj = courseEval[c];
          obj.effSashiRate = Math.max(0.5, Math.min(60.0, obj.effSashiRate));
          obj.effMakuriRate = Math.max(0.5, Math.min(94.0, obj.effMakuriRate));
          obj.effMsRate = Math.max(0.5, Math.min(60.0, obj.effMsRate));
          obj.effWaitRate = Math.max(5.0, Math.min(94.0, obj.effWaitRate));
          if (!obj.couplingReason) obj.couplingReason = "標準水準(同体並走)";
        }

        return couplingNotes;
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

        const vInMod = (af.env ? venue.inMod : 0) + (learnedBias.inModAdj || 0);
        const vMakuriMod = (af.env ? venue.makuriMod : 0) + (learnedBias.makuriModAdj || 0);
        const vSashiMod = (af.env ? venue.sashiMod : 0) + (learnedBias.sashiModAdj || 0);

        const courseEval = {};
        courseOrder.forEach((boatId, idx) => {
          const courseNo = idx + 1;
          const b = boatsData[boatId];
          const isDash = courseNo >= kadoCourse;
          const isKado = courseNo === kadoCourse;

          const ladiesMode = document.getElementById("ladiesModeSelect")?.value || "exclude";
          const isFemaleRacer = Boolean(b.isLady || b.weight <= 49.0);
          const useLadiesData = af.ladiesRule && ladiesMode === "include";
          const excludeLadiesInflation = !af.ladiesRule || ladiesMode === "exclude";

          let effWinRate = g1Active ? (b.g1WinRate ?? b.winRate) : b.winRate;
          let effLocalWin = g1Active ? (b.g1LocalWin ?? b.localWin) : b.localWin;
          let effCourseWin = g1Active ? (b.g1CourseWin ?? b.courseWin) : b.courseWin;
          let effCourseTri = g1Active ? (b.g1CourseTri ?? b.courseTri) : b.courseTri;
          let effAvgSt = g1Active ? (b.g1AvgSt ?? b.avgSt) : b.avgSt;

          if (excludeLadiesInflation && isFemaleRacer) {
            // 女子戦データを入れない（女子戦でのB級相手かさ増し勝率・コース実績を割引補正）
            effWinRate = Math.max(3.5, effWinRate - 0.55);
            effLocalWin = Math.max(3.5, effLocalWin - 0.50);
            effCourseWin = Math.max(2.0, effCourseWin * 0.86);
            effCourseTri = Math.max(15.0, effCourseTri * 0.90);
          } else if (useLadiesData) {
            // 女子戦データを入れる（女子戦特有の2・3コースまくり増、道中逆転・抜き増、軽量ダッシュ有利を反映）
            if (courseNo >= 2 && courseNo <= 4) effCourseWin = Math.min(85.0, effCourseWin * 1.12);
          }

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
          if (b.manualTactic === "sashi" || b.manualTactic === "nibanzashi") baseSt -= 0.005;
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

          // 当日のコース環境補正を加味した「コース別攻め成功率(%)」の算出
          const envSashiAdj = (windDir === "tail" ? windSpeed * 0.8 : 0) + (tide === "high" ? 1.5 : 0) + vSashiMod * 0.4 + (b.visTurn * 1.5);
          const envMakuriAdj = (windDir === "head" ? windSpeed * 0.9 : 0) + (tide === "low" ? 1.8 : 0) + vMakuriMod * 0.45 + (isKado ? 3.5 : 0) + (b.visSlit * 1.8);
          const envMsAdj = (isKado ? 2.5 : 0) + (b.visTurn * 1.4) + (b.visSlit * 1.2) + vSashiMod * 0.3;

          const effSashiRate = Math.max(0.5, Math.min(55.0, (b.sashiRate ?? 10.0) + envSashiAdj));
          const effMakuriRate = courseNo === 1
            ? Math.max(25.0, Math.min(92.0, effCourseWin + vInMod - (deepIn === "deep" ? 12 : deepIn === "semi" ? 5 : 0)))
            : Math.max(0.5, Math.min(48.0, (b.makuriRate ?? 6.0) + envMakuriAdj));
          const effMsRate = Math.max(0.5, Math.min(45.0, (b.makurisashiRate ?? 5.0) + envMsAdj));
          const effWaitRate = Math.max(10.0, Math.min(88.0, (b.waitRentaiRate ?? 42.0) + (b.visTurn * 3.5) + (courseNo >= 4 ? (learnedBias.waitBonusAdj || 0) : 0)));

          const kimariteFirstBonus = af.courseKimarite
            ? (courseNo === 1 ? effMakuriRate * 0.18 : (effSashiRate * 0.42 + effMakuriRate * 0.52 + effMsRate * 0.48)) * cw.wc
            : 0;
          const kimaritePlaceBonus = af.courseKimarite
            ? (effWaitRate * 0.25 + effSashiRate * 0.22 + effMsRate * 0.25) * cw.wc
            : 0;

          const cWinBonus = af.courseWin ? (effCourseWin * 0.40 * cw.wc) : ([65, 18, 15, 13, 7, 3][courseNo - 1] * 0.40);
          const cTriBonus = af.courseTri ? (effCourseTri * 0.50 * cw.wc) : ([75, 55, 52, 48, 38, 25][courseNo - 1] * 0.50);

          courseEval[courseNo] = {
            courseNo,
            boatId,
            b,
            effWinRate,
            effLocalWin,
            effCourseWin,
            effCourseTri,
            effAvgSt,
            effSashiRate,
            effMakuriRate,
            effMsRate,
            effWaitRate,
            isDash,
            isKado,
            expectedSt: Math.max(0.04, Math.min(0.28, baseSt)),
            slitPower,
            firstScore: blendedPower + weightBonus + partsBonus + totalExBonus + cWinBonus + kimariteFirstBonus,
            placeScore: blendedPower + weightBonus + partsBonus + totalExBonus + cTriBonus + kimaritePlaceBonus + (af.vis ? b.visTurn * 5 * cw.we : 0),
            roleText: "標準",
            attackType: "auto"
          };
        });

        // ★他艇展開連動・動的相関エンジンの実行（他艇の壁・凹み・攻め手に連動して成功率を動的補正）
        const couplingNotes = applyInterBoatCoupling(courseEval, kadoCourse, deepIn, windDir, windSpeed, vSashiMod, vMakuriMod, cw);

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

        // =========================================================
        // 📊 過去レース統計（会場特性×蓄積DB×風潮×ST段差×選手過去決まり手）
        // から導く「6艇整合1マーク展開シナリオ分析」
        // =========================================================
        const c1 = courseEval[1], c2 = courseEval[2], c3 = courseEval[3], c4 = courseEval[4], c5 = courseEval[5], c6 = courseEval[6];
        const kadoObj = courseEval[kadoCourse] || c4;
        const receiverObj = courseEval[Math.max(1, kadoCourse - 1)] || c3;

        let logs = [];
        try {
          logs = JSON.parse(localStorage.getItem("BOATRACE_REVIEW_LOGS") || "[]");
        } catch (e) {}
        const venueLogs = logs.filter(x => x.venue === venue.name);
        const targetLogs = venueLogs.length >= 3 ? venueLogs : logs;
        const logTotal = targetLogs.length;
        const logMakuriRatio = logTotal > 0 ? targetLogs.filter(x => ["center_makuri_atk", "c2_makuri_atk"].includes(x.firstMarkPat) || x.kimarite === "makuri").length / logTotal : 0.20;
        const logSashiRatio = logTotal > 0 ? targetLogs.filter(x => ["in_flow", "c2_sashi_atk"].includes(x.firstMarkPat) || x.kimarite === "sashi").length / logTotal : 0.22;
        const logClashRatio = logTotal > 0 ? targetLogs.filter(x => x.firstMarkPat === "clash_wait" || (x.dochuType && x.dochuType !== "none")).length / logTotal : 0.15;

        const stDiff2over1 = c1.expectedSt - c2.expectedSt;
        const stDiff3over2 = c2.expectedSt - c3.expectedSt;
        const stDiffKado = receiverObj.expectedSt - kadoObj.expectedSt;

        const scWeights = {
          in_nige: Math.max(15, c1.effMakuriRate * 1.15 + (c2.b.nigashi - 50) * 0.4 + (stDiffKado < 0.02 ? 12 : -10) + vInMod),
          c2_sashi: Math.max(8, c2.effSashiRate * 1.7 + (windDir === "tail" ? windSpeed * 2.5 : 0) + (deepIn !== "normal" ? 8 : 0) + vSashiMod + logSashiRatio * 20),
          c3_ms: Math.max(8, c3.effMsRate * 1.85 + (c3.b.visTurn * 4) + (windDir === "head" ? windSpeed * 1.5 : 0) + vSashiMod * 0.6),
          c3_makuri: Math.max(5, c3.effMakuriRate * 1.4 + (stDiff3over2 >= 0.02 ? 22 : -6) + (c3.b.exTimeRank === 1 ? 8 : 0) + vMakuriMod),
          c4_makuri: Math.max(6, kadoObj.effMakuriRate * 1.5 + (stDiffKado >= 0.025 ? 28 : -8) + (kadoObj.b.exTimeRank === 1 ? 8 : 0) + (deepIn === "deep" ? 12 : 0) + vMakuriMod + logMakuriRatio * 20),
          clash_wait: Math.max(5, (c5.effWaitRate + c6.effWaitRate) * 0.18 + ((stDiff3over2 >= 0.02 || stDiffKado >= 0.02) && c1.expectedSt <= 0.13 ? 18 : 0) + logClashRatio * 25)
        };
        const scTotal = Object.values(scWeights).reduce((a, b) => a + b, 0);

        const c3DefaultTac = c3.effSashiRate >= c3.effMsRate && c3.effSashiRate >= c3.effMakuriRate ? "nibanzashi" : (c3.effMsRate >= c3.effMakuriRate ? "makurisashi" : "sotomai");
        const scenarioCatalog = [
          {
            key: "in_nige",
            name: "🛡️ イン先マイ・王道隊形",
            pct: Math.round((scWeights.in_nige / scTotal) * 100),
            desc: `1C${c1.b.name}が先マイ押し切り。2C${c2.b.name}がブイ際差し、3C${c3.b.name}が${c3DefaultTac === "nibanzashi" ? "二番差し" : c3DefaultTac === "makurisashi" ? "まくり差し" : "外マイ追走"}、4C${c4.b.name}が二番差しで追走する過去最多の基本形。`,
            plan: { 1: "nige", 2: "sashi", 3: c3DefaultTac, 4: "nibanzashi", 5: "makurisashi", 6: "tenkaimachi" }
          },
          {
            key: "c2_sashi",
            name: "📐 イン膨らみ・2C差し＆3C/4C二番差し展開",
            pct: Math.round((scWeights.c2_sashi / scTotal) * 100),
            desc: `1Cが風・波で僅かに膨らんだ懐を2C${c2.b.name}(差し率${c2.effSashiRate.toFixed(1)}%)が差し、3C・4Cが二番差しで連動追走する展開。`,
            plan: { 1: "nige", 2: "sashi", 3: "nibanzashi", 4: "nibanzashi", 5: "makurisashi", 6: "tenkaimachi" }
          },
          {
            key: "c3_attack",
            name: "⚡ 3コースまくり差し強襲展開",
            pct: Math.round((scWeights.c3_ms / scTotal) * 100),
            desc: `3C${c3.b.name}(捲差率${c3.effMsRate.toFixed(1)}%)が1Cと2Cの間を鋭く割るスピード旋回。1Cが内粘り、4C二番差し・5Cが連動浮上。`,
            plan: { 1: "nige", 2: "sashi", 3: "makurisashi", 4: "nibanzashi", 5: "makurisashi", 6: "tenkaimachi" }
          },
          {
            key: "c4_makuri",
            name: `🔥 ${kadoCourse}カドまくり一撃（壁崩壊）展開`,
            pct: Math.round((scWeights.c4_makuri / scTotal) * 100),
            desc: `カド受け${kadoCourse - 1}Cの遅れを突いて${kadoCourse}C${kadoObj.b.name}がスリット主導権から絞りまくり！内枠が被弾し、外隣5Cのまくり差し＆6C最内差しが連動。`,
            plan: { 1: "hekomi", 2: "hekomi", 3: "hekomi", 4: "makuri", 5: "makurisashi", 6: "tenkaimachi" }
          },
          {
            key: "c3_makuri",
            name: "🔥 3コースツケマイ・まくり展開",
            pct: Math.round((scWeights.c3_makuri / scTotal) * 100),
            desc: `2Cの凹みまたは3C${c3.b.name}の好STから1Mを握ってツケマイ敢行！インが抵抗して流れる懐を4C二番差し・5Cまくり差しが突く展開。`,
            plan: { 1: "hekomi", 2: "hekomi", 3: "makuri", 4: "nibanzashi", 5: "makurisashi", 6: "tenkaimachi" }
          },
          {
            key: "out_wait",
            name: "💥 1Mやり合い・外枠展開待ち波乱",
            pct: Math.max(4, 100 - Math.round((scWeights.in_nige / scTotal) * 100) - Math.round((scWeights.c2_sashi / scTotal) * 100) - Math.round((scWeights.c3_ms / scTotal) * 100) - Math.round((scWeights.c4_makuri / scTotal) * 100) - Math.round((scWeights.c3_makuri / scTotal) * 100)),
            desc: `1Cとセンター攻め艇が1Mで激しくやり合って大外へ流れ、ガラ空きになった最内ブイ際を4C二番差し・5C・6Cが展開待ち差しで突き抜ける高配当パターン。`,
            plan: { 1: "nige", 2: "hekomi", 3: "makuri", 4: "nibanzashi", 5: "tenkaimachi", 6: "tenkaimachi" }
          }
        ].sort((a, b) => b.pct - a.pct);

        let kadoMakuriTrigger = false;
        let primaryScenario = scenarioCatalog[0];
        if (stDiffKado >= 0.025 && (kadoObj.slitPower - receiverObj.slitPower >= 11) && kadoObj.effMakuriRate >= 12.0) {
          kadoMakuriTrigger = true;
          primaryScenario = scenarioCatalog.find(s => s.key === "c4_makuri") || scenarioCatalog[0];
        } else if (primaryScenario.key === "c4_makuri" && stDiffKado < 0.02) {
          primaryScenario = scenarioCatalog[1] || scenarioCatalog[0];
        }

        const top3Box = document.getElementById("pastRaceScenarioTop3Box");
        if (top3Box) {
          const logNote = logTotal > 0 ? `蓄積DB ${logTotal}R ＋ ` : "";
          top3Box.innerHTML = `
            <div class="flex items-center justify-between text-[11px] text-amber-300 font-bold">
              <span>📊 過去レース分析（${logNote}${venue.name}過去統計×ST段差×選手決まり手履歴）による展開予測 TOP3</span>
              <span class="text-[10px] text-slate-400">クリックで6艇に一括セット</span>
            </div>
            <div class="grid grid-cols-1 sm:grid-cols-3 gap-1.5">
              ${scenarioCatalog.slice(0, 3).map((sc, i) => `
                <div onclick="setTacticsPreset('${sc.key}')" class="cursor-pointer bg-slate-900 hover:bg-slate-800 border ${i === 0 ? "border-amber-500/60" : "border-slate-700"} rounded p-2 transition">
                  <div class="flex items-center justify-between font-bold text-[11px] ${i === 0 ? "text-amber-300" : "text-sky-300"}">
                    <span>#${i + 1} ${sc.name}</span>
                    <span class="font-mono bg-slate-950 px-1.5 py-0.5 rounded">${sc.pct}%</span>
                  </div>
                  <p class="text-[10px] text-slate-300 mt-1 leading-snug">${sc.desc}</p>
                </div>
              `).join("")}
            </div>
          `;
        }

        const manualNotes = [];
        let hasActiveMakuri = kadoMakuriTrigger;
        for (let c = 1; c <= 6; c++) {
          const obj = courseEval[c];
          if (c >= 2) {
            if (af.nigashiTri) obj.placeScore += (obj.b.nigashiTri - 50.0) * 0.42 * cw.wc;
            if (af.env && af.partsTilt && (wave >= 5 || tide === "high") && obj.b.tilt >= 0.5) {
              obj.firstScore -= 12;
              obj.placeScore -= 10;
            }
          }
          const chosenTac = obj.b.manualTactic !== "auto" ? obj.b.manualTactic : (primaryScenario.plan[c] || "sashi");
          obj.attackType = chosenTac;
          if (chosenTac === "makuri") hasActiveMakuri = true;
        }

        for (let c = 1; c <= 6; c++) {
          const obj = courseEval[c];
          const isManual = obj.b.manualTactic !== "auto";
          const tac = obj.attackType;
          const prefix = isManual ? "🎯指定:" : "";

          if (tac === "nige") {
            obj.firstScore += (isManual ? 32 : 12) * cw.ws;
            obj.placeScore += 12 * cw.ws;
            obj.roleText = `${prefix}🛡️イン先マイ(${obj.effMakuriRate.toFixed(0)}%)`;
            if (isManual) manualNotes.push(`${c}コース(${obj.boatId}号艇・${obj.b.name})の【逃げ(先マイ)】を指定`);
          } else if (tac === "nibanzashi") {
            obj.firstScore += (isManual ? 20 : 9 + vSashiMod * 0.5) * cw.ws;
            obj.placeScore += (isManual ? 30 : 20) * cw.ws;
            obj.roleText = `${prefix}📐${c}C二番差し(${obj.effSashiRate.toFixed(1)}%)`;
            if (isManual) manualNotes.push(`${c}コース(${obj.boatId}号艇・${obj.b.name})の【二番差し】を指定 → 一番差しの内・引き波を越えてシャープに差し追走`);
            if (courseEval[1] && c >= 2) courseEval[1].placeScore += 10 * cw.ws;
          } else if (tac === "sashi") {
            obj.firstScore += (isManual ? 22 : 8 + vSashiMod * 0.5) * cw.ws;
            obj.placeScore += (isManual ? 28 : 16) * cw.ws;
            const sLabel = (c === 3 || c === 4) && courseEval[2]?.attackType === "sashi" ? `${c}C二番差し` : `${c}C差し`;
            obj.roleText = `${prefix}📐${sLabel}(${obj.effSashiRate.toFixed(1)}%)`;
            if (isManual) manualNotes.push(`${c}コース(${obj.boatId}号艇・${obj.b.name})の【1M差し】を指定 → ターンマーク際を鋭く差し抜け`);
            if (courseEval[1] && c >= 2) courseEval[1].placeScore += 10 * cw.ws;
          } else if (tac === "makuri") {
            obj.firstScore += (isManual ? 36 : 20 + vMakuriMod) * cw.ws;
            obj.placeScore += 15 * cw.ws;
            obj.roleText = `${prefix}🔥${c}Cまくり(${obj.effMakuriRate.toFixed(1)}%)`;
            if (isManual) manualNotes.push(`${c}コース(${obj.boatId}号艇・${obj.b.name})の【まくり】を指定 → 内枠被弾＆外連動`);
            for (let inner = 1; inner < c; inner++) {
              courseEval[inner].firstScore -= (inner === c - 1 ? 18 : 12) * cw.ws;
              courseEval[inner].placeScore -= (inner === c - 1 ? 12 : 8) * cw.ws;
            }
          } else if (tac === "makurisashi") {
            obj.firstScore += (isManual ? 28 : 14 + vSashiMod * 0.5) * cw.ws;
            obj.placeScore += (isManual ? 26 : 20) * cw.ws;
            obj.roleText = `${prefix}⚡${c}Cまくり差(${obj.effMsRate.toFixed(1)}%)`;
            if (isManual) manualNotes.push(`${c}コース(${obj.boatId}号艇・${obj.b.name})の【まくり差し】を指定`);
            if (courseEval[1] && c >= 3) courseEval[1].placeScore += 8;
          } else if (tac === "tenkaimachi") {
            const clashBoost = hasActiveMakuri ? 14 : 6;
            obj.firstScore += (isManual ? 14 : 6 + clashBoost * 0.5) * cw.ws;
            obj.placeScore += (isManual ? 30 : 18 + clashBoost) * cw.ws;
            obj.roleText = `${prefix}⏳${c}C展開待(${obj.effWaitRate.toFixed(0)}%)`;
            if (isManual) manualNotes.push(`${c}コース(${obj.boatId}号艇・${obj.b.name})の【展開待ち(最内・連動差し)】を指定`);
          } else if (tac === "sotomai") {
            obj.firstScore += 6 * cw.ws;
            obj.placeScore += 22 * cw.ws;
            obj.roleText = `${prefix}🌀${c}C外マイ追走`;
            if (isManual) manualNotes.push(`${c}コース(${obj.boatId}号艇・${obj.b.name})の【外マイ追走】を指定`);
          } else if (tac === "hekomi") {
            obj.firstScore -= 24 * cw.ws;
            obj.placeScore -= 16 * cw.ws;
            obj.roleText = `${prefix}⚠️被弾・壁崩壊`;
            if (isManual) manualNotes.push(`${c}コース(${obj.boatId}号艇・${obj.b.name})の【壁崩壊・被弾】を指定`);
          }
        }

        renderCourseTacticsGrid(courseEval);
        renderCourseAttackMatrix(courseEval);
        renderSlitMap(courseEval, kadoCourse);
        const kimariteStats = renderKimariteBars(courseEval);
        drawSlitCanvas(courseEval, kadoCourse, venue, raceNo, raceGrade, windDir, windSpeed);
        drawFirstMarkCanvas(courseEval, kadoCourse, venue, raceNo, raceGrade, windDir, windSpeed, kimariteStats);
        renderScoreTable(courseEval);

        // =========================================================
        // 🚀 Version 3.0 5段階パイプライン実行
        // (展開予測 ➔ 勝率シミュレーション ➔ 期待値分析 ➔ 買い目生成 ➔ 自己学習)
        // =========================================================
        const stData = RaceAnalyzer.calculateSTAdvantage(courseEval);
        const exSorted = [1, 2, 3, 4, 5, 6].sort(
          (x, y) => (courseEval[x]?.b?.exTime || 6.8) - (courseEval[y]?.b?.exTime || 6.8)
        );
        const avgExTime = Object.values(courseEval).reduce((s, x) => s + (x.b.exTime || 6.75), 0) / 6;
        for (let c = 1; c <= 6; c++) {
          const exRank = exSorted.indexOf(c) + 1;
          courseEval[c].motorV2 = RaceAnalyzer.calculateMotorIndexV2(courseEval[c].b, exRank, avgExTime);
          courseEval[c].firstScore += (courseEval[c].stAdvantage || 0) * 1.25 + (courseEval[c].motorV2.score - 52) * 0.40;
          courseEval[c].placeScore += (courseEval[c].motorV2.score - 52) * 0.50;
        }

        const upsetIndex = RaceAnalyzer.calculateUpsetIndex(courseEval, venue, windSpeed, wave, deepIn);
        const raceType = RaceAnalyzer.classifyRaceType(courseEval, upsetIndex, kadoCourse, windDir, windSpeed);
        const explanations = RaceAnalyzer.buildBoatFactorExplanations(courseEval, venue, windDir, windSpeed, kadoCourse, deepIn);

        UIManager.renderRaceTypeHeader(raceType, upsetIndex);
        UIManager.renderExplanationsAndStAdvantage(explanations, stData, courseEval);

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
          kimariteStats,
          couplingNotes
        );

        // Stage 2〜5: Monte Carlo ➔ EV期待値 ➔ AI買い目・資金管理 ➔ 会場別学習・重み最適化・リプレイ
        const mcResult = SimulationEngine.runMonteCarlo(courseEval, {
          runs: AppStateV3.mcRuns,
          inEscapePct: kimariteStats.inEscapePct,
          kadoCourse,
          windDir,
          windSpeed,
          deepIn,
          venue
        });
        latestMonteCarloResult = mcResult;
        UIManager.renderMonteCarloV3(mcResult, boatsData);

        const evAnalysis = OddsEngine.calculateExpectedValues(mcResult.trifectaList, liveOddsMap);
        latestEVAnalysis = evAnalysis;

        const ticketCountV3 = Number(document.getElementById("ticketCountSelect")?.value || 12);
        const smartPortfolio = BettingEngine.generateAIBetsPortfolio(
          evAnalysis,
          latestSimContext?.patternABetsPool || [],
          latestSimContext?.patternBBetsPool || [],
          AppStateV3.budget,
          AppStateV3.bankrollMode,
          ticketCountV3
        );
        latestSmartPortfolio = smartPortfolio;
        UIManager.renderEVAndBettingPanel(evAnalysis, smartPortfolio);

        const venueBias = LearningEngine.getVenueEmpiricalBias(venue.id);
        const currentWeights = {
          w_course: Number(document.getElementById("w_course")?.value ?? 100),
          w_exhibit: Number(document.getElementById("w_exhibit")?.value ?? 100),
          w_motor: Number(document.getElementById("w_motor")?.value ?? 100),
          w_slit: Number(document.getElementById("w_slit")?.value ?? 100)
        };
        const weightComparison = LearningEngine.compareCurrentAndRecommendedWeights(currentWeights);
        const debugLog = JSON.stringify({
          version: "3.0.0",
          venue: `${venue.id}:${venue.name}`,
          racePattern: raceType.patternName,
          shortBadge: raceType.shortBadge,
          upsetIndex: { score: upsetIndex.score, label: upsetIndex.label, factors: upsetIndex.factors },
          stAdvantage: Object.fromEntries(Object.entries(stData.details).map(([k, v]) => [k, v.stAdvantage])),
          motorV2: Object.fromEntries(Object.entries(courseEval).map(([k, v]) => [k, `${v.motorV2.grade}(${v.motorV2.score})`])),
          mcRuns: mcResult.runs,
          bankrollMode: AppStateV3.bankrollMode,
          expectedRoiPct: `${smartPortfolio.expectedRoiPct}%`
        }, null, 2);
        UIManager.renderLearningAndDebugPanel(venueBias, weightComparison, AppStateV3.lastMissReport, debugLog);

        ReplayEngine.renderFrame("raceReplayCanvas", replayProgress, courseEval, mcResult);
        evaluateUserPredictions();
      }

      function renderCourseAttackMatrix(courseEval) {
        const tbody = document.getElementById("courseAttackMatrixBody");
        if (!tbody) return;
        tbody.innerHTML = "";
        for (let c = 1; c <= 6; c++) {
          const obj = courseEval[c];
          const makuriLabel = c === 1 ? `逃げ ${obj.effMakuriRate.toFixed(1)}%` : `まくり ${obj.effMakuriRate.toFixed(1)}%`;
          const sashiHighlight = c >= 2 && obj.effSashiRate >= obj.effMakuriRate && obj.effSashiRate >= obj.effMsRate ? "text-emerald-300 font-black underline" : "text-emerald-300/80";
          const makuriHighlight = c === 1 || (obj.effMakuriRate > obj.effSashiRate && obj.effMakuriRate >= obj.effMsRate) ? "text-rose-300 font-black underline" : "text-rose-300/80";
          const msHighlight = c >= 2 && obj.effMsRate > obj.effMakuriRate && obj.effMsRate > obj.effSashiRate ? "text-amber-300 font-black underline" : "text-amber-300/80";

          const reasonBadge = obj.couplingReason && obj.couplingReason !== "標準水準(同体並走)"
            ? `<span class="bg-amber-950/70 border border-amber-500/40 text-amber-200 px-1.5 py-0.5 rounded text-[10px] font-bold">${obj.couplingReason}</span>`
            : `<span class="text-slate-500 text-[10px]">標準水準(同体並走)</span>`;

          const isManual = obj.b.manualTactic !== "auto";
          const tacticSelectHtml = `
            <div class="flex items-center gap-1">
              <select onchange="updateCourseManualTactic(${c}, this.value)" class="text-[10px] font-bold py-0.5 px-1 rounded ${isManual ? "bg-pink-950 text-pink-200 border border-pink-500 font-black shadow" : "bg-slate-800 text-sky-200 border border-slate-700"}">
                <option value="auto" ${obj.b.manualTactic === "auto" ? "selected" : ""}>🤖 自動: ${obj.roleText}</option>
                <option value="nige" ${obj.b.manualTactic === "nige" ? "selected" : ""}>🛡️ 逃げ(先マイ)</option>
                <option value="sashi" ${obj.b.manualTactic === "sashi" ? "selected" : ""}>📐 差し(1M差し)</option>
                <option value="nibanzashi" ${obj.b.manualTactic === "nibanzashi" ? "selected" : ""}>📐 二番差し(連動差)</option>
                <option value="makuri" ${obj.b.manualTactic === "makuri" ? "selected" : ""}>🔥 まくり(強襲)</option>
                <option value="makurisashi" ${obj.b.manualTactic === "makurisashi" ? "selected" : ""}>⚡ まくり差し</option>
                <option value="tenkaimachi" ${obj.b.manualTactic === "tenkaimachi" ? "selected" : ""}>⏳ 展開待ち(内差)</option>
                <option value="sotomai" ${obj.b.manualTactic === "sotomai" ? "selected" : ""}>🌀 外マイ(追走)</option>
                <option value="hekomi" ${obj.b.manualTactic === "hekomi" ? "selected" : ""}>⚠️ 凹み・壁崩壊</option>
              </select>
              ${isManual ? '<span class="text-[9px] bg-pink-600 text-white font-bold px-1 rounded">手動</span>' : ""}
            </div>
          `;

          tbody.innerHTML += `
          <tr>
            <td class="py-1 font-bold text-slate-300">${c}コース${obj.isKado ? '<span class="text-[9px] bg-rose-600 text-white px-1 rounded ml-1">カド</span>' : ""}</td>
            <td class="py-1 flex items-center gap-1.5"><span class="boat-${obj.boatId} w-5 h-5 rounded text-[11px] font-black flex items-center justify-center">${obj.boatId}</span><span class="font-bold text-white">${obj.b.name}</span></td>
            <td class="py-1">${tacticSelectHtml}</td>
            <td class="py-1 text-right font-mono ${sashiHighlight}">${c === 1 ? `抜き ${obj.effSashiRate.toFixed(1)}%` : `${obj.effSashiRate.toFixed(1)}%`}</td>
            <td class="py-1 text-right font-mono ${makuriHighlight}">${makuriLabel}</td>
            <td class="py-1 text-right font-mono ${msHighlight}">${c === 1 ? "-" : `${obj.effMsRate.toFixed(1)}%`}</td>
            <td class="py-1 text-right font-mono text-purple-300 font-bold">${obj.effWaitRate.toFixed(1)}%</td>
            <td class="py-1 pl-2">${reasonBadge}</td>
          </tr>`;
        }
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
            arrowBadge = `<span class="text-[10px] text-rose-400 font-bold ml-1">⤴まくり(${obj.effMakuriRate.toFixed(0)}%)</span>`;
          } else if (obj.attackType === "makurisashi") {
            arrowBadge = `<span class="text-[10px] text-amber-300 font-bold ml-1">⚡捲差(${obj.effMsRate.toFixed(0)}%)</span>`;
          } else if (obj.attackType === "nibanzashi") {
            arrowBadge = `<span class="text-[10px] text-emerald-300 font-bold ml-1">📐二番差(${obj.effSashiRate.toFixed(0)}%)</span>`;
          } else if (obj.attackType === "sashi") {
            arrowBadge = `<span class="text-[10px] text-emerald-400 font-bold ml-1">📐差し(${obj.effSashiRate.toFixed(0)}%)</span>`;
          } else if (obj.attackType === "tenkaimachi") {
            arrowBadge = `<span class="text-[10px] text-purple-300 font-bold ml-1">⏳展開待(${obj.effWaitRate.toFixed(0)}%)</span>`;
          } else if (obj.attackType === "sotomai") {
            arrowBadge = `<span class="text-[10px] text-cyan-300 font-bold ml-1">🌀外マイ</span>`;
          } else if (obj.attackType === "hekomi") {
            arrowBadge = `<span class="text-[10px] text-slate-400 font-bold ml-1">⚠️被弾/凹</span>`;
          } else if (c === 1) {
            arrowBadge = `<span class="text-[10px] text-sky-400 font-bold ml-1">➡先マイ(${obj.effMakuriRate.toFixed(0)}%)</span>`;
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


      

      // 参考画像(競艇解説図スタイル)を2倍Retina高解像度で完全再現した6艇ボートアイコン描画関数（ターン後も艇番数字が常に正立）
      function drawClassicBoatIcon(ctx, x, y, scale, boatId, angleRad, alpha = 1.0, labelText = "", rankBadge = "") {
        const c = BOAT_COLORS[boatId] || BOAT_COLORS[1];
        ctx.save();
        ctx.globalAlpha = alpha;
        ctx.translate(x, y);
        ctx.rotate(angleRad);
        ctx.scale(scale, scale);

        // 1. 外側ホワイトハル（参考画像と同じ白縁＋黒細枠のシャープな五角形）
        ctx.fillStyle = "#ffffff";
        ctx.strokeStyle = "#0f172a";
        ctx.lineWidth = 2.2;
        ctx.beginPath();
        ctx.moveTo(-48, -22);
        ctx.lineTo(14, -22);
        ctx.lineTo(54, 0);
        ctx.lineTo(14, 22);
        ctx.lineTo(-48, 22);
        ctx.closePath();
        ctx.fill();
        ctx.stroke();

        // 2. 内側カラーボディ（先端ノーズの白い三角形を残して艇番カラーで塗る）
        ctx.fillStyle = c.body;
        ctx.strokeStyle = c.innerBorder;
        ctx.lineWidth = 1.4;
        ctx.beginPath();
        ctx.moveTo(-44, -18);
        ctx.lineTo(12, -18);
        ctx.lineTo(30, -8);
        ctx.lineTo(30, 8);
        ctx.lineTo(12, 18);
        ctx.lineTo(-44, 18);
        ctx.closePath();
        ctx.fill();
        ctx.stroke();

        // 先端ノーズのV字ディテール
        ctx.strokeStyle = "#64748b";
        ctx.lineWidth = 1.1;
        ctx.beginPath();
        ctx.moveTo(30, -8);
        ctx.lineTo(51, 0);
        ctx.lineTo(30, 8);
        ctx.stroke();

        // 3. 後部の黒いモーター突起
        ctx.fillStyle = "#090d16";
        ctx.fillRect(-55, -8, 12, 16);

        // 4. 中央の白丸ナンバーサークル
        const numCenterX = -10;
        ctx.fillStyle = "#ffffff";
        ctx.strokeStyle = boatId === 1 ? "#475569" : c.innerBorder;
        ctx.lineWidth = 2.2;
        ctx.beginPath();
        ctx.arc(numCenterX, 0, 15, 0, Math.PI * 2);
        ctx.fill();
        ctx.stroke();

        // 5. 艇番数字（★重要：ターン後も逆さまにならないよう -angleRad で常に正立させる！）
        ctx.save();
        ctx.translate(numCenterX, 0);
        ctx.rotate(-angleRad);
        ctx.fillStyle = c.numText;
        ctx.font = "900 21px sans-serif";
        ctx.textAlign = "center";
        ctx.textBaseline = "middle";
        ctx.fillText(String(boatId), 0, 1);
        ctx.restore();

        ctx.restore();

        // 6. 出口ボートの選手名＆順位ラベル（艇の先端前方に水平配置し、ボートや軌跡と一切重ならない）
        if (labelText && alpha >= 0.9) {
          ctx.save();
          const noseDist = 42 * scale;
          const lx = x + Math.cos(angleRad) * noseDist;
          const ly = y + Math.sin(angleRad) * noseDist;
          const fullLabel = rankBadge ? `${rankBadge} ${labelText}` : labelText;
          ctx.font = "bold 12px sans-serif";
          const tw = ctx.measureText(fullLabel).width + 14;
          const bx = lx - tw - 4;
          const by = ly - 10;
          ctx.fillStyle = "rgba(15, 23, 42, 0.90)";
          ctx.fillRect(bx, by, tw, 20);
          ctx.strokeStyle = c.body === "#111827" ? "#94a3b8" : c.body;
          ctx.lineWidth = 1.5;
          ctx.strokeRect(bx, by, tw, 20);
          ctx.fillStyle = "#ffffff";
          ctx.textAlign = "center";
          ctx.textBaseline = "middle";
          ctx.fillText(fullLabel, bx + tw / 2, by + 10);
          ctx.restore();
        }
      }

      function drawSlitCanvas(courseEval, kadoCourse, venue, raceNo, raceGrade, windDir, windSpeed) {
        const canvas = document.getElementById("slitCanvas");
        if (!canvas) return;
        const W = 920;
        const H = 400;
        if (canvas.width !== W * 2 || canvas.height !== H * 2) {
          canvas.width = W * 2;
          canvas.height = H * 2;
        }
        const ctx = canvas.getContext("2d");
        ctx.save();
        ctx.scale(2, 2);

        // 鮮やかな水色水面背景
        ctx.fillStyle = "#18d4f2";
        ctx.fillRect(0, 0, W, H);

        // 上部ヘッダー帯
        ctx.fillStyle = "#0f172a";
        ctx.fillRect(0, 0, W, 40);
        ctx.fillStyle = "#ffffff";
        ctx.font = "bold 15px sans-serif";
        ctx.textAlign = "left";
        const gStr = raceGrade === "ippan" ? "一般" : raceGrade;
        const wStr = windDir === "head" ? `向かい風${windSpeed}m` : windDir === "tail" ? `追い風${windSpeed}m` : windDir === "cross" ? `横風${windSpeed}m` : "無風";
        ctx.fillText(`🎓 ぼーとだいがくせい｜${venue.name} ${raceNo}R (${gStr}) 想定スリット隊形（6艇）`, 14, 25);

        ctx.fillStyle = "#38bdf8";
        ctx.font = "bold 13px sans-serif";
        ctx.textAlign = "right";
        ctx.fillText(`${wStr} ／ カド: ${kadoCourse}コース`, W - 14, 25);

        const startX = 735;
        const stToX = (stVal) => Math.max(200, Math.min(730, startX - stVal * 2000));

        // 縦のST目盛り線 (.20 / .15 / .10 / .05 / 0.00 START)
        [
          { st: 0.20, label: ".20 (遅れ)" },
          { st: 0.15, label: ".15 (標準)" },
          { st: 0.10, label: ".10 (好ST)" },
          { st: 0.05, label: ".05 (踏み込み)" }
        ].forEach(t => {
          const tx = stToX(t.st);
          ctx.strokeStyle = "rgba(15, 23, 42, 0.22)";
          ctx.lineWidth = 1.5;
          ctx.setLineDash([6, 4]);
          ctx.beginPath();
          ctx.moveTo(tx, 42);
          ctx.lineTo(tx, H - 26);
          ctx.stroke();
          ctx.setLineDash([]);
          ctx.fillStyle = "#0f172a";
          ctx.font = "bold 12px sans-serif";
          ctx.textAlign = "center";
          ctx.fillText(t.label, tx, H - 8);
        });

        // START 0.00 赤ライン
        ctx.strokeStyle = "#dc2626";
        ctx.lineWidth = 4;
        ctx.beginPath();
        ctx.moveTo(startX, 42);
        ctx.lineTo(startX, H - 24);
        ctx.stroke();
        ctx.fillStyle = "#dc2626";
        ctx.font = "900 13px sans-serif";
        ctx.textAlign = "center";
        ctx.fillText("START (0.00)", startX, H - 8);

        const topY = 48;
        const laneH = 54;
        for (let c = 1; c <= 6; c++) {
          const obj = courseEval[c];
          const yCenter = topY + (c - 0.5) * laneH;
          const yTop = topY + (c - 1) * laneH;

          // コース区切り線
          ctx.strokeStyle = "rgba(15, 23, 42, 0.15)";
          ctx.lineWidth = 1;
          ctx.beginPath();
          ctx.moveTo(10, yTop + laneH);
          ctx.lineTo(W - 10, yTop + laneH);
          ctx.stroke();

          // カド赤い太破線
          if (c === kadoCourse) {
            ctx.strokeStyle = "#e11d48";
            ctx.lineWidth = 3;
            ctx.setLineDash([10, 5]);
            ctx.beginPath();
            ctx.moveTo(10, yTop);
            ctx.lineTo(W - 10, yTop);
            ctx.stroke();
            ctx.setLineDash([]);
            ctx.fillStyle = "#e11d48";
            ctx.font = "900 11px sans-serif";
            ctx.textAlign = "left";
            ctx.fillText(`▼ ${kadoCourse}コースカド（ダッシュ境界線）`, 145, yTop + 12);
          }

          // 左側：コース＋選手名＋展示タイム
          const cleanName = (obj.b.name || `${obj.boatId}号艇`).replace(/\s+/g, "");
          ctx.fillStyle = "#0f172a";
          ctx.font = "900 14px sans-serif";
          ctx.textAlign = "left";
          ctx.fillText(`${c}コース`, 14, yCenter - 5);
          ctx.font = "bold 12px sans-serif";
          ctx.fillStyle = c >= kadoCourse ? "#be123c" : "#1e293b";
          ctx.fillText(`${cleanName} (${(obj.b.exTime || 6.80).toFixed(2)}s)`, 14, yCenter + 13);

          // ボート描画（先端がexpectedStの位置）
          const noseX = stToX(obj.expectedSt);
          const boatX = noseX - 35;
          drawClassicBoatIcon(ctx, boatX, yCenter, 0.66, obj.boatId, 0, 1.0, "");

          // ボート右側にST値と1M戦法バッジ
          const stText = `.${Math.round(obj.expectedSt * 100).toString().padStart(2, "0")}`;
          let atkLabel = "➡逃げ先マイ";
          if (obj.attackType === "makuri") atkLabel = `🔥まくり(${obj.effMakuriRate.toFixed(0)}%)`;
          else if (obj.attackType === "makurisashi") atkLabel = `⚡まくり差(${obj.effMsRate.toFixed(0)}%)`;
          else if (obj.attackType === "nibanzashi") atkLabel = `📐二番差(${obj.effSashiRate.toFixed(0)}%)`;
          else if (obj.attackType === "sashi") atkLabel = `📐差し(${obj.effSashiRate.toFixed(0)}%)`;
          else if (obj.attackType === "tenkaimachi") atkLabel = `⏳展開待(${obj.effWaitRate.toFixed(0)}%)`;
          else if (obj.attackType === "sotomai") atkLabel = "🌀外マイ";
          else if (obj.attackType === "hekomi") atkLabel = "⚠️凹み・被弾";

          ctx.fillStyle = "rgba(15, 23, 42, 0.88)";
          ctx.fillRect(noseX + 8, yCenter - 13, 162, 26);
          ctx.fillStyle = "#38bdf8";
          ctx.font = "900 13px monospace";
          ctx.textAlign = "left";
          ctx.fillText(`ST${stText}`, noseX + 14, yCenter + 4);
          ctx.fillStyle = "#ffffff";
          ctx.font = "bold 12px sans-serif";
          ctx.fillText(atkLabel, noseX + 64, yCenter + 4);
        }
        ctx.restore();
      }

      // 参考画像の構図・6艇同心円アーク・正立ナンバー・2倍Retina高解像度による1マーク展開図
      function drawFirstMarkCanvas(courseEval, kadoCourse, venue, raceNo, raceGrade, windDir, windSpeed, kimariteStats) {
        const canvas = document.getElementById("firstMarkCanvas");
        if (!canvas) return;
        const W = 920;
        const H = 640;
        if (canvas.width !== W * 2 || canvas.height !== H * 2) {
          canvas.width = W * 2;
          canvas.height = H * 2;
        }
        const ctx = canvas.getContext("2d");
        ctx.save();
        ctx.scale(2, 2);

        ctx.fillStyle = "#18d4f2";
        ctx.fillRect(0, 0, W, H);

        ctx.fillStyle = "#0f172a";
        ctx.fillRect(0, 0, W, 38);
        ctx.fillStyle = "#ffffff";
        ctx.font = "bold 15px sans-serif";
        ctx.textAlign = "left";
        const gStr = raceGrade === "ippan" ? "一般" : raceGrade;
        ctx.fillText(`🌀 ${venue.name} ${raceNo}R (${gStr}) 1マーク（6艇）旋回展開シミュレーション`, 14, 24);
        ctx.fillStyle = "#fbbf24";
        ctx.font = "bold 13px sans-serif";
        ctx.textAlign = "right";
        ctx.fillText(`🟦イン逃げ ${kimariteStats.inEscapePct}% ／ 🟥非イン逆転 ${kimariteStats.nonInPct}%`, W - 14, 24);

        const buoyX = 390;
        const buoyY = 305;

        ctx.fillStyle = "#ffffff";
        ctx.strokeStyle = "#dc2626";
        ctx.lineWidth = 3.5;
        ctx.fillRect(42, buoyY - 18, 314, 36);
        ctx.strokeRect(42, buoyY - 18, 314, 36);
        ctx.fillStyle = "#1e3a8a";
        ctx.font = "bold 14px sans-serif";
        ctx.textAlign = "center";
        ctx.fillText("🎓 ぼーとだいがくせい  @Boatrace__daisu", 199, buoyY + 5);

        const br = 22;
        ctx.save();
        ctx.translate(buoyX, buoyY);
        ctx.fillStyle = "#ffffff";
        ctx.beginPath();
        ctx.arc(0, 0, br, 0, Math.PI * 2);
        ctx.fill();
        ctx.fillStyle = "#ef4444";
        ctx.beginPath();
        ctx.moveTo(0, 0);
        ctx.arc(0, 0, br, -Math.PI * 0.75, -Math.PI * 0.25);
        ctx.closePath();
        ctx.fill();
        ctx.beginPath();
        ctx.moveTo(0, 0);
        ctx.arc(0, 0, br, Math.PI * 0.25, Math.PI * 0.75);
        ctx.closePath();
        ctx.fill();
        ctx.strokeStyle = "#0f172a";
        ctx.lineWidth = 2.5;
        ctx.beginPath();
        ctx.arc(0, 0, br, 0, Math.PI * 2);
        ctx.stroke();
        ctx.restore();

        ctx.fillStyle = "#0f172a";
        ctx.font = "900 20px sans-serif";
        ctx.textAlign = "center";
        ctx.fillText("1 マーク", buoyX - 52, buoyY + 45);

        const arr = Object.values(courseEval);
        const ranked = [...arr].sort((a, b) => (b.firstScore * 0.65 + b.placeScore * 0.35) - (a.firstScore * 0.65 + a.placeScore * 0.35));
        const rankMap = {};
        ranked.forEach((item, idx) => { rankMap[item.courseNo] = idx; });

        // ★重要：戦法ごとの旋回レーン（0:最内 〜 5:最外）の決定
        // 展開待ち（tenkaimachi）は「まくり艇の外を大外で回す」のではなく、「まくり等の隙を突いて内へ切り込む（最内・内目差し）」！
        const radiusPriority = arr.map(obj => {
          const c = obj.courseNo;
          let rScore = 20;
          if (obj.attackType === "sashi") {
            rScore = 10 + c;                       // 最内差し（1Cのブイ際を鋭く切り込む）
          } else if (obj.attackType === "nibanzashi") {
            rScore = 13 + c;                       // 二番差し（一番差しのすぐ内・後ろを鋭く突く）
          } else if (obj.attackType === "tenkaimachi") {
            rScore = 16 + c * 1.5;                 // 展開待ち：まくり艇の内側・差し場へ内切り込み！大外は絶対に回さない
          } else if (c === 1 && obj.attackType === "nige") {
            rScore = 22;                           // イン先マイ
          } else if (obj.attackType === "makurisashi") {
            rScore = 32 + c;                       // まくり差し（中割り）
          } else if (obj.attackType === "makuri") {
            rScore = 46 + c;                       // まくり（外包み）
          } else {
            rScore = 56 + c;                       // 外マイ（大外追走）
          }
          return { c, rScore };
        }).sort((a, b) => a.rScore - b.rScore);

        const laneMap = {};
        radiusPriority.forEach((item, idx) => { laneMap[item.c] = idx; }); // 0(最内) 〜 5(最外)

        const boatRenderQueue = [];
        const tList = [0.56, 0.41, 0.50, 0.58, 0.43, 0.52];

        for (let c = 1; c <= 6; c++) {
          const obj = courseEval[c];
          const bColor = BOAT_COLORS[obj.boatId] || BOAT_COLORS[1];
          const cleanName = (obj.b.name || `${obj.boatId}号艇`).split(" ")[0];
          const rk = rankMap[c] ?? (c - 1);       // 0 = 1M出口1番手, 5 = 6番手
          const laneIdx = laneMap[c] ?? (c - 1);  // 0 = 最内レーン, 5 = 最外レーン

          const stOffset = Math.max(-26, Math.min(32, (0.15 - obj.expectedSt) * 400));
          const startX = 235 + stOffset - (c - 1) * 4;
          const startY = 374 + (c - 1) * 45;

          const endAngle = -Math.PI * (0.90 - laneIdx * 0.018);

          const leadAdvance = (2.5 - rk) * 18;
          const baseExitX = 490 + laneIdx * 56;
          const baseExitY = 248 - laneIdx * 35;
          const endX = baseExitX + Math.cos(endAngle) * leadAdvance;
          const endY = baseExitY + Math.sin(endAngle) * leadAdvance;

          const p0x = startX + 34;
          const p0y = startY;
          const sternDist = 34;
          const p3x = endX - Math.cos(endAngle) * sternDist;
          const p3y = endY - Math.sin(endAngle) * sternDist;

          // ★展開待ちの場合の制御点：
          // 展開待ちは外へ大きく膨らまず、まくり艇の内側スペースを狙って早めに内へ切り込む！
          let cp1x, cp1y, cp2x, cp2y;
          if (obj.attackType === "tenkaimachi") {
            // 進入はコース位置から直進しつつ、1マーク手前で内側（laneIdx）へ向けて鋭角に切れ込む
            cp1x = 510 + laneIdx * 45;
            cp1y = startY - 25 - (c - 1) * 4;
            cp2x = 520 + laneIdx * 48;
            cp2y = endY + 35 + laneIdx * 6;
          } else {
            const entryBulgeX = 545 + (c - 1) * 54;
            const exitBulgeX = 555 + laneIdx * 56;
            cp1x = entryBulgeX;
            cp1y = startY - 4 - (c - 1) * 6;
            cp2x = exitBulgeX + 22;
            cp2y = endY + 28 + laneIdx * 8;
          }

          const t = tList[c - 1] || 0.50;
          const mt = 1 - t;
          const midX = mt*mt*mt*p0x + 3*mt*mt*t*cp1x + 3*mt*t*t*cp2x + t*t*t*p3x;
          const midY = mt*mt*mt*p0y + 3*mt*mt*t*cp1y + 3*mt*t*t*cp2y + t*t*t*p3y;
          const dxdt = 3*mt*mt*(cp1x - p0x) + 6*mt*t*(cp2x - cp1x) + 3*t*t*(p3x - cp2x);
          const dydt = 3*mt*mt*(cp1y - p0y) + 6*mt*t*(cp2y - cp1y) + 3*t*t*(p3y - cp2y);
          const midAngle = Math.atan2(dydt, dxdt);

          let atkShort = "先マイ";
          if (obj.attackType === "makuri") atkShort = "まくり";
          else if (obj.attackType === "makurisashi") atkShort = "まくり差";
          else if (obj.attackType === "nibanzashi") atkShort = "二番差し";
          else if (obj.attackType === "sashi") atkShort = "差し";
          else if (obj.attackType === "tenkaimachi") atkShort = "展開待(内差)";
          else if (obj.attackType === "sotomai") atkShort = "外マイ";

          boatRenderQueue.push({
            c,
            boatId: obj.boatId,
            bColor,
            cleanName,
            atkShort,
            rk,
            laneIdx,
            startX,
            startY,
            p0x,
            p0y,
            cp1x,
            cp1y,
            cp2x,
            cp2y,
            p3x,
            p3y,
            midX,
            midY,
            midAngle,
            endX,
            endY,
            endAngle
          });
        }

        boatRenderQueue.forEach(item => {
          ctx.save();
          if (item.boatId === 1 || item.boatId === 5) {
            ctx.strokeStyle = "rgba(15, 23, 42, 0.45)";
            ctx.lineWidth = 6.2;
            ctx.lineCap = "round";
            ctx.beginPath();
            ctx.moveTo(item.p0x, item.p0y);
            ctx.bezierCurveTo(item.cp1x, item.cp1y, item.cp2x, item.cp2y, item.p3x, item.p3y);
            ctx.stroke();
          }
          ctx.strokeStyle = item.bColor.line;
          ctx.lineWidth = 4.2;
          ctx.lineCap = "round";
          ctx.beginPath();
          ctx.moveTo(item.p0x, item.p0y);
          ctx.bezierCurveTo(item.cp1x, item.cp1y, item.cp2x, item.cp2y, item.p3x, item.p3y);
          ctx.stroke();
          ctx.restore();
        });

        boatRenderQueue.forEach(item => {
          drawClassicBoatIcon(ctx, item.startX, item.startY, 0.66, item.boatId, 0, 1.0, "");
          ctx.fillStyle = "#0f172a";
          ctx.font = "900 13px sans-serif";
          ctx.textAlign = "right";
          ctx.fillText(`${item.c}C ${item.cleanName} (${item.atkShort})`, item.startX - 42, item.startY + 4);
        });

        boatRenderQueue.forEach(item => {
          drawClassicBoatIcon(ctx, item.midX, item.midY, 0.62, item.boatId, item.midAngle, 0.40, "");
        });

        const rankCircles = ["①", "②", "③", "④", "⑤", "⑥"];
        boatRenderQueue.forEach(item => {
          drawClassicBoatIcon(ctx, item.endX, item.endY, 0.68, item.boatId, item.endAngle, 1.0, item.cleanName, rankCircles[item.rk] || "");
        });
  ctx.restore();
      }

      function showImageToast(msg) {
        const toast = document.getElementById("imageCopyToast");
        if (!toast) return;
        toast.textContent = msg;
        toast.classList.remove("hidden");
        setTimeout(() => toast.classList.add("hidden"), 3500);
      }

      async function copyCanvasToClipboard(canvasId, labelName) {
        const canvas = document.getElementById(canvasId);
        if (!canvas) return;
        const dataUrl = canvas.toDataURL("image/png");
        const prevModal = document.getElementById("copyPreviewModal");
        const prevImg = document.getElementById("copyPreviewImg");
        if (prevImg) prevImg.src = dataUrl;

        try {
          const blob = await new Promise(resolve => canvas.toBlob(resolve, "image/png"));
          if (navigator.clipboard && window.ClipboardItem) {
            await navigator.clipboard.write([new ClipboardItem({ "image/png": blob })]);
            showImageToast(`✅ ${labelName}をクリップボードにコピーしました！Xやnoteの投稿欄でそのまま貼り付け(Ctrl+V)できます。`);
            return;
          }
        } catch (e) {}

        if (prevModal) prevModal.classList.remove("hidden");
        showImageToast(`📸 下に${labelName}を表示しました！右クリック「画像をコピー」またはスマホ長押しでコピーできます。`);
      }

      function createCombinedCanvas() {
        const c1 = document.getElementById("slitCanvas");
        const c2 = document.getElementById("firstMarkCanvas");
        if (!c1 || !c2) return null;
        const out = document.createElement("canvas");
        out.width = Math.max(c1.width, c2.width);
        out.height = c1.height + c2.height + 8;
        const ctx = out.getContext("2d");
        ctx.fillStyle = "#090d16";
        ctx.fillRect(0, 0, out.width, out.height);
        ctx.drawImage(c1, 0, 0);
        ctx.drawImage(c2, 0, c1.height + 8);
        return out;
      }

      async function copyCombinedSnsImage() {
        const combined = createCombinedCanvas();
        if (!combined) return;
        const dataUrl = combined.toDataURL("image/png");
        const prevModal = document.getElementById("copyPreviewModal");
        const prevImg = document.getElementById("copyPreviewImg");
        if (prevImg) prevImg.src = dataUrl;

        try {
          const blob = await new Promise(resolve => combined.toBlob(resolve, "image/png"));
          if (navigator.clipboard && window.ClipboardItem) {
            await navigator.clipboard.write([new ClipboardItem({ "image/png": blob })]);
            showImageToast("✅ スリット図＋1マーク展開図の【2枚合体画像】をクリップボードにコピーしました！そのままXやnoteに貼り付けできます！");
            return;
          }
        } catch (e) {}

        if (prevModal) prevModal.classList.remove("hidden");
        showImageToast("📸 下に【2枚合体画像】を表示しました！右クリック「画像をコピー」またはスマホ長押しで保存できます。");
      }

      function downloadCombinedSnsImage() {
        const combined = createCombinedCanvas();
        if (!combined) return;
        const a = document.createElement("a");
        const vCode = document.getElementById("venueSelect")?.value || "04";
        const rno = document.getElementById("raceNoSelect")?.value || "12";
        a.href = combined.toDataURL("image/png");
        a.download = `boatrace_${vCode}_${rno}R_slit_1mark.png`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        showImageToast("💾 スリット＋1マーク合体PNG画像をダウンロードしました！");
      }

      function renderKimariteBars(courseEval) {
        const arr = Object.values(courseEval);
        const nigeW = Math.max(8, courseEval[1].firstScore * (courseEval[1].attackType === "hekomi" ? 0.45 : 1.0));
        const sashiW = Math.max(6, arr.filter(x => x.courseNo >= 2).reduce((s, x) => s + (x.attackType === "sashi" ? x.firstScore * 0.55 : x.effSashiRate * 1.6), 0));
        const makuriW = Math.max(6, arr.filter(x => x.courseNo >= 2).reduce((s, x) => s + (x.attackType === "makuri" ? x.firstScore * 0.65 : x.effMakuriRate * 1.7), 0));
        const msW = Math.max(6, arr.filter(x => x.courseNo >= 3).reduce((s, x) => s + (x.attackType === "makurisashi" ? x.firstScore * 0.60 : x.effMsRate * 1.8), 0));
        const waitW = Math.max(5, arr.filter(x => x.courseNo >= 3).reduce((s, x) => s + (x.attackType === "tenkaimachi" ? x.firstScore * 0.45 : x.effWaitRate * 0.35), 0));
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
        if (!tbody) return;
        tbody.innerHTML = "";
        const exSorted = [1,2,3,4,5,6].sort((x, y) => (courseEval[x]?.b?.exTime || 6.8) - (courseEval[y]?.b?.exTime || 6.8));
        for (let c = 1; c <= 6; c++) {
          const obj = courseEval[c];
          const isManual = obj.b.manualTactic !== "auto";
          const exStr = (obj.b.exTime || 6.80).toFixed(2);
          const exRank = exSorted.indexOf(c) + 1;
          const mInfo = (typeof RaceAnalyzer !== "undefined" && RaceAnalyzer.calculateCompositeMotorIndex)
            ? RaceAnalyzer.calculateCompositeMotorIndex(obj.b, exRank)
            : { grade: "B", score: 55, color: "text-sky-300", bg: "bg-slate-800" };
          tbody.innerHTML += `
          <tr>
            <td class="py-1 font-bold text-slate-400">${c}C</td>
            <td class="py-1 flex items-center gap-1.5"><span class="boat-${obj.boatId} w-5 h-5 rounded text-[11px] font-black flex items-center justify-center">${obj.boatId}</span><span class="font-bold text-white">${obj.b.name}</span></td>
            <td class="py-1 text-center"><span class="text-[10px] px-1.5 py-0.5 rounded border ${mInfo.bg} ${mInfo.color}">${mInfo.grade} (${mInfo.score})</span></td>
            <td class="py-1 text-right font-mono text-sky-300">${exStr}s / .${Math.round(obj.expectedSt * 100).toString().padStart(2, "0")}</td>
            <td class="py-1 text-right font-bold text-amber-300">${obj.firstScore.toFixed(1)}</td>
            <td class="py-1 text-right font-bold text-emerald-300">${obj.placeScore.toFixed(1)}</td>
            <td class="py-1 text-center"><span class="text-[10px] px-1.5 py-0.5 rounded ${isManual ? "bg-pink-900 text-pink-200 font-bold" : "bg-slate-800 text-slate-200"}">${obj.roleText}</span></td>
          </tr>`;
        }
      }

      function generateNarrativeAndBets(courseEval, venue, raceNo, raceGrade, g1Active, windDir, windSpeed, wave, tide, kadoCourse, deepIn, kadoMakuriTrigger, manualNotes, kimariteStats, couplingNotes = []) {
        const arr = Object.values(courseEval);
        const inObj = courseEval[1];
        const c2Obj = courseEval[2];
        const c3Obj = courseEval[3];
        const c4Obj = courseEval[4];
        const kadoObj = courseEval[kadoCourse] || courseEval[4];

        // ---------------------------------------------------------
        // 1. パターンA（イン逃げ：1コース1着）専用連対スコアと全20通り買い目生成
        // ---------------------------------------------------------
        const inFollowers = arr
          .filter(x => x.courseNo !== 1)
          .map(x => {
            let s = x.placeScore;
            if (x.courseNo === 2 && x.attackType !== "hekomi") s += 10 + x.effSashiRate * 0.35;
            if (x.courseNo === 3 && ["sotomai", "makurisashi", "sashi", "nibanzashi"].includes(x.attackType)) s += 8 + x.effMsRate * 0.3;
            if (x.attackType === "sashi" || x.attackType === "nibanzashi") s += 8;
            if (x.attackType === "tenkaimachi") s += 6 + x.effWaitRate * 0.12;
            return { ...x, inFollowScore: s };
          })
          .sort((a, b) => b.inFollowScore - a.inFollowScore);

        const inP1 = inFollowers[0], inP2 = inFollowers[1], inP3 = inFollowers[2], inP4 = inFollowers[3], inP5 = inFollowers[4];

        // パターンA 全20通りをスコア順に生成（6点上限を完全撤廃）
        const rawPatternAList = [];
        inFollowers.forEach((secondObj, idx2) => {
          inFollowers.forEach((thirdObj, idx3) => {
            if (secondObj.boatId === thirdObj.boatId) return;
            const comboScore = secondObj.inFollowScore * 1.45 + thirdObj.inFollowScore * 0.85 + (thirdObj.attackType === "tenkaimachi" ? 6 : 0);
            rawPatternAList.push({
              l1: inObj.boatId,
              l2: secondObj.boatId,
              l3: thirdObj.boatId,
              score: comboScore,
              idx2,
              idx3
            });
          });
        });
        rawPatternAList.sort((a, b) => b.score - a.score);

        const patternABetsPool = rawPatternAList.map((item, rankIdx) => {
          const typeLabel = rankIdx < 2 ? "イン本線◎" : rankIdx < 4 ? "イン対抗○" : rankIdx < 7 ? "イン差し▲" : rankIdx < 11 ? "イン展開待★" : "イン抑え△";
          const estProb = Math.max(1.2, Math.round((16.5 * Math.pow(0.83, rankIdx)) * 10) / 10);
          const comboKey = `${item.l1}-${item.l2}-${item.l3}`;
          const estOdds = liveOddsMap[comboKey] || (Math.round((6.5 + rankIdx * 3.8 + (rankIdx >= 6 ? rankIdx * 2.5 : 0)) * 10) / 10);
          return {
            pattern: "A",
            type: typeLabel,
            l1: item.l1,
            l2: item.l2,
            l3: item.l3,
            prob: estProb,
            odds: estOdds
          };
        });

        // ---------------------------------------------------------
        // 2. パターンB（イン逃げ以外：2〜6コース1着）専用スコアと全30通り買い目生成
        // ---------------------------------------------------------
        const nonInWinners = arr
          .filter(x => x.courseNo !== 1)
          .map(x => {
            let s = x.firstScore + (x.effSashiRate * 0.5 + x.effMakuriRate * 0.65 + x.effMsRate * 0.6);
            if (x.attackType === "makuri") s += 14;
            if (x.attackType === "makurisashi") s += 12;
            if (x.attackType === "sashi" || x.attackType === "nibanzashi") s += 10;
            if (x.attackType === "tenkaimachi") s += 8;
            return { ...x, nonInWinScore: s };
          })
          .sort((a, b) => b.nonInWinScore - a.nonInWinScore);

        const nonIn1 = nonInWinners[0];
        const nonIn2 = nonInWinners[1];
        const nonIn3 = nonInWinners[2];

        const getFollowersForWinner = (winnerObj) => {
          return arr
            .filter(x => x.boatId !== winnerObj.boatId)
            .map(x => {
              let s = x.placeScore;
              if (winnerObj.attackType === "makuri") {
                if (x.courseNo === winnerObj.courseNo + 1) s += 24;
                if (x.courseNo === winnerObj.courseNo + 2 || x.attackType === "tenkaimachi") s += 18;
                if (x.courseNo < winnerObj.courseNo) s -= 12;
              } else if (winnerObj.attackType === "sashi" || winnerObj.attackType === "nibanzashi" || winnerObj.attackType === "makurisashi") {
                if (x.courseNo === 1) s += 22;
                if (x.attackType === "tenkaimachi") s += 14;
              } else if (winnerObj.attackType === "tenkaimachi") {
                if (x.courseNo === 1 || x.isKado) s += 16;
              }
              return { ...x, followScore: s };
            })
            .sort((a, b) => b.followScore - a.followScore);
        };

        const nonIn1Followers = getFollowersForWinner(nonIn1);
        const nf1 = nonIn1Followers[0], nf2 = nonIn1Followers[1], nf3 = nonIn1Followers[2];
        const nonIn2Followers = getFollowersForWinner(nonIn2);
        const ng1 = nonIn2Followers[0], ng2 = nonIn2Followers[1];

        const rawPatternBList = [];
        nonInWinners.slice(0, 4).forEach((wObj, wRank) => {
          const flist = getFollowersForWinner(wObj);
          flist.slice(0, 4).forEach((f2, idx2) => {
            flist.slice(0, 4).forEach((f3, idx3) => {
              if (f2.boatId === f3.boatId) return;
              const sc = wObj.nonInWinScore * 1.25 + f2.followScore * 0.95 + f3.followScore * 0.65 - wRank * 8;
              rawPatternBList.push({
                l1: wObj.boatId,
                l2: f2.boatId,
                l3: f3.boatId,
                wObj,
                f2,
                f3,
                score: sc
              });
            });
          });
        });
        rawPatternBList.sort((a, b) => b.score - a.score);

        const patternBBetsPool = rawPatternBList.slice(0, 24).map((item, rankIdx) => {
          const atkName = item.wObj.attackType === "makuri" ? "まくり連動" : item.wObj.attackType === "sashi" ? "差し逆転" : item.wObj.attackType === "makurisashi" ? "捲差逆転" : "展開待ち穴";
          const mark = rankIdx < 2 ? "◎" : rankIdx < 5 ? "○" : rankIdx < 9 ? "▲" : rankIdx < 14 ? "★" : "☆";
          const estProb = Math.max(0.8, Math.round((8.8 * Math.pow(0.86, rankIdx)) * 10) / 10);
          const comboKey = `${item.l1}-${item.l2}-${item.l3}`;
          const estOdds = liveOddsMap[comboKey] || (Math.round((21.0 + rankIdx * 6.5) * 10) / 10);
          return {
            pattern: "B",
            type: `${atkName}${mark}`,
            l1: item.l1,
            l2: item.l2,
            l3: item.l3,
            prob: estProb,
            odds: estOdds
          };
        });

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
            <div class="text-amber-300 font-bold flex items-center justify-between">
              <span>🔄 他艇の攻め手に連動した動的相関分析（壁崩壊・センター仕掛け連動）</span>
              <span class="text-[10px] bg-amber-500/20 text-amber-300 px-2 py-0.5 rounded border border-amber-500/40">他艇相関エンジン適用</span>
            </div>
            ${couplingNotes.length > 0 
              ? `<ul class="list-disc list-inside space-y-0.5 text-slate-300 text-[11px]">${couplingNotes.map(n => `<li>${n}</li>`).join("")}</ul>`
              : `<p class="text-slate-400 text-[11px]">各艇が想定ST同体で並走しており、極端な壁崩壊や単独凹みはありません。</p>`
            }
          </div>

          <div class="space-y-1 border-b border-slate-800 pb-2">
            <div class="text-emerald-400 font-bold">② コース別の攻め方・決まり手成功率（他艇連動補正後）</div>
            <p>・<strong>1コース（${inObj.boatId}号艇・${inObj.b.name}）</strong>：イン逃げ成功率 <strong>${inObj.effMakuriRate.toFixed(1)}%</strong>（想定ST .${Math.round(inObj.expectedSt * 100).toString().padStart(2, "0")} / 起こし:${deepLabel}）<br>
               ・<strong>2コース（${c2Obj.boatId}号艇・${c2Obj.b.name}）</strong>：<strong>📐差し成功率 ${c2Obj.effSashiRate.toFixed(1)}% ／ 🔥まくり成功率 ${c2Obj.effMakuriRate.toFixed(1)}%</strong> ／ 壁としての逃がし率 ${c2Obj.b.nigashi.toFixed(1)}%<br>
               ・<strong>3コース（${c3Obj.boatId}号艇・${c3Obj.b.name}）</strong>：<strong>🔥まくり率 ${c3Obj.effMakuriRate.toFixed(1)}% ／ ⚡まくり差し率 ${c3Obj.effMsRate.toFixed(1)}% ／ 📐差し率 ${c3Obj.effSashiRate.toFixed(1)}%</strong><br>
               ・<strong>4コース（${c4Obj.boatId}号艇・${c4Obj.b.name}）</strong>：<strong>🔥まくり率 ${c4Obj.effMakuriRate.toFixed(1)}% ／ ⚡まくり差し率 ${c4Obj.effMsRate.toFixed(1)}% ／ ⏳展開待ち連対率 ${c4Obj.effWaitRate.toFixed(1)}%</strong><br>
               ・展示時計トップは<strong>${exBest.boatId}号艇・${exBest.b.name}（${exBest.b.exTime.toFixed(2)}秒）</strong>、モーター2連率トップは<strong>${motorBest.boatId}号艇・${motorBest.b.name}（${motorBest.b.motorBi.toFixed(1)}%）</strong>です。</p>
          </div>

          <div class="bg-sky-950/40 border border-sky-500/40 rounded-lg p-2.5 space-y-1">
            <div class="text-sky-300 font-bold flex items-center justify-between">
              <span>🟦 【パターンA：イン逃げ本線シナリオ】</span>
              <span class="text-[11px] bg-sky-500 text-slate-950 font-black px-2 py-0.5 rounded">成立確率 ${kimariteStats.inEscapePct}%</span>
            </div>
            <p>1コース<strong>${inObj.boatId}号艇（${inObj.b.name}）</strong>が先マイ押し切り（逃げ成功率${inObj.effMakuriRate.toFixed(1)}%）。2番手争いは、${inP1.roleText}から追走する<strong>${inP1.boatId}号艇（${inP1.b.name}）</strong>と、${inP2.roleText}で浮上する<strong>${inP2.boatId}号艇（${inP2.b.name}）</strong>が軸。3着ヒモには展開待ち連対率の高い<strong>${inP3.boatId}号艇（${inP3.b.name}）・${inP4.boatId}号艇（${inP4.b.name}）</strong>までケアした<strong>「${inObj.boatId}-${inP1.boatId}${inP2.boatId}-${inP1.boatId}${inP2.boatId}${inP3.boatId}${inP4.boatId}」</strong>が本線です。</p>
          </div>

          <div class="bg-rose-950/40 border border-rose-500/40 rounded-lg p-2.5 space-y-1">
            <div class="text-rose-300 font-bold flex items-center justify-between">
              <span>🟥 【パターンB：イン逃げ以外（差し・まくり・展開待ち逆転）シナリオ】</span>
              <span class="text-[11px] bg-rose-500 text-white font-black px-2 py-0.5 rounded">成立確率 ${kimariteStats.nonInPct}%</span>
            </div>
            <p>インの${inObj.boatId}号艇が敗れる場合、逆転1着の筆頭はコース別攻め成功率上位の<strong>${nonIn1.courseNo}コース${nonIn1.boatId}号艇（${nonIn1.b.name} / ${nonIn1.roleText}）</strong>、対抗アタマは<strong>${nonIn2.courseNo}コース${nonIn2.boatId}号艇（${nonIn2.b.name} / ${nonIn2.roleText}）</strong>。${nonIn1.boatId}号艇が攻めた際、スジ連動する<strong>${nf1.boatId}号艇（${nf1.b.name}）</strong>と展開待ちから突き抜ける<strong>${nf2.boatId}号艇（${nf2.b.name}）</strong>への<strong>「${nonIn1.boatId}-${nf1.boatId}${nf2.boatId}-${nf1.boatId}${nf2.boatId}${nf3.boatId}」</strong>および<strong>「${nonIn2.boatId}-${ng1.boatId}-${ng2.boatId}」</strong>が高配当の勝負目です。</p>
          </div>
        `;
        document.getElementById("aiNarrativeBox").innerHTML = longHtml;

        const nameOf = (id) => (boatsData[id]?.name || `${id}`).split(" ")[0];

        const patternMode = document.getElementById("patternFilterSelect")?.value || "both";
        const ticketCount = Number(document.getElementById("ticketCountSelect")?.value || 12);
        const budget = Math.max(400, Number(document.getElementById("budgetInput")?.value || 5000));

        // 6点制限を撤廃：指定された点数（4〜24点）を完全に満たすように抽出
        let selectedBets = [];
        if (patternMode === "in_only") {
          selectedBets = patternABetsPool.slice(0, ticketCount);
        } else if (patternMode === "non_in_only") {
          selectedBets = patternBBetsPool.slice(0, ticketCount);
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



        // My予想チェッカー用に現在のシミュレーション結果を保存
        latestSimContext = {
          courseEval,
          inObj,
          c2Obj,
          c3Obj,
          c4Obj,
          kadoObj,
          inFollowers,
          nonInWinners,
          nonIn1,
          nonIn2,
          nonIn3,
          nf1,
          nf2,
          nf3,
          kimariteStats,
          patternABetsPool,
          patternBBetsPool,
          selectedBets: bets
        };

        const allocStrategy = document.getElementById("allocStrategySelect")?.value || "prob";
        const weightsForAlloc = bets.map(x => {
          if (allocStrategy === "ev") {
            const evVal = (x.prob / 100) * (x.odds || 10);
            return Math.max(0.1, x.prob * (evVal >= 1.05 ? 1.8 : 0.7));
          } else if (allocStrategy === "equal_return") {
            return 1.0 / Math.max(1.5, x.odds || 10.0);
          }
          return x.prob;
        });
        const totalWeight = weightsForAlloc.reduce((s, w) => s + w, 0) || 1;
        const allocs = weightsForAlloc.map(w => Math.max(100, Math.round(((w / totalWeight) * budget) / 100) * 100));
        let sumAlloc = allocs.reduce((a, b) => a + b, 0);
        let k = 0;
        while (sumAlloc !== budget && k < 200) {
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
                <input type="number" step="0.1" value="${b.odds}" onchange="updateEv(${idx},${b.prob},this.value,'${b.combo}',true)" oninput="updateEv(${idx},${b.prob},this.value,'${b.combo}',false)" class="w-14 text-right font-mono text-amber-200 font-bold" />
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
          renderBetGroup(`🟦 パターンA：イン逃げ予想（${groupA.length}点 ／ 1C${inObj.boatId}号艇・${inObj.b.name} 逃げ成功率 ${inObj.effMakuriRate.toFixed(1)}%）`, "bg-sky-950/80 text-sky-300 border border-sky-600/40", groupA) +
          renderBetGroup(`🟥 パターンB：イン逃げ以外予想（${groupB.length}点 ／ ${nonIn1.boatId}号艇${nonIn1.b.name}・${nonIn2.boatId}号艇${nonIn2.b.name} 差し・まくり・展開待ち逆転）`, "bg-rose-950/80 text-rose-300 border border-rose-600/40", groupB);

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
          `■ 2. 進入隊形・コース別攻め成功率 ＆ 直前展示ピックアップ`,
          `・想定進入: [${arr.map(x => x.boatId).join("-")}] （${kadoCourse}コース${kadoObj.boatId}号艇・${kadoObj.b.name}がカド / イン:${deepLabel}）`,
          `・1コース(${inObj.boatId}号艇 ${inObj.b.name}): 逃げ成功率 ${inObj.effMakuriRate.toFixed(1)}%`,
          `・2コース(${c2Obj.boatId}号艇 ${c2Obj.b.name}): 差し成功率 ${c2Obj.effSashiRate.toFixed(1)}% ／ まくり成功率 ${c2Obj.effMakuriRate.toFixed(1)}%`,
          `・3コース(${c3Obj.boatId}号艇 ${c3Obj.b.name}): まくり率 ${c3Obj.effMakuriRate.toFixed(1)}% ／ まくり差し率 ${c3Obj.effMsRate.toFixed(1)}%`,
          `・4コース(${c4Obj.boatId}号艇 ${c4Obj.b.name}): まくり率 ${c4Obj.effMakuriRate.toFixed(1)}% ／ まくり差し率 ${c4Obj.effMsRate.toFixed(1)}%`,
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
          `【🟦 パターンA：イン逃げ推奨目（${groupA.length}点）】`,
          `  ・${aCombos || "なし（非イン特化選択中）"}`,
          `【🟥 パターンB：イン逃げ以外（逆転・穴）推奨目（${groupB.length}点）】`,
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
          `✅ 2C(${c2Obj.boatId}号艇): 差し率${c2Obj.effSashiRate.toFixed(1)}% / まくり率${c2Obj.effMakuriRate.toFixed(1)}%`,
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

      // ---------------------------------------------------------
      // 🧐 自分の予想を入力してAIが採点・スジ評価するチェッカー関数群
      // ---------------------------------------------------------
      function parseUserBetsString(rawStr) {
        if (!rawStr) return [];
        const tokens = rawStr
          .replace(/、|，|\n|\r|\t/g, ",")
          .split(/[,\s]+/)
          .map(s => s.trim())
          .filter(Boolean);

        const comboSet = new Set();
        const expandDigits = (part) => {
          if (part === "全" || part === "9" || part.toUpperCase() === "ALL") return [1, 2, 3, 4, 5, 6];
          return [...part.matchAll(/[1-6]/g)].map(m => Number(m[0]));
        };

        tokens.forEach(tok => {
          const parts = tok.split(/[-=→>]/);
          if (parts.length === 3) {
            const p1 = expandDigits(parts[0]);
            const p2 = expandDigits(parts[1]);
            const p3 = expandDigits(parts[2]);
            p1.forEach(a => {
              p2.forEach(b => {
                p3.forEach(c => {
                  if (a !== b && b !== c && a !== c) {
                    comboSet.add(`${a}-${b}-${c}`);
                  }
                });
              });
            });
          } else if (/^[1-6]{3}$/.test(tok)) {
            const a = Number(tok[0]), b = Number(tok[1]), c = Number(tok[2]);
            if (a !== b && b !== c && a !== c) comboSet.add(`${a}-${b}-${c}`);
          }
        });
        return Array.from(comboSet);
      }

      function addPresetUserFormation(str) {
        const el = document.getElementById("userBetsInput");
        if (el) {
          el.value = str;
          evaluateUserPredictions();
        }
      }


      function insertScenarioTemplate(tplType) {
        const el = document.getElementById("userScenarioMemo");
        if (!el || !latestSimContext) return;
        const { inObj, c2Obj, kadoObj, nonIn1, nf1, inFollowers } = latestSimContext;
        if (tplType === "in_escape") {
          el.value = `1コース${inObj.boatId}号艇(${inObj.b.name})がスタート互角から1マークを先マイ押し切り。2コース${c2Obj.boatId}号艇(${c2Obj.b.name})の差し追走と、外から握って回る${inFollowers[1].boatId}号艇(${inFollowers[1].b.name})を連対軸にしたイン逃げ本線シナリオ。`;
        } else if (tplType === "kado_makuri") {
          el.value = `${kadoObj.courseNo}コースカドの${kadoObj.boatId}号艇(${kadoObj.b.name})がスリットから覗いて1Mまくり敢行！内枠が引き波にハマる展開を突き、外隣からまくり差し連動する${nf1.boatId}号艇(${nf1.b.name})と最内展開待ち勢への高配当スジを狙い撃つ。`;
        } else if (tplType === "sashi_wait") {
          el.value = `1マークで1号艇(${inObj.b.name})とセンター攻め艇(${nonIn1.boatId}号艇)がやり合って外へ流れる展開を想定。ブイ際を冷静に差し抜ける${c2Obj.boatId}号艇・展開待ちから浮上する${nf1.boatId}号艇を軸にイン残しまでケア。`;
        }
        evaluateUserPredictions();
      }

      function applyUserScenarioToReport() {
        const memo = (document.getElementById("userScenarioMemo")?.value || "").trim();
        const rawBets = document.getElementById("userBetsInput")?.value || "";
        const userCombos = parseUserBetsString(rawBets);
        if (!memo && userCombos.length === 0) return;

        const nameOf = (id) => (boatsData[id]?.name || `${id}`).split(" ")[0];
        const formattedUserBets = userCombos.map(c => {
          const [a, b, d] = c.split("-").map(Number);
          const od = liveOddsMap[c] ? ` (${liveOddsMap[c].toFixed(1)}倍)` : "";
          return `${c} (${nameOf(a)}→${nameOf(b)}→${nameOf(d)})${od}`;
        }).join("\n  ・");

        const customPaidSection = [
          `■ 3. 1マークの攻防（✍️ ぼーとだいがくせいの勝負展開シナリオ）`,
          memo || "スリット隊形と1マークのスジ連動から算出した勝負シナリオです。",
          ``,
          `🎯 4. 推奨3連単買い目（計${userCombos.length}点）`,
          `  ・${formattedUserBets || "買い目未入力"}`,
          `※直前オッズでEV(期待値)105%以上の目を厚めに推奨。舟券の購入は自己責任でお楽しみください。`,
          `🎓 ぼーとだいがくせい｜X: https://x.com/Boatrace__daisu ｜ note: https://note.com/boatrace__daisu`,
          `━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━`
        ].join("\n");

        latestReportParts.paid = customPaidSection;
        latestReportParts.paywall = `${latestReportParts.free}\n\n--- 🔒 ここから先は有料エリア（noteの有料ラインをここに設定） ---\n\n${customPaidSection}`;
        latestReportParts.full = `${latestReportParts.free.split("▼ ここから先の有料パートでは")[0].trim()}\n\n${customPaidSection}`;

        const reportFmt = document.getElementById("reportFormatSelect")?.value || "note_paywall";
        const outEl = document.getElementById("noteReportTextarea");
        if (outEl) {
          outEl.value = reportFmt === "note_paywall" ? latestReportParts.paywall : (reportFmt === "x_promo" ? latestReportParts.x_promo : latestReportParts.full);
        }
        const toast = document.getElementById("copyNoteToast");
        if (toast) {
          toast.textContent = "✅ あなたが書いたシナリオと入力買い目を、下のnote/Xレポートに反映しました！";
          toast.classList.remove("hidden");
          setTimeout(() => toast.classList.add("hidden"), 3000);
        }
      }

      function clearUserBetsInput() {
        const el = document.getElementById("userBetsInput");
        if (el) {
          el.value = "";
          evaluateUserPredictions();
        }
      }

      function loadAiBetsToUserInput() {
        if (!latestSimContext || !latestSimContext.selectedBets) return;
        const el = document.getElementById("userBetsInput");
        if (el) {
          el.value = latestSimContext.selectedBets.map(b => b.combo).join(", ");
          evaluateUserPredictions();
        }
      }

      function evaluateUserPredictions() {
        const box = document.getElementById("userEvalResultBox");
        if (!box || !latestSimContext) return;

        const rawInput = document.getElementById("userBetsInput")?.value || "";
        const userCombos = parseUserBetsString(rawInput);
        const userScenario = document.getElementById("userScenarioSelect")?.value || "auto";

        if (userCombos.length === 0) {
          box.innerHTML = `<div class="text-xs text-slate-400 bg-slate-950/60 border border-slate-800 rounded p-2.5">💡 上の入力欄にあなたの買い目（例: <code>1-2-3, 1-2-4</code> や <code>1-23-2345</code>）を入力すると、AIが100点満点で展開整合性・スジ・死角（抜け目）を診断します。</div>`;
          return;
        }

        const { courseEval, inObj, c2Obj, c3Obj, c4Obj, nonIn1, nonIn2, nf1, nf2, inFollowers, patternABetsPool, patternBBetsPool } = latestSimContext;
        const boatToCourse = {};
        Object.values(courseEval).forEach(obj => {
          boatToCourse[obj.boatId] = obj;
        });

        const allAiMap = {};
        [...patternABetsPool, ...patternBBetsPool].forEach(b => {
          allAiMap[`${b.l1}-${b.l2}-${b.l3}`] = b;
        });

        const nameOf = (id) => (boatsData[id]?.name || `${id}`).split(" ")[0];

        let sumFitScore = 0;
        let sumProb = 0;
        let inCount = 0;
        let nonInCount = 0;
        const headBoatsSet = new Set();
        const secondBoatsByHead = {};

        const evaluatedItems = userCombos.map(combo => {
          const [b1, b2, b3] = combo.split("-").map(Number);
          const o1 = boatToCourse[b1], o2 = boatToCourse[b2], o3 = boatToCourse[b3];
          headBoatsSet.add(b1);
          if (!secondBoatsByHead[b1]) secondBoatsByHead[b1] = new Set();
          secondBoatsByHead[b1].add(b2);

          if (o1.courseNo === 1) inCount++;
          else nonInCount++;

          const aiHit = allAiMap[combo];
          let sujiBadge = "□ 標準連動";
          let sujiCls = "bg-slate-800 text-slate-300";
          let itemScore = 60;
          let sujiComment = "";

          if (o1.courseNo === 1) {
            // イン逃げ目
            const fRank2 = inFollowers.findIndex(x => x.boatId === b2);
            const fRank3 = inFollowers.findIndex(x => x.boatId === b3);
            if (fRank2 <= 1 && fRank3 <= 2) {
              sujiBadge = "◎ 王道イン鉄板スジ";
              sujiCls = "bg-sky-950 text-sky-300 border border-sky-600/40";
              itemScore = 92;
              sujiComment = `イン先マイから連対上位(${nameOf(b2)}・${nameOf(b3)})の王道本線`;
            } else if (o2.attackType === "tenkaimachi" || o3.attackType === "tenkaimachi") {
              sujiBadge = "⏳ イン＋展開待ち好妙味";
              sujiCls = "bg-purple-950 text-purple-300 border border-purple-600/40";
              itemScore = 85;
              sujiComment = `1Mもつれを最内展開待ちで拾う高配当スジ`;
            } else if (o2.attackType === "hekomi") {
              sujiBadge = "⚠️ 壁崩壊・2着凹み懸念";
              sujiCls = "bg-rose-950 text-rose-300 border border-rose-600/40";
              itemScore = 45;
              sujiComment = `${b2}号艇はスリット劣勢・被弾懸念があり2着軸にはリスク大`;
            } else {
              sujiBadge = "○ イン逃げ押さえ";
              sujiCls = "bg-slate-800 text-sky-200";
              itemScore = 74;
              sujiComment = `イン逃げ時のヒモ穴ケア`;
            }
          } else {
            // イン逃げ以外の目
            if (o1.attackType === "makuri") {
              if (o2.courseNo === o1.courseNo + 1 || o2.attackType === "tenkaimachi") {
                sujiBadge = "🔥 まくり×外連動 絶好スジ";
                sujiCls = "bg-amber-500/20 text-amber-300 border border-amber-500/50";
                itemScore = 94;
                sujiComment = `${o1.courseNo}Cまくり(${o1.effMakuriRate.toFixed(1)}%)から外隣・展開待ちが連動する黄金スジ！`;
              } else if (o2.courseNo < o1.courseNo) {
                sujiBadge = "⚠️ まくり被弾・逆スジ注意";
                sujiCls = "bg-rose-950 text-rose-300 border border-rose-600/40";
                itemScore = 52;
                sujiComment = `${b1}号艇がまくると内側の${b2}号艇は引き波に沈みやすく、まくり差しなら成立`;
              } else {
                sujiBadge = "○ まくり一撃目";
                sujiCls = "bg-slate-800 text-amber-200";
                itemScore = 76;
                sujiComment = `${o1.courseNo}Cまくり突破からの連対構成`;
              }
            } else if (o1.attackType === "sashi" || o1.attackType === "makurisashi") {
              if (o2.courseNo === 1) {
                sujiBadge = "📐 差し×イン残し 王道スジ";
                sujiCls = "bg-emerald-950 text-emerald-300 border border-emerald-600/40";
                itemScore = 91;
                sujiComment = `${o1.courseNo}Cの${o1.attackType === "sashi" ? "差し" : "まくり差し"}が決まり1コースが残る鉄板スジ！`;
              } else {
                sujiBadge = "⚡ センター攻め連動";
                sujiCls = "bg-slate-800 text-emerald-200";
                itemScore = 79;
                sujiComment = `差し・まくり差しからの波乱連動目`;
              }
            } else {
              sujiBadge = "⏳ 展開待ち一撃大穴";
              sujiCls = "bg-purple-950 text-purple-300 border border-purple-600/40";
              itemScore = 75;
              sujiComment = `1M激戦の隙を突く展開待ち高配当狙い`;
            }
          }

          const estProb = aiHit ? aiHit.prob : Math.max(0.4, Math.round(((o1.firstScore / 220) * (o2.placeScore / 180) * (o3.placeScore / 190) * 6.5) * 10) / 10);
          sumFitScore += itemScore;
          sumProb += estProb;

          const itemOdds = liveOddsMap[combo] || (aiHit ? aiHit.odds : Math.round((100 / Math.max(0.8, estProb)) * 0.75 * 10) / 10);
          const itemEv = Math.round((estProb / 100) * itemOdds * 100);
          return {
            combo,
            runners: `${nameOf(b1)}→${nameOf(b2)}→${nameOf(b3)}`,
            estProb,
            itemOdds,
            itemEv,
            sujiBadge,
            sujiCls,
            itemScore,
            sujiComment,
            isAiRecommended: Boolean(aiHit)
          };
        });

        // 総合スコア（100点満点）とS/A/B/Cランク算出
        const avgFit = sumFitScore / evaluatedItems.length;
        const coverageBonus = Math.min(15, sumProb * 0.32);
        const countPenalty = evaluatedItems.length > 16 ? (evaluatedItems.length - 16) * 1.5 : 0;
        const totalScore = Math.max(35, Math.min(99, Math.round(avgFit * 0.85 + coverageBonus - countPenalty)));
        const gradeRank = totalScore >= 88 ? "S" : totalScore >= 78 ? "A" : totalScore >= 66 ? "B" : "C";
        const rankColor = gradeRank === "S" ? "bg-amber-400 text-slate-950" : gradeRank === "A" ? "bg-sky-400 text-slate-950" : gradeRank === "B" ? "bg-emerald-400 text-slate-950" : "bg-slate-700 text-white";

        // 死角（抜け目）と改善アドバイスの自動生成
        const advices = [];
        headBoatsSet.forEach(hBoat => {
          const hObj = boatToCourse[hBoat];
          if (!hObj) return;
          const secs = secondBoatsByHead[hBoat] || new Set();
          if (hObj.courseNo === 1) {
            if (!secs.has(inFollowers[0].boatId)) {
              advices.push(`⚠️ <strong>【イン逃げの抜け目警告】</strong> 1コース${hBoat}号艇のアタマを買っていますが、連対スコア1位の<strong>${inFollowers[0].boatId}号艇（${inFollowers[0].b.name}・${inFollowers[0].roleText}）</strong>が2着から抜けています。「<strong>${hBoat}-${inFollowers[0].boatId}-${inFollowers[1].boatId}</strong>」の追加を強く推奨します。`);
            }
          } else if (hObj.attackType === "makuri" && hObj.courseNo < 6) {
            const outNeighbor = courseEval[hObj.courseNo + 1];
            if (outNeighbor && !secs.has(outNeighbor.boatId)) {
              advices.push(`🔥 <strong>【まくりスジの死角警告】</strong> ${hObj.courseNo}コース${hBoat}号艇（${hObj.b.name}）のまくり（まくり率${hObj.effMakuriRate.toFixed(1)}%）を狙っていますが、まくった際に一番展開が向く外隣<strong>${outNeighbor.courseNo}コース${outNeighbor.boatId}号艇（${outNeighbor.b.name}）</strong>が2着に入っていません！スジ舟券の鉄則として「<strong>${hBoat}-${outNeighbor.boatId}</strong>」ラインは必見です。`);
            }
          } else if ((hObj.attackType === "sashi" || hObj.attackType === "makurisashi") && !secs.has(inObj.boatId)) {
            advices.push(`📐 <strong>【差し・イン残しの死角警告】</strong> ${hObj.courseNo}コース${hBoat}号艇の差し/まくり差し1着を狙っていますが、差された1コース<strong>${inObj.boatId}号艇（${inObj.b.name}）の2着残り（「${hBoat}-${inObj.boatId}」スジ）</strong>が抜けています。`);
          }
        });

        if (userScenario === "c2_sashi" && c2Obj.effSashiRate < 10.0) {
          advices.push(`💡 <strong>【2コース差し率チェック】</strong> 2コース差しを想定されていますが、本日の風・水面補正後の2コース差し成功率は<strong>${c2Obj.effSashiRate.toFixed(1)}%</strong>とやや低めです。3・4コースの攻め（${nonIn1.boatId}号艇）も併せて押さえると安定します。`);
        }
        if (userScenario === "c2_makuri" && c2Obj.effMakuriRate >= 6.0) {
          advices.push(`🔥 <strong>【2コースジカまくり妙味】</strong> 2コース${c2Obj.boatId}号艇のまくり率は<strong>${c2Obj.effMakuriRate.toFixed(1)}%</strong>。2コースがまくると1コースが引き波に沈み、3コース<strong>${c3Obj.boatId}号艇</strong>・4コース<strong>${c4Obj.boatId}号艇</strong>の差し連動（${c2Obj.boatId}-${c3Obj.boatId}-${c4Obj.boatId}）が特大万舟スジになります！`);
        }
        const memoText = (document.getElementById("userScenarioMemo")?.value || "").trim();
        if (memoText) {
          let memoCheckMsg = `📖 <strong>【あなたの記述シナリオ診断】</strong> 「<em>${memoText.slice(0, 75)}${memoText.length > 75 ? "..." : ""}</em>」`;
          if (memoText.includes("まくり") && !memoText.includes("まくり差") && inCount === evaluatedItems.length) {
            memoCheckMsg += ` → ⚠️ シナリオ文章で「まくり」に言及されていますが、買い目が1コース1着（イン逃げ）のみになっています。まくった艇のアタマ（非イン目）も追加するとシナリオと一致します！`;
          } else if (memoText.includes("逃げ") && nonInCount === evaluatedItems.length) {
            memoCheckMsg += ` → ⚠️ シナリオ文章に「逃げ」とありますが、買い目に1コース1着が入っていません。`;
          } else {
            memoCheckMsg += ` → ✅ <strong>シナリオのストーリーと買い目のスジ構成がしっかり一致しています！</strong>（「📝 このシナリオ＆買い目をnote/Xレポートに反映」ボタンでそのまま記事化できます）`;
          }
          advices.unshift(memoCheckMsg);
        }
        if (advices.length === 0) {
          advices.push(`✅ <strong>【スジ整合性◎】</strong> 狙っている1着艇の決まり手（逃げ・差し・まくり）に対して、2・3着の連動艇（外隣やイン残し・展開待ち）が的確に押さえられた完成度の高いフォーメーションです！`);
        }

        const rowsHtml = evaluatedItems.map(item => `
          <div class="flex flex-wrap items-center justify-between bg-slate-950 border border-slate-800 px-2 py-1 rounded text-[11px] gap-1">
            <div class="flex items-center gap-1.5">
              <span class="font-mono font-black text-white text-xs">${item.combo}</span>
              <span class="text-slate-400 text-[10px]">(${item.runners})</span>
              <span class="px-1.5 py-0.5 rounded text-[10px] font-bold ${item.sujiCls}">${item.sujiBadge}</span>
              ${item.isAiRecommended ? '<span class="text-[9px] bg-amber-500/20 text-amber-300 border border-amber-500/40 px-1 rounded">AI推奨一致</span>' : ""}
            </div>
            <div class="flex items-center gap-2">
              <span class="text-[10px] text-slate-300">${item.sujiComment}</span>
              <span class="font-mono text-sky-300 font-bold">確率 ${item.estProb.toFixed(1)}%</span>
              <span class="font-mono text-amber-300">オッズ ${item.itemOdds.toFixed(1)}倍</span>
              <span class="font-mono px-1.5 py-0.5 rounded text-[10px] font-bold ${item.itemEv >= 105 ? "bg-amber-400 text-slate-950" : "bg-slate-800 text-slate-400"}">EV ${item.itemEv}%</span>
            </div>
          </div>
        `).join("");

        box.innerHTML = `
          <div class="bg-slate-950 border border-pink-500/40 rounded-lg p-2.5 space-y-2">
            <div class="flex flex-wrap items-center justify-between gap-2 border-b border-slate-800 pb-2">
              <div class="flex items-center gap-2">
                <span class="${rankColor} font-black text-sm px-2.5 py-1 rounded shadow">総合判定 ${gradeRank}ランク (${totalScore}点 / 100点)</span>
                <div class="text-[11px] text-slate-200">
                  <div>入力点数: <strong>${evaluatedItems.length}点</strong> （イン逃げ ${inCount}点 ／ 非イン逆転 ${nonInCount}点）</div>
                  <div class="text-sky-300">推定合計カバー確率: <strong>約${Math.min(89.0, sumProb).toFixed(1)}%</strong></div>
                </div>
              </div>
            </div>
            <div class="space-y-1 text-xs leading-relaxed text-slate-200">
              ${advices.map(a => `<p>${a}</p>`).join("")}
            </div>
            <div class="space-y-1 max-h-[240px] overflow-y-auto pr-1 pt-1 border-t border-slate-800/80">
              ${rowsHtml}
            </div>
          </div>
        `;
      }

      function updateEv(idx, prob, oddsVal, comboKey = "", triggerRealloc = false) {
        const parsedOdds = parseFloat(oddsVal) || 0;
        if (comboKey && parsedOdds > 0) {
          liveOddsMap[comboKey] = parsedOdds;
        }
        const ev = Math.round((prob / 100) * parsedOdds * 100);
        const badge = document.getElementById(`ev_badge_${idx}`);
        if (badge) {
          const plus = ev >= 105;
          badge.className = `text-[10px] font-bold px-1.5 py-0.5 rounded ${plus ? "bg-amber-500 text-slate-950" : "bg-slate-800 text-slate-400"}`;
          badge.textContent = `EV ${ev}%${plus ? " ★" : ""}`;
        }
        if (triggerRealloc) {
          runSimulation();
        } else {
          evaluateUserPredictions();
        }
      }

      async function refreshLiveOddsInBrowser() {
        const vCode = document.getElementById("venueSelect").value || "04";
        const rno = document.getElementById("raceNoSelect").value || "12";
        const now = new Date();
        const hd = INITIAL_SERVER_DATA?.meta?.hd || `${now.getFullYear()}${String(now.getMonth() + 1).padStart(2, "0")}${String(now.getDate()).padStart(2, "0")}`;
        const statusEl = document.getElementById("oddsUpdateStatus");
        if (statusEl) {
          statusEl.classList.remove("hidden");
          statusEl.textContent = `⏳ BOAT RACE公式から ${hd} 場コード:${vCode} ${rno}R の最新3連単オッズを取得中...`;
        }

        const targetUrl = `https://www.boatrace.jp/owpc/pc/race/odds3t?rno=${rno}&jcd=${vCode}&hd=${hd}`;
        const proxies = [
          (u) => `https://api.allorigins.win/raw?url=${encodeURIComponent(u)}`,
          (u) => `https://api.codetabs.com/v1/proxy?quest=${encodeURIComponent(u)}`
        ];
        let htmlTxt = null;
        for (const makeUrl of proxies) {
          try {
            const res = await fetch(makeUrl(targetUrl));
            if (res.ok) {
              const t = await res.text();
              if (t && t.includes("oddsPoint")) {
                htmlTxt = t;
                break;
              }
            }
          } catch (e) {}
        }

        if (!htmlTxt) {
          if (statusEl) {
            statusEl.textContent = `💡 ブラウザ直接通信がブロックされたため、画面最上部の「💹 最新オッズのみ更新」ボタンを押すか「📋 オッズ貼付」をご利用ください。`;
          }
          return;
        }

        const parser = new DOMParser();
        const doc = parser.parseFromString(htmlTxt, "text/html");
        const cells = Array.from(doc.querySelectorAll("td.oddsPoint")).map(td => td.textContent.trim());
        let updatedCount = 0;
        if (cells.length === 120) {
          for (let col = 0; col < 6; col++) {
            const fst = col + 1;
            const colVals = [];
            for (let row = 0; row < 20; row++) colVals.push(cells[row * 6 + col]);
            let idxV = 0;
            for (let snd = 1; snd <= 6; snd++) {
              if (snd === fst) continue;
              for (let trd = 1; trd <= 6; trd++) {
                if (trd === fst || trd === snd) continue;
                const val = parseFloat(colVals[idxV]);
                idxV++;
                if (Number.isFinite(val) && val > 0) {
                  liveOddsMap[`${fst}-${snd}-${trd}`] = val;
                  updatedCount++;
                }
              }
            }
          }
        }
        if (statusEl) {
          statusEl.textContent = `✅ 最新3連単オッズ（${updatedCount}通り / ${new Date().toLocaleTimeString()}時点）を更新し、EV・配分を再計算しました！`;
        }
        runSimulation();
      }

      function applyPastedOdds() {
        const raw = (document.getElementById("rawOddsPasteInput")?.value || "").trim();
        if (!raw) return;
        let cnt = 0;

        // 1. 「1-2-3 6.8」や「1-2-3: 12.4」形式の直接ペア抽出
        const pairMatches = [...raw.matchAll(/([1-6])\s*[-=]\s*([1-6])\s*[-=]\s*([1-6])[^\d\n]{1,15}(\d+\.\d+)/g)];
        pairMatches.forEach(m => {
          const combo = `${m[1]}-${m[2]}-${m[3]}`;
          const val = parseFloat(m[4]);
          if (val > 0) {
            liveOddsMap[combo] = val;
            cnt++;
          }
        });

        // 2. 公式3連単オッズ表全文コピペ（120個の小数）の場合
        if (cnt < 6) {
          const allFloats = [...raw.matchAll(/(\d{1,4}\.\d)/g)].map(m => parseFloat(m[1]));
          if (allFloats.length >= 120) {
            const cells = allFloats.slice(0, 120);
            for (let col = 0; col < 6; col++) {
              const fst = col + 1;
              const colVals = [];
              for (let row = 0; row < 20; row++) colVals.push(cells[row * 6 + col]);
              let idxV = 0;
              for (let snd = 1; snd <= 6; snd++) {
                if (snd === fst) continue;
                for (let trd = 1; trd <= 6; trd++) {
                  if (trd === fst || trd === snd) continue;
                  const val = colVals[idxV++];
                  if (Number.isFinite(val) && val > 0) {
                    liveOddsMap[`${fst}-${snd}-${trd}`] = val;
                    cnt++;
                  }
                }
              }
            }
          }
        }

        const statusEl = document.getElementById("oddsUpdateStatus");
        if (statusEl) {
          statusEl.classList.remove("hidden");
          statusEl.textContent = `✅ 貼り付けテキストから ${cnt} 件の3連単オッズを反映しました！`;
        }
        document.getElementById("oddsPasteBox").classList.add("hidden");
        runSimulation();
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
            if (parsed.type === "BOATRACE_LEARNED_PARAMS" && parsed.weights) {
              localStorage.setItem("BOATRACE_LEARNED_PARAMS", JSON.stringify(parsed));
              applyLearnedFeedbackParams();
              document.getElementById("pasteImportBox").classList.add("hidden");
              return;
            }
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

      
    
      // ---------------------------------------------------------
      // ⑭ 本格レースリプレイ 60fps連続アニメーションコントローラー
      // ---------------------------------------------------------
      function updateReplayCanvas(progress) {
        replayProgress = Math.max(0, Math.min(100, progress));
        const slider = document.getElementById("replayProgressSlider");
        if (slider) slider.value = replayProgress;
        const lbl = document.getElementById("replayProgressLabel");
        if (lbl) lbl.textContent = `${Math.round(replayProgress)}%`;

        ReplayEngine.renderFrame("raceReplayCanvas", replayProgress, latestSimContext?.courseEval || {}, latestMonteCarloResult);
      }

      function tickReplayAnimation() {
        if (!replayRunning) return;
        replayProgress += 0.38 * replaySpeed;
        if (replayProgress >= 100) {
          replayProgress = 100;
          updateReplayCanvas(100);
          toggleReplayAutoPlay(false);
          return;
        }
        updateReplayCanvas(replayProgress);
        replayAnimFrameId = requestAnimationFrame(tickReplayAnimation);
      }

      function toggleReplayAutoPlay(forceState = null) {
        const btn = document.getElementById("btnReplayPlay");
        if (forceState !== null) replayRunning = forceState;
        else replayRunning = !replayRunning;

        if (replayRunning) {
          if (replayProgress >= 100) replayProgress = 0;
          if (btn) btn.innerHTML = "⏸️ 一時停止";
          cancelAnimationFrame(replayAnimFrameId);
          replayAnimFrameId = requestAnimationFrame(tickReplayAnimation);
        } else {
          if (btn) btn.innerHTML = "▶️ 再生";
          cancelAnimationFrame(replayAnimFrameId);
        }
      }

      function setReplaySpeed(spd) {
        replaySpeed = spd;
        [1, 1.5, 2].forEach(s => {
          const id = s === 1 ? "btnSpeed1" : s === 1.5 ? "btnSpeed15" : "btnSpeed2";
          const el = document.getElementById(id);
          if (el) {
            if (s === spd) el.className = "px-1.5 py-0.5 rounded bg-slate-800 text-sky-300 font-bold";
            else el.className = "px-1.5 py-0.5 rounded text-slate-400 hover:text-white";
          }
        });
      }

      // ---------------------------------------------------------
      // ⑪ 初級者モード vs ⑫ 上級者モード切替
      // ---------------------------------------------------------
      function switchUIMode(mode) {
        const btnBeg = document.getElementById("btnModeBeginner");
        const btnPro = document.getElementById("btnModePro");
        if (btnBeg && btnPro) {
          if (mode === "beginner") {
            btnBeg.className = "px-3 py-1 text-xs font-black rounded-md transition-colors bg-teal-600 text-white shadow";
            btnPro.className = "px-3 py-1 text-xs font-bold rounded-md transition-colors text-slate-400 hover:text-white";
          } else {
            btnPro.className = "px-3 py-1 text-xs font-black rounded-md transition-colors bg-sky-600 text-white shadow";
            btnBeg.className = "px-3 py-1 text-xs font-bold rounded-md transition-colors text-slate-400 hover:text-white";
          }
        }
        UIManager.applyUIMode(mode);
      }

      // ---------------------------------------------------------
      // イベントリスナー統一バインド (addEventListener)
      // ---------------------------------------------------------
      function initAppEventListeners() {
        // モード切替
        document.getElementById("btnModeBeginner")?.addEventListener("click", () => switchUIMode("beginner"));
        document.getElementById("btnModePro")?.addEventListener("click", () => switchUIMode("pro"));

        // 再計算ボタン & 試行回数 & 資金
        document.getElementById("btnRunSimTop")?.addEventListener("click", () => runSimulation());
        document.getElementById("simRunsSelect")?.addEventListener("change", () => runSimulation());
        document.getElementById("smartBudgetInput")?.addEventListener("change", () => runSimulation());

        // リプレイ操作バインド
        document.getElementById("btnReplayPlay")?.addEventListener("click", () => toggleReplayAutoPlay());
        document.getElementById("replayProgressSlider")?.addEventListener("input", (e) => {
          toggleReplayAutoPlay(false);
          updateReplayCanvas(parseFloat(e.target.value));
        });
        document.querySelectorAll(".btn-replay-stage").forEach((btn) => {
          btn.addEventListener("click", () => {
            toggleReplayAutoPlay(false);
            updateReplayCanvas(parseFloat(btn.dataset.pct || 0));
          });
        });
        document.getElementById("btnSpeed1")?.addEventListener("click", () => setReplaySpeed(1.0));
        document.getElementById("btnSpeed15")?.addEventListener("click", () => setReplaySpeed(1.5));
        document.getElementById("btnSpeed2")?.addEventListener("click", () => setReplaySpeed(2.0));

        // Version 3.0 イベントデリゲーション (addEventListener 統一)
        document.addEventListener("click", (e) => {
          const btn = e.target.closest("[data-action]");
          if (!btn) return;
          const act = btn.dataset.action;
          if (act === "setUIMode") {
            switchUIMode(btn.dataset.mode || "pro");
          } else if (act === "setQuickBudget") {
            const bVal = Number(btn.dataset.budget || 5000);
            AppStateV3.budget = bVal;
            const bIn = document.getElementById("budgetInput");
            if (bIn) bIn.value = String(bVal);
            runSimulation();
          } else if (act === "applyRecommendedWeights") {
            const comp = LearningEngine.compareCurrentAndRecommendedWeights();
            setWeightPreset(comp.recommended.w_course, comp.recommended.w_exhibit, comp.recommended.w_motor, comp.recommended.w_slit);
          } else if (act === "replayToggle") {
            toggleReplayAutoPlay();
          } else if (act === "replayStage") {
            toggleReplayAutoPlay(false);
            updateReplayCanvas(Number(btn.dataset.pct || 0));
          } else if (act === "replaySpeed") {
            setReplaySpeed(Number(btn.dataset.speed || 1.0));
          }
        });

        document.addEventListener("change", (e) => {
          const el = e.target.closest("[data-change]");
          if (!el) return;
          const chg = el.dataset.change;
          if (chg === "changeMcRuns") {
            AppStateV3.mcRuns = Number(el.value || 5000);
            runSimulation();
          } else if (chg === "changeBankrollMode") {
            AppStateV3.bankrollMode = el.value || "ev_focus";
            runSimulation();
          }
        });

        // 保存されたUIモードの復元
        const savedMode = StorageManager.getUIMode();
        switchUIMode(savedMode || "pro");
      }

      

    
      // ---------------------------------------------------------
      // 🎯 手動戦術・展開指定コントロール機能
      // ---------------------------------------------------------
      function getCourseLayout() {
        const layout = [];
        for (let c = 1; c <= 6; c++) {
          const el = document.getElementById("course_" + c);
          layout.push(el ? Number(el.value || c) : c);
        }
        return layout;
      }

      function renderCourseTacticsGrid(courseEval = null) {
        const grid = document.getElementById("courseTacticsControlGrid");
        if (!grid) return;
        grid.innerHTML = "";

        const courses = getCourseLayout();
        for (let c = 1; c <= 6; c++) {
          const bId = courses[c - 1] || c;
          const bData = boatsData[bId] || {};
          const curTactic = bData.manualTactic || "auto";
          const isManual = curTactic !== "auto";
          const bColor = BOAT_COLORS[bId] || BOAT_COLORS[1];
          const cleanName = (bData.name || `${bId}号艇`).split(" ")[0];
          const autoRoleLabel = courseEval && courseEval[c] && courseEval[c].roleText
            ? `🤖 自動: ${courseEval[c].roleText}`
            : "🤖 過去分析AI自動";

          const pastTendency = c === 1
            ? `逃${(bData.courseWin || 70).toFixed(0)}% / ST.${Math.round((bData.seriesSt || 0.13) * 100).toString().padStart(2, "0")}`
            : c === 2
              ? `差${(bData.sashiRate || 16).toFixed(0)}%・逃がし${(bData.nigashi || 55).toFixed(0)}%`
              : `捲${(bData.makuriRate || 10).toFixed(0)}% / 捲差${(bData.makurisashiRate || 10).toFixed(0)}% / 二番差${(bData.sashiRate || 5).toFixed(0)}%`;

          grid.innerHTML += `
            <div class="bg-slate-950 border ${isManual ? "border-pink-500 shadow-md shadow-pink-500/20" : "border-slate-800"} rounded-lg p-2 text-center space-y-1">
              <div class="flex items-center justify-center gap-1">
                <span class="text-[11px] font-bold text-slate-400">${c}コース</span>
                <span class="w-4 h-4 rounded text-[10px] font-black flex items-center justify-center" style="background:${bColor.body};color:${bColor.text};border:1px solid ${bColor.border}">${bId}</span>
              </div>
              <div class="text-[11px] font-bold text-white truncate">${cleanName}</div>
              <div class="text-[9px] font-mono text-emerald-300 bg-emerald-950/50 rounded px-1 py-0.5 truncate" title="過去レース傾向">${pastTendency}</div>
              <select onchange="updateCourseManualTactic(${c}, this.value)" class="w-full text-[10px] font-bold py-1 px-1 rounded ${isManual ? "bg-pink-950 text-pink-200 border-pink-500" : "bg-slate-900 text-sky-200 border-slate-700"}">
                <option value="auto" ${curTactic === "auto" ? "selected" : ""}>${autoRoleLabel}</option>
                <option value="nige" ${curTactic === "nige" ? "selected" : ""}>🛡️ 逃げ(先マイ)</option>
                <option value="sashi" ${curTactic === "sashi" ? "selected" : ""}>📐 差し(1M差し)</option>
                <option value="nibanzashi" ${curTactic === "nibanzashi" ? "selected" : ""}>📐 二番差し(連動差)</option>
                <option value="makuri" ${curTactic === "makuri" ? "selected" : ""}>🔥 まくり(強襲)</option>
                <option value="makurisashi" ${curTactic === "makurisashi" ? "selected" : ""}>⚡ まくり差し</option>
                <option value="tenkaimachi" ${curTactic === "tenkaimachi" ? "selected" : ""}>⏳ 展開待ち(内差)</option>
                <option value="sotomai" ${curTactic === "sotomai" ? "selected" : ""}>🌀 外マイ(追走)</option>
                <option value="hekomi" ${curTactic === "hekomi" ? "selected" : ""}>⚠️ 凹み・壁崩壊</option>
              </select>
              ${isManual ? '<div class="text-[9px] text-pink-400 font-bold">🎯 手動指定中</div>' : `<div class="text-[9px] text-sky-400 truncate">${courseEval && courseEval[c] ? courseEval[c].roleText : "📊 過去傾向連動"}</div>`}
            </div>
          `;
        }
      }

      function updateCourseManualTactic(c, tacticVal) {
        const courses = getCourseLayout();
        const bId = courses[c - 1] || c;
        if (boatsData[bId]) {
          boatsData[bId].manualTactic = tacticVal;
        }

        const autoCouple = document.getElementById("chkAutoCoupleTactics")?.checked ?? true;
        if (autoCouple && tacticVal !== "auto") {
          const setCourseTac = (courseNum, tac) => {
            const id = courses[courseNum - 1] || courseNum;
            if (boatsData[id]) boatsData[id].manualTactic = tac;
          };
          if (c === 1 && tacticVal === "nige") {
            setCourseTac(2, "sashi"); setCourseTac(3, "sotomai"); setCourseTac(4, "nibanzashi"); setCourseTac(5, "makurisashi"); setCourseTac(6, "tenkaimachi");
          } else if (c === 2 && tacticVal === "sashi") {
            setCourseTac(1, "nige"); setCourseTac(3, "nibanzashi"); setCourseTac(4, "nibanzashi"); setCourseTac(5, "makurisashi"); setCourseTac(6, "tenkaimachi");
          } else if (c === 2 && tacticVal === "makuri") {
            setCourseTac(1, "hekomi"); setCourseTac(3, "sashi"); setCourseTac(4, "nibanzashi"); setCourseTac(5, "tenkaimachi"); setCourseTac(6, "tenkaimachi");
          } else if (c === 3 && (tacticVal === "nibanzashi" || tacticVal === "sashi")) {
            setCourseTac(1, "nige"); setCourseTac(2, "sashi"); setCourseTac(4, "nibanzashi"); setCourseTac(5, "makurisashi"); setCourseTac(6, "tenkaimachi");
          } else if (c === 3 && tacticVal === "makuri") {
            setCourseTac(1, "hekomi"); setCourseTac(2, "hekomi"); setCourseTac(4, "nibanzashi"); setCourseTac(5, "makurisashi"); setCourseTac(6, "tenkaimachi");
          } else if (c === 3 && tacticVal === "makurisashi") {
            setCourseTac(1, "nige"); setCourseTac(2, "sashi"); setCourseTac(4, "nibanzashi"); setCourseTac(5, "makurisashi"); setCourseTac(6, "tenkaimachi");
          } else if (c === 4 && (tacticVal === "nibanzashi" || tacticVal === "sashi")) {
            setCourseTac(1, "nige"); setCourseTac(2, "sashi"); setCourseTac(3, "sotomai"); setCourseTac(5, "makurisashi"); setCourseTac(6, "tenkaimachi");
          } else if (c === 4 && tacticVal === "makuri") {
            setCourseTac(1, "hekomi"); setCourseTac(2, "hekomi"); setCourseTac(3, "hekomi"); setCourseTac(5, "makurisashi"); setCourseTac(6, "tenkaimachi");
          } else if (c === 4 && tacticVal === "makurisashi") {
            setCourseTac(1, "nige"); setCourseTac(2, "sashi"); setCourseTac(3, "sotomai"); setCourseTac(5, "makurisashi"); setCourseTac(6, "tenkaimachi");
          }
        }

        renderBoatCards();
        runSimulation();
      }

      function setTacticsPreset(type) {
        const courses = getCourseLayout();
        const presets = {
          in_nige:   { 1: "nige",   2: "sashi",  3: "sotomai",     4: "nibanzashi",  5: "makurisashi", 6: "tenkaimachi" },
          c2_sashi:  { 1: "nige",   2: "sashi",  3: "nibanzashi",  4: "nibanzashi",  5: "tenkaimachi", 6: "tenkaimachi" },
          c2_makuri: { 1: "hekomi", 2: "makuri", 3: "sashi",       4: "nibanzashi",  5: "tenkaimachi", 6: "tenkaimachi" },
          c3_attack: { 1: "nige",   2: "sashi",  3: "makurisashi", 4: "nibanzashi",  5: "makurisashi", 6: "tenkaimachi" },
          c3_makuri: { 1: "hekomi", 2: "hekomi", 3: "makuri",      4: "nibanzashi",  5: "makurisashi", 6: "tenkaimachi" },
          c4_makuri: { 1: "hekomi", 2: "hekomi", 3: "hekomi",      4: "makuri",      5: "makurisashi", 6: "tenkaimachi" },
          out_wait:  { 1: "nige",   2: "hekomi", 3: "makuri",      4: "nibanzashi",  5: "tenkaimachi", 6: "tenkaimachi" },
          reset:     { 1: "auto",   2: "auto",   3: "auto",        4: "auto",        5: "auto",        6: "auto" }
        };

        const target = presets[type] || presets.reset;
        for (let c = 1; c <= 6; c++) {
          const bId = courses[c - 1] || c;
          if (boatsData[bId]) {
            boatsData[bId].manualTactic = target[c] || "auto";
          }
        }
        renderCourseTacticsGrid();
        renderBoatCards();
        runSimulation();
      }

    

      

    window.addEventListener("DOMContentLoaded", () => {
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
  </body>
</html>"""


EMBEDDED_REVIEWER_HTML = r"""<!doctype html>
<html lang="ja">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>🎓 ぼーとだいがくせい｜レース結果×予想 振り返りアナライザー (POST-RACE REVIEW LAB)</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
      body { background: #090d16; color: #f8fafc; font-family: sans-serif; margin: 0; }
      .boat-1 { background: #ffffff; color: #0f172a; border: 1px solid #cbd5e1; }
      .boat-2 { background: #1e293b; color: #ffffff; border: 1px solid #64748b; }
      .boat-3 { background: #ef4444; color: #ffffff; }
      .boat-4 { background: #3b82f6; color: #ffffff; }
      .boat-5 { background: #eab308; color: #0f172a; }
      .boat-6 { background: #22c55e; color: #ffffff; }
      input[type="number"], select, input[type="date"], input[type="text"], textarea {
        background: #131c2e; border: 1px solid #2dd4bf40; color: #f8fafc;
        border-radius: 0.375rem; padding: 0.25rem 0.45rem; font-size: 0.78rem;
      }
      .slit-lane {
        position: relative; height: 42px; border-bottom: 1px dashed #1e293b;
        display: flex; align-items: center;
      }
      .kado-line { border-top: 2px dashed #f43f5e !important; }
    </style>
  </head>
  <body class="pb-14">
    <!-- Header -->
    <header class="sticky top-0 z-30 bg-slate-950/95 border-b border-teal-500/30 px-3 py-2.5 shadow-lg backdrop-blur">
      <div class="max-w-7xl mx-auto flex flex-wrap items-center justify-between gap-2">
        <div class="flex items-center gap-2">
          <span class="bg-teal-400 text-slate-950 font-black px-2 py-0.5 rounded text-xs">POST-RACE REVIEW LAB</span>
          <h1 class="text-sm md:text-base font-bold text-white">
            🎓 ぼーとだいがくせい｜レース結果×予想 答え合わせ＆敗因解剖アナライザー
          </h1>
          <span id="headerStatusBadge" class="text-[11px] font-bold text-teal-300 ml-1"></span>
        </div>

        <div class="flex flex-wrap items-center gap-1.5 text-xs">
          <!-- もう1個のサイト（予想シミュレーター）への直通リンク -->
          <a href="https://bdkzgfy4igpjbzjachuzwu.streamlit.app/" target="_blank" rel="noopener" class="bg-sky-500 hover:bg-sky-400 text-slate-950 font-black px-3 py-1 rounded shadow flex items-center gap-1">
            🚤 予想シミュレーター(本サイト)へ移動 ↗
          </a>
          <button onclick="document.getElementById('pasteResultModal').classList.toggle('hidden')" class="bg-teal-700 hover:bg-teal-600 text-white font-bold px-2.5 py-1 rounded shadow">
            📥 結果テキスト貼付
          </button>
          <button onclick="loadSampleCase('makuri_hit')" class="bg-slate-800 hover:bg-slate-700 text-amber-300 border border-amber-500/40 px-2 py-1 rounded">
            例①: 4カドまくり的中
          </button>
          <button onclick="loadSampleCase('sashi_miss')" class="bg-slate-800 hover:bg-slate-700 text-rose-300 border border-rose-500/40 px-2 py-1 rounded">
            例②: イン買い→2差抜け
          </button>
          <button onclick="loadSampleCase('in_hit')" class="bg-slate-800 hover:bg-slate-700 text-sky-300 border border-sky-500/40 px-2 py-1 rounded">
            例③: イン逃げ的中
          </button>
          <a href="https://x.com/Boatrace__daisu" target="_blank" rel="noopener" class="bg-slate-900 hover:bg-slate-800 text-white border border-slate-600 px-2 py-1 rounded font-bold">
            𝕏 @Boatrace__daisu
          </a>
          <a href="https://note.com/boatrace__daisu" target="_blank" rel="noopener" class="bg-emerald-950 hover:bg-emerald-900 text-emerald-300 border border-emerald-600/50 px-2 py-1 rounded font-bold">
            📓 note
          </a>
        </div>
      </div>
    </header>

    <main class="max-w-7xl mx-auto px-3 pt-3 space-y-3">
      <!-- 🔄 公式レース結果＆配当(3連単・2連単・人気) 自動取得バー -->
      <section class="bg-slate-900 border-2 border-teal-500/40 rounded-xl p-2.5 flex flex-wrap items-center justify-between gap-2">
        <div class="flex flex-wrap items-center gap-2 text-xs">
          <span class="bg-teal-500/20 text-teal-300 border border-teal-500/40 font-bold px-2 py-0.5 rounded text-[11px]">🏁 公式結果・配当 自動取得</span>
          <div>
            <label class="text-[10px] text-slate-400 mr-1">開催日</label>
            <input type="date" id="fetchDateInput" class="font-mono" />
          </div>
          <div>
            <label class="text-[10px] text-slate-400 mr-1">場</label>
            <select id="fetchVenueCode" class="font-bold">
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
            <label class="text-[10px] text-slate-400 mr-1">R</label>
            <select id="fetchRno" class="font-bold text-amber-300">
              <option value="1">1R</option><option value="2">2R</option><option value="3">3R</option><option value="4">4R</option>
              <option value="5">5R</option><option value="6">6R</option><option value="7">7R</option><option value="8">8R</option>
              <option value="9">9R</option><option value="10">10R</option><option value="11">11R</option><option value="12" selected>12R</option>
            </select>
          </div>
          <button onclick="autoFetchOfficialResultFromWeb()" class="bg-teal-400 hover:bg-teal-300 text-slate-950 font-black px-3 py-1 rounded shadow">
            🔄 公式から着順・配当・実STを自動取得
          </button>
        </div>
        <span id="autoFetchMsg" class="text-[11px] font-bold text-amber-300">💡 開催日・場・Rを選んで自動取得を押すと、3連単/2連単配当・人気・決まり手・実STが自動入力されます</span>
      </section>

      <!-- 公式結果テキストコピペ取込ボックス -->
      <section id="pasteResultModal" class="hidden bg-slate-900 border-2 border-teal-500/50 rounded-xl p-3 space-y-2">
        <div class="flex items-center justify-between border-b border-slate-800 pb-1">
          <h2 class="text-xs font-bold text-teal-300">📥 BOAT RACE公式「レース結果」ページの全文コピペ一括取込</h2>
          <button onclick="document.getElementById('pasteResultModal').classList.add('hidden')" class="text-xs text-slate-400 hover:text-white">✕ 閉じる</button>
        </div>
        <textarea id="rawResultPasteInput" rows="4" placeholder="BOAT RACE公式の「結果（raceresult）」ページを全選択コピー（Ctrl+A → Ctrl+C）してここに貼り付けると、1〜6着順・選手名・本番進入・本番ST・決まり手・3連単配当・2連単配当・人気順を自動で読み取ります。" class="w-full bg-slate-950 border border-slate-700 rounded p-2 text-xs font-mono text-slate-200"></textarea>
        <div class="flex justify-end gap-2">
          <button onclick="parsePastedOfficialResult()" class="bg-teal-400 hover:bg-teal-300 text-slate-950 font-black text-xs px-4 py-1.5 rounded shadow">⚡ 結果テキストを解析して反映する</button>
        </div>
      </section>

      <div class="grid grid-cols-1 lg:grid-cols-12 gap-4">
        <!-- 左カラム (6 cols): ①実際のレース結果入力 ＋ ②あなたの事前予想入力 ＋ ③展示ST vs 本番ST比較 -->
        <section class="lg:col-span-6 space-y-3">
          <!-- ① 確定したレース結果データ -->
          <div class="bg-slate-900 border border-teal-500/30 rounded-xl p-3 space-y-2.5">
            <div class="flex flex-wrap items-center justify-between gap-1 border-b border-slate-800 pb-1.5">
              <h2 class="text-xs font-bold text-teal-300">🏁 ① 確定したレース結果（着順・決まり手・3連単/2連単配当・人気）</h2>
              <span id="payoutPopularBadge" class="text-[10px] bg-amber-950 text-amber-300 border border-amber-600/40 px-2 py-0.5 rounded font-bold">3連単配当 自動連動</span>
            </div>

            <div class="grid grid-cols-2 sm:grid-cols-6 gap-2 text-xs">
              <div>
                <label class="block text-slate-400 text-[10px]">レース場</label>
                <select id="revVenue" onchange="runReviewAnalysis()" class="w-full font-bold">
                  <option value="桐生">01 桐生</option><option value="戸田">02 戸田</option><option value="江戸川">03 江戸川</option>
                  <option value="平和島" selected>04 平和島</option><option value="多摩川">05 多摩川</option><option value="浜名湖">06 浜名湖</option>
                  <option value="蒲郡">07 蒲郡</option><option value="常滑">08 常滑</option><option value="津">09 津</option>
                  <option value="三国">10 三国</option><option value="びわこ">11 びわこ</option><option value="住之江">12 住之江</option>
                  <option value="尼崎">13 尼崎</option><option value="鳴門">14 鳴門</option><option value="丸亀">15 丸亀</option>
                  <option value="児島">16 児島</option><option value="宮島">17 宮島</option><option value="徳山">18 徳山</option>
                  <option value="下関">19 下関</option><option value="若松">20 若松</option><option value="芦屋">21 芦屋</option>
                  <option value="福岡">22 福岡</option><option value="唐津">23 唐津</option><option value="大村">24 大村</option>
                </select>
              </div>
              <div>
                <label class="block text-slate-400 text-[10px]">R / グレード</label>
                <div class="flex gap-1">
                  <select id="revRaceNo" onchange="runReviewAnalysis()" class="w-1/2 font-bold text-amber-300">
                    <option value="1">1R</option><option value="2">2R</option><option value="3">3R</option><option value="4">4R</option>
                    <option value="5">5R</option><option value="6">6R</option><option value="7">7R</option><option value="8">8R</option>
                    <option value="9">9R</option><option value="10">10R</option><option value="11">11R</option><option value="12" selected>12R</option>
                  </select>
                  <select id="revGrade" onchange="runReviewAnalysis()" class="w-1/2 font-bold text-amber-200">
                    <option value="一般">一般</option><option value="G3">G3</option><option value="G2">G2</option>
                    <option value="G1" selected>G1</option><option value="PG1">PG1</option><option value="SG">SG</option>
                  </select>
                </div>
              </div>
              <div>
                <label class="block text-teal-300 font-bold text-[10px]">確定 1着-2着-3着</label>
                <div class="flex gap-1">
                  <select id="fin1" onchange="runReviewAnalysis()" class="w-1/3 font-black text-amber-300"><option value="1">1</option><option value="2">2</option><option value="3">3</option><option value="4" selected>4</option><option value="5">5</option><option value="6">6</option></select>
                  <select id="fin2" onchange="runReviewAnalysis()" class="w-1/3 font-black text-slate-200"><option value="1">1</option><option value="2">2</option><option value="3">3</option><option value="4">4</option><option value="5" selected>5</option><option value="6">6</option></select>
                  <select id="fin3" onchange="runReviewAnalysis()" class="w-1/3 font-black text-amber-600"><option value="1" selected>1</option><option value="2">2</option><option value="3">3</option><option value="4">4</option><option value="5">5</option><option value="6">6</option></select>
                </div>
              </div>
              <div>
                <label class="block text-teal-300 font-bold text-[10px]">実際の決まり手</label>
                <select id="actualKimarite" onchange="runReviewAnalysis()" class="w-full font-bold text-rose-300">
                  <option value="nige">🛡️ 逃げ</option>
                  <option value="sashi">📐 差し</option>
                  <option value="makuri" selected>🔥 まくり</option>
                  <option value="makurisashi">⚡ まくり差し</option>
                  <option value="nuki">🌀 抜き(道中逆転)</option>
                  <option value="megumare">⚠️ 恵まれ(F/事故)</option>
                </select>
              </div>
              <div>
                <label class="block text-amber-300 font-bold text-[10px]">3連単配当(円)/人気</label>
                <div class="flex gap-1">
                  <input type="number" id="payoutYen" value="4820" step="10" min="100" onchange="runReviewAnalysis()" class="w-2/3 font-mono font-bold text-amber-300" title="3連単払戻金(円)" />
                  <input type="number" id="payoutPop" value="18" min="1" max="120" onchange="runReviewAnalysis()" class="w-1/3 font-mono text-slate-300" title="人気順" />
                </div>
              </div>
              <div>
                <label class="block text-slate-400 text-[10px]">2連単配当 / 風速(m)</label>
                <div class="flex gap-1">
                  <input type="number" id="payout2tYen" value="1450" step="10" min="100" onchange="runReviewAnalysis()" class="w-1/2 font-mono text-sky-300" title="2連単払戻金(円)" />
                  <select id="actualWindDir" onchange="runReviewAnalysis()" class="w-1/4" title="風向">
                    <option value="向かい風" selected>向</option><option value="追い風">追</option><option value="横風">横</option><option value="無風">無</option>
                  </select>
                  <input type="number" id="actualWindSpeed" value="4" min="0" max="15" onchange="runReviewAnalysis()" class="w-1/4" title="風速(m)" />
                </div>
              </div>
            </div>

            <!-- 6艇の展示ST vs 本番ST ＆ 1M実際の動きテーブル -->
            <div class="pt-2 border-t border-slate-800">
              <div class="flex items-center justify-between mb-1">
                <span class="text-[11px] font-bold text-slate-300">⏱️ コース別【事前想定(展示)ST vs 本番実ST】＆ 1マーク実際の動き</span>
                <span class="text-[10px] text-slate-400">カド位置(標準4カド): <select id="actualKado" onchange="runReviewAnalysis()" class="text-[10px] py-0 px-1 font-bold text-rose-400"><option value="3">3カド</option><option value="4" selected>4カド(標準)</option><option value="5">5カド</option></select></span>
              </div>
              <div class="overflow-x-auto">
                <table class="w-full text-xs text-left">
                  <thead class="text-[10px] text-slate-400 border-b border-slate-800">
                    <tr>
                      <th class="py-1">進入</th>
                      <th class="py-1">艇・選手名</th>
                      <th class="py-1 text-center">展示時計</th>
                      <th class="py-1 text-center">事前/展示ST</th>
                      <th class="py-1 text-center text-teal-300">本番実ST</th>
                      <th class="py-1 text-center">ST変化</th>
                      <th class="py-1 text-center text-amber-300">1Mの実際の攻め/動き</th>
                      <th class="py-1 text-center text-sky-300">1M出口順</th>
                      <th class="py-1 text-center text-teal-300">確定着順</th>
                    </tr>
                  </thead>
                  <tbody id="boatStInputTable" class="divide-y divide-slate-800/60"></tbody>
                </table>
              </div>
            </div>

            <!-- 🌀 新設：1周1マークの実際の攻防プロセス ＆ 道中（2M以降）の逆転・推移 -->
            <div class="pt-2.5 border-t border-slate-800 space-y-2">
              <div class="flex flex-wrap items-center justify-between gap-1">
                <span class="text-[11px] font-bold text-amber-300">🌀 1マークの実際の攻防プロセス ＆ 道中逆転（映像なし・数値逆算エンジン搭載）</span>
                <button onclick="infer1MProcessFromNumbers(true)" class="text-[10px] bg-amber-400 hover:bg-amber-300 text-slate-950 font-black px-2 py-0.5 rounded shadow">
                  🤖 ST差×着順×タイムから1M攻防＆道中逆転を自動逆算
                </button>
              </div>
              <div class="grid grid-cols-1 sm:grid-cols-3 gap-2 text-xs">
                <div>
                  <label class="block text-slate-400 text-[10px]">① 1マークの展開トリガー(実際の攻防)</label>
                  <select id="firstMarkPattern" onchange="runReviewAnalysis()" class="w-full font-bold text-amber-200">
                    <option value="clean_in">🛡️ インが完璧先マイ・壁機能</option>
                    <option value="in_flow">🌊 インが先マイもターン膨らみ/流れ</option>
                    <option value="c2_sashi_atk">📐 2コースが鋭く差し切り/肉薄</option>
                    <option value="c2_makuri_atk">🔥 2コースがジカまくり仕掛け</option>
                    <option value="center_makuri_atk" selected>🔥 3・4コースがまくり仕掛け(内被弾)</option>
                    <option value="center_ms_atk">⚡ 3・4コースがまくり差し突き抜け</option>
                    <option value="clash_wait">💥 1Mで内と攻め艇がやり合い(展開待ち浮上)</option>
                  </select>
                </div>
                <div>
                  <label class="block text-slate-400 text-[10px]">② 道中（1周2M以降）の着順変動・逆転</label>
                  <select id="dochuOvertakeType" onchange="runReviewAnalysis()" class="w-full font-bold text-sky-200">
                    <option value="none" selected>✅ 1M出口隊形のまま確定(道中逆転なし)</option>
                    <option value="overtake_1st">🔄 1着が道中逆転(2M差し返し・抜き)</option>
                    <option value="overtake_2nd">🔄 2着が道中逆転(2番手競り・2M逆転)</option>
                    <option value="overtake_3rd">🔄 3着が道中逆転(道中追い上げ・3番手逆転)</option>
                    <option value="overtake_both">🔄 2・3着ともに道中で入れ替わり(混戦)</option>
                    <option value="accident">⚠️ キャビり・不良航法・転覆等で変動</option>
                  </select>
                </div>
                <div>
                  <label class="block text-slate-400 text-[10px]">③ 道中逆転・浮上の主な要因</label>
                  <select id="dochuReason" onchange="runReviewAnalysis()" class="w-full font-bold text-emerald-200">
                    <option value="none" selected>ー (1Mスジ通り決着)</option>
                    <option value="turn_power">⚙️ 出足・回り足(周回気配・機力)の圧倒的差</option>
                    <option value="2m_mistake">🌊 2マークで先行艇がツケマイ失敗・流れ</option>
                    <option value="racer_skill">🎓 選手の道中さばき・実力(G1勝率)差</option>
                    <option value="bad_water">💨 波・うねり・強風でのターン乱れ</option>
                  </select>
                </div>
              </div>
            </div>
          </div>

          <!-- ② あなたの事前予想（買い目・想定展開・投資金額） -->
          <div class="bg-slate-900 border border-pink-500/40 rounded-xl p-3 space-y-2.5">
            <div class="flex flex-wrap items-center justify-between gap-1 border-b border-slate-800 pb-1.5">
              <h2 class="text-xs font-bold text-pink-300">🎯 ② あなたが事前に予想していた内容（買い目・想定展開・投資金額）</h2>
              <span class="text-[10px] text-slate-400">単発 `1-2-3` やフォーメーション `1-23-2345` に対応</span>
            </div>

            <div class="grid grid-cols-1 sm:grid-cols-3 gap-2 text-xs">
              <div>
                <label class="block text-slate-400 text-[10px]">事前の本命シナリオ</label>
                <select id="preExpectedScenario" onchange="runReviewAnalysis()" class="w-full font-bold text-pink-200">
                  <option value="nige">🛡️ 1コースイン逃げ本線</option>
                  <option value="sashi">📐 2・3コース差し逆転</option>
                  <option value="makuri" selected>🔥 4カド・センターまくり</option>
                  <option value="makurisashi">⚡ センターまくり差し</option>
                  <option value="tenkaimachi">⏳ 展開待ち高配当狙い</option>
                  <option value="two_pattern">🔄 イン逃げ＋非インの2パターン</option>
                </select>
              </div>
              <div>
                <label class="block text-slate-400 text-[10px]">総投資額(円)</label>
                <input type="number" id="totalInvestYen" value="4000" step="100" min="100" onchange="runReviewAnalysis()" class="w-full font-mono font-bold text-amber-300" />
              </div>
              <div>
                <label class="block text-slate-400 text-[10px]">的中目の購入額(円/1点)</label>
                <input type="number" id="hitTicketYen" value="500" step="100" min="100" onchange="runReviewAnalysis()" class="w-full font-mono font-bold text-emerald-300" />
              </div>
            </div>

            <div>
              <label class="block text-slate-400 text-[10px] mb-1">事前購入・予想していた3連単買い目（カンマ・スペース・フォーメーション可）</label>
              <textarea id="preBetsInput" rows="2" oninput="runReviewAnalysis()" class="w-full bg-slate-950 border border-pink-500/40 rounded p-2 text-xs font-mono text-white">1-2-4, 1-4-2, 4-5-1, 4-1-5, 4-5-2, 3-4-5</textarea>
            </div>
          </div>

          <!-- ③ 事前想定スリット vs 本番実スリット 比較ビジュアルマップ -->
          <div class="bg-slate-900 border border-slate-800 rounded-xl p-3 space-y-2">
            <div class="flex items-center justify-between">
              <h2 class="text-xs font-bold text-teal-400">📊 ③ 事前想定スリット vs 本番実スリット 比較マップ（赤破線＝4カド標準）</h2>
              <span class="text-[10px] text-slate-400">半透明＝展示/事前ST ／ 実線バッジ＝本番実ST</span>
            </div>
            <div class="bg-slate-950 border border-slate-800 rounded-lg p-2 relative overflow-hidden">
              <div class="absolute right-10 top-0 bottom-0 w-0.5 bg-teal-400 shadow-[0_0_8px_#2dd4bf] z-10"></div>
              <div class="absolute right-11 top-1 text-[9px] text-teal-300 font-bold">START</div>
              <div id="slitComparisonLanes"></div>
            </div>
          </div>
        </section>

        <!-- 右カラム (6 cols): ④結果×予想 答え合わせ総合判定 ＋ ⑤シミュレーター設定フィードバック処方箋 ＋ ⑥X/note振り返り投稿生成 ＋ ⑦収支・研究履歴ログ -->
        <section class="lg:col-span-6 space-y-3">
          <!-- ④ 答え合わせ総合ジャッジ＆5段階敗因/勝因解剖 -->
          <div class="bg-slate-900 border-2 border-teal-500/40 rounded-xl p-3 space-y-2.5">
            <div class="flex flex-wrap items-center justify-between gap-2 border-b border-slate-800 pb-2">
              <div class="flex items-center gap-2">
                <span id="hitOrMissBadge" class="px-3 py-1 rounded font-black text-sm">解析中</span>
                <div>
                  <div id="resultSummaryTitle" class="text-xs font-bold text-white"></div>
                  <div id="roiSummaryText" class="text-[11px] font-mono text-amber-300"></div>
                </div>
              </div>
              <button onclick="saveCurrentReviewToLog()" class="bg-teal-500 hover:bg-teal-400 text-slate-950 font-black text-xs px-3 py-1.5 rounded shadow">
                💾 このレースを研究履歴に保存
              </button>
            </div>

            <!-- 5段階解剖レポート -->
            <div id="retrospectiveDetailBox" class="text-xs leading-relaxed text-slate-200 bg-slate-950/90 border border-slate-800 rounded-lg p-3 space-y-2.5"></div>
          </div>

          <!-- ⑤ 予想シミュレーター（PHASE 2 PRO）への改善フィードバック処方箋 -->
          <div class="bg-slate-900 border border-amber-500/40 rounded-xl p-3 space-y-2">
            <div class="flex items-center justify-between">
              <h2 class="text-xs font-bold text-amber-300">🛠️ ⑤ 次レースに向けた「予想シミュレーター」設定調整処方箋</h2>
              <a href="https://bdkzgfy4igpjbzjachuzwu.streamlit.app/" target="_blank" rel="noopener" class="text-[10px] bg-sky-500 hover:bg-sky-400 text-slate-950 font-black px-2 py-0.5 rounded">🚤 予想シミュレーターを開く ↗</a>
            </div>
            <div id="simulatorPrescriptionBox" class="text-xs leading-relaxed text-slate-200 bg-slate-950/80 border border-slate-800 rounded-lg p-2.5 space-y-1.5"></div>
          </div>

          <!-- ⑥ X (@Boatrace__daisu) & note 振り返り・的中報告／検証レポート出力 -->
          <div class="bg-slate-900 border-2 border-sky-500/40 rounded-xl p-3 space-y-2">
            <div class="flex flex-wrap items-center justify-between gap-2">
              <div>
                <h2 class="text-xs font-bold text-sky-300">📝 ⑥ X (旧Twitter) ＆ note用「レース後振り返り・的中/検証レポート」自動生成</h2>
                <span class="text-[10px] text-slate-400">的中時は「展開読みの的中報告」、不的中時はフォロワーの信頼を高める「1M原因検証ログ」を出力</span>
              </div>
              <div class="flex items-center gap-1.5 text-xs">
                <select id="postReportMode" onchange="runReviewAnalysis()" class="font-bold text-sky-200">
                  <option value="auto" selected>🤖 的中/不的中に応じて自動切替</option>
                  <option value="x_hit">🎉 X用：的中＆展開完全一致報告</option>
                  <option value="x_verify">🔬 X用：1Mスリット＆展開検証ログ</option>
                  <option value="note_retro">📓 note追記・振り返り記事用(長文)</option>
                </select>
                <button onclick="copyRetroReport()" class="bg-sky-500 hover:bg-sky-400 text-slate-950 font-black px-2.5 py-1 rounded text-[11px] shadow">
                  レポートをコピー
                </button>
              </div>
            </div>
            <div id="copyRetroToast" class="hidden text-[11px] text-emerald-300 bg-emerald-950/70 border border-emerald-700/50 rounded px-2 py-1">
              振り返りレポートをクリップボードにコピーしました！
            </div>
            <textarea id="retroReportTextarea" rows="13" readonly class="w-full bg-slate-950 border border-slate-800 rounded-lg p-2.5 text-[11px] font-mono text-slate-200 leading-relaxed focus:outline-none"></textarea>
          </div>

          <!-- ⑦ 本日の研究・収支履歴ログ（累計的中率・回収率・傾向分析） -->
          <div class="bg-slate-900 border border-slate-800 rounded-xl p-3 space-y-2">
            <div class="flex flex-wrap items-center justify-between gap-2 border-b border-slate-800 pb-1.5">
              <div>
                <h2 class="text-xs font-bold text-emerald-400">📈 ⑦ 累計レース振り返り履歴 ＆ 収支・弱点傾向サマリー</h2>
                <span id="logStatsSummary" class="text-[11px] font-mono text-slate-300">保存履歴: 0件</span>
              </div>
              <div class="flex items-center gap-1.5">
                <button onclick="exportLearnedParamsToSimulator()" class="text-[11px] bg-amber-400 hover:bg-amber-300 text-slate-950 font-black px-2.5 py-1 rounded shadow">
                  🧠 蓄積データから学習パラメータを生成・コピー
                </button>
                <button onclick="clearReviewLogs()" class="text-[11px] bg-slate-800 hover:bg-slate-700 text-slate-400 px-2 py-0.5 rounded">履歴クリア</button>
              </div>
            </div>
            <div id="learnedFeedbackBanner" class="bg-indigo-950/70 border border-indigo-500/40 rounded-lg p-2 text-[11px] text-indigo-200 space-y-1">
              <div class="font-bold text-amber-300">🧠 蓄積データ自動学習ステータス（シミュレーター連携）</div>
              <div id="learnedParamsPreview">レース履歴を保存すると、決まり手傾向・STズレ・3着抜けパターンを統計処理し、予想シミュレーター用の最適パラメータを自動算出します。</div>
            </div>
            <div id="reviewLogsContainer" class="space-y-1.5 max-h-[220px] overflow-y-auto text-xs"></div>
          </div>
        </section>
      </div>
    </main>

    <script>
      let reviewBoats = {};
      let reviewLogs = [];

      const VENUE_CODE_TO_NAME = {
        "01": "桐生", "02": "戸田", "03": "江戸川", "04": "平和島", "05": "多摩川", "06": "浜名湖",
        "07": "蒲郡", "08": "常滑", "09": "津", "10": "三国", "11": "びわこ", "12": "住之江",
        "13": "尼崎", "14": "鳴門", "15": "丸亀", "16": "児島", "17": "宮島", "18": "徳山",
        "19": "下関", "20": "若松", "21": "芦屋", "22": "福岡", "23": "唐津", "24": "大村"
      };

      const KIMARITE_LABELS = {
        nige: "逃げ",
        sashi: "差し",
        makuri: "まくり",
        makurisashi: "まくり差し",
        nuki: "抜き",
        megumare: "恵まれ"
      };

      function loadSampleCase(mode) {
        if (mode === "makuri_hit") {
          document.getElementById("revVenue").value = "平和島";
          document.getElementById("revRaceNo").value = "12";
          document.getElementById("revGrade").value = "G1";
          document.getElementById("fin1").value = "4";
          document.getElementById("fin2").value = "5";
          document.getElementById("fin3").value = "1";
          document.getElementById("actualKimarite").value = "makuri";
          document.getElementById("payoutYen").value = "4820";
          document.getElementById("payoutPop").value = "18";
          document.getElementById("payout2tYen").value = "1450";
          document.getElementById("actualWindDir").value = "向かい風";
          document.getElementById("actualWindSpeed").value = "4";
          document.getElementById("actualKado").value = "4";
          document.getElementById("preExpectedScenario").value = "two_pattern";
          document.getElementById("totalInvestYen").value = "4000";
          document.getElementById("hitTicketYen").value = "500";
          document.getElementById("preBetsInput").value = "1-2-4, 1-4-2, 4-5-1, 4-1-5, 4-5-2, 3-4-5";

          document.getElementById("firstMarkPattern").value = "center_makuri_atk";
          document.getElementById("dochuOvertakeType").value = "overtake_3rd";
          document.getElementById("dochuReason").value = "turn_power";
          reviewBoats = {
            1: { id: 1, course: 1, name: "白井 英治", exTime: 6.75, preSt: 0.11, actualSt: 0.14, m1Action: "被弾・残し", m1Rank: 4, rank: 3 },
            2: { id: 2, course: 2, name: "瓜生 正義", exTime: 6.79, preSt: 0.14, actualSt: 0.16, m1Action: "引き波被弾", m1Rank: 5, rank: 4 },
            3: { id: 3, course: 3, name: "澤田 尚也", exTime: 6.77, preSt: 0.14, actualSt: 0.21, m1Action: "凹み・壁崩壊", m1Rank: 6, rank: 5 },
            4: { id: 4, course: 4, name: "大峯 豊", exTime: 6.71, preSt: 0.12, actualSt: 0.08, m1Action: "まくり敢行", m1Rank: 1, rank: 1 },
            5: { id: 5, course: 5, name: "篠崎 仁志", exTime: 6.75, preSt: 0.13, actualSt: 0.11, m1Action: "まくり差し連動", m1Rank: 2, rank: 2 },
            6: { id: 6, course: 6, name: "吉田 裕平", exTime: 6.82, preSt: 0.15, actualSt: 0.15, m1Action: "展開待ち最内", m1Rank: 3, rank: 6 }
          };
        } else if (mode === "sashi_miss") {
          document.getElementById("revVenue").value = "福岡";
          document.getElementById("revRaceNo").value = "11";
          document.getElementById("revGrade").value = "G1";
          document.getElementById("fin1").value = "2";
          document.getElementById("fin2").value = "1";
          document.getElementById("fin3").value = "5";
          document.getElementById("actualKimarite").value = "sashi";
          document.getElementById("payoutYen").value = "3640";
          document.getElementById("payoutPop").value = "14";
          document.getElementById("payout2tYen").value = "920";
          document.getElementById("actualWindDir").value = "追い風";
          document.getElementById("actualWindSpeed").value = "5";
          document.getElementById("actualKado").value = "4";
          document.getElementById("preExpectedScenario").value = "nige";
          document.getElementById("totalInvestYen").value = "3600";
          document.getElementById("hitTicketYen").value = "400";
          document.getElementById("preBetsInput").value = "1-2-3, 1-2-4, 1-3-2, 1-3-4, 1-4-2, 1-4-3";

          document.getElementById("firstMarkPattern").value = "c2_sashi_atk";
          document.getElementById("dochuOvertakeType").value = "none";
          document.getElementById("dochuReason").value = "none";
          reviewBoats = {
            1: { id: 1, course: 1, name: "峰 竜太", exTime: 6.78, preSt: 0.12, actualSt: 0.13, m1Action: "先マイ膨らみ", m1Rank: 2, rank: 2 },
            2: { id: 2, course: 2, name: "毒島 誠", exTime: 6.74, preSt: 0.13, actualSt: 0.11, m1Action: "1M差し抜け", m1Rank: 1, rank: 1 },
            3: { id: 3, course: 3, name: "馬場 貴也", exTime: 6.76, preSt: 0.14, actualSt: 0.14, m1Action: "外マイ流れ", m1Rank: 4, rank: 4 },
            4: { id: 4, course: 4, name: "桐生 順平", exTime: 6.79, preSt: 0.15, actualSt: 0.16, m1Action: "差し届かず", m1Rank: 5, rank: 5 },
            5: { id: 5, course: 5, name: "茅原 悠紀", exTime: 6.75, preSt: 0.14, actualSt: 0.13, m1Action: "展開待ち最内", m1Rank: 3, rank: 3 },
            6: { id: 6, course: 6, name: "池田 浩二", exTime: 6.81, preSt: 0.16, actualSt: 0.17, m1Action: "展開待ち", m1Rank: 6, rank: 6 }
          };
        } else {
          document.getElementById("revVenue").value = "大村";
          document.getElementById("revRaceNo").value = "12";
          document.getElementById("revGrade").value = "SG";
          document.getElementById("fin1").value = "1";
          document.getElementById("fin2").value = "2";
          document.getElementById("fin3").value = "4";
          document.getElementById("actualKimarite").value = "nige";
          document.getElementById("payoutYen").value = "980";
          document.getElementById("payoutPop").value = "2";
          document.getElementById("payout2tYen").value = "380";
          document.getElementById("actualWindDir").value = "無風";
          document.getElementById("actualWindSpeed").value = "1";
          document.getElementById("actualKado").value = "4";
          document.getElementById("preExpectedScenario").value = "nige";
          document.getElementById("totalInvestYen").value = "3000";
          document.getElementById("hitTicketYen").value = "1000";
          document.getElementById("preBetsInput").value = "1-2-4, 1-4-2, 1-2-3, 1-3-2";

          document.getElementById("firstMarkPattern").value = "clean_in";
          document.getElementById("dochuOvertakeType").value = "none";
          document.getElementById("dochuReason").value = "none";
          reviewBoats = {
            1: { id: 1, course: 1, name: "白井 英治", exTime: 6.72, preSt: 0.11, actualSt: 0.09, m1Action: "先マイ逃走", m1Rank: 1, rank: 1 },
            2: { id: 2, course: 2, name: "瓜生 正義", exTime: 6.76, preSt: 0.13, actualSt: 0.12, m1Action: "差し追走", m1Rank: 2, rank: 2 },
            3: { id: 3, course: 3, name: "澤田 尚也", exTime: 6.79, preSt: 0.14, actualSt: 0.15, m1Action: "外マイ", m1Rank: 4, rank: 4 },
            4: { id: 4, course: 4, name: "大峯 豊", exTime: 6.74, preSt: 0.13, actualSt: 0.12, m1Action: "二番差し", m1Rank: 3, rank: 3 },
            5: { id: 5, course: 5, name: "篠崎 仁志", exTime: 6.80, preSt: 0.15, actualSt: 0.15, m1Action: "展開待ち", m1Rank: 5, rank: 5 },
            6: { id: 6, course: 6, name: "吉田 裕平", exTime: 6.82, preSt: 0.16, actualSt: 0.17, m1Action: "最内差し", m1Rank: 6, rank: 6 }
          };
        }

        renderBoatStTable();
        runReviewAnalysis();
      }

      async function fetchViaCorsProxy(targetUrl) {
        const proxies = [
          (u) => `https://api.allorigins.win/raw?url=${encodeURIComponent(u)}`,
          (u) => `https://api.codetabs.com/v1/proxy?quest=${encodeURIComponent(u)}`
        ];
        for (const makeUrl of proxies) {
          try {
            const res = await fetch(makeUrl(targetUrl));
            if (res.ok) {
              const txt = await res.text();
              if (txt && txt.length > 500) return txt;
            }
          } catch (e) {}
        }
        return null;
      }

      async function autoFetchOfficialResultFromWeb() {
        const dateVal = (document.getElementById("fetchDateInput").value || "").replace(/-/g, "");
        const jcd = document.getElementById("fetchVenueCode").value || "04";
        const rno = document.getElementById("fetchRno").value || "12";
        const msgEl = document.getElementById("autoFetchMsg");
        const vName = VENUE_CODE_TO_NAME[jcd] || "平和島";

        msgEl.textContent = `⏳ BOAT RACE公式から ${dateVal} ${vName} ${rno}R の確定結果・配当を取得中...`;
        document.getElementById("revVenue").value = vName;
        document.getElementById("revRaceNo").value = String(rno);

        const resUrl = `https://www.boatrace.jp/owpc/pc/race/raceresult?rno=${rno}&jcd=${jcd}&hd=${dateVal}`;
        const befUrl = `https://www.boatrace.jp/owpc/pc/race/beforeinfo?rno=${rno}&jcd=${jcd}&hd=${dateVal}`;

        const [resHtml, befHtml] = await Promise.all([
          fetchViaCorsProxy(resUrl),
          fetchViaCorsProxy(befUrl)
        ]);

        if (!resHtml) {
          msgEl.textContent = `⚠️ ブラウザの通信制限または未開催のため取得できませんでした。「📥 結果テキスト貼付」またはStreamlit上部バーをご利用ください。`;
          return;
        }

        const parser = new DOMParser();
        if (befHtml) {
          const befDoc = parser.parseFromString(befHtml, "text/html");
          befDoc.querySelectorAll("div.table1 table tbody.is-fs12").forEach(tb => {
            const firstRow = tb.querySelector("tr");
            if (!firstRow) return;
            const tds = firstRow.querySelectorAll("td");
            if (tds.length >= 5) {
              const bNo = parseInt(tds[0].textContent.trim(), 10);
              const nm = tds[2].textContent.replace(/\s+/g, " ").trim();
              const exM = tds[4].textContent.match(/[67]\.\d{2}/);
              if (reviewBoats[bNo]) {
                if (nm) reviewBoats[bNo].name = nm;
                if (exM) reviewBoats[bNo].exTime = parseFloat(exM[0]);
              }
            }
          });
          befDoc.querySelectorAll("div.table1_boatImage1").forEach(box => {
            const nEl = box.querySelector(".table1_boatImage1Number");
            const tEl = box.querySelector(".table1_boatImage1Time");
            if (nEl && tEl) {
              const bNo = parseInt(nEl.textContent.trim(), 10);
              const stM = tEl.textContent.replace(/[FL]/g, "").trim().match(/\.?\d{2}/);
              if (reviewBoats[bNo] && stM) {
                const raw = stM[0];
                reviewBoats[bNo].preSt = parseFloat(raw.startsWith(".") ? "0" + raw : raw);
              }
            }
          });
        }

        const resDoc = parser.parseFromString(resHtml, "text/html");
        const fullText = resDoc.body.textContent.replace(/\s+/g, " ");
        if (fullText.includes("データがありません")) {
          msgEl.textContent = `⚠️ ${dateVal} ${vName} ${rno}R は結果未確定または非開催です。`;
          return;
        }

        // 着順・選手名解析
        const finishOrders = [];
        resDoc.querySelectorAll("div.table1 table tbody tr").forEach(tr => {
          const tds = Array.from(tr.querySelectorAll("td")).map(td => td.textContent.replace(/\s+/g, " ").trim());
          if (tds.length >= 4 && /^[1-6]$/.test(tds[0]) && /^[1-6]$/.test(tds[1])) {
            const rk = parseInt(tds[0], 10);
            const bNo = parseInt(tds[1], 10);
            finishOrders.push({ rk, bNo });
            if (reviewBoats[bNo]) {
              reviewBoats[bNo].rank = rk;
              const nmParts = tds[2].split(/\s+/).filter(x => !/^\d{4}$/.test(x));
              if (nmParts.length > 0) reviewBoats[bNo].name = nmParts.join(" ");
            }
          }
        });
        finishOrders.sort((a, b) => a.rk - b.rk);
        if (finishOrders.length >= 3) {
          document.getElementById("fin1").value = String(finishOrders[0].bNo);
          document.getElementById("fin2").value = String(finishOrders[1].bNo);
          document.getElementById("fin3").value = String(finishOrders[2].bNo);
        }

        // 本番スリットST解析
        resDoc.querySelectorAll("div.table1_boatImage1").forEach((box, idx) => {
          const nEl = box.querySelector(".table1_boatImage1Number");
          const tEl = box.querySelector(".table1_boatImage1Time");
          if (nEl) {
            const bNo = parseInt(nEl.textContent.trim(), 10);
            if (reviewBoats[bNo]) {
              reviewBoats[bNo].course = idx + 1;
              if (tEl) {
                const stM = tEl.textContent.match(/0?\.\d{2}/);
                if (stM) {
                  const s = stM[0];
                  reviewBoats[bNo].actualSt = parseFloat(s.startsWith(".") ? "0" + s : s);
                }
              }
            }
          }
        });

        // 決まり手解析
        if (fullText.includes("まくり差し")) document.getElementById("actualKimarite").value = "makurisashi";
        else if (fullText.includes("まくり")) document.getElementById("actualKimarite").value = "makuri";
        else if (fullText.includes("差し")) document.getElementById("actualKimarite").value = "sashi";
        else if (fullText.includes("抜き")) document.getElementById("actualKimarite").value = "nuki";
        else if (fullText.includes("恵まれ")) document.getElementById("actualKimarite").value = "megumare";
        else document.getElementById("actualKimarite").value = "nige";

        // 払戻金（3連単・2連単・人気）の確実な抽出
        const payoutSpans = Array.from(resDoc.querySelectorAll("span.is-payout1"))
          .map(el => parseInt(el.textContent.replace(/[^\d]/g, ""), 10))
          .filter(n => Number.isFinite(n) && n >= 100);
        if (payoutSpans.length >= 1) {
          document.getElementById("payoutYen").value = payoutSpans[0];
        } else {
          const m3 = fullText.match(/3連単[\s\S]{1,80}?¥\s*([\d,]+)/);
          if (m3) document.getElementById("payoutYen").value = parseInt(m3[1].replace(/,/g, ""), 10);
        }
        const m2 = fullText.match(/2連単[\s\S]{1,80}?¥\s*([\d,]+)/);
        if (m2) document.getElementById("payout2tYen").value = parseInt(m2[1].replace(/,/g, ""), 10);

        const popM = fullText.match(/3連単[\s\S]{1,80}?¥\s*[\d,]+\s+(\d{1,3})\b/);
        if (popM) document.getElementById("payoutPop").value = parseInt(popM[1], 10);

        const windM = fullText.match(/風速\s*(\d+)\s*m/);
        if (windM) document.getElementById("actualWindSpeed").value = parseInt(windM[1], 10);

        infer1MProcessFromNumbers(false);
        renderBoatStTable();
        runReviewAnalysis();
        msgEl.textContent = `✅ 公式結果＆配当を自動反映しました！（確定: ${document.getElementById("fin1").value}-${document.getElementById("fin2").value}-${document.getElementById("fin3").value} ／ 3連単 ${Number(document.getElementById("payoutYen").value).toLocaleString()}円）`;
      }


      function infer1MProcessFromNumbers(triggerRun = true) {
        const f1 = Number(document.getElementById("fin1").value);
        const f2 = Number(document.getElementById("fin2").value);
        const f3 = Number(document.getElementById("fin3").value);
        const kim = document.getElementById("actualKimarite").value;
        const arr = Object.values(reviewBoats);
        if (arr.length < 6) return;

        // 1. 本番STと着順の乖離から「仕掛け不発（やり合い）」「壁崩壊」「引き波被弾」を数値逆算
        const c1 = arr.find(x => x.course === 1) || reviewBoats[1];
        const c2 = arr.find(x => x.course === 2) || reviewBoats[2];
        const c3 = arr.find(x => x.course === 3) || reviewBoats[3];
        const c4 = arr.find(x => x.course === 4) || reviewBoats[4];
        const wBoat = reviewBoats[f1];

        // センター勢がST踏み込んだのに4〜6着に沈み、差し・まくり差し決着になった場合＝「1Mやり合い（抵抗）発生」
        const centerChargedAndSank = [c3, c4].some(x => x && x.actualSt <= c1.actualSt - 0.02 && x.rank >= 4 && c1.rank >= 3);

        if (kim === "nige") {
          document.getElementById("firstMarkPattern").value = "clean_in";
        } else if (kim === "sashi" && wBoat?.course === 2) {
          document.getElementById("firstMarkPattern").value = c1.rank === 2 ? "in_flow" : "c2_sashi_atk";
        } else if (kim === "makuri" && wBoat?.course === 2) {
          document.getElementById("firstMarkPattern").value = "c2_makuri_atk";
        } else if (centerChargedAndSank) {
          document.getElementById("firstMarkPattern").value = "clash_wait";
        } else if (kim === "makuri") {
          document.getElementById("firstMarkPattern").value = "center_makuri_atk";
        } else if (kim === "makurisashi") {
          document.getElementById("firstMarkPattern").value = "center_ms_atk";
        } else if (kim === "nuki") {
          document.getElementById("firstMarkPattern").value = "in_flow";
        }

        // 2. 道中逆転の自動推論（決まり手が「抜き」または展示時計上位艇がスジ外から2・3着に食い込んだ場合）
        if (kim === "nuki") {
          document.getElementById("dochuOvertakeType").value = "overtake_1st";
          document.getElementById("dochuReason").value = "turn_power";
        } else {
          const b3Obj = reviewBoats[f3];
          const exSorted = [...arr].sort((a, b) => a.exTime - b.exTime);
          if (b3Obj && (b3Obj.exTime <= exSorted[1].exTime || b3Obj.course === 1 && kim === "makuri")) {
            document.getElementById("dochuOvertakeType").value = "overtake_3rd";
            document.getElementById("dochuReason").value = "turn_power";
          } else {
            document.getElementById("dochuOvertakeType").value = "none";
            document.getElementById("dochuReason").value = "none";
          }
        }

        // 3. 6艇それぞれの1Mアクションと1M出口順位をST・コース・確定着順から自動推定
        arr.forEach(d => {
          const prevCourseBoat = arr.find(x => x.course === d.course - 1);
          const isDoka = d.actualSt >= 0.19 || (prevCourseBoat && d.actualSt - prevCourseBoat.actualSt >= 0.04);

          if (d.id === f1) {
            if (kim === "nige") d.m1Action = "先マイ逃走";
            else if (kim === "makuri") d.m1Action = "まくり敢行";
            else if (kim === "makurisashi") d.m1Action = "まくり差し連動";
            else if (kim === "sashi") d.m1Action = "1M差し抜け";
            else d.m1Action = "差し追走";
            d.m1Rank = kim === "nuki" ? 2 : 1;
          } else if (isDoka && d.rank >= 4) {
            d.m1Action = "凹み・壁崩壊";
            d.m1Rank = d.rank;
          } else if (d.course >= 3 && d.actualSt <= c1.actualSt - 0.02 && d.rank >= 4) {
            d.m1Action = "まくり不発(抵抗被弾)";
            d.m1Rank = 4;
          } else if (d.course === 1 && d.rank >= 2) {
            d.m1Action = kim === "makuri" ? "引き波被弾" : "先マイ膨らみ";
            d.m1Rank = kim === "nuki" ? 1 : (kim === "makuri" && d.rank === 3 ? 4 : d.rank);
          } else if (d.rank <= 3) {
            if (d.course >= 5 || (kim === "makuri" && d.course > wBoat.course + 1)) {
              d.m1Action = "展開待ち最内";
            } else if (kim === "makuri" && d.course === wBoat.course + 1) {
              d.m1Action = "まくり差し連動";
            } else if (d.course === 2) {
              d.m1Action = "差し追走";
            } else {
              d.m1Action = "二番差し";
            }
            d.m1Rank = d.rank;
          } else {
            d.m1Action = d.course < (wBoat?.course || 1) ? "引き波被弾" : "外マイ";
            d.m1Rank = d.rank;
          }
        });

        renderBoatStTable();
        if (triggerRun) runReviewAnalysis();
      }

      function renderBoatStTable() {
        const tbody = document.getElementById("boatStInputTable");
        tbody.innerHTML = "";
        for (let b = 1; b <= 6; b++) {
          const d = reviewBoats[b];
          const diff = d.actualSt - d.preSt;
          const diffStr = (diff >= 0 ? "+" : "") + diff.toFixed(2);
          const diffCls = diff <= -0.02 ? "text-amber-300 font-bold" : diff >= 0.03 ? "text-rose-400 font-bold" : "text-slate-400";
          const diffLabel = diff <= -0.02 ? "🚀踏み込み" : diff >= 0.03 ? "⚠️ドカ遅れ" : "通り";

          tbody.innerHTML += `
          <tr>
            <td class="py-1 font-bold text-slate-300">${d.course}C</td>
            <td class="py-1 flex items-center gap-1.5">
              <span class="boat-${b} w-5 h-5 rounded text-[11px] font-black flex items-center justify-center">${b}</span>
              <input type="text" value="${d.name}" onchange="updateRevBoat(${b},'name',this.value)" class="w-24 bg-slate-950 px-1 py-0.5 text-xs font-bold" />
            </td>
            <td class="py-1 text-center"><input type="number" step="0.01" value="${d.exTime.toFixed(2)}" onchange="updateRevBoat(${b},'exTime',parseFloat(this.value))" class="w-14 text-center font-mono" /></td>
            <td class="py-1 text-center"><input type="number" step="0.01" value="${d.preSt.toFixed(2)}" onchange="updateRevBoat(${b},'preSt',parseFloat(this.value))" class="w-14 text-center font-mono text-slate-300" /></td>
            <td class="py-1 text-center"><input type="number" step="0.01" value="${d.actualSt.toFixed(2)}" onchange="updateRevBoat(${b},'actualSt',parseFloat(this.value))" class="w-14 text-center font-mono text-teal-300 font-bold" /></td>
            <td class="py-1 text-center font-mono text-[10px] ${diffCls}">${diffStr} (${diffLabel})</td>
            <td class="py-1 text-center">
              <select onchange="updateRevBoat(${b},'m1Action',this.value)" class="text-[10px] py-0.5 px-1 text-amber-200">
                ${["先マイ逃走","先マイ膨らみ","まくり敢行","まくり不発(抵抗被弾)","まくり差し連動","1M差し抜け","差し追走","二番差し","外マイ","展開待ち最内","引き波被弾","凹み・壁崩壊"].map(act => `<option value="${act}" ${(d.m1Action || "差し追走") === act ? "selected" : ""}>${act}</option>`).join("")}
              </select>
            </td>
            <td class="py-1 text-center"><input type="number" min="1" max="6" value="${d.m1Rank ?? d.rank}" onchange="updateRevBoat(${b},'m1Rank',parseInt(this.value,10))" class="w-10 text-center font-bold text-sky-300" title="1周1M出口時点の順位" /></td>
            <td class="py-1 text-center"><input type="number" min="1" max="6" value="${d.rank}" onchange="updateRevBoat(${b},'rank',parseInt(this.value,10))" class="w-10 text-center font-bold text-teal-300" title="最終確定着順" /></td>
          </tr>`;
        }
      }

      function updateRevBoat(b, key, val) {
        reviewBoats[b][key] = val;
        renderBoatStTable();
        runReviewAnalysis();
      }

      function parseUserBets(rawStr) {
        if (!rawStr) return [];
        const tokens = rawStr.replace(/、|，|\n|\r|\t/g, ",").split(/[,\s]+/).map(s => s.trim()).filter(Boolean);
        const comboSet = new Set();
        const expandDigits = (part) => {
          if (part === "全" || part === "9" || part.toUpperCase() === "ALL") return [1, 2, 3, 4, 5, 6];
          return [...part.matchAll(/[1-6]/g)].map(m => Number(m[0]));
        };
        tokens.forEach(tok => {
          const parts = tok.split(/[-=→>]/);
          if (parts.length === 3) {
            const p1 = expandDigits(parts[0]), p2 = expandDigits(parts[1]), p3 = expandDigits(parts[2]);
            p1.forEach(a => p2.forEach(b => p3.forEach(c => {
              if (a !== b && b !== c && a !== c) comboSet.add(`${a}-${b}-${c}`);
            })));
          } else if (/^[1-6]{3}$/.test(tok)) {
            const a = Number(tok[0]), b = Number(tok[1]), c = Number(tok[2]);
            if (a !== b && b !== c && a !== c) comboSet.add(`${a}-${b}-${c}`);
          }
        });
        return Array.from(comboSet);
      }

      function renderSlitComparison() {
        const container = document.getElementById("slitComparisonLanes");
        const kado = Number(document.getElementById("actualKado").value || 4);
        container.innerHTML = "";
        for (let b = 1; b <= 6; b++) {
          const d = reviewBoats[b];
          const preLeft = Math.max(12, Math.min(72, 42 + (0.16 - d.preSt) * 280));
          const actLeft = Math.max(12, Math.min(75, 42 + (0.16 - d.actualSt) * 280));
          const diff = d.actualSt - d.preSt;
          const badge = diff <= -0.02 ? "🚀本番踏み込み" : diff >= 0.03 ? "⚠️本番凹み" : "";
          container.innerHTML += `
          <div class="slit-lane ${d.course === kado ? "kado-line" : ""}">
            <span class="text-[10px] text-slate-400 w-12 pl-1 font-mono">${d.course}C</span>
            <div style="left:${preLeft}%;" class="absolute flex items-center opacity-35 pointer-events-none">
              <span class="boat-${b} px-1.5 py-0.5 rounded text-[10px] font-bold">${b}</span>
              <span class="text-[9px] text-slate-300 ml-1">展.${Math.round(d.preSt * 100).toString().padStart(2, "0")}</span>
            </div>
            <div style="left:${actLeft}%;" class="absolute flex items-center gap-1.5 z-10">
              <span class="boat-${b} px-2 py-0.5 rounded text-xs font-black shadow">${b}</span>
              <span class="text-[11px] font-bold text-white whitespace-nowrap">${d.name.replace(/\s+/g, "")} <span class="font-mono text-teal-300">(実.${Math.round(d.actualSt * 100).toString().padStart(2, "0")})</span> <span class="text-[10px] text-amber-300">${badge}</span></span>
            </div>
          </div>`;
        }
      }

      function runReviewAnalysis() {
        renderSlitComparison();

        const venue = document.getElementById("revVenue").value;
        const raceNo = document.getElementById("revRaceNo").value;
        const grade = document.getElementById("revGrade").value;
        const f1 = Number(document.getElementById("fin1").value);
        const f2 = Number(document.getElementById("fin2").value);
        const f3 = Number(document.getElementById("fin3").value);
        const actualCombo = `${f1}-${f2}-${f3}`;
        const kimarite = document.getElementById("actualKimarite").value;
        const kimariteName = KIMARITE_LABELS[kimarite] || "逃げ";
        const payout = Number(document.getElementById("payoutYen").value || 0);
        const payoutPop = Number(document.getElementById("payoutPop")?.value || 1);
        const payout2t = Number(document.getElementById("payout2tYen")?.value || 0);
        const windDir = document.getElementById("actualWindDir").value;
        const windSpeed = Number(document.getElementById("actualWindSpeed").value || 0);
        const kado = Number(document.getElementById("actualKado").value || 4);

        const popBadge = document.getElementById("payoutPopularBadge");
        if (popBadge) {
          popBadge.textContent = `3連単 ${payout.toLocaleString()}円 (${payoutPop}番人気) ／ 2連単 ${payout2t.toLocaleString()}円`;
        }

        const preScenario = document.getElementById("preExpectedScenario").value;
        const invest = Number(document.getElementById("totalInvestYen").value || 3000);
        const hitUnitYen = Number(document.getElementById("hitTicketYen").value || 500);
        const userBets = parseUserBets(document.getElementById("preBetsInput").value);

        const isHit = userBets.includes(actualCombo);
        const returnYen = isHit ? Math.round((payout / 100) * hitUnitYen) : 0;
        const profitYen = returnYen - invest;
        const roiPct = invest > 0 ? Math.round((returnYen / invest) * 100) : 0;

        const has1stHit = userBets.some(c => Number(c.split("-")[0]) === f1);
        const has1st2ndHit = userBets.some(c => {
          const [a, b] = c.split("-").map(Number);
          return a === f1 && b === f2;
        });
        const hasUra = userBets.includes(`${f2}-${f1}-${f3}`) || userBets.includes(`${f1}-${f3}-${f2}`);

        const hitBadge = document.getElementById("hitOrMissBadge");
        if (isHit) {
          hitBadge.className = "bg-amber-400 text-slate-950 px-3 py-1 rounded font-black text-sm shadow";
          hitBadge.textContent = "🎯 的中！ (展開一致)";
        } else if (has1st2ndHit) {
          hitBadge.className = "bg-purple-500 text-white px-3 py-1 rounded font-black text-sm shadow";
          hitBadge.textContent = "惜敗：1・2着的中 (3着抜け)";
        } else if (hasUra) {
          hitBadge.className = "bg-rose-500 text-white px-3 py-1 rounded font-black text-sm shadow";
          hitBadge.textContent = "惜敗：裏目決着 (スジ合致)";
        } else if (has1stHit) {
          hitBadge.className = "bg-sky-600 text-white px-3 py-1 rounded font-black text-sm shadow";
          hitBadge.textContent = "惜敗：1着的中 (2着スジ抜け)";
        } else {
          hitBadge.className = "bg-slate-800 text-rose-300 border border-rose-500/40 px-3 py-1 rounded font-black text-sm";
          hitBadge.textContent = "不的中 (1M展開逆行)";
        }

        const b1 = reviewBoats[f1] || { name: `${f1}号艇`, actualSt: 0.13, preSt: 0.13, exTime: 6.75 };
        const b2 = reviewBoats[f2] || { name: `${f2}号艇`, actualSt: 0.14, preSt: 0.14, exTime: 6.77 };
        const b3 = reviewBoats[f3] || { name: `${f3}号艇`, actualSt: 0.15, preSt: 0.15, exTime: 6.79 };

        document.getElementById("resultSummaryTitle").textContent =
          `${venue} ${raceNo}R (${grade}) 確定結果：${actualCombo} （${b1.name} → ${b2.name} → ${b3.name} ／ 決まり手：${kimariteName}）`;
        document.getElementById("roiSummaryText").textContent =
          `3連単配当: ${payout.toLocaleString()}円(${payoutPop}人気) ｜ 投資: ${invest.toLocaleString()}円 → 回収: ${returnYen.toLocaleString()}円 (収支 ${profitYen >= 0 ? "+" : ""}${profitYen.toLocaleString()}円 / 回収率 ${roiPct}%)`;

        const boatsArr = Object.values(reviewBoats);
        const dokaBoats = boatsArr.filter(x => x.actualSt - x.preSt >= 0.03 || x.actualSt >= 0.18);
        const topStBoat = [...boatsArr].sort((a, b) => a.actualSt - b.actualSt)[0];

        const dokaText = dokaBoats.length > 0
          ? dokaBoats.map(x => `${x.course}コース${x.id}号艇(${x.name})が展示.${Math.round(x.preSt*100).toString().padStart(2,"0")}→本番.${Math.round(x.actualSt*100).toString().padStart(2,"0")}と遅れ`).join("、")
          : "大きなスタート遅れはなく、ほぼ展示通りのスリット隊形";

        let why2nd3rdText = "";
        if (kimarite === "makuri") {
          why2nd3rdText = `${f1}号艇（${b1.name}）が本番ST .${Math.round(b1.actualSt*100).toString().padStart(2,"0")}から豪快にまくったことで内枠勢が引き波に沈み、マーク外側から連動した<strong>${f2}号艇（${b2.name}）</strong>と、1マークのもつれ・引き波を最内「展開待ち」で突いた<strong>${f3}号艇（${b3.name}）</strong>が浮上する典型的な『まくり外連動スジ』で決着しました。`;
        } else if (kimarite === "sashi" || kimarite === "makurisashi") {
          why2nd3rdText = `1マークで先マイを図ったインに対し、<strong>${f1}号艇（${b1.name}）</strong>がブイ際を鋭く${kimariteName}突破。差された${f2}号艇（${b2.name}）が2着に踏みとどまり、3着には引き波を避けて展開待ちから差した<strong>${f3}号艇（${b3.name}）</strong>が食い込みました。`;
        } else if (kimarite === "nige") {
          why2nd3rdText = `1コース<strong>${f1}号艇（${b1.name}）</strong>が本番ST .${Math.round(b1.actualSt*100).toString().padStart(2,"0")}から完璧な先マイで押し切り。2着には順当に差し・外マイ追走した<strong>${f2}号艇（${b2.name}）</strong>、3着には道中連絡みした<strong>${f3}号艇（${b3.name}）</strong>が入りました。`;
        } else {
          why2nd3rdText = `1マークの攻防からバックストレッチ・2マークでの逆転（${kimariteName}）が発生し、出足・回り足に勝る<strong>${f1}号艇→${f2}号艇→${f3}号艇</strong>の順で決着しました。`;
        }

        let reflectionAdvice = "";
        if (isHit) {
          reflectionAdvice = `✅ <strong>【勝因の解剖】</strong> 事前のスジ読み（${actualCombo}）と本番の1マーク展開（${kimariteName}）が完全に一致しています。特に2着${f2}号艇・3着${f3}号艇の連動ルートを正確に網羅できていた点が最大の勝因です。`;
        } else if (has1st2ndHit) {
          reflectionAdvice = `🔍 <strong>【3着抜けの原因解剖】</strong> 1着${f1}号艇・2着${f2}号艇の本線ラインは完璧に読めていましたが、3着に入った<strong>${f3}号艇（${b3.name}）</strong>が抜けています。1マークで${kimariteName}が起きた際、外枠や展開待ちの艇（${f3}号艇）が最内を小回りして3着に浮上するパターンを「展開待ち連対率」でケアするのが次回の改善ポイントです。`;
        } else if (has1stHit) {
          reflectionAdvice = `🔍 <strong>【2着スジ抜けの原因解剖】</strong> 1着アタマ（${f1}号艇・${kimariteName}）の狙いは的中していましたが、2着に入った<strong>${f2}号艇（${b2.name}）</strong>へのスジ連動が抜けていました。${kimarite === "makuri" ? "まくり決着時は内枠ではなく『まくった艇の1つ外（" + f2 + "号艇）』を2着筆頭に置くスジ鉄則" : "差し決着時は『1コースの2着残り』を最優先するスジ鉄則"}を徹底すると取りこぼしがなくなります。`;
        } else {
          reflectionAdvice = `🔍 <strong>【展開逆行の原因解剖】</strong> 事前は「${preScenario === "nige" ? "イン逃げ本線" : "別展開"}」を想定していましたが、本番は<strong>${dokaText}</strong>したことでスリット隊形が一変し、<strong>${f1}号艇の「${kimariteName}」</strong>が決まりました。${windDir}${windSpeed}mの水面条件と壁役の信頼度を再点検する必要があります。`;
        }

        const m1Sorted = [...boatsArr].sort((a, b) => (a.m1Rank ?? a.rank) - (b.m1Rank ?? b.rank));
        const m1Combo = `${m1Sorted[0].id}-${m1Sorted[1].id}-${m1Sorted[2].id}`;
        const isM1Hit = userBets.includes(m1Combo);
        const firstMarkPat = document.getElementById("firstMarkPattern")?.value || "clean_in";
        const dochuType = document.getElementById("dochuOvertakeType")?.value || "none";
        const dochuReason = document.getElementById("dochuReason")?.value || "none";

        const dochuChangedBoats = boatsArr.filter(x => (x.m1Rank ?? x.rank) !== x.rank);
        const dochuSummaryText = (dochuType === "none" && m1Combo === actualCombo)
          ? `1周1マーク出口隊形 <strong>[${m1Combo}]</strong> のまま道中逆転なく確定（純粋な1Mスジ決着）。`
          : `1周1マーク出口時点では <strong>[${m1Combo}]</strong> でしたが、道中（1周2M以降）で <strong>[${actualCombo}]</strong> へ着順が入れ替わりました（${dochuChangedBoats.map(x => `${x.id}号艇:${x.m1Rank ?? x.rank}番手→${x.rank}着`).join(" / ")}）。${isM1Hit && !isHit ? "<span class=\"text-amber-300 font-bold\">★あなたの事前買い目は『1マーク出口時点では的中』していたため、1M展開読み自体は正解です！道中の機力（出足・回り足）差のみ補正します。</span>" : ""}`;

        document.getElementById("retrospectiveDetailBox").innerHTML = `
          <div class="space-y-1 border-b border-slate-800 pb-2">
            <div class="text-teal-300 font-bold">① スリット（展示ST vs 本番実ST）のズレ診断</div>
            <p>トップスタートは<strong>${topStBoat.course}コース${topStBoat.id}号艇（${topStBoat.name} / 実ST .${Math.round(topStBoat.actualSt*100).toString().padStart(2,"0")}）</strong>。全体としては「${dokaText}」というスリット結果でした。</p>
          </div>
          <div class="space-y-1 border-b border-slate-800 pb-2">
            <div class="text-amber-300 font-bold">② 1マーク実際の攻め方 ＆ 1M出口隊形 [${m1Combo}] の解剖</div>
            <p>各艇の1Mアクション：<strong>${boatsArr.map(x => `${x.course}C(${x.id}):${x.m1Action || "追走"}`).join(" ／ ")}</strong></p>
            <p>${why2nd3rdText}</p>
          </div>
          <div class="space-y-1 border-b border-slate-800 pb-2">
            <div class="text-sky-300 font-bold">③ 道中（1周2M〜3周）の逆転・着順変動の分離評価</div>
            <p>${dochuSummaryText}</p>
          </div>
          <div class="space-y-1">
            <div class="text-pink-300 font-bold">④ あなたの事前予想（${userBets.length}点）に対する答え合わせ結論</div>
            <p>${reflectionAdvice}</p>
          </div>
        `;

        let prescriptionHtml = "";
        if (kimarite === "makuri") {
          prescriptionHtml = `
            <p>🔧 <strong>1. 重み付けスライダー調整：</strong> 本日の${venue}水面（${windDir}${windSpeed}m）ではダッシュ・スリット攻めが強く決まっています。予想シミュレーターの<strong>「④ スリット＆戦法連動ボーナス比重」を 140%〜160%</strong> に引き上げてください。</p>
            <p>🔧 <strong>2. 手動1M攻め設定：</strong> カド受け（${kado - 1}コース）のSTが不安な番組では、カド（${kado}コース）に<strong>「🔥まくり」</strong>、その外隣に<strong>「⚡まくり差し」または「⏳展開待ち」</strong>を指定した【🟥パターンB（イン逃げ以外）】の比重を高めると高配当を仕留められます。</p>
          `;
        } else if (kimarite === "sashi" || kimarite === "makurisashi") {
          prescriptionHtml = `
            <p>🔧 <strong>1. コース別攻め成功率の重視：</strong> ターンマーク際の「差し・まくり差し」が決まる水面です。予想シミュレーターの<strong>「① コース別実績・攻め成功率比重」を 130%〜150%</strong> に上げ、2コース差し率・3/4コースまくり差し率が高い選手を素直に狙ってください。</p>
            <p>🔧 <strong>2. 3着ヒモ穴対策：</strong> 差し決着の3着には<strong>「⏳展開待ち連対率」</strong>が50%を超える外枠選手を3着流しに加えると、${actualCombo}のような中穴〜万舟を取りこぼしません。</p>
          `;
        } else {
          prescriptionHtml = `
            <p>🔧 <strong>1. イン逃げ信頼度◎：</strong> 壁役の2コースがしっかり機能しインが押し切る水面です。<strong>【🟦パターンA：イン逃げ本線】</strong>を中心に、点数を6〜8点に絞って回収率（EV）を高める運用が有効です。</p>
          `;
        }
        document.getElementById("simulatorPrescriptionBox").innerHTML = prescriptionHtml;

        let mode = document.getElementById("postReportMode").value;
        if (mode === "auto") mode = isHit ? "x_hit" : "x_verify";

        let postText = "";
        if (mode === "x_hit") {
          postText = [
            `🎯【${venue}${raceNo}R (${grade}) 展開シミュレーション完全的中！】🎯`,
            ``,
            `🏁 結果：${actualCombo} (${kimariteName} / 3連単 ${payout.toLocaleString()}円・${payoutPop}番人気)`,
            `🥇 1着：${f1}号艇 ${b1.name} (実ST .${Math.round(b1.actualSt*100).toString().padStart(2,"0")})`,
            `🥈 2着：${f2}号艇 ${b2.name}`,
            `🥉 3着：${f3}号艇 ${b3.name}`,
            ``,
            `事前のシミュレーター解析通り、${windDir}${windSpeed}mのスリット攻防から1M「${kimariteName}」→2・3着スジ連動（${f2}号艇・${f3}号艇）がドンピシャで決まりました🚤🔥`,
            `回収率 ${roiPct}%（+${profitYen.toLocaleString()}円）達成！`,
            ``,
            `次レースの2パターン展開解析＆勝負目もnoteで公開中です👇`,
            `https://note.com/boatrace__daisu`,
            `#ぼーとだいがくせい #ボートレース #競艇予想 #${venue}競艇`
          ].join("\n");
        } else if (mode === "x_verify") {
          postText = [
            `🔬【ぼーとだいがくせいの1M展開・答え合わせ研究室】${venue}${raceNo}R (${grade})`,
            ``,
            `🏁 確定結果：${actualCombo}（決まり手：${kimariteName} / 3連単 ${payout.toLocaleString()}円・${payoutPop}番人気）`,
            `⏱️ 本番スリット変化：${dokaText}`,
            ``,
            `【1マーク解剖ログ】`,
            `${f1}号艇(${b1.name})が実ST .${Math.round(b1.actualSt*100).toString().padStart(2,"0")}から${kimariteName}。引き波と展開の隙を突いて2着に${f2}号艇(${b2.name})、3着に${f3}号艇(${b3.name})が浮上するスジ決着でした。`,
            ``,
            `本日の${venue}の水面傾向とスタート変化データをシミュレーターの重み付けに反映完了💻 次Rの予想に活かします！👇`,
            `https://note.com/boatrace__daisu`,
            `#ぼーとだいがくせい #ボートレース #競艇検証 #${venue}競艇`
          ].join("\n");
        } else {
          postText = [
            `━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━`,
            `🎓 ぼーとだいがくせい｜${venue}${raceNo}R (${grade}) レース結果×予想 徹底振り返りレポート`,
            `━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━`,
            `■ 1. 確定結果・払戻・収支判定`,
            `・確定着順: ${actualCombo} （1着:${f1}号艇 ${b1.name} → 2着:${f2}号艇 ${b2.name} → 3着:${f3}号艇 ${b3.name}）`,
            `・決まり手: ${kimariteName} ／ 3連単配当: ${payout.toLocaleString()}円 (${payoutPop}番人気) ／ 2連単: ${payout2t.toLocaleString()}円`,
            `・水面気象: ${windDir}${windSpeed}m`,
            `・予想判定: ${isHit ? "🎯 的中" : "🔍 不的中（検証完了）"} （投資 ${invest.toLocaleString()}円 → 回収 ${returnYen.toLocaleString()}円 / 回収率 ${roiPct}%）`,
            ``,
            `■ 2. 展示ST vs 本番実STのズレ検証`,
            `・トップST: ${topStBoat.course}コース ${topStBoat.id}号艇 ${topStBoat.name} (実ST .${Math.round(topStBoat.actualSt*100).toString().padStart(2,"0")})`,
            `・スリット総括: ${dokaText}`,
            ``,
            `■ 3. 1マークの攻防と2・3着スジ連動の解剖`,
            why2nd3rdText.replace(/<[^>]+>/g, ""),
            ``,
            `■ 4. 次レースに向けたシミュレーター調整方針`,
            reflectionAdvice.replace(/<[^>]+>/g, ""),
            `🎓 ぼーとだいがくせい｜予想シミュレーター: https://bdkzgfy4igpjbzjachuzwu.streamlit.app/`,
            `X: https://x.com/Boatrace__daisu ｜ note: https://note.com/boatrace__daisu`,
            `━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━`
          ].join("\n");
        }
        document.getElementById("retroReportTextarea").value = postText;
      }

      function saveCurrentReviewToLog() {
        const venue = document.getElementById("revVenue").value;
        const raceNo = document.getElementById("revRaceNo").value;
        const grade = document.getElementById("revGrade").value;
        const f1 = Number(document.getElementById("fin1").value);
        const f2 = Number(document.getElementById("fin2").value);
        const f3 = Number(document.getElementById("fin3").value);
        const actualCombo = `${f1}-${f2}-${f3}`;
        const kimarite = document.getElementById("actualKimarite").value;
        const payout = Number(document.getElementById("payoutYen").value || 0);
        const invest = Number(document.getElementById("totalInvestYen").value || 3000);
        const hitUnitYen = Number(document.getElementById("hitTicketYen").value || 500);
        const userBets = parseUserBets(document.getElementById("preBetsInput").value);
        const isHit = userBets.includes(actualCombo);
        const returnYen = isHit ? Math.round((payout / 100) * hitUnitYen) : 0;

        const has1st2nd = userBets.some(c => {
          const [a, b] = c.split("-").map(Number);
          return a === f1 && b === f2;
        });
        const boatsArr = Object.values(reviewBoats);
        const m1Sorted = [...boatsArr].sort((a, b) => (a.m1Rank ?? a.rank) - (b.m1Rank ?? b.rank));
        const m1Combo = `${m1Sorted[0].id}-${m1Sorted[1].id}-${m1Sorted[2].id}`;
        const isM1Hit = userBets.includes(m1Combo);
        const firstMarkPat = document.getElementById("firstMarkPattern")?.value || "clean_in";
        const dochuType = document.getElementById("dochuOvertakeType")?.value || "none";
        const dochuReason = document.getElementById("dochuReason")?.value || "none";
        const stDiffKado = (reviewBoats[4]?.actualSt || 0.14) - (reviewBoats[4]?.preSt || 0.14);

        reviewLogs.unshift({
          venue,
          raceNo,
          grade,
          actualCombo,
          m1Combo,
          kimarite,
          kimariteName: KIMARITE_LABELS[kimarite] || "逃げ",
          firstMarkPat,
          dochuType,
          dochuReason,
          payout,
          invest,
          returnYen,
          isHit,
          isM1Hit,
          missedThirdOnly: !isHit && has1st2nd,
          stDiffKado
        });
        try {
          localStorage.setItem("BOATRACE_REVIEW_LOGS", JSON.stringify(reviewLogs));
        } catch (e) {}
        computeAndSaveLearnedParams();
        renderReviewLogs();
      }


      function computeAndSaveLearnedParams() {
        if (reviewLogs.length === 0) return null;
        const total = reviewLogs.length;
        const nigeCnt = reviewLogs.filter(x => x.kimarite === "nige").length;
        const makuriCnt = reviewLogs.filter(x => x.kimarite === "makuri").length;
        const sashiCnt = reviewLogs.filter(x => x.kimarite === "sashi" || x.kimarite === "makurisashi").length;
        const thirdMissCnt = reviewLogs.filter(x => x.missedThirdOnly).length;

        const dochuOvertakeCnt = reviewLogs.filter(x => x.dochuType && x.dochuType !== "none").length;
        const turnPowerCnt = reviewLogs.filter(x => x.dochuReason === "turn_power" || x.dochuReason === "racer_skill").length;
        const clashWaitCnt = reviewLogs.filter(x => x.firstMarkPat === "clash_wait").length;
        const m1MakuriAtkCnt = reviewLogs.filter(x => ["center_makuri_atk", "c2_makuri_atk", "clash_wait"].includes(x.firstMarkPat) || x.kimarite === "makuri").length;

        const nigeRatio = nigeCnt / total;
        const makuriRatio = m1MakuriAtkCnt / total;
        const sashiRatio = sashiCnt / total;
        const dochuRatio = dochuOvertakeCnt / total;

        // 1M展開要因（スリット・コース攻め）と道中逆転要因（展示気配・モーター・実力）を分離して重み付け学習
        const w_course = Math.min(180, Math.max(70, Math.round((100 + (sashiRatio - 0.25) * 85 + (nigeRatio - 0.50) * 35) / 5) * 5));
        const w_exhibit = Math.min(190, Math.max(80, Math.round((105 + dochuRatio * 55 + (turnPowerCnt / total) * 45) / 5) * 5));
        const w_motor = Math.min(190, Math.max(80, Math.round((100 + dochuRatio * 60 + sashiRatio * 35) / 5) * 5));
        const w_slit = Math.min(190, Math.max(80, Math.round((100 + (makuriRatio - 0.20) * 130) / 5) * 5));

        const inModAdj = Math.round((nigeRatio - 0.52) * 24);
        const makuriModAdj = Math.round((makuriRatio - 0.22) * 28);
        const sashiModAdj = Math.round((sashiRatio - 0.24) * 26);
        const waitBonusAdj = Math.min(22, thirdMissCnt * 5 + clashWaitCnt * 6 + dochuOvertakeCnt * 3);

        // 会場別（24場別）の蓄積バイアスも個別に計算して保持
        const venueBiases = {};
        const byVenue = {};
        reviewLogs.forEach(item => {
          const v = item.venue || "平和島";
          if (!byVenue[v]) byVenue[v] = [];
          byVenue[v].push(item);
        });
        Object.keys(byVenue).forEach(v => {
          const list = byVenue[v];
          const vc = list.length;
          const vNige = list.filter(x => x.kimarite === "nige").length / vc;
          const vMak = list.filter(x => ["center_makuri_atk", "c2_makuri_atk", "clash_wait"].includes(x.firstMarkPat) || x.kimarite === "makuri").length / vc;
          const vSas = list.filter(x => x.kimarite === "sashi" || x.kimarite === "makurisashi").length / vc;
          const vWait = list.filter(x => x.missedThirdOnly || x.firstMarkPat === "clash_wait" || (x.dochuType && x.dochuType !== "none")).length;
          venueBiases[v] = {
            count: vc,
            inModAdj: Math.round((vNige - 0.52) * 24),
            makuriModAdj: Math.round((vMak - 0.22) * 28),
            sashiModAdj: Math.round((vSas - 0.24) * 26),
            waitBonusAdj: Math.min(22, vWait * 5)
          };
        });

        const learnedObj = {
          type: "BOATRACE_LEARNED_PARAMS",
          sampleCount: total,
          hitRate: Math.round((reviewLogs.filter(x => x.isHit).length / total) * 100),
          m1HitRate: Math.round((reviewLogs.filter(x => x.isM1Hit || x.isHit).length / total) * 100),
          dochuRate: Math.round(dochuRatio * 100),
          weights: { w_course, w_exhibit, w_motor, w_slit },
          bias: { inModAdj, makuriModAdj, sashiModAdj, waitBonusAdj },
          venueBiases,
          recentLogs: reviewLogs.slice(0, 20),
          updatedAt: new Date().toLocaleTimeString()
        };

        try {
          localStorage.setItem("BOATRACE_LEARNED_PARAMS", JSON.stringify(learnedObj));
        } catch (e) {}

        const prevEl = document.getElementById("learnedParamsPreview");
        if (prevEl) {
          prevEl.innerHTML = `全<strong>${total}R</strong>の蓄積結果から算出 → 推奨重み付け: <strong>[①コース:${w_course}% / ②展示:${w_exhibit}% / ③機力:${w_motor}% / ④スリット:${w_slit}%]</strong> ｜ 補正: <strong>[イン${inModAdj >= 0 ? "+" : ""}${inModAdj} / まくり${makuriModAdj >= 0 ? "+" : ""}${makuriModAdj} / 差し${sashiModAdj >= 0 ? "+" : ""}${sashiModAdj} / 3着展開待ち+${waitBonusAdj}]</strong> （ブラウザ自動同期済）`;
        }
        return learnedObj;
      }

      function exportLearnedParamsToSimulator() {
        const obj = computeAndSaveLearnedParams();
        if (!obj) return;
        const jsonStr = JSON.stringify(obj);
        try {
          const ta = document.createElement("textarea");
          ta.value = jsonStr;
          document.body.appendChild(ta);
          ta.select();
          document.execCommand("copy");
          document.body.removeChild(ta);
        } catch (e) {}
        const prevEl = document.getElementById("learnedParamsPreview");
        if (prevEl) {
          prevEl.innerHTML += `<span class="ml-2 bg-emerald-500 text-slate-950 font-black px-2 py-0.5 rounded">✅ 学習パラメータをコピー＆同期しました！予想シミュレーターの「🧠 学習データ反映」で即適用できます</span>`;
        }
      }

      function clearReviewLogs() {
        reviewLogs = [];
        try {
          localStorage.removeItem("BOATRACE_REVIEW_LOGS");
          localStorage.removeItem("BOATRACE_LEARNED_PARAMS");
        } catch (e) {}
        const prevEl = document.getElementById("learnedParamsPreview");
        if (prevEl) prevEl.textContent = "蓄積データをリセットしました。";
        renderReviewLogs();
      }

      function renderReviewLogs() {
        const container = document.getElementById("reviewLogsContainer");
        const sumEl = document.getElementById("logStatsSummary");
        if (reviewLogs.length === 0) {
          sumEl.textContent = "保存履歴: 0件";
          container.innerHTML = `<div class="text-slate-500 text-[11px]">まだ保存されたレース履歴はありません。「💾 このレースを研究履歴に保存」を押すとここに蓄積されます。</div>`;
          return;
        }
        const totalRaces = reviewLogs.length;
        const hits = reviewLogs.filter(x => x.isHit).length;
        const sumInv = reviewLogs.reduce((s, x) => s + x.invest, 0);
        const sumRet = reviewLogs.reduce((s, x) => s + x.returnYen, 0);
        const roi = sumInv > 0 ? Math.round((sumRet / sumInv) * 100) : 0;
        const profit = sumRet - sumInv;

        sumEl.textContent = `全${totalRaces}R ｜ 的中 ${hits}/${totalRaces} (${Math.round((hits/totalRaces)*100)}%) ｜ 累計回収率 ${roi}% (${profit >= 0 ? "+" : ""}${profit.toLocaleString()}円)`;
        container.innerHTML = reviewLogs.map((item) => `
          <div class="flex items-center justify-between bg-slate-950 border border-slate-800 px-2.5 py-1.5 rounded">
            <div class="flex items-center gap-2">
              <span class="px-1.5 py-0.5 rounded text-[10px] font-bold ${item.isHit ? "bg-amber-400 text-slate-950" : "bg-slate-800 text-slate-400"}">${item.isHit ? "🎯的中" : "不的中"}</span>
              <span class="font-bold text-white">${item.venue} ${item.raceNo}R (${item.grade})</span>
              <span class="font-mono font-bold text-teal-300">${item.actualCombo}</span>
              <span class="text-[10px] text-slate-400">[${item.kimariteName} / ${item.payout.toLocaleString()}円]</span>
            </div>
            <div class="font-mono text-[11px] ${item.returnYen - item.invest >= 0 ? "text-amber-300 font-bold" : "text-slate-400"}">
              投資${item.invest.toLocaleString()}円 → 回収${item.returnYen.toLocaleString()}円
            </div>
          </div>
        `).join("");
      }

      function copyRetroReport() {
        const txt = document.getElementById("retroReportTextarea").value;
        try {
          const ta = document.createElement("textarea");
          ta.value = txt; document.body.appendChild(ta); ta.select(); document.execCommand("copy"); document.body.removeChild(ta);
        } catch (e) {}
        const toast = document.getElementById("copyRetroToast");
        toast.classList.remove("hidden");
        setTimeout(() => toast.classList.add("hidden"), 2300);
      }

      function parsePastedOfficialResult() {
        const raw = (document.getElementById("rawResultPasteInput").value || "").trim();
        if (!raw) return;

        if (raw.includes("まくり差し")) document.getElementById("actualKimarite").value = "makurisashi";
        else if (raw.includes("まくり")) document.getElementById("actualKimarite").value = "makuri";
        else if (raw.includes("差し")) document.getElementById("actualKimarite").value = "sashi";
        else if (raw.includes("逃げ")) document.getElementById("actualKimarite").value = "nige";
        else if (raw.includes("抜き")) document.getElementById("actualKimarite").value = "nuki";

        // スペースを含む「1 - 2 - 3」や改行を含む3連単組番＆配当の確実な抽出
        const triMatch = raw.match(/3連単[\s\S]{1,80}?([1-6])\s*[-=ー]\s*([1-6])\s*[-=ー]\s*([1-6])[\s\S]{1,80}?¥?\s*([\d,]+)/);
        if (triMatch) {
          document.getElementById("fin1").value = triMatch[1];
          document.getElementById("fin2").value = triMatch[2];
          document.getElementById("fin3").value = triMatch[3];
          document.getElementById("payoutYen").value = parseInt(triMatch[4].replace(/,/g, ""), 10);
        } else {
          const payOnly = raw.match(/3連単[\s\S]{1,80}?¥\s*([\d,]+)/);
          if (payOnly) document.getElementById("payoutYen").value = parseInt(payOnly[1].replace(/,/g, ""), 10);
        }

        const nirentanM = raw.match(/2連単[\s\S]{1,80}?¥\s*([\d,]+)/);
        if (nirentanM) {
          document.getElementById("payout2tYen").value = parseInt(nirentanM[1].replace(/,/g, ""), 10);
        }

        const stMatches = [...raw.matchAll(/\b0?\.(\d{2})\b/g)].map(m => parseFloat(`0.${m[1]}`));
        if (stMatches.length >= 6) {
          for (let b = 1; b <= 6; b++) {
            reviewBoats[b].actualSt = stMatches[b - 1];
          }
        }

        infer1MProcessFromNumbers(false);
        renderBoatStTable();
        runReviewAnalysis();
        document.getElementById("pasteResultModal").classList.add("hidden");
      }

      window.addEventListener("DOMContentLoaded", () => {
        const now = new Date();
        const yyyy = now.getFullYear();
        const mm = String(now.getMonth() + 1).padStart(2, "0");
        const dd = String(now.getDate()).padStart(2, "0");
        const dateEl = document.getElementById("fetchDateInput");
        if (dateEl) dateEl.value = `${yyyy}-${mm}-${dd}`;

        // 過去に保存した蓄積ログをlocalStorageから復元（上書き消去しない！）
        let loadedFromStorage = false;
        try {
          const savedLogs = localStorage.getItem("BOATRACE_REVIEW_LOGS");
          if (savedLogs) {
            const parsed = JSON.parse(savedLogs);
            if (Array.isArray(parsed) && parsed.length > 0) {
              reviewLogs = parsed;
              loadedFromStorage = true;
            }
          }
        } catch (e) {}

        loadSampleCase("makuri_hit");
        if (!loadedFromStorage) {
          saveCurrentReviewToLog();
        } else {
          computeAndSaveLearnedParams();
          renderReviewLogs();
        }
      });
    </script>
  </body>
</html>
"""


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
            "💡 上のバーで日付・レース場・Rを選んで「🔄 公式データ自動取得」を押すと、出走表・直前情報・コース別攻め成功率・レースグレード(G1以上判定)が自動反映されます。"
        )

    c_mode, c_date, c_venue, c_rno, c_btn, c_odds = st.columns([1.6, 0.95, 1.35, 0.7, 1.5, 1.1])
    with c_mode:
        app_mode = st.radio(
            "ツール切替",
            ["🚤 予想シミュレーター", "🔬 結果振り返りサイト"],
            horizontal=True,
        )
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
        if st.button("🔄 公式データ一括取得 (出走表＋展示＋オッズ)", type="primary", use_container_width=True):
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

    with c_odds:
        st.write("")
        if st.button("💹 最新オッズ更新", use_container_width=True):
            with st.spinner(f"{selected_venue[1]} {rno_int}R の最新3連単オッズを更新中..."):
                if not st.session_state.get("server_race_data"):
                    st.session_state["server_race_data"] = fetch_race_data_from_official(hd_str, jcd_str, rno_int)
                else:
                    odds_bundle = fetch_latest_odds_only(hd_str, jcd_str, rno_int)
                    st.session_state["server_race_data"]["odds3t"] = odds_bundle.get("odds3t", {})
                    if odds_bundle.get("settledResult"):
                        st.session_state["server_race_data"]["settledResult"] = odds_bundle["settledResult"]
                cnt_o = len((st.session_state["server_race_data"] or {}).get("odds3t", {}))
                st.session_state["status_banner"] = (
                    f"💹 最新オッズ更新完了【{hd_str} {selected_venue[1]} {rno_int}R】：3連単 {cnt_o}通り反映済"
                )

    active_venues = get_active_venues_for_date(hd_str)
    active_info = f" ｜ 📍 {hd_str} 開催場: {', '.join(active_venues)}" if active_venues else ""
    st.caption(st.session_state.get("status_banner", "") + active_info)

    if app_mode == "🔬 結果振り返りサイト":
        components.html(EMBEDDED_REVIEWER_HTML, height=1750, scrolling=True)
    else:
        json_payload = json.dumps(st.session_state["server_race_data"], ensure_ascii=False)
        rendered_html = ULTIMATE_HTML_TEMPLATE.replace("__INJECTED_SERVER_DATA__", json_payload)
        components.html(rendered_html, height=3400, scrolling=True)


if __name__ == "__main__":
    main()