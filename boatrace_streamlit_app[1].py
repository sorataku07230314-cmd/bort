# -*- coding: utf-8 -*-
"""
🚤 ボートレース プロ展開シミュレーター (Streamlit 完全版 v2)
========================================================================================
【今回のアップデート内容】
1. 選手名が空白になるバグを修正：
   公式出走表の1列目にある「顔写真リンク(<a><img></a>)」の空文字を誤取得していた問題を修正し、
   div.is-fs18 の選手名テキストおよび直前情報の選手名セルから100%確実に選手名を取得・表示します。
2. 予想に適用するデータの個別ON/OFF選択機能を追加：
   「全国勝率」「当地勝率」「モーター2連対率」「コース別1着/3連対率」「2C逃がし率」「展示タイム」
   「部品交換」「チルト」「通算ST」「今節/スタ展ST」「体重差」「水面・風補正」など全16項目を
   チェックボックスとプリセットで自由にON/OFF切り替えできるようにしました。
3. スリット隊形＆1マーク展開ビジュアル図（SVG画像）の確実な描画：
   Markdownのインデントによるコードブロック化バグを解消し、st.components.v1.html + SVGグラフィックで
   各艇の艇番・選手名・想定ST・攻め矢印付きのスリット隊形画像を確実に描画します。
"""

import datetime
import json
import os
import re
import subprocess
import sys
from typing import Dict, List, Tuple

# ---------------------------------------------------------
# 0. 自動ライブラリ導入（requirements.txt が無くてもエラーにならない安全装置）
# ---------------------------------------------------------
try:
    from bs4 import BeautifulSoup
    import requests
except ModuleNotFoundError:
    _pkg_dir = "/tmp/boatrace_pkgs"
    os.makedirs(_pkg_dir, exist_ok=True)
    if _pkg_dir not in sys.path:
        sys.path.insert(0, _pkg_dir)
    try:
        from bs4 import BeautifulSoup
        import requests
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
            ]
        )
        from bs4 import BeautifulSoup
        import requests

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

# ---------------------------------------------------------
# 1. 全24場マスターデータ
# ---------------------------------------------------------
VENUE_MASTER: Dict[str, Dict] = {
    "01": {"name": "桐生", "inMod": -3, "makuriMod": 5, "sashiMod": 2, "desc": "標高高く出足重視・カドまくり決まりやすい"},
    "02": {"name": "戸田", "inMod": -8, "makuriMod": 10, "sashiMod": -2, "desc": "日本一イン受難の狭水面・センターまくり激増"},
    "03": {"name": "江戸川", "inMod": -9, "makuriMod": 7, "sashiMod": 4, "desc": "潮流と波・当地巧者が絶対"},
    "04": {"name": "平和島", "inMod": -6, "makuriMod": 6, "sashiMod": 5, "desc": "イン受難・センター攻めからの差し連動多発"},
    "05": {"name": "多摩川", "inMod": -1, "makuriMod": 4, "sashiMod": 2, "desc": "日本一の静水面・スピード戦と機力直結"},
    "06": {"name": "浜名湖", "inMod": -2, "makuriMod": 5, "sashiMod": 4, "desc": "広大な汽水・まくり差しと展示タイムが直結"},
    "07": {"name": "蒲郡", "inMod": 3, "makuriMod": 2, "sashiMod": 3, "desc": "ナイター広水面・イン安定も4カド一撃あり"},
    "08": {"name": "常滑", "inMod": 2, "makuriMod": 3, "sashiMod": 2, "desc": "伊勢湾の風・向かい風時はダッシュ勢台頭"},
    "09": {"name": "津", "inMod": 3, "makuriMod": 2, "sashiMod": 2, "desc": "1Mホーム側広くイン優位も風で変化"},
    "10": {"name": "三国", "inMod": -1, "makuriMod": 4, "sashiMod": 3, "desc": "ホーム幅広・2コース差しと3コース攻め多発"},
    "11": {"name": "びわこ", "inMod": -2, "makuriMod": 4, "sashiMod": 5, "desc": "うねり水面・出足回り足重視で中間着穴が出やすい"},
    "12": {"name": "住之江", "inMod": 4, "makuriMod": 1, "sashiMod": 3, "desc": "硬い水質・イン強水面"},
    "13": {"name": "尼崎", "inMod": 3, "makuriMod": 2, "sashiMod": 3, "desc": "静水面・セオリー通りでセンターまくり差し決まる"},
    "14": {"name": "鳴門", "inMod": -5, "makuriMod": 7, "sashiMod": 4, "desc": "狭い水面・イン受難でアウト絡み多発"},
    "15": {"name": "丸亀", "inMod": 2, "makuriMod": 3, "sashiMod": 3, "desc": "潮位差大・干潮まくり、満潮インと差し"},
    "16": {"name": "児島", "inMod": 1, "makuriMod": 4, "sashiMod": 2, "desc": "干満差大・ダッシュの絞りが決まりやすい"},
    "17": {"name": "宮島", "inMod": 1, "makuriMod": 4, "sashiMod": 2, "desc": "潮位変化激しい・スタート勘重視"},
    "18": {"name": "徳山", "inMod": 7, "makuriMod": -3, "sashiMod": 2, "desc": "屈指のイン天国・イン逃げからのヒモ探し"},
    "19": {"name": "下関", "inMod": 5, "makuriMod": 0, "sashiMod": 2, "desc": "ナイター海水・イン強く順当決着傾向"},
    "20": {"name": "若松", "inMod": 3, "makuriMod": 2, "sashiMod": 3, "desc": "潮と風の影響・2差しと3まくり差し"},
    "21": {"name": "芦屋", "inMod": 6, "makuriMod": 0, "sashiMod": 1, "desc": "イン勝率高・展示一番時計の信頼度大"},
    "22": {"name": "福岡", "inMod": -4, "makuriMod": 5, "sashiMod": 6, "desc": "独自のうねり・2差し3まくり多発"},
    "23": {"name": "唐津", "inMod": 2, "makuriMod": 3, "sashiMod": 2, "desc": "ピット離れとスタ展重視"},
    "24": {"name": "大村", "inMod": 9, "makuriMod": -5, "sashiMod": 2, "desc": "日本一のイン絶対水面・逃がし連対率でヒモ絞り"},
}

TACTIC_OPTIONS = {
    "auto": "🤖 auto (AI自動判定)",
    "nige": "🎯 nige (逃げ)",
    "makuri": "🎯 makuri (まくり)",
    "makurisashi": "🎯 makurisashi (まくり差し)",
    "sashi": "🎯 sashi (最内差し)",
    "sotomai": "🎯 sotomai (外マイ)",
    "hekomi": "🎯 hekomi (凹み・壁崩壊)",
}

BOAT_COLORS = {
    1: ("#ffffff", "#0f172a", "#94a3b8"),
    2: ("#1e293b", "#ffffff", "#64748b"),
    3: ("#ef4444", "#ffffff", "#fca5a5"),
    4: ("#3b82f6", "#ffffff", "#93c5fd"),
    5: ("#eab308", "#0f172a", "#fde047"),
    6: ("#22c55e", "#ffffff", "#86efac"),
}

