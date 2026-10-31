# -*- coding: utf-8 -*-
"""
🚤 ボートレース プロ展開シミュレーター (Streamlit Webアプリ完全版・自動ライブラリ導入対応)
========================================================================================
【特徴】
1. Streamlit Cloud上で requirements.txt が読み込まれなかった場合でも、自動で /tmp に
   beautifulsoup4 と requests をインストールして起動する自己修復機能付きです。
2. Pythonサーバー側でBOAT RACE公式サイト(出走表 racelist / 直前情報 beforeinfo)と直接通信するため、
   ブラウザのCORS制限が一切なく、ボタン1つで全24場・全12Rのデータを100%自動取得＆即時反映します。
3. 5段階プロ展開計算エンジン・重み付けスライダー・配分点数(4点/6点/8点/12点)・軍資金配分・
   note / X (Twitter) そのままコピペ用レポート出力をすべて1画面に統合しています。
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
    1: ("#ffffff", "#0f172a", "#cbd5e1"),
    2: ("#1e293b", "#ffffff", "#64748b"),
    3: ("#ef4444", "#ffffff", "#fca5a5"),
    4: ("#3b82f6", "#ffffff", "#93c5fd"),
    5: ("#eab308", "#0f172a", "#fde047"),
    6: ("#22c55e", "#ffffff", "#86efac"),
}


# ---------------------------------------------------------
# 2. 公式データ自動スクレイピング関数 (CORS制限なし・列ズレ防止済)
# ---------------------------------------------------------
@st.cache_data(ttl=120, show_spinner=False)
def get_active_venues(target_date: str) -> List[str]:
    """指定日に開催中のレース場コード一覧を公式サイトから取得"""
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/122.0.0.0 Safari/537.36"}
    url = f"https://www.boatrace.jp/owpc/pc/race/index?hd={target_date}"
    try:
        r = requests.get(url, headers=headers, timeout=10)
        r.encoding = "utf-8"
        codes = sorted(set(re.findall(r"jcd=(\d{2})", r.text)))
        return [c for c in codes if c in VENUE_MASTER]
    except Exception:
        return []


def fetch_official_race_data(
    target_date: str, venue_code: str, race_no: int, use_start_ex: bool = True
) -> Tuple[List[Dict], Dict, List[int], str]:
    """
    BOAT RACE公式の『出走表(racelist)』と『直前情報(beforeinfo)』を厳密にスクレイピング。
    ・td.is-lineH2 のセル単位抽出で勝率とモーター2連対率の列ズレを防止
    ・beforeinfo の1行目セル(tds[4]=展示, tds[5]=チルト)指定で調整重量(0.0)との混同を防止
    """
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/122.0.0.0 Safari/537.36"}
    racelist_url = f"https://www.boatrace.jp/owpc/pc/race/racelist?rno={race_no}&jcd={venue_code}&hd={target_date}"
    beforeinfo_url = f"https://www.boatrace.jp/owpc/pc/race/beforeinfo?rno={race_no}&jcd={venue_code}&hd={target_date}"

    res_list = requests.get(racelist_url, headers=headers, timeout=10)
    res_list.encoding = "utf-8"
    soup_list = BeautifulSoup(res_list.text, "html.parser")

    tbodies = [
        tb
        for tb in soup_list.select("div.table1 table tbody.is-fs12")
        if tb.select_one("div.is-fs18, a[href*='toban=']")
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
        name_tag = tbody.select_one("div.is-fs18 a, a[href*='profile?toban=']")
        name = re.sub(r"[\s\u3000]+", "", name_tag.get_text(strip=True)) if name_tag else f"{boat_no}号艇"

        toban_m = re.search(r"(\d{4})\s*/\s*(A1|A2|B1|B2)", full_text)
        grade = toban_m.group(2) if toban_m else "B1"

        f_m = re.search(r"F([0-3])", full_text)
        f_count = int(f_m.group(1)) if f_m else 0

        w_m = re.search(r"(\d{2}\.\d)kg", full_text)
        weight = float(w_m.group(1)) if w_m else 52.0

        # td.is-lineH2 のセル単位で厳密に抽出
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

        # 今節ST (.08, .15 などのセルのみ抽出)
        series_sts = []
        for td in tbody.find_all("td"):
            t_str = td.get_text(strip=True)
            if re.fullmatch(r"F?\.\d{2}", t_str):
                series_sts.append(float("0" + t_str.replace("F", "")))
        series_st = round(sum(series_sts) / len(series_sts), 2) if series_sts else avg_st

        # 選手の勝率・2連率・3連率からコース別1着率・3連対率・2C逃がし率を初期推定
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
# 3. 5段階プロ展開計算エンジン
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
    rules: Dict[str, bool],
) -> Tuple[Dict[int, Dict], List[str], Dict]:
    v = VENUE_MASTER.get(venue_code, VENUE_MASTER["13"])
    w_series = {1: 0.0, 2: 0.30, 3: 0.55, 4: 0.65, 5: 0.75, 6: 0.85}.get(series_day, 0.5)
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
        tac = b.get("tactic", "auto")

        base_skill = (
            (b["winRate"] * 8.5)
            + ((b["localWin"] - b["winRate"]) * 14.0 * weights["wMotor"])
            + (b["motorBi"] * 0.65 * weights["wMotor"])
        )
        raw_series = min(95, max(45, b["winRate"] * 11))
        adj_series = 78 if (b["parts"] == "ring" and raw_series < 75) else raw_series
        blended = (base_skill * w_base) + (adj_series * w_series)

        weight_bonus = (52.0 - b["weight"]) * 3.2 * weights["wMotor"]
        parts_bonus = (5 if b["parts"] == "ring" else (4 if b["parts"] == "elec" else 0)) * weights["wExhibit"]
        ex_r = ex_ranks[b["id"]]
        raw_ex_bonus = 8 if ex_r == 1 else (4 if ex_r == 2 else (-6 if ex_r == 5 else 0))
        ex_bonus = (raw_ex_bonus * weights["wExhibit"]) if rules["exhibitTop"] else 0

        base_st = (b["avgSt"] * w_base) + (b["seriesSt"] * w_series)
        if rules["fHolder"]:
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

        slit_power = 50 + (0.17 - base_st) * 380 + (b["tilt"] + 0.5) * 8
        if is_dash:
            slit_power += 6
        if is_kado:
            slit_power += 8

        first_score = blended + weight_bonus + parts_bonus + ex_bonus + (b["courseWin"] * 0.45 * weights["wCourse"])
        place_score = blended + weight_bonus + parts_bonus + ex_bonus + (b["courseTri"] * 0.55 * weights["wCourse"])

        course_eval[c_no] = {
            "courseNo": c_no,
            "boatId": boat_id,
            "b": b,
            "exRank": ex_r,
            "isDash": is_dash,
            "isKado": is_kado,
            "expectedSt": max(0.05, min(0.28, base_st)),
            "slitPower": slit_power,
            "firstScore": first_score,
            "placeScore": place_score,
            "roleText": "標準",
            "tac": tac,
        }

    course_eval[1]["firstScore"] += 28 + v["inMod"]
    if deep_in == "semi":
        course_eval[1]["firstScore"] -= 8
    elif deep_in == "deep":
        course_eval[1]["firstScore"] -= 18
    if rules["nigashiLink"] and 2 in course_eval:
        course_eval[1]["firstScore"] += (course_eval[2]["b"]["nigashi"] - 52.0) * 0.45 * weights["wCourse"]

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
    for c in range(1, 7):
        obj = course_eval[c]
        tac = obj["tac"]
        if tac == "nige":
            obj["firstScore"] += 32 * weights["wSlit"]
            obj["roleText"] = "🎯指定:逃げ"
            manual_notes.append(f"{c}C({obj['boatId']}号艇)の【逃げ】を指定")
        elif tac == "makuri":
            obj["firstScore"] += (36 + v["makuriMod"]) * weights["wSlit"]
            obj["roleText"] = "🎯指定:まくり"
            manual_notes.append(f"{c}C({obj['boatId']}号艇)の【まくり】を指定 → 内枠被弾＆外枠連動")
            if rules["makuriFollow"]:
                for inner in range(1, c):
                    course_eval[inner]["firstScore"] -= (22 if inner == c - 1 else 16) * weights["wSlit"]
                    course_eval[inner]["placeScore"] -= (16 if inner == c - 1 else 10) * weights["wSlit"]
                    course_eval[inner]["roleText"] = "被弾・引き波"
                if c + 1 in course_eval:
                    course_eval[c + 1]["firstScore"] += (14 + v["sashiMod"]) * weights["wSlit"]
                    course_eval[c + 1]["placeScore"] += 28 * weights["wSlit"]
                    course_eval[c + 1]["roleText"] = "★まくり連動◎"
        elif tac == "makurisashi":
            obj["firstScore"] += (28 + v["sashiMod"]) * weights["wSlit"]
            obj["placeScore"] += 26 * weights["wSlit"]
            obj["roleText"] = "🎯指定:まくり差"
            manual_notes.append(f"{c}C({obj['boatId']}号艇)の【まくり差し】を指定")
            if c - 1 in course_eval and c > 2:
                course_eval[c - 1]["firstScore"] -= 12 * weights["wSlit"]
        elif tac == "sashi":
            obj["firstScore"] += (14 + v["sashiMod"]) * weights["wSlit"]
            obj["placeScore"] += 28 * weights["wSlit"]
            obj["roleText"] = "🎯指定:最内差し"
            manual_notes.append(f"{c}C({obj['boatId']}号艇)の【差し】を指定")
        elif tac == "sotomai":
            obj["firstScore"] += (16 + v["makuriMod"] * 0.5) * weights["wSlit"]
            obj["placeScore"] += 26 * weights["wSlit"]
            obj["roleText"] = "🎯指定:外マイ"
            manual_notes.append(f"{c}C({obj['boatId']}号艇)の【外マイ】を指定")
        elif tac == "hekomi":
            obj["firstScore"] -= 30 * weights["wSlit"]
            obj["placeScore"] -= 25 * weights["wSlit"]
            obj["roleText"] = "🎯指定:凹み壁崩壊"
            manual_notes.append(f"{c}C({obj['boatId']}号艇)の【壁崩壊】を指定")
            if c + 1 in course_eval:
                course_eval[c + 1]["firstScore"] += (24 + v["makuriMod"]) * weights["wSlit"]
                course_eval[c + 1]["placeScore"] += 18 * weights["wSlit"]
                course_eval[c + 1]["roleText"] = "★壁崩壊まくり"
        elif tac == "auto" and rules["autoSlit"] and c >= 3:
            if obj["slitPower"] - course_eval[c - 1]["slitPower"] >= 14:
                obj["firstScore"] += 15 + v["makuriMod"] * 0.6
                obj["placeScore"] += 12
                if obj["roleText"] == "標準":
                    obj["roleText"] = "⚡スリット覗く"

    if course_eval[1]["roleText"] == "標準" and course_eval[1]["firstScore"] >= course_eval.get(kado_course, {}).get(
        "firstScore", 0
    ):
        course_eval[1]["roleText"] = "◎イン先マイ"

    return course_eval, manual_notes, v


# ---------------------------------------------------------
# 4. Streamlit UI 構築
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
        st.session_state["fetch_msg"] = "初期データ表示中（2026/10/30 尼崎12R SGボートレースダービー）"

    with st.sidebar:
        st.header("⚙️ マイ予想ロジック調整")
        st.caption("各ファクターの比重（0%〜200%）と展開ルールをリアルタイム調整できます。")
        w_course = st.slider("① コース別1着/3連率・逃がし率", 0, 200, 100, 10) / 100.0
        w_exhibit = st.slider("② 展示タイム順位・部品・チルト", 0, 200, 100, 10) / 100.0
        w_motor = st.slider("③ 当地勝率差・モーター2連・体重", 0, 200, 100, 10) / 100.0
        w_slit = st.slider("④ スリット＆戦法連動ボーナス", 0, 200, 100, 10) / 100.0

        st.divider()
        st.subheader("📌 展開マイルール ON/OFF")
        rule_ex_top = st.checkbox("展示1番時計ボーナス (+8pt)", value=True)
        rule_nigashi = st.checkbox("2コース逃がし率連動", value=True)
        rule_f_holder = st.checkbox("F持ち・深インST割引補正", value=True)
        rule_makuri = st.checkbox("まくり内枠被弾＆外枠連動", value=True)
        rule_auto_slit = st.checkbox("AI自動スリット覗き判定", value=True)

        st.divider()
        use_start_ex = st.checkbox("取得時にスタート展示の進入・STを自動反映", value=True)

    weights = {"wCourse": w_course, "wExhibit": w_exhibit, "wMotor": w_motor, "wSlit": w_slit}
    rules = {
        "exhibitTop": rule_ex_top,
        "nigashiLink": rule_nigashi,
        "fHolder": rule_f_holder,
        "makuriFollow": rule_makuri,
        "autoSlit": rule_auto_slit,
    }

    st.title("🚤 ボートレース プロ展開シミュレーター (Streamlit Python連携版)")
    st.caption("Pythonサーバーから直接BOAT RACE公式データを取得するためCORS制限ゼロで全場・全Rを自動反映します。")

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
                    names_str = " / ".join([f"{b['id']}.{b['name']}" for b in fetched_boats])
                    st.session_state["fetch_msg"] = (
                        f"✅ 取得完了【{target_date} {VENUE_MASTER[venue_code]['name']} {race_no}R】({b_status})：{names_str}"
                    )
                except Exception as err:
                    st.error(str(err))

    st.info(st.session_state.get("fetch_msg", ""))

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

    st.subheader("🚤 出走データ・コース別実績・手動戦法 (MANUAL_TACTICS) 編集")
    st.caption("表の数値を直接書き換えるか、右端の『tactic (手動戦法)』を切り替えると即座に下の展開予想へ反映されます。")

    df_boats = pd.DataFrame(st.session_state["boats_data"])
    edited_df = st.data_editor(
        df_boats,
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
        rules,
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

    col_slit, col_score = st.columns([1.0, 1.2])
    with col_slit:
        st.subheader("📊 想定スリット隊形 (右端＝スリットライン)")
        slit_html = '<div style="background:#0f172a;padding:14px;border-radius:12px;border:1px solid #1e293b;">'
        for c in range(1, 7):
            o = course_eval[c]
            bg, fg, bd = BOAT_COLORS[o["boatId"]]
            pct = max(18, min(94, int(25 + (o["slitPower"] - 35) * 1.15)))
            kado_tag = (
                '<span style="background:#0284c7;color:#fff;font-size:10px;padding:1px 5px;border-radius:4px;margin-left:6px;">🔥カド</span>'
                if o["isKado"]
                else ""
            )
            slit_html += f"""
            <div style="display:flex;align-items:center;margin-bottom:8px;">
              <div style="width:70px;font-size:12px;color:#94a3b8;font-family:monospace;">{c}C {kado_tag}</div>
              <div style="flex:1;background:#1e293b;border-radius:6px;height:28px;position:relative;padding-right:10px;border-right:3px solid #fbbf24;">
                <div style="width:{pct}%;height:100%;display:flex;justify-content:flex-end;align-items:center;">
                  <span style="background:{bg};color:{fg};border:2px solid {bd};border-radius:5px;padding:1px 8px;font-weight:900;font-size:12px;">
                    {o['boatId']} {o['b']['name'][:3]} .{int(o['expectedSt']*100):02d}
                  </span>
                </div>
              </div>
            </div>
            """
        slit_html += "</div>"
        st.markdown(slit_html, unsafe_allow_html=True)

    with col_score:
        st.subheader("📈 総合算出スコア一覧 (firstScore / placeScore)")
        score_rows = []
        for c in range(1, 7):
            o = course_eval[c]
            b = o["b"]
            score_rows.append(
                {
                    "進入": f"{c}C",
                    "艇番": f"{o['boatId']}号艇",
                    "選手名": b["name"],
                    "展示時計": f"{b['exhibitTime']:.2f}秒 ({o['exRank']}位)",
                    "想定ST": f".{int(o['expectedSt']*100):02d}",
                    "1着力 (firstScore)": round(o["firstScore"], 1),
                    "連対力 (placeScore)": round(o["placeScore"], 1),
                    "展開役割": o["roleText"],
                }
            )
        st.dataframe(pd.DataFrame(score_rows), hide_index=True, use_container_width=True)

    st.divider()
    col_bet_hdr1, col_bet_hdr2, col_bet_hdr3 = st.columns([2.0, 1.0, 1.0])
    with col_bet_hdr1:
        st.subheader("🎯 推奨3連単買い目 ＆ 軍資金配分シミュレーション")
    with col_bet_hdr2:
        ticket_count = st.selectbox("配分点数", [4, 6, 8, 12], index=1, format_func=lambda x: f"{x}点配分")
    with col_bet_hdr3:
        total_budget = st.number_input("総軍資金 (円)", min_value=400, max_value=500000, value=3000, step=100)

    honsen_pool = [
        ("本線◎", f"{top1['boatId']}-{p1['boatId']}-{p2['boatId']}", 18.5),
        ("本線○", f"{top1['boatId']}-{p2['boatId']}-{p1['boatId']}", 13.0),
        ("本線▲", f"{top1['boatId']}-{p1['boatId']}-{p3['boatId']}", 9.5),
        ("本線△", f"{top1['boatId']}-{p2['boatId']}-{p3['boatId']}", 6.8),
    ]
    osae_pool = [
        ("対抗★", f"{top1['boatId']}-{p3['boatId']}-{p1['boatId']}", 6.5),
        ("抑え△", f"{top1['boatId']}-{p3['boatId']}-{p2['boatId']}", 4.8),
        ("抑え△", f"{top1['boatId']}-{p1['boatId']}-{p4['boatId']}", 4.0),
        ("抑え△", f"{top1['boatId']}-{p2['boatId']}-{p4['boatId']}", 3.4),
    ]
    ana_pool = [
        ("逆転穴", f"{top2['boatId']}-{q1['boatId']}-{q2['boatId']}", 5.2),
        ("連動穴", f"{top2['boatId']}-{q2['boatId']}-{q1['boatId']}", 4.3),
        ("穴展開", f"{top2['boatId']}-{q1['boatId']}-{q3['boatId']}", 3.1),
        ("大穴☆", f"{top3['boatId']}-{r1['boatId']}-{r2['boatId']}", 2.4),
    ]

    split_map = {4: (2, 1, 1), 6: (2, 2, 2), 8: (3, 3, 2), 12: (4, 4, 4)}
    h_cnt, o_cnt, a_cnt = split_map.get(ticket_count, (2, 2, 2))
    h_list = honsen_pool[:h_cnt]
    o_list = osae_pool[:o_cnt]
    a_list = ana_pool[:a_cnt]
    active_bets = h_list + o_list + a_list

    total_p = sum(x[2] for x in active_bets)
    allocs = [max(100, round((x[2] / total_p) * total_budget / 100) * 100) for x in active_bets]
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

    b_col1, b_col2 = st.columns([1.3, 1.0])
    with b_col1:
        alloc_rows = []
        for (b_type, code, prob), yen in zip(active_bets, allocs):
            alloc_rows.append(
                {
                    "区分": b_type,
                    "3連単買い目": code,
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
◎ 本線：{' / '.join(x[1] for x in h_list)}
▲ 抑え：{' / '.join(x[1] for x in o_list)}
★ 穴目：{' / '.join(x[1] for x in a_list)}
━━━━━━━━━━━━━━━━━━━━"""
        st.text_area("📝 note / X (Twitter) コピペ用レポート", value=note_text, height=290)


if __name__ == "__main__":
    main()
