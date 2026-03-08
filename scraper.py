#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HGVC Resale Scraper — timesharebrokersmls.com
검색 결과 테이블(400+ 매물)을 한 번에 파싱하고,
상위 매물의 상세 페이지(MF, 시즌)를 추가 수집합니다.
"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

import requests
from bs4 import BeautifulSoup
import json, re, time
from datetime import datetime

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

BASE       = "https://timesharebrokersmls.com"
SEARCH_URL = f"{BASE}/Search/N/hgv/N/gt/0/1/0/N/N/N/N/N/N/N/Results.html"

SESSION = requests.Session()
SESSION.headers.update(HEADERS)

# ── 리조트명 정규화 맵 ────────────────────────────────────────────────────────
RESORT_NORMALIZE = {
    "HGVCLUB AT HILTON HAWAIIAN VILLAGE":                    ("Lagoon Tower",     "Hawaii"),
    "GRAND WAIKIKIAN BY HILTON GRAND VACATIONS CLUB HGVC":   ("Grand Waikikian",  "Hawaii"),
    "GRAND WAIKIKIAN BY HILTON GRAND VACATIONS CLUB":        ("Grand Waikikian",  "Hawaii"),
    "KINGS LAND BY HILTON GRAND VACATIONS CLUB HGVC":        ("Kings Land",       "Hawaii"),
    "KINGS LAND BY HILTON GRAND VACATIONS CLUB":             ("Kings Land",       "Hawaii"),
    "Hokulani Waikiki by Hilton Grand Vacations Club HGVC":  ("Hokulani Waikiki", "Hawaii"),
    "HGVCLUB AT THE KALIA TOWER":                            ("Kalia Tower",      "Hawaii"),
    "HGVCLUB AT HILTON HAWAIIAN VILLAGE - LAGOON TOWER":     ("Lagoon Tower",     "Hawaii"),
    "HILTON GRAND VACATIONS AT ELARA":                       ("Elara",            "Las Vegas"),
    "HILTON GRAND VACATIONS CLUB AT THE ELARA":              ("Elara",            "Las Vegas"),
    "ELARA BY HILTON GRAND VACATIONS CLUB HGVC":             ("Elara",            "Las Vegas"),
    "ELARA A HILTON GRAND VACATIONS CLUB":                   ("Elara",            "Las Vegas"),
    "HILTON GRAND VACATIONS CLUB ON THE BOULEVARD":          ("Boulevard",        "Las Vegas"),
    "HILTON GRAND VACATIONS CLUB ON THE LAS VEGAS STRIP":    ("Boulevard",        "Las Vegas"),
    "HILTON GRAND VACATIONS CLUB ON THE BLVD":               ("Boulevard",        "Las Vegas"),
    "HILTON GRAND VACATIONS AT THE FLAMINGO":                ("Flamingo",         "Las Vegas"),
    "HILTON GRAND VACATIONS CLUB AT THE FLAMINGO":           ("Flamingo",         "Las Vegas"),
    "HILTON GRAND VACATIONS CLUB LAS VEGAS":                 ("Paradise",         "Las Vegas"),
    "HILTON GRAND VACATIONS CLUB ON PARADISE":               ("Paradise",         "Las Vegas"),
    "PARC SOLEIL BY HILTON GRAND VACATIONS CLUB HGVC":       ("Parc Soleil",      "Orlando"),
    "HILTON GRAND VACATIONS CLUB AT PARC SOLEIL":            ("Parc Soleil",      "Orlando"),
    "HILTON GRAND VACATIONS CLUB AT TUSCANY VILLAGE":        ("Tuscany Village",  "Orlando"),
    "HILTON GRAND VACATIONS CLUB AT SEAWORLD":               ("SeaWorld",         "Orlando"),
    "HILTON GRAND VACATIONS CLUB AT SEA WORLD":              ("SeaWorld",         "Orlando"),
    "OCEAN ENCLAVE BY HILTON GRAND VACATIONS CLUB":          ("Ocean Enclave",    "Hawaii"),
    "OCEAN TOWER BY HILTON GRAND VACATIONS CLUB":            ("Ocean Tower",      "Hawaii"),
    "GRAND ISLANDER BY HILTON GRAND VACATIONS CLUB":         ("Grand Islander",   "Hawaii"),
    "KOHALA SUITES BY HILTON GRAND VACATIONS CLUB":          ("Kohala Suites",    "Hawaii"),
    "BAY CLUB AT WAIKOLOA BY HILTON GRAND VACATIONS CLUB":   ("Bay Club",         "Hawaii"),
}