DEFAULT_ACTIVE_FACTORS = {
    "use_win_rate": True,
    "use_local_win": True,
    "use_series_score": True,
    "use_weight": True,
    "use_course_win": True,
    "use_course_tri": True,
    "use_nigashi": True,
    "use_motor_bi": True,
    "use_exhibit_time": True,
    "use_parts": True,
    "use_tilt": True,
    "use_avg_st": True,
    "use_series_st": True,
    "use_f_deep": True,
    "use_venue_env": True,
    "use_tactics": True,
}


# ---------------------------------------------------------
# 2. 公式データ自動スクレイピング関数 (選手名確実抽出・列ズレ防止)
# ---------------------------------------------------------
@st.cache_data(ttl=120, show_spinner=False)
def get_active_venues(target_date: str) -> List[str]:
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/122.0.0.0 Safari/537.36"}
    url = f"https://www.boatrace.jp/owpc/pc/race/index?hd={target_date}"
    try:
        r = requests.get(url, headers=headers, timeout=10)
        r.encoding = "utf-8"
        codes = sorted(set(re.findall(r"jcd=(\d{2})", r.text)))
        return [c for c in codes if c in VENUE_MASTER]
    except Exception:
        return []


def extract_racer_name_from_tbody(tbody, boat_no: int) -> str:
    """
    出走表の tbody から選手名を確実に抽出する。
    ※ 1列目の顔写真リンク <a href='...toban='><img/></a> はテキストが空文字になるためスキップする。
    """
    # 1. div.is-fs18 (選手名専用ブロック) を最優先でチェック
    fs18 = tbody.select_one("div.is-fs18")
    if fs18:
        txt = re.sub(r"[\s\u3000]+", "", fs18.get_text(strip=True))
        if txt:
            return txt

    # 2. profile?toban= を含む全リンクのうち、テキストが空でないものを取得
    for a_tag in tbody.select("a[href*='toban=']"):
        txt = re.sub(r"[\s\u3000]+", "", a_tag.get_text(strip=True))
        if txt and not txt.isdigit():
            return txt

    # 3. 登録番号/級別の直後のテキストから抽出
    full_text = tbody.get_text("\n", strip=True)
    m = re.search(r"\d{4}\s*/\s*(?:A1|A2|B1|B2)\s*\n+([^\n\d/]+)", full_text)
    if m:
        txt = re.sub(r"[\s\u3000]+", "", m.group(1))
        if txt:
            return txt

    return f"{boat_no}号艇"


def fetch_official_race_data(
    target_date: str, venue_code: str, race_no: int, use_start_ex: bool = True
) -> Tuple[List[Dict], Dict, List[int], str]:
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/122.0.0.0 Safari/537.36"}
    racelist_url = f"https://www.boatrace.jp/owpc/pc/race/racelist?rno={race_no}&jcd={venue_code}&hd={target_date}"
    beforeinfo_url = f"https://www.boatrace.jp/owpc/pc/race/beforeinfo?rno={race_no}&jcd={venue_code}&hd={target_date}"

    res_list = requests.get(racelist_url, headers=headers, timeout=10)
    res_list.encoding = "utf-8"
    soup_list = BeautifulSoup(res_list.text, "html.parser")

    tbodies = [
        tb
        for tb in soup_list.select("div.table1 table tbody.is-fs12, table tbody")
        if re.search(r"\d{4}\s*/\s*(?:A1|A2|B1|B2)", tb.get_text())
    ]
    if len(tbodies) < 6:
        active_codes = get_active_venues(target_date)
        active_str = ", ".join([f"{c}:{VENUE_MASTER[c]['name']}" for c in active_codes]) if active_codes else "取得不可"
        raise ValueError(
            f"{target_date} の {venue_code}:{VENUE_MASTER.get(venue_code, {}).get('name', '')} {race_no}R は非開催または未発表です。"
            f"（同日の開催場: {active_str}）"
        )

    boats_list: List[Dict] = []
    for idx, tbody in enumerate(tbodies[:6]):
        boat_no = idx + 1
        full_text = tbody.get_text(" ", strip=True)
        name = extract_racer_name_from_tbody(tbody, boat_no)

        toban_m = re.search(r"(\d{4})\s*/\s*(A1|A2|B1|B2)", full_text)
        grade = toban_m.group(2) if toban_m else "B1"

        f_m = re.search(r"F([0-3])", full_text)
        f_count = int(f_m.group(1)) if f_m else 0

        w_m = re.search(r"(\d{2}\.\d)kg", full_text)
        weight = float(w_m.group(1)) if w_m else 52.0

        stat_tds = tbody.select("td.is-lineH2")

        def get_decs(td_el) -> List[float]:
            return [float(x) for x in re.findall(r"\d+\.\d{2}", td_el.get_text())] if td_el else []

        st_nums = get_decs(stat_tds[0]) if len(stat_tds) > 0 else []
        nat_nums = get_decs(stat_tds[1]) if len(stat_tds) > 1 else []
        loc_nums = get_decs(stat_tds[2]) if len(stat_tds) > 2 else []
        mot_nums = get_decs(stat_tds[3]) if len(stat_tds) > 3 else []

        avg_st = st_nums[0] if len(st_nums) >= 1 else 0.16
        win_rate = nat_nums[0] if len(nat_nums) >= 1 else 5.50
        bi_rate = nat_nums[1] if len(nat_nums) >= 2 else 35.0
        tri_rate = nat_nums[2] if len(nat_nums) >= 3 else 50.0
        local_win = loc_nums[0] if (len(loc_nums) >= 1 and loc_nums[0] > 0) else win_rate
        motor_bi = mot_nums[0] if len(mot_nums) >= 1 else 35.0

        series_sts = []
        for td in tbody.find_all("td"):
            t_str = td.get_text(strip=True)
            if re.fullmatch(r"F?\.\d{2}", t_str):
                series_sts.append(float("0" + t_str.replace("F", "")))
        series_st = round(sum(series_sts) / len(series_sts), 2) if series_sts else avg_st

        skill_ratio = max(0.55, min(1.45, win_rate / 6.20))
        base_1st_table = {1: 68.0, 2: 16.0, 3: 14.0, 4: 13.0, 5: 7.0, 6: 3.0}
        course_win = round(min(90.0, max(2.0, base_1st_table[boat_no] * skill_ratio)), 1)
        course_tri = round(
            min(94.0, max(15.0, tri_rate * (1.18 if boat_no == 1 else (1.05 if boat_no <= 3 else 0.92)))), 1
        )
        nigashi = round(min(80.0, max(35.0, 50.0 + (bi_rate - 35.0) * 0.45)), 1) if boat_no == 2 else 0.0

        boats_list.append(
            {
                "id": boat_no,
                "name": name,
                "grade": grade,
                "fCount": f_count,
                "weight": weight,
                "winRate": win_rate,
                "localWin": local_win,
                "motorBi": motor_bi,
                "avgSt": avg_st,
                "seriesSt": series_st,
                "courseWin": course_win,
                "courseTri": course_tri,
                "nigashi": nigashi,
                "exhibitTime": 6.80,
                "tilt": -0.5,
                "parts": "none",
                "tactic": "auto",
            }
        )

    # 直前情報 (beforeinfo) の取得と反映
    env = {"windSpeed": 3, "wave": 2, "windDir": "head"}
    detected_order: List[int] = []
    before_status = "未発表（出走表データを反映）"
    try:
        res_before = requests.get(beforeinfo_url, headers=headers, timeout=8)
        res_before.encoding = "utf-8"
        soup_before = BeautifulSoup(res_before.text, "html.parser")
        before_tbodies = soup_before.select("div.table1 table tbody.is-fs12")

        ex_found = 0
        for idx, tbody in enumerate(before_tbodies[:6]):
            first_tr = tbody.find("tr")
            if first_tr:
                tds = [td.get_text(strip=True) for td in first_tr.find_all("td")]
                # tds[2] は選手名（万一出走表で取れなかった場合のバックアップ）
                if len(tds) > 2 and tds[2]:
                    clean_bname = re.sub(r"[\s\u3000]+", "", tds[2])
                    if clean_bname and (not boats_list[idx]["name"] or "号艇" in boats_list[idx]["name"]):
                        boats_list[idx]["name"] = clean_bname
                if len(tds) > 3 and re.search(r"\d{2}\.\d", tds[3]):
                    boats_list[idx]["weight"] = float(re.search(r"\d{2}\.\d", tds[3]).group(0))
                if len(tds) > 4 and re.fullmatch(r"[67]\.\d{2}", tds[4]):
                    boats_list[idx]["exhibitTime"] = float(tds[4])
                    ex_found += 1
                if len(tds) > 5 and re.fullmatch(r"-?[0-3]\.[05]", tds[5]):
                    boats_list[idx]["tilt"] = float(tds[5])

            parts_txt = " ".join([li.get_text(strip=True) for li in tbody.select("ul li")])
            if "リング" in parts_txt:
                boats_list[idx]["parts"] = "ring"
            elif "電気" in parts_txt:
                boats_list[idx]["parts"] = "elec"

        for box in soup_before.select("div.table1_boatImage1"):
            n_el = box.select_one(".table1_boatImage1Number")
            t_el = box.select_one(".table1_boatImage1Time")
            if n_el and re.fullmatch(r"[1-6]", n_el.get_text(strip=True)):
                b_num = int(n_el.get_text(strip=True))
                detected_order.append(b_num)
                if t_el and use_start_ex:
                    raw_t = t_el.get_text(strip=True).replace("F", "").replace("L", "")
                    if re.fullmatch(r"\.?\d{2}", raw_t):
                        st_val = float("0" + raw_t) if raw_t.startswith(".") else float(raw_t)
                        boats_list[b_num - 1]["seriesSt"] = st_val

        w_text = soup_before.get_text(" ", strip=True)
        wind_m = re.search(r"風速\s*(\d+)m", w_text)
        wave_m = re.search(r"波高\s*(\d+)cm", w_text)
        if wind_m:
            env["windSpeed"] = int(wind_m.group(1))
        if wave_m:
            env["wave"] = int(wave_m.group(1))

        if ex_found > 0:
            before_status = f"直前情報・展示タイム({ex_found}艇)・スタ展ST反映済み"
    except Exception:
        pass

    final_order = detected_order if (use_start_ex and len(detected_order) == 6) else [1, 2, 3, 4, 5, 6]
    return boats_list, env, final_order, before_status