def normalize_resort(raw: str) -> tuple[str, str]:
    """리조트명 → (정규화명, 지역)"""
    key = raw.strip().upper()
    for k, v in RESORT_NORMALIZE.items():
        if k.upper() in key or key in k.upper():
            return v
    # 키워드 기반 fallback
    if any(x in key for x in ["WAIKIKIAN", "LAGOON", "KALIA", "HOKULANI",
                                "KINGS LAND", "OCEAN TOWER", "OCEAN ENCLAVE",
                                "GRAND ISLANDER", "KOHALA", "BAY CLUB"]):
        return (raw.strip().title(), "Hawaii")
    if any(x in key for x in ["ELARA", "BOULEVARD", "FLAMINGO", "PARADISE", "STRIP"]):
        return (raw.strip().title(), "Las Vegas")
    if any(x in key for x in ["PARC SOLEIL", "TUSCANY", "SEAWORLD", "SEA WORLD", "ORLANDO"]):
        return (raw.strip().title(), "Orlando")
    return (raw.strip().title(), "Other")


# ── MF 데이터베이스 (2025 실제 고지서 기반) ──────────────────────────────────
# 출처: atimeshare.com + TUG 포럼 실오너 빌 데이터 + Lagoon Tower 실제 이미지
# 키: (resort_key, annual_points) → 연간 MF ($, Club Dues 포함)
MF_DB = {
    # ── 라스베이거스 ─────────────────────────────────────────────────────────
    # Elara (출처: TUG 2025 MF 스레드)
    ("elara",            23040): 1332,   # 2BR Grand Premier Plat
    ("elara",            16800): 1107,   # 2BR Premier Plat  ← CLAUDE.md 기존값 유지
    ("elara",            11520): 1006,   # 1BR Premier Plat  ($1,006.13)
    ("elara",             8400):  814,   # 1BR Plat
    ("elara",             4800):  428,   # Studio Plat
    # Boulevard
    ("boulevard",         9600): 1436,   # 3BR+ Plat ($1,436.04)
    ("boulevard",         8400): 1132,   # 2BR+ Plat ($1,131.61)
    ("boulevard",         7000):  906,   # 2BR Plat
    # Flamingo
    ("flamingo",          7000): 1340,   # 2BR Plat ($1,340.42)
    ("flamingo",          4800): 1192,   # 1BR Plat ($1,191.70)
    # Paradise
    ("paradise",          8000): 1213,   # 2BR Plat ($1,213.39)
    # Trump (참고용)
    ("trump",            16800): 2331,   # 2BR Plat ($2,331.20)
    # ── 하와이 ───────────────────────────────────────────────────────────────
    # Lagoon Tower — 실제 2025 고지서 이미지 (Grand Total D열)
    ("lagoon tower",      4800): 1290,   # Studio (~4,800pt 추정)
    ("lagoon tower",      8400): 2029,   # 1BR ($2,028.54)
    ("lagoon tower",     13440): 2639,   # 2BR OceanView ($2,639.19)
    ("lagoon tower",     15360): 3271,   # 2BR+ OceanFront/2PH ($3,270.84)
    ("lagoon tower",     20160): 3902,   # 3BR ($3,902.48)
    # Grand Waikikian (출처: atimeshare.com 2025)
    ("grand waikikian",  20160): 2066,   # 1BR Premier Plat ($2,065.54 추정)
    ("grand waikikian",  23040): 2434,   # 2BR Premier Plat ($2,433.65)
    ("grand waikikian",  46000): 5835,   # 3BR Pent Plat ($5,834.72)
    ("grand waikikian",  14880): 1803,   # 1BR (older config)
    ("grand waikikian",  12000): 2200,
    ("grand waikikian",  11520): 2122,
    ("grand waikikian",  10080): 1860,
    ("grand waikikian",   8160): 1803,   # 1BR Gold ($1,802.54 근사)
    # Kings Land (출처: atimeshare.com 2025)
    ("kings land",       36800): 3118,   # 3BR Premier Plat ($3,117.93)
    ("kings land",       23040): 2321,   # 2BR Premier Plat ($2,321.47)
    ("kings land",       20160): 1870,   # 1BR Premier Plat ($1,869.56)
    ("kings land",       16800): 1530,
    ("kings land",       14880): 1360,
    ("kings land",       11520): 1107,
    ("kings land",        9920):  950,
    ("kings land",        9280):  890,
    ("kings land",        7680):  730,
    # Hokulani Waikiki (출처: atimeshare.com 2025)
    ("hokulani waikiki", 13440): 1626,   # 1BR Premier Plat ($1,626.07)
    ("hokulani waikiki",  9920): 1502,
    ("hokulani waikiki",  9280): 1400,
    ("hokulani waikiki",  6720): 1010,
    # Kalia Tower (출처: atimeshare.com 2025)
    ("kalia tower",       9920): 1755,   # 1BR+ Plat ($1,754.74)
    ("kalia tower",       7680): 1300,
    ("kalia tower",       5440):  920,
    # Grand Islander (출처: atimeshare.com 2025)
    ("grand islander",   46000): 6061,   # 3BR Pent Premier ($6,061.18)
    ("grand islander",   30720): 2440,   # 2BR Premier ($2,439.52)
    ("grand islander",   26880): 1804,   # 1BR Premier ($1,803.76)
    ("grand islander",   20160): 3630,
    ("grand islander",   11520): 2100,
    # Ocean Tower (출처: atimeshare.com 2025)
    ("ocean tower",      46000): 3335,   # 3BR Pent Premier ($3,335.00)
    ("ocean tower",      38400): 2233,   # 2BR Pent Premier ($2,232.89)
    # Ocean Enclave
    ("ocean enclave",    28800): 1591,
    # Kohala Suites
    ("kohala suites",    11200): 2100,
    # Bay Club
    ("bay club",          7680): 1450,
    # ── 올랜도 ──────────────────────────────────────────────────────────────
    # Parc Soleil (출처: TUG 2025)
    ("parc soleil",      15360): 1348,   # 1BR Pent Premier Plat ($1,348.46)
    ("parc soleil",      13440): 1304,
    ("parc soleil",      11200): 1225,
    ("parc soleil",       8000): 1348,   # 1BR Gold (~같은 범위)
    # Tuscany Village
    ("tuscany village",  13440): 2154,   # 3BR Plat ($2,154.20)
    ("tuscany village",  11200): 1660,   # 2BR Plat ($1,660.17)
    ("tuscany village",   7680): 1439,
    # SeaWorld
    ("seaworld",         15360): 2600,
    ("seaworld",         11200): 1668,   # 2BR Plat ($1,668.34)
}

def lookup_mf(resort_name: str, points: int) -> float | None:
    key = resort_name.lower()
    # 정확 매칭
    if (key, points) in MF_DB:
        return float(MF_DB[(key, points)])
    # 유사 매칭 (포인트 ±5%)
    for (rk, rp), mf in MF_DB.items():
        if rk in key and abs(rp - points) / max(points, 1) < 0.05:
            return float(mf)
    return None


# ── 지표 계산 ────────────────────────────────────────────────────────────────
def compute_metrics(l: dict) -> dict:
    pts   = l.get("annual_points") or 0
    ask   = l.get("asking_price") or 0
    mf    = l.get("maintenance_fee") or 0
    usage = l.get("usage", "Annual")
    isEOY = "Biennial" in usage or "EOY" in usage

    epts = pts / 2 if isEOY else pts
    emf  = mf  / 2 if isEOY else mf

    mfPP     = round(emf / epts, 4)      if epts else None
    costPP   = round(ask / epts, 4)      if epts else None
    totalAnn = round((ask / 10) + emf)   if emf  else None
    hNights  = round(epts / 7000 * 7, 1) if epts else None
    beven    = round(2450 / totalAnn, 1) if (totalAnn and totalAnn > 0) else None

    rn = l.get("resort_name", "").lower()
    rofr = "Unknown"
    if costPP is not None:
        isHI = any(k in rn for k in ["waikikian","lagoon","kalia","hokulani",
                                       "kings","ocean","islander","kohala","bay club"])
        isLV = any(k in rn for k in ["elara","boulevard","flamingo","paradise"])
        if isHI:   rofr = "High" if costPP < 0.50 else ("Med" if costPP < 0.80 else "Low")
        elif isLV: rofr = "High" if costPP < 0.20 else ("Med" if costPP < 0.35 else "Low")
        else:      rofr = "Med"

    sc = 0
    if mfPP is not None:
        if mfPP <= 0.08: sc += 35
        elif mfPP <= 0.10: sc += 28
        elif mfPP <= 0.12: sc += 20
        elif mfPP <= 0.15: sc += 10
    if costPP is not None:
        if costPP == 0:      sc += 25
        elif costPP <= 0.20: sc += 22
        elif costPP <= 0.35: sc += 16
        elif costPP <= 0.60: sc += 8
    if epts >= 16000:   sc += 15
    elif epts >= 11000: sc += 10
    elif epts >= 7000:  sc += 6
    else:               sc += 3
    season = l.get("season", "")
    if "Platinum" in season: sc += 15
    elif "Gold"   in season: sc += 10
    elif "Silver" in season: sc += 5
    if not isEOY: sc += 10
    else:         sc += 5

    return {**l,
            "mf_per_point": mfPP, "cost_per_point": costPP,
            "total_annual_cost": totalAnn, "hawaii_nights": hNights,
            "breakeven_years": beven, "rofr_risk": rofr, "value_score": sc}