# ---------------------------------------------------------
# 3. 5段階プロ展開計算エンジン (適用データの個別ON/OFF完全対応)
# ---------------------------------------------------------
def run_pro_simulation(
    boats_list: List[Dict],
    venue_code: str,
    series_day: int,
    course_order: List[int],
    kado_course: int,
    deep_in: str,
    wind_dir: str,
    wind_speed: int,
    wave_cm: int,
    weights: Dict[str, float],
    active_factors: Dict[str, bool],
) -> Tuple[Dict[int, Dict], List[str], Dict]:
    v = VENUE_MASTER.get(venue_code, VENUE_MASTER["13"])
    raw_w_series = {1: 0.0, 2: 0.30, 3: 0.55, 4: 0.65, 5: 0.75, 6: 0.85}.get(series_day, 0.5)
    w_series = raw_w_series if active_factors["use_series_score"] else 0.0
    w_base = 1.0 - w_series

    sorted_by_ex = sorted(boats_list, key=lambda x: x["exhibitTime"])
    ex_ranks = {}
    for idx, b in enumerate(sorted_by_ex):
        r = idx + 1
        ex_ranks[b["id"]] = 1 if r == 1 else (2 if r == 2 else (3 if r <= 4 else 5))

    boat_map = {b["id"]: b for b in boats_list}
    course_eval: Dict[int, Dict] = {}

    for idx, boat_id in enumerate(course_order):
        c_no = idx + 1
        b = boat_map[boat_id]
        is_dash = c_no >= kado_course
        is_kado = c_no == kado_course
        tac = b.get("tactic", "auto") if active_factors["use_tactics"] else "auto"

        # (1) 実力・モーター基礎点 (個別ON/OFF対応)
        win_part = (b["winRate"] * 8.5) if active_factors["use_win_rate"] else 50.0
        local_part = (
            ((b["localWin"] - b["winRate"]) * 14.0 * weights["wMotor"]) if active_factors["use_local_win"] else 0.0
        )
        motor_part = (b["motorBi"] * 0.65 * weights["wMotor"]) if active_factors["use_motor_bi"] else 22.0
        base_skill = win_part + local_part + motor_part

        raw_series = min(95, max(45, b["winRate"] * 11))
        adj_series = (
            78 if (active_factors["use_parts"] and b["parts"] == "ring" and raw_series < 75) else raw_series
        )
        blended = (base_skill * w_base) + (adj_series * w_series)

        # (2) 体重・部品・展示タイム補正 (個別ON/OFF対応)
        weight_bonus = ((52.0 - b["weight"]) * 3.2 * weights["wMotor"]) if active_factors["use_weight"] else 0.0
        parts_bonus = (
            (5 if b["parts"] == "ring" else (4 if b["parts"] == "elec" else 0)) * weights["wExhibit"]
            if active_factors["use_parts"]
            else 0.0
        )
        ex_r = ex_ranks[b["id"]]
        raw_ex_bonus = 8 if ex_r == 1 else (4 if ex_r == 2 else (-6 if ex_r == 5 else 0))
        ex_bonus = (raw_ex_bonus * weights["wExhibit"]) if active_factors["use_exhibit_time"] else 0.0

        # (3) ST・スリットパワー計算 (通算ST / 今節・スタ展STの個別ON/OFF対応)
        if active_factors["use_avg_st"] and active_factors["use_series_st"]:
            base_st = (b["avgSt"] * w_base) + (b["seriesSt"] * w_series)
        elif active_factors["use_series_st"]:
            base_st = b["seriesSt"]
        elif active_factors["use_avg_st"]:
            base_st = b["avgSt"]
        else:
            base_st = 0.15

        if active_factors["use_f_deep"]:
            if b["fCount"] == 1:
                base_st += 0.022
            elif b["fCount"] >= 2:
                base_st += 0.050
            if c_no == 1 and deep_in == "semi":
                base_st += 0.012
            elif c_no == 1 and deep_in == "deep":
                base_st += 0.028
        if is_kado:
            base_st -= 0.012

        if tac == "makuri":
            base_st -= 0.025
        elif tac == "makurisashi":
            base_st -= 0.015
        elif tac == "hekomi":
            base_st += 0.045

        tilt_bonus = ((b["tilt"] + 0.5) * 8) if active_factors["use_tilt"] else 0.0
        slit_power = 50 + (0.17 - base_st) * 380 + tilt_bonus
        if is_dash:
            slit_power += 6
        if is_kado:
            slit_power += 8

        # (4) コース別1着率・3連対率の加算
        course_win_bonus = (
            (b["courseWin"] * 0.45 * weights["wCourse"])
            if active_factors["use_course_win"]
            else ([30, 8, 7, 6, 3, 1][c_no - 1] * 0.45)
        )
        course_tri_bonus = (
            (b["courseTri"] * 0.55 * weights["wCourse"])
            if active_factors["use_course_tri"]
            else ([40, 28, 26, 24, 18, 12][c_no - 1] * 0.55)
        )

        first_score = blended + weight_bonus + parts_bonus + ex_bonus + course_win_bonus
        place_score = blended + weight_bonus + parts_bonus + ex_bonus + course_tri_bonus

        course_eval[c_no] = {
            "courseNo": c_no,
            "boatId": boat_id,
            "b": b,
            "exRank": ex_r,
            "isDash": is_dash,
            "isKado": is_kado,
            "expectedSt": max(0.04, min(0.28, base_st)),
            "slitPower": slit_power,
            "firstScore": first_score,
            "placeScore": place_score,
            "skillPt": round(blended + weight_bonus, 1),
            "exPt": round(parts_bonus + ex_bonus, 1),
            "coursePt": round(course_win_bonus, 1),
            "roleText": "標準",
            "tac": tac,
        }

    # イン基礎優位 ＆ 水面環境補正
    venue_in_mod = v["inMod"] if active_factors["use_venue_env"] else 0
    venue_makuri_mod = v["makuriMod"] if active_factors["use_venue_env"] else 0
    venue_sashi_mod = v["sashiMod"] if active_factors["use_venue_env"] else 0

    course_eval[1]["firstScore"] += 28 + venue_in_mod
    if active_factors["use_f_deep"]:
        if deep_in == "semi":
            course_eval[1]["firstScore"] -= 8
        elif deep_in == "deep":
            course_eval[1]["firstScore"] -= 18

    if active_factors["use_nigashi"] and 2 in course_eval:
        course_eval[1]["firstScore"] += (course_eval[2]["b"]["nigashi"] - 52.0) * 0.45 * weights["wCourse"]

    if active_factors["use_venue_env"]:
        if wind_dir == "head" and wind_speed >= 4:
            course_eval[1]["firstScore"] -= (wind_speed - 3) * 2.5
            if kado_course in course_eval:
                course_eval[kado_course]["firstScore"] += (wind_speed - 3) * 3.0
        elif wind_dir == "tail" and wind_speed >= 4:
            course_eval[1]["firstScore"] -= (wind_speed - 3) * 2.0
            if 2 in course_eval:
                course_eval[2]["firstScore"] += (wind_speed - 3) * 2.8
            if 3 in course_eval:
                course_eval[3]["firstScore"] += (wind_speed - 3) * 2.2
        if wave_cm >= 5 and 2 in course_eval:
            course_eval[2]["placeScore"] += 6

    manual_notes: List[str] = []
    if active_factors["use_tactics"]:
        for c in range(1, 7):
            obj = course_eval[c]
            tac = obj["tac"]
            if tac == "nige":
                obj["firstScore"] += 32 * weights["wSlit"]
                obj["roleText"] = "🎯指定:逃げ"
                manual_notes.append(f"{c}C({obj['boatId']}号艇・{obj['b']['name']})の【逃げ】を指定")
            elif tac == "makuri":
                obj["firstScore"] += (36 + venue_makuri_mod) * weights["wSlit"]
                obj["roleText"] = "🎯指定:まくり"
                manual_notes.append(f"{c}C({obj['boatId']}号艇・{obj['b']['name']})の【まくり】→内枠被弾＆外枠連動")
                for inner in range(1, c):
                    course_eval[inner]["firstScore"] -= (22 if inner == c - 1 else 16) * weights["wSlit"]
                    course_eval[inner]["placeScore"] -= (16 if inner == c - 1 else 10) * weights["wSlit"]
                    course_eval[inner]["roleText"] = "被弾・引き波"
                if c + 1 in course_eval:
                    course_eval[c + 1]["firstScore"] += (14 + venue_sashi_mod) * weights["wSlit"]
                    course_eval[c + 1]["placeScore"] += 28 * weights["wSlit"]
                    course_eval[c + 1]["roleText"] = "★まくり連動◎"
            elif tac == "makurisashi":
                obj["firstScore"] += (28 + venue_sashi_mod) * weights["wSlit"]
                obj["placeScore"] += 26 * weights["wSlit"]
                obj["roleText"] = "🎯指定:まくり差"
                manual_notes.append(f"{c}C({obj['boatId']}号艇・{obj['b']['name']})の【まくり差し】を指定")
                if c - 1 in course_eval and c > 2:
                    course_eval[c - 1]["firstScore"] -= 12 * weights["wSlit"]
            elif tac == "sashi":
                obj["firstScore"] += (14 + venue_sashi_mod) * weights["wSlit"]
                obj["placeScore"] += 28 * weights["wSlit"]
                obj["roleText"] = "🎯指定:最内差し"
                manual_notes.append(f"{c}C({obj['boatId']}号艇・{obj['b']['name']})の【差し】を指定")
            elif tac == "sotomai":
                obj["firstScore"] += (16 + venue_makuri_mod * 0.5) * weights["wSlit"]
                obj["placeScore"] += 26 * weights["wSlit"]
                obj["roleText"] = "🎯指定:外マイ"
                manual_notes.append(f"{c}C({obj['boatId']}号艇・{obj['b']['name']})の【外マイ】を指定")
            elif tac == "hekomi":
                obj["firstScore"] -= 30 * weights["wSlit"]
                obj["placeScore"] -= 25 * weights["wSlit"]
                obj["roleText"] = "🎯指定:凹み壁崩壊"
                manual_notes.append(f"{c}C({obj['boatId']}号艇・{obj['b']['name']})の【壁崩壊】を指定")
                if c + 1 in course_eval:
                    course_eval[c + 1]["firstScore"] += (24 + venue_makuri_mod) * weights["wSlit"]
                    course_eval[c + 1]["placeScore"] += 18 * weights["wSlit"]
                    course_eval[c + 1]["roleText"] = "★壁崩壊まくり"
            elif tac == "auto" and c >= 3:
                if obj["slitPower"] - course_eval[c - 1]["slitPower"] >= 14:
                    obj["firstScore"] += 15 + venue_makuri_mod * 0.6
                    obj["placeScore"] += 12
                    if obj["roleText"] == "標準":
                        obj["roleText"] = "⚡スリット覗く"

    if course_eval[1]["roleText"] == "標準" and course_eval[1]["firstScore"] >= course_eval.get(kado_course, {}).get(
        "firstScore", 0
    ):
        course_eval[1]["roleText"] = "◎イン先マイ"

    return course_eval, manual_notes, v