# ── HTTP ─────────────────────────────────────────────────────────────────────
def fetch(url: str, retries=2) -> BeautifulSoup | None:
    for i in range(retries + 1):
        try:
            r = SESSION.get(url, timeout=20)
            if r.status_code == 200:
                return BeautifulSoup(r.text, "html.parser")
            print(f"  HTTP {r.status_code}: {url}")
            return None
        except Exception as e:
            if i < retries:
                time.sleep(2)
            else:
                print(f"  오류: {e}")
    return None


# ── 검색 결과 테이블 파싱 ─────────────────────────────────────────────────────
def parse_search_table(soup: BeautifulSoup) -> list[dict]:
    listings = []
    table = soup.find("table")
    if not table:
        print("  테이블을 찾지 못했습니다.")
        return []

    rows = table.find_all("tr")
    print(f"  테이블 행 수: {len(rows)}")

    for row in rows[1:]:  # 헤더 제외
        cols = row.find_all("td")
        if len(cols) < 9:
            continue
        try:
            mls_id  = cols[0].get_text(strip=True)
            resort_raw = cols[1].get_text(strip=True)
            price_raw  = cols[2].get_text(strip=True)
            usage_raw  = cols[3].get_text(strip=True)
            # cols[4] = Week, cols[5]=Bed, cols[6]=Bath, cols[7]=Sleeps, cols[8]=Float
            beds_raw   = cols[5].get_text(strip=True)
            pts_raw    = cols[9].get_text(strip=True) if len(cols) > 9 else ""

            # URL
            a = row.find("a", href=re.compile(r"Listing/", re.I))
            if not a:
                continue
            href = a["href"]
            # 상대경로 정규화: ../../Listing/... → /Listing/...
            clean = re.sub(r"^[./]+", "/", href)
            if not clean.startswith("/Listing"):
                m = re.search(r"(/Listing/.+)", clean)
                clean = m.group(1) if m else clean
            url = BASE + clean

            # 리조트명 정규화
            resort_name, region = normalize_resort(resort_raw)

            # 가격
            price = 0.0 if "FREE" in price_raw.upper() else float(re.sub(r"[^\d.]", "", price_raw) or "0")

            # 포인트
            pts_str = re.sub(r"[^\d]", "", pts_raw)
            pts = int(pts_str) if pts_str else None
            if not pts:
                continue

            # 사용방식
            if "Biennial-Odd" in usage_raw or "Odd" in usage_raw:
                usage = "EOY-Odd"
            elif "Biennial-Even" in usage_raw or "Even" in usage_raw:
                usage = "EOY-Even"
            elif "Biennial" in usage_raw:
                usage = "EOY-Even"
            else:
                usage = "Annual"

            # 침실 수
            beds = beds_raw.strip()
            if beds == "1":   unit = "1BR"
            elif beds == "2": unit = "2BR"
            elif beds == "3": unit = "3BR"
            elif beds == "0": unit = "Studio"
            else:             unit = f"{beds}BR" if beds else ""

            # MF (DB 조회)
            mf = lookup_mf(resort_name, pts)

            listing = {
                "mls_id":        mls_id,
                "resort_name":   resort_name,
                "unit_size":     unit,
                "season":        "",       # 상세 페이지에서 보완
                "annual_points": pts,
                "usage":         usage,
                "asking_price":  price,
                "maintenance_fee": mf,
                "source_url":    url,
                "region":        region,
            }
            listings.append(listing)

        except Exception as e:
            continue

    return listings


# ── 상세 페이지에서 MF·시즌 보완 ─────────────────────────────────────────────
def enrich_from_detail(listing: dict) -> dict:
    soup = fetch(listing["source_url"])
    if not soup:
        return listing
    text = soup.get_text(" ", strip=True)

    # MF
    mf_m = re.search(r"Maintenance(?:\s*Fee)?[:\s]*\$?([\d,]+(?:\.\d+)?)", text, re.I)
    if mf_m:
        try:
            listing["maintenance_fee"] = float(mf_m.group(1).replace(",", ""))
        except:
            pass

    # 시즌
    season_m = re.search(r"Resort Season[:\s]*(Platinum|Gold|Silver|Bronze)", text, re.I)
    if season_m:
        listing["season"] = season_m.group(1).capitalize()
    else:
        if re.search(r"\bPlatinum\b", text, re.I): listing["season"] = "Platinum"
        elif re.search(r"\bGold\b", text, re.I):   listing["season"] = "Gold"
        elif re.search(r"\bSilver\b", text, re.I): listing["season"] = "Silver"

    return listing


# ── 메인 스크래퍼 ─────────────────────────────────────────────────────────────
def scrape_all(enrich_top: int = 30) -> list[dict]:
    """
    1. 검색 결과 테이블 전체 파싱 (1회 요청)
    2. 상위 enrich_top개 매물 상세 페이지 추가 수집 (MF·시즌)
    """
    print(f"\n=== timesharebrokersmls.com 스크래핑 시작 ===\n")
    print(f"검색 페이지 수집 중...")
    soup = fetch(SEARCH_URL)
    if not soup:
        return []

    listings = parse_search_table(soup)
    print(f"테이블 파싱 완료: {len(listings)}개 매물\n")

    if not listings:
        return []

    # Value Score로 정렬 (MF 없이 1차 계산)
    listings = [compute_metrics(l) for l in listings]
    listings.sort(key=lambda x: x.get("value_score", 0), reverse=True)

    # 상위 N개 상세 페이지 수집
    print(f"상위 {enrich_top}개 매물 상세 페이지 수집 (MF·시즌 보완)...")
    for i, l in enumerate(listings[:enrich_top]):
        print(f"  [{i+1}/{enrich_top}] {l['resort_name']} {l['annual_points']}pt", end=" ")
        listings[i] = enrich_from_detail(l)
        listings[i] = compute_metrics(listings[i])
        print(f"→ MF=${listings[i].get('maintenance_fee','?')} 시즌={listings[i].get('season','?')}")
        time.sleep(0.7)

    # 최종 재정렬
    listings.sort(key=lambda x: x.get("value_score", 0), reverse=True)
    return listings