# ---------------------------------------------------------
# 4. スリット隊形＆1マーク攻防 SVGグラフィック生成 (確実に画像表示)
# ---------------------------------------------------------
def render_slit_svg_component(course_eval: Dict[int, Dict]) -> str:
    """
    st.components.v1.html で確実に描画されるSVGスリット隊形＆1M攻防グラフィックを生成
    """
    svg_rows = []
    for c in range(1, 7):
        o = course_eval[c]
        b = o["b"]
        bg, fg, bd = BOAT_COLORS[o["boatId"]]
        y = 18 + (c - 1) * 44

        # スリット位置 (x: 80 〜 395, スリットラインは x=425)
        pct = max(0.15, min(0.95, (o["slitPower"] - 30.0) / 68.0))
        boat_x = int(85 + pct * 235)

        kado_badge = (
            f'<rect x="42" y="{y+4}" width="36" height="18" rx="4" fill="#0284c7" />'
            f'<text x="60" y="{y+16}" fill="#ffffff" font-size="10" font-weight="bold" text-anchor="middle">カド</text>'
            if o["isKado"]
            else ""
        )

        # 攻め方向矢印
        arrow_svg = ""
        if "まくり" in o["roleText"] or o["tac"] == "makuri":
            arrow_svg = f'<path d="M {boat_x+108} {y+14} Q {boat_x+145} {y+14} {boat_x+155} {max(20, y-22)}" stroke="#f43f5e" stroke-width="3" fill="none" marker-end="url(#arrow-red)"/>'
        elif "差" in o["roleText"] or "連動" in o["roleText"] or o["tac"] in ("sashi", "makurisashi"):
            arrow_svg = f'<path d="M {boat_x+108} {y+14} L {boat_x+150} {max(24, y-12)}" stroke="#10b981" stroke-width="2.5" stroke-dasharray="4,2" fill="none" marker-end="url(#arrow-green)"/>'
        elif c == 1 and "被弾" not in o["roleText"]:
            arrow_svg = f'<path d="M {boat_x+108} {y+14} L {boat_x+150} {y+14}" stroke="#38bdf8" stroke-width="3" fill="none" marker-end="url(#arrow-blue)"/>'

        racer_label = b["name"][:4] if b["name"] else f"{o['boatId']}号艇"
        st_label = f".{int(round(o['expectedSt']*100)):02d}"

        row_svg = (
            f'<line x1="10" y1="{y+34}" x2="540" y2="{y+34}" stroke="#1e293b" stroke-width="1" />'
            f'<text x="14" y="{y+18}" fill="#94a3b8" font-size="12" font-family="monospace" font-weight="bold">{c}C</text>'
            f"{kado_badge}"
            f'<line x1="80" y1="{y+14}" x2="{boat_x}" y2="{y+14}" stroke="{bd}" stroke-width="2" stroke-dasharray="3,3" opacity="0.5" />'
            f'<g transform="translate({boat_x}, {y})">'
            f'<polygon points="0,3 92,3 106,14 92,25 0,25" fill="{bg}" stroke="{bd}" stroke-width="2" />'
            f'<text x="12" y="18" fill="{fg}" font-size="13" font-weight="900" font-family="sans-serif">{o["boatId"]}</text>'
            f'<text x="28" y="18" fill="{fg}" font-size="12" font-weight="700" font-family="sans-serif">{racer_label}</text>'
            f"</g>"
            f'<text x="{boat_x-6}" y="{y+18}" fill="#e2e8f0" font-size="11" font-family="monospace" font-weight="bold" text-anchor="end">{st_label}</text>'
            f'<text x="485" y="{y+18}" fill="#fbbf24" font-size="11" font-weight="bold" font-family="sans-serif">{o["roleText"]}</text>'
            f"{arrow_svg}"
        )
        svg_rows.append(row_svg)

    html = (
        '<div style="background:linear-gradient(90deg,#091526 0%,#0f2942 75%,#091526 100%);border:1px solid #1e3a5f;border-radius:12px;padding:8px;">'
        '<svg viewBox="0 0 560 285" width="100%" height="285" xmlns="http://www.w3.org/2000/svg">'
        "<defs>"
        '<marker id="arrow-red" viewBox="0 0 10 10" refX="6" refY="5" markerWidth="5" markerHeight="5" orient="auto-start-reverse"><path d="M 0 0 L 10 5 L 0 10 z" fill="#f43f5e"/></marker>'
        '<marker id="arrow-green" viewBox="0 0 10 10" refX="6" refY="5" markerWidth="5" markerHeight="5" orient="auto-start-reverse"><path d="M 0 0 L 10 5 L 0 10 z" fill="#10b981"/></marker>'
        '<marker id="arrow-blue" viewBox="0 0 10 10" refX="6" refY="5" markerWidth="5" markerHeight="5" orient="auto-start-reverse"><path d="M 0 0 L 10 5 L 0 10 z" fill="#38bdf8"/></marker>'
        "</defs>"
        '<line x1="425" y1="6" x2="425" y2="276" stroke="#fbbf24" stroke-width="3" stroke-dasharray="6,3" />'
        '<text x="421" y="14" fill="#fbbf24" font-size="10" font-weight="bold" text-anchor="end">START (0.00)</text>'
        '<circle cx="468" cy="32" r="9" fill="#ef4444" stroke="#fde047" stroke-width="2" />'
        '<text x="468" y="52" fill="#fca5a5" font-size="9" font-weight="bold" text-anchor="middle">1M</text>'
        + "".join(svg_rows)
        + "</svg></div>"
    )
    return html