# ── 샘플 데이터 (실제 매물, 2026-03-08 수집) ──────────────────────────────────
SAMPLE_LISTINGS = [
    {"mls_id":"63674","resort_name":"Kings Land","unit_size":"1BR","season":"Platinum",
     "annual_points":10080,"usage":"EOY-Odd","asking_price":100,"maintenance_fee":950,
     "source_url":"https://timesharebrokersmls.com/Listing/KINGS_LAND_BY_HILTON_GRAND_VACATIONS_CLUB_HGVC/63674.html","region":"Hawaii"},
    {"mls_id":"55822","resort_name":"Grand Waikikian","unit_size":"1BR","season":"Gold",
     "annual_points":10080,"usage":"EOY-Even","asking_price":100,"maintenance_fee":1860,
     "source_url":"https://timesharebrokersmls.com/Listing/GRAND_WAIKIKIAN_BY_HILTON_GRAND_VACATIONS_CLUB_HGVC/55822.html","region":"Hawaii"},
    {"mls_id":"62053","resort_name":"Grand Waikikian","unit_size":"1BR","season":"Platinum",
     "annual_points":14880,"usage":"Annual","asking_price":4800,"maintenance_fee":2740,
     "source_url":"https://timesharebrokersmls.com/Listing/GRAND_WAIKIKIAN_BY_HILTON_GRAND_VACATIONS_CLUB_HGVC/62053.html","region":"Hawaii"},
    {"mls_id":"62957","resort_name":"Grand Waikikian","unit_size":"1BR","season":"Platinum",
     "annual_points":14880,"usage":"EOY-Odd","asking_price":2000,"maintenance_fee":2740,
     "source_url":"https://timesharebrokersmls.com/Listing/GRAND_WAIKIKIAN_BY_HILTON_GRAND_VACATIONS_CLUB_HGVC/62957.html","region":"Hawaii"},
    {"mls_id":"63459","resort_name":"Grand Waikikian","unit_size":"2BR","season":"Platinum",
     "annual_points":23040,"usage":"Annual","asking_price":15000,"maintenance_fee":4200,
     "source_url":"https://timesharebrokersmls.com/Listing/GRAND_WAIKIKIAN_BY_HILTON_GRAND_VACATIONS_CLUB_HGVC/63459.html","region":"Hawaii"},
    {"mls_id":"62592","resort_name":"Grand Waikikian","unit_size":"2BR","season":"Platinum",
     "annual_points":23040,"usage":"Annual","asking_price":32000,"maintenance_fee":4200,
     "source_url":"https://timesharebrokersmls.com/Listing/GRAND_WAIKIKIAN_BY_HILTON_GRAND_VACATIONS_CLUB_HGVC/62592.html","region":"Hawaii"},
    {"mls_id":"28489","resort_name":"Kings Land","unit_size":"1BR","season":"Platinum",
     "annual_points":20160,"usage":"Annual","asking_price":29800,"maintenance_fee":1820,
     "source_url":"https://timesharebrokersmls.com/Listing/KINGS_LAND_BY_HILTON_GRAND_VACATIONS_CLUB_HGVC/28489.html","region":"Hawaii"},
    {"mls_id":"61183","resort_name":"Kings Land","unit_size":"2BR","season":"Platinum",
     "annual_points":20160,"usage":"EOY-Even","asking_price":2100,"maintenance_fee":1820,
     "source_url":"https://timesharebrokersmls.com/Listing/KINGS_LAND_BY_HILTON_GRAND_VACATIONS_CLUB_HGVC/61183.html","region":"Hawaii"},
    {"mls_id":"55355","resort_name":"Kings Land","unit_size":"2BR","season":"Platinum",
     "annual_points":9280,"usage":"EOY-Even","asking_price":800,"maintenance_fee":890,
     "source_url":"https://timesharebrokersmls.com/Listing/KINGS_LAND_BY_HILTON_GRAND_VACATIONS_CLUB_HGVC/55355.html","region":"Hawaii"},
    {"mls_id":"63916","resort_name":"Hokulani Waikiki","unit_size":"1BR","season":"Platinum",
     "annual_points":9920,"usage":"Annual","asking_price":8000,"maintenance_fee":1502,
     "source_url":"https://timesharebrokersmls.com/Listing/Hokulani_Waikiki_by_Hilton_Grand_Vacations_Club_HGVC/63916.html","region":"Hawaii"},
    {"mls_id":"60348","resort_name":"Hokulani Waikiki","unit_size":"1BR","season":"Platinum",
     "annual_points":6720,"usage":"EOY-Odd","asking_price":100,"maintenance_fee":1010,
     "source_url":"https://timesharebrokersmls.com/Listing/Hokulani_Waikiki_by_Hilton_Grand_Vacations_Club_HGVC/60348.html","region":"Hawaii"},
    {"mls_id":"59190","resort_name":"Lagoon Tower","unit_size":"1BR","season":"Platinum",
     "annual_points":5440,"usage":"EOY-Odd","asking_price":250,"maintenance_fee":900,
     "source_url":"https://timesharebrokersmls.com/Listing/HGVCLUB_AT_HILTON_HAWAIIAN_VILLAGE/59190.html","region":"Hawaii"},
    {"mls_id":"62299","resort_name":"Lagoon Tower","unit_size":"2BR","season":"Platinum",
     "annual_points":13440,"usage":"Annual","asking_price":4000,"maintenance_fee":2800,
     "source_url":"https://timesharebrokersmls.com/Listing/HGVCLUB_AT_HILTON_HAWAIIAN_VILLAGE/62299.html","region":"Hawaii"},
    {"mls_id":"3016","resort_name":"Lagoon Tower","unit_size":"2BR","season":"Platinum",
     "annual_points":13440,"usage":"Annual","asking_price":10000,"maintenance_fee":2800,
     "source_url":"https://timesharebrokersmls.com/Listing/HGVCLUB_AT_HILTON_HAWAIIAN_VILLAGE/3016.html","region":"Hawaii"},
    {"mls_id":"6545","resort_name":"Lagoon Tower","unit_size":"2BR","season":"Platinum",
     "annual_points":15360,"usage":"Annual","asking_price":59000,"maintenance_fee":3200,
     "source_url":"https://timesharebrokersmls.com/Listing/HGVCLUB_AT_HILTON_HAWAIIAN_VILLAGE/6545.html","region":"Hawaii"},
    {"mls_id":"55175","resort_name":"Kalia Tower","unit_size":"1BR","season":"Platinum",
     "annual_points":5440,"usage":"EOY-Odd","asking_price":250,"maintenance_fee":920,
     "source_url":"https://timesharebrokersmls.com/Listing/HGVCLUB_AT_THE_KALIA_TOWER/55175.html","region":"Hawaii"},
    {"mls_id":"51879","resort_name":"Kalia Tower","unit_size":"1BR","season":"Gold",
     "annual_points":7680,"usage":"EOY-Even","asking_price":2300,"maintenance_fee":1300,
     "source_url":"https://timesharebrokersmls.com/Listing/HGVCLUB_AT_THE_KALIA_TOWER/51879.html","region":"Hawaii"},
]


# ── 실행 ─────────────────────────────────────────────────────────────────────
def main():
    import sys
    use_sample  = "--sample" in sys.argv or "-s" in sys.argv
    enrich_top  = 30
    for arg in sys.argv:
        if arg.startswith("--enrich="):
            try: enrich_top = int(arg.split("=")[1])
            except: pass

    if use_sample:
        print("샘플 데이터 모드 (--sample)")
        listings = [compute_metrics(dict(l)) for l in SAMPLE_LISTINGS]
    else:
        listings = scrape_all(enrich_top=enrich_top)
        if not listings:
            print("\n스크래핑 실패 → 샘플 데이터로 대체합니다.")
            listings = [compute_metrics(dict(l)) for l in SAMPLE_LISTINGS]

    output = {
        "generated_at": datetime.now().isoformat(),
        "source": "timesharebrokersmls.com",
        "count": len(listings),
        "listings": listings,
    }
    with open("listings.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n✅ {len(listings)}개 매물 → listings.json 저장 완료")
    print("   dashboard.html 을 브라우저로 열어 확인하세요.")
    print("\n사용법:")
    print("  python scraper.py           # 실제 스크래핑 (상위 30개 상세 보완)")
    print("  python scraper.py --enrich=50  # 상위 50개 상세 보완")
    print("  python scraper.py --sample  # 샘플 데이터만")


if __name__ == "__main__":
    main()