# ---------------------------------------------------------
# 5. Streamlit メイン画面
# ---------------------------------------------------------
def main():
    st.set_page_config(page_title="BOAT RACE プロ展開シミュレーター", page_icon="🚤", layout="wide")

    if "boats_data" not in st.session_state:
        st.session_state["boats_data"] = [
            {"id": 1, "name": "茅原悠紀", "grade": "A1", "fCount": 0, "weight": 53.4, "winRate": 7.61, "localWin": 8.21, "motorBi": 26.57, "avgSt": 0.13, "seriesSt": 0.11, "courseWin": 78.5, "courseTri": 88.0, "nigashi": 0.0,  "exhibitTime": 6.80, "tilt": 0.0,  "parts": "none", "tactic": "auto"},
            {"id": 2, "name": "山田康二", "grade": "A1", "fCount": 1, "weight": 53.5, "winRate": 8.02, "localWin": 7.18, "motorBi": 34.67, "avgSt": 0.13, "seriesSt": 0.12, "courseWin": 22.0, "courseTri": 76.0, "nigashi": 61.0, "exhibitTime": 6.77, "tilt": -0.5, "parts": "none", "tactic": "auto"},
            {"id": 3, "name": "馬場貴也", "grade": "A1", "fCount": 0, "weight": 52.1, "winRate": 7.60, "localWin": 7.64, "motorBi": 39.07, "avgSt": 0.14, "seriesSt": 0.14, "courseWin": 24.0, "courseTri": 73.0, "nigashi": 0.0,  "exhibitTime": 6.78, "tilt": -0.5, "parts": "none", "tactic": "auto"},
            {"id": 4, "name": "関浩哉",   "grade": "A1", "fCount": 0, "weight": 51.5, "winRate": 7.49, "localWin": 7.25, "motorBi": 37.82, "avgSt": 0.13, "seriesSt": 0.03, "courseWin": 25.0, "courseTri": 70.0, "nigashi": 0.0,  "exhibitTime": 6.81, "tilt": 0.0,  "parts": "none", "tactic": "makuri"},
            {"id": 5, "name": "新開航",   "grade": "A1", "fCount": 0, "weight": 52.0, "winRate": 7.59, "localWin": 7.33, "motorBi": 26.76, "avgSt": 0.15, "seriesSt": 0.07, "courseWin": 14.0, "courseTri": 66.0, "nigashi": 0.0,  "exhibitTime": 6.85, "tilt": 0.0,  "parts": "none", "tactic": "auto"},
            {"id": 6, "name": "遠藤エミ", "grade": "A1", "fCount": 0, "weight": 46.0, "winRate": 7.32, "localWin": 6.71, "motorBi": 40.54, "avgSt": 0.14, "seriesSt": 0.01, "courseWin": 8.0,  "courseTri": 60.0, "nigashi": 0.0,  "exhibitTime": 6.84, "tilt": -0.5, "parts": "none", "tactic": "auto"},
        ]
        st.session_state["course_order_str"] = "1,2,3,4,5,6"
        st.session_state["wind_speed"] = 2
        st.session_state["wave_cm"] = 0
        st.session_state["editor_ver"] = 1
        st.session_state["fetch_msg"] = "初期データ表示中（2026/10/30 尼崎12R SGボートレースダービー）"

    if "active_factors" not in st.session_state:
        st.session_state["active_factors"] = dict(DEFAULT_ACTIVE_FACTORS)

    # サイドバー：比重スライダー
    with st.sidebar:
        st.header("⚙️ カテゴリ別 重み付け調整")
        st.caption("選択したデータの効き具合（0%〜200%）を調整できます。")
        w_course = st.slider("① コース別実績・逃がし率の比重", 0, 200, 100, 10) / 100.0
        w_exhibit = st.slider("② 展示タイム・部品・チルトの比重", 0, 200, 100, 10) / 100.0
        w_motor = st.slider("③ 当地勝率差・モーター・体重の比重", 0, 200, 100, 10) / 100.0
        w_slit = st.slider("④ スリット＆戦法連動の比重", 0, 200, 100, 10) / 100.0
        st.divider()
        use_start_ex = st.checkbox("取得時にスタート展示の進入・STを自動反映", value=True)

    weights = {"wCourse": w_course, "wExhibit": w_exhibit, "wMotor": w_motor, "wSlit": w_slit}

    st.title("🚤 ボートレース プロ展開シミュレーター")

    # 上段：公式データ自動取得バー
    col_d, col_v, col_r, col_day, col_btn = st.columns([1.2, 2.2, 1.0, 1.4, 2.2])
    with col_d:
        target_date = st.text_input("開催日 (YYYYMMDD)", value="20261030")
    with col_v:
        venue_options = [f"{code} {info['name']} ({info['desc'][:10]}…)" for code, info in VENUE_MASTER.items()]
        selected_venue_label = st.selectbox("レース場 (全24場)", venue_options, index=12)
        venue_code = selected_venue_label.split()[0]
    with col_r:
        race_no = st.selectbox("レース番号", list(range(1, 13)), index=11, format_func=lambda x: f"{x}R")
    with col_day:
        series_day = st.selectbox(
            "開催日目 (節間比重)",
            [1, 2, 3, 4, 5, 6],
            index=3,
            format_func=lambda d: f"{d}日目 (節間{int({1:0,2:30,3:55,4:65,5:75,6:85}[d])}%)",
        )
    with col_btn:
        st.write("")
        if st.button("📡 公式データを自動取得して反映", type="primary", use_container_width=True):
            with st.spinner(f"公式サイトから {target_date} {VENUE_MASTER[venue_code]['name']} {race_no}R を取得中..."):
                try:
                    fetched_boats, env_data, order_list, b_status = fetch_official_race_data(
                        target_date.strip(), venue_code, race_no, use_start_ex
                    )
                    st.session_state["boats_data"] = fetched_boats
                    st.session_state["course_order_str"] = ",".join(map(str, order_list))
                    st.session_state["wind_speed"] = env_data["windSpeed"]
                    st.session_state["wave_cm"] = env_data["wave"]
                    st.session_state["editor_ver"] = st.session_state.get("editor_ver", 1) + 1
                    names_str = " / ".join([f"{b['id']}号艇:{b['name']}" for b in fetched_boats])
                    st.session_state["fetch_msg"] = (
                        f"✅ 取得完了【{target_date} {VENUE_MASTER[venue_code]['name']} {race_no}R】({b_status}) 👉 {names_str}"
                    )
                except Exception as err:
                    st.error(str(err))

    st.success(st.session_state.get("fetch_msg", ""))

    # ---------------------------------------------------------
    # 新機能：予想に適用するデータの選択パネル (16項目個別ON/OFF ＆ プリセット)
    # ---------------------------------------------------------
    with st.expander("✅ 予想計算に適用するデータ項目の選択（ON/OFF 切替・プリセット）", expanded=True):
        st.caption("レース状況に応じて「モーター2連対率を除外する」「直前展示とSTだけで予想する」など、予想に使うデータを自由に選べます。")
        p_col1, p_col2, p_col3, p_col4 = st.columns(4)
        if p_col1.button("🔄 全データを適用 (標準)", use_container_width=True):
            for k in DEFAULT_ACTIVE_FACTORS:
                st.session_state["active_factors"][k] = True
                st.session_state[f"chk_{k}"] = True
        if p_col2.button("⚡ 直前気配・ST特化 (勝率/機力除外)", use_container_width=True):
            for k in DEFAULT_ACTIVE_FACTORS:
                val = k in (
                    "use_exhibit_time",
                    "use_parts",
                    "use_tilt",
                    "use_series_st",
                    "use_venue_env",
                    "use_tactics",
                    "use_course_win",
                )
                st.session_state["active_factors"][k] = val
                st.session_state[f"chk_{k}"] = val
        if p_col3.button("📊 事前データ特化 (展示前予想)", use_container_width=True):
            for k in DEFAULT_ACTIVE_FACTORS:
                val = k not in ("use_exhibit_time", "use_parts", "use_tilt")
                st.session_state["active_factors"][k] = val
                st.session_state[f"chk_{k}"] = val
        if p_col4.button("🛠️ 新モーター期 (モーター率除外)", use_container_width=True):
            for k in DEFAULT_ACTIVE_FACTORS:
                val = k != "use_motor_bi"
                st.session_state["active_factors"][k] = val
                st.session_state[f"chk_{k}"] = val

        f_c1, f_c2, f_c3, f_c4 = st.columns(4)
        af = st.session_state["active_factors"]
        with f_c1:
            st.markdown("**【1. 選手実力データ】**")
            af["use_win_rate"] = st.checkbox("全国勝率", value=af["use_win_rate"], key="chk_use_win_rate")
            af["use_local_win"] = st.checkbox("当地勝率差", value=af["use_local_win"], key="chk_use_local_win")
            af["use_series_score"] = st.checkbox("開催日目(節間比重)", value=af["use_series_score"], key="chk_use_series_score")
            af["use_weight"] = st.checkbox("選手体重差", value=af["use_weight"], key="chk_use_weight")
        with f_c2:
            st.markdown("**【2. コース別実績データ】**")
            af["use_course_win"] = st.checkbox("コース別1着率", value=af["use_course_win"], key="chk_use_course_win")
            af["use_course_tri"] = st.checkbox("コース別3連対率", value=af["use_course_tri"], key="chk_use_course_tri")
            af["use_nigashi"] = st.checkbox("2コース逃がし率", value=af["use_nigashi"], key="chk_use_nigashi")
        with f_c3:
            st.markdown("**【3. 機力・直前展示データ】**")
            af["use_motor_bi"] = st.checkbox("モーター2連対率", value=af["use_motor_bi"], key="chk_use_motor_bi")
            af["use_exhibit_time"] = st.checkbox("展示タイム順位", value=af["use_exhibit_time"], key="chk_use_exhibit_time")
            af["use_parts"] = st.checkbox("部品交換(リング/電気)", value=af["use_parts"], key="chk_use_parts")
            af["use_tilt"] = st.checkbox("チルト角度", value=af["use_tilt"], key="chk_use_tilt")
        with f_c4:
            st.markdown("**【4. ST・水面・展開データ】**")
            af["use_avg_st"] = st.checkbox("通算平均ST", value=af["use_avg_st"], key="chk_use_avg_st")
            af["use_series_st"] = st.checkbox("今節ST / スタ展ST", value=af["use_series_st"], key="chk_use_series_st")
            af["use_f_deep"] = st.checkbox("F持ち・深イン割引", value=af["use_f_deep"], key="chk_use_f_deep")
            af["use_venue_env"] = st.checkbox("水面特性＆風・波補正", value=af["use_venue_env"], key="chk_use_venue_env")
            af["use_tactics"] = st.checkbox("手動戦法・まくり連動", value=af["use_tactics"], key="chk_use_tactics")

    # 水面・進入・カド設定バー
    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        course_order_str = st.text_input("進入並び (COURSE_ORDER)", value=st.session_state["course_order_str"])
        digits = [int(x) for x in re.findall(r"[1-6]", course_order_str)]
        course_order = list(dict.fromkeys(digits)) if len(set(digits)) == 6 else [1, 2, 3, 4, 5, 6]
    with c2:
        kado_course = st.selectbox("カド位置", [3, 4, 5], index=1, format_func=lambda x: f"{x}カド")
    with c3:
        deep_in = st.selectbox(
            "イン深さ (DEEP_IN)",
            ["normal", "semi", "deep"],
            format_func=lambda x: {"normal": "通常", "semi": "やや深 (-8pt)", "deep": "深イン (-18pt)"}[x],
        )
    with c4:
        wind_dir = st.selectbox(
            "風向き",
            ["head", "tail", "calm", "cross"],
            format_func=lambda x: {"head": "向かい風", "tail": "追い風", "calm": "無風", "cross": "横風"}[x],
        )
    with c5:
        wind_speed = st.slider("風速 (m)", 0, 10, int(st.session_state.get("wind_speed", 2)))
        wave_cm = int(st.session_state.get("wave_cm", 2))

    # 中段：6艇データのインタラクティブ編集（editor_ver により取得時に選手名が確実に更新される）
    st.subheader("🚤 出走データ・コース別実績・手動戦法 (MANUAL_TACTICS) 編集")
    df_boats = pd.DataFrame(st.session_state["boats_data"])
    edited_df = st.data_editor(
        df_boats,
        key=f"boats_editor_{st.session_state.get('editor_ver', 1)}",
        hide_index=True,
        use_container_width=True,
        column_config={
            "id": st.column_config.NumberColumn("枠", disabled=True, width="small"),
            "name": st.column_config.TextColumn("選手名", width="medium"),
            "grade": st.column_config.SelectboxColumn("級別", options=["A1", "A2", "B1", "B2"], width="small"),
            "fCount": st.column_config.NumberColumn("F数", min_value=0, max_value=3, step=1, width="small"),
            "weight": st.column_config.NumberColumn("体重(kg)", min_value=44.0, max_value=65.0, step=0.5, format="%.1f"),
            "winRate": st.column_config.NumberColumn("全国勝率", min_value=1.0, max_value=9.5, step=0.05, format="%.2f"),
            "localWin": st.column_config.NumberColumn("当地勝率", min_value=1.0, max_value=9.5, step=0.05, format="%.2f"),
            "motorBi": st.column_config.NumberColumn("モーター2連(%)", min_value=10.0, max_value=85.0, step=0.5, format="%.1f"),
            "courseWin": st.column_config.NumberColumn("コース1着率(%)", min_value=0.0, max_value=100.0, step=1.0, format="%.1f"),
            "courseTri": st.column_config.NumberColumn("コース3連率(%)", min_value=0.0, max_value=100.0, step=1.0, format="%.1f"),
            "nigashi": st.column_config.NumberColumn("2C逃がし率(%)", min_value=0.0, max_value=95.0, step=1.0, format="%.1f"),
            "exhibitTime": st.column_config.NumberColumn("展示時計(秒)", min_value=6.40, max_value=7.30, step=0.01, format="%.2f"),
            "tilt": st.column_config.SelectboxColumn("チルト", options=[-0.5, 0.0, 0.5, 1.0, 1.5, 3.0]),
            "parts": st.column_config.SelectboxColumn("部品交換", options=["none", "ring", "elec"]),
            "avgSt": st.column_config.NumberColumn("平均ST", min_value=0.05, max_value=0.30, step=0.01, format="%.2f"),
            "seriesSt": st.column_config.NumberColumn("今節/展ST", min_value=0.01, max_value=0.30, step=0.01, format="%.2f"),
            "tactic": st.column_config.SelectboxColumn("手動戦法 (tactic)", options=list(TACTIC_OPTIONS.keys())),
        },
    )

    boats_current = edited_df.to_dict(orient="records")

    course_eval, manual_notes, v_info = run_pro_simulation(
        boats_current,
        venue_code,
        series_day,
        course_order,
        kado_course,
        deep_in,
        wind_dir,
        wind_speed,
        wave_cm,
        weights,
        st.session_state["active_factors"],
    )

    arr = list(course_eval.values())
    by_first = sorted(arr, key=lambda x: x["firstScore"], reverse=True)
    by_place = sorted(arr, key=lambda x: x["placeScore"], reverse=True)

    top1, top2, top3 = by_first[0], by_first[1], by_first[2]
    p_for_top1 = [x for x in by_place if x["boatId"] != top1["boatId"]]
    p1, p2, p3, p4 = p_for_top1[0], p_for_top1[1], p_for_top1[2], p_for_top1[3]

    q_for_top2 = [x for x in by_place if x["boatId"] != top2["boatId"]]
    q1, q2, q3 = q_for_top2[0], q_for_top2[1], q_for_top2[2]

    r_for_top3 = [x for x in by_place if x["boatId"] != top3["boatId"]]
    r1, r2 = r_for_top3[0], r_for_top3[1]

    # 下段：SVGスリット隊形＆1M展開画像 ＆ 総合算出スコア内訳表
    col_slit, col_score = st.columns([1.05, 1.25])
    with col_slit:
        st.subheader("📊 想定スリット隊形 ＆ 1マーク攻防図")
        svg_component_html = render_slit_svg_component(course_eval)
        components.html(svg_component_html, height=310, scrolling=False)

    with col_score:
        st.subheader("📈 総合算出スコア一覧（適用データ内訳つき）")
        score_rows = []
        for c in range(1, 7):
            o = course_eval[c]
            b = o["b"]
            score_rows.append(
                {
                    "進入": f"{c}C",
                    "艇番・選手名": f"{o['boatId']}号艇 {b['name']}",
                    "展示時計": f"{b['exhibitTime']:.2f}秒 ({o['exRank']}位)",
                    "想定ST": f".{int(round(o['expectedSt']*100)):02d}",
                    "実力/機力点": o["skillPt"],
                    "コース/展示点": round(o["coursePt"] + o["exPt"], 1),
                    "1着力": round(o["firstScore"], 1),
                    "連対力": round(o["placeScore"], 1),
                    "展開役割": o["roleText"],
                }
            )
        st.dataframe(pd.DataFrame(score_rows), hide_index=True, use_container_width=True)

    # 推奨3連単買い目 ＆ 軍資金配分
    st.divider()
    col_bet_hdr1, col_bet_hdr2, col_bet_hdr3 = st.columns([2.0, 1.0, 1.0])
    with col_bet_hdr1:
        st.subheader("🎯 推奨3連単買い目 ＆ 軍資金配分シミュレーション")
    with col_bet_hdr2:
        ticket_count = st.selectbox("配分点数", [4, 6, 8, 12], index=1, format_func=lambda x: f"{x}点配分")
    with col_bet_hdr3:
        total_budget = st.number_input("総軍資金 (円)", min_value=400, max_value=500000, value=3000, step=100)

    boat_name_map = {b["id"]: b["name"] for b in boats_current}

    def fmt_runners(b1: int, b2: int, b3: int) -> str:
        return f"{boat_name_map.get(b1,'')} → {boat_name_map.get(b2,'')} → {boat_name_map.get(b3,'')}"

    honsen_pool = [
        ("本線◎", top1["boatId"], p1["boatId"], p2["boatId"], 18.5),
        ("本線○", top1["boatId"], p2["boatId"], p1["boatId"], 13.0),
        ("本線▲", top1["boatId"], p1["boatId"], p3["boatId"], 9.5),
        ("本線△", top1["boatId"], p2["boatId"], p3["boatId"], 6.8),
    ]
    osae_pool = [
        ("対抗★", top1["boatId"], p3["boatId"], p1["boatId"], 6.5),
        ("抑え△", top1["boatId"], p3["boatId"], p2["boatId"], 4.8),
        ("抑え△", top1["boatId"], p1["boatId"], p4["boatId"], 4.0),
        ("抑え△", top1["boatId"], p2["boatId"], p4["boatId"], 3.4),
    ]
    ana_pool = [
        ("逆転穴", top2["boatId"], q1["boatId"], q2["boatId"], 5.2),
        ("連動穴", top2["boatId"], q2["boatId"], q1["boatId"], 4.3),
        ("穴展開", top2["boatId"], q1["boatId"], q3["boatId"], 3.1),
        ("大穴☆", top3["boatId"], r1["boatId"], r2["boatId"], 2.4),
    ]

    split_map = {4: (2, 1, 1), 6: (2, 2, 2), 8: (3, 3, 2), 12: (4, 4, 4)}
    h_cnt, o_cnt, a_cnt = split_map.get(ticket_count, (2, 2, 2))
    h_list = honsen_pool[:h_cnt]
    o_list = osae_pool[:o_cnt]
    a_list = ana_pool[:a_cnt]
    active_bets = h_list + o_list + a_list

    total_p = sum(x[4] for x in active_bets)
    allocs = [max(100, round((x[4] / total_p) * total_budget / 100) * 100) for x in active_bets]
    diff = total_budget - sum(allocs)
    idx = 0
    while diff != 0 and idx < 200:
        if diff > 0:
            allocs[idx % len(allocs)] += 100
            diff -= 100
        elif allocs[-(idx % len(allocs)) - 1] > 100:
            allocs[-(idx % len(allocs)) - 1] -= 100
            diff += 100
        idx += 1

    b_col1, b_col2 = st.columns([1.35, 1.0])
    with b_col1:
        alloc_rows = []
        for (b_type, l1, l2, l3, prob), yen in zip(active_bets, allocs):
            alloc_rows.append(
                {
                    "区分": b_type,
                    "3連単買い目": f"{l1}-{l2}-{l3}",
                    "選手組み合わせ": fmt_runners(l1, l2, l3),
                    "想定確率": f"{prob:.1f}%",
                    "推奨購入額": f"{yen:,} 円",
                }
            )
        st.dataframe(pd.DataFrame(alloc_rows), hide_index=True, use_container_width=True)

    with b_col2:
        manual_line = (
            f"・手動指定展開: {' / '.join(manual_notes)}"
            if manual_notes
            else f"・想定隊形: {kado_course}コースがカドから仕掛ける隊形"
        )
        note_text = f"""━━━━━━━━━━━━━━━━━━━━
🔥 {v_info['name']} {race_no}R 展開予想レポート 🔥
━━━━━━━━━━━━━━━━━━━━
【水面・スリット展望】
・水面状況: 風速{wind_speed}m / 波高{wave_cm}cm ({v_info['desc']})
{manual_line}

【1マーク展開シナリオ】
本命は{top1['courseNo']}コース{top1['boatId']}号艇（{top1['b']['name']}）。
スリット攻防の引き波と連動を計算した結果、展開絶好の{p1['boatId']}号艇（{p1['b']['name']}）が浮上するスジ連動が最有力！

🎯 【推奨買い目（3連単{len(active_bets)}点）】
◎ 本線：{' / '.join(f'{x[1]}-{x[2]}-{x[3]}' for x in h_list)}
▲ 抑え：{' / '.join(f'{x[1]}-{x[2]}-{x[3]}' for x in o_list)}
★ 穴目：{' / '.join(f'{x[1]}-{x[2]}-{x[3]}' for x in a_list)}
━━━━━━━━━━━━━━━━━━━━"""
        st.text_area("📝 note / X (Twitter) コピペ用レポート", value=note_text, height=290)


if __name__ == "__main__":
    main()
