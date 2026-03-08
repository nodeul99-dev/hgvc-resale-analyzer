# HGVC Resale Analyzer

## 목적
하와이 여행을 위해 HGVC 리세일 매물을 자동 수집·분석하는 도구.
라스베이거스 등 저유지비 리조트를 홈으로 사서 포인트만 활용하는 전략 기반.

## 데이터 소스
**TimeshareBrokerSales.com** (Diane Nadeau, TUG 포럼 최고 호평 HGVC 브로커)
- 메인: https://www.timesharebrokersales.com/hilton-timeshare/
- 개별 매물: /listing/HGVC-{리조트명}-{ID}/
- 리조트별 서브페이지 예시:
  - Elara: /hilton-timeshare/hilton-elara/
  - Boulevard: /hilton-timeshare/hilton-grand-vacations-club-on-the-las-vegas-strip/
  - Paradise: /hilton-timeshare/hilton-grand-vacations-club-las-vegas/
  - Flamingo: /hilton-timeshare/hilton-flamingo/
  - Kings Land: /hilton-timeshare/hilton-kings-land/
  - Lagoon Tower: /hilton-timeshare/hilton-hawaiian-village-lagoon-tower/
  - Grand Waikikian: /hilton-timeshare/hilton-grand-waikikian-by-hgvc/

## 워크플로우
1. web_fetch로 위 사이트 매물 수집
2. 아래 유지비 DB로 누락된 MF 보강
3. 분석 지표 계산
4. React 대시보드(.jsx) 또는 HTML로 결과 출력

## 매물에서 추출할 데이터
- resort_name: 홈 리조트명
- unit_size: Studio / 1BR / 2BR / 2BR+ / 3BR
- season: Platinum / Gold / Silver / Bronze
- annual_points: 연간 ClubPoints
- usage: Annual / EOY-Even / EOY-Odd
- asking_price: 호가 (USD)
- maintenance_fee: 연간 유지비
- source_url: 매물 링크

## 분석 지표
- **mf_per_point**: 유지비 ÷ 포인트. 핵심 지표. 목표 $0.12 이하.
- **cost_per_point**: 호가 ÷ 포인트 (EOY면 포인트/2로 환산)
- **total_annual_cost**: (호가÷10년 상각) + 유지비
- **hawaii_nights**: 보유 포인트로 하와이 몇 박 가능 (아래 차트 기준)
- **breakeven_years**: 호텔($350/박 × 7박) 대비 손익분기점
- **rofr_risk**: Low/Med/High (하와이 $0.50/pt 이하 High, 베이거스 $0.20 이하 High)
- **value_score**: 종합 0-100점 (MF/pt 35% + 구매가/pt 25% + 포인트량 15% + 시즌 15% + Annual여부 10%)

## 2025 유지비 DB (리조트별 포인트당 MF)
출처: atimeshare.com + TUG 실제 오너 빌 데이터

### 라스베이거스 (저유지비 TOP)
| 리조트 | 유닛 | 포인트 | MF($) | $/pt |
|--------|------|--------|-------|------|
| Elara | 2BR Grand Premier Plat | 23,040 | 1,332 | 0.058 |
| Elara | 2BR Premier Plat | 16,800 | 1,107 | 0.066 |
| Elara | 1BR Premier Plat | 11,520 | 763 | 0.066 |
| Elara | 1BR Plat | 8,400 | 763 | 0.091 |
| Elara | Studio Plat | 4,800 | 428 | 0.089 |
| Boulevard | 3BR+ Plat | 9,600 | 1,132 | 0.118 |
| Boulevard | 2BR+ Plat | 8,400 | 994 | 0.118 |
| Boulevard | 2BR Plat | 7,000 | 906 | 0.129 |
| Flamingo | 2BR Plat | 7,000 | 839 | 0.120 |
| Flamingo | 1BR Plat | 4,800 | 702 | 0.146 |

### 올랜도
| 리조트 | 유닛 | 포인트 | MF($) | $/pt |
|--------|------|--------|-------|------|
| Parc Soleil | 2BR Pent Premier Plat | 15,360 | 1,311 | 0.085 |
| Parc Soleil | 2BR+ Plat | 13,440 | 1,304 | 0.097 |
| Parc Soleil | 2BR Plat | 11,200 | 1,225 | 0.109 |
| Tuscany | 2BR Plat | 11,200 | 1,400 | 0.125 |
| SeaWorld | 2BR Plat | 11,200 | 1,600 | 0.143 |

### 하와이 (참고용 — 홈으로 사면 MF 비쌈)
| 리조트 | 유닛 | 포인트 | MF($) | $/pt |
|--------|------|--------|-------|------|
| Ocean Enclave | 3BR Premier Plat | 28,800 | 1,591 | 0.055 |
| Ocean Tower | Studio Pent Premier Plat | 19,840 | 1,129 | 0.057 |
| Kings Land | 2BR Premier Plat | 23,040 | 2,074 | 0.090 |
| Kings Land | 1BR Plat | 11,520 | 1,107 | 0.096 |
| Grand Waikikian | 2BR Pent Plat | 28,800 | 5,255 | 0.183 |
| Lagoon Tower | 2BR OV Plat | 13,440 | 2,800 | 0.208 |
| Lagoon Tower | 1BR Plat | 8,400 | 1,800 | 0.214 |

## 하와이 예약 필요 포인트 (1주 = 7박 기준)
| 리조트 | 유닛 | Platinum | Gold |
|--------|------|----------|------|
| Lagoon Tower | 1BR | 7,000 | 4,480 |
| Lagoon Tower | 2BR OceanView | 13,440 | 8,600 |
| Lagoon Tower | 2BR+ OceanFront | 15,360 | 9,840 |
| Grand Waikikian | Studio | 7,200 | 4,600 |
| Grand Waikikian | 1BR | 11,520 | 7,360 |
| Kings Land | 1BR | 11,520 | 7,360 |
| Kings Land | 2BR | 16,800 | 10,800 |
| Grand Islander | 1BR | 11,520 | 7,360 |
| Kalia Tower | 1BR | 8,400 | 5,400 |
| Bay Club | 1BR | 7,000 | 5,000 |

## 대시보드 UI
React(.jsx) 또는 HTML로 생성. 기능:
- **필터**: 지역, 리조트, 시즌, 가격대, MF/pt 범위
- **정렬**: Value Score, MF/pt, 호가, 포인트 등 컬럼별
- **테이블**: 매물 리스트. MF/pt ≤0.12 녹색, ≥0.15 적색
- **Top 5 카드**: 가성비 최고 매물 하이라이트
- **하와이 시뮬레이터**: 포인트 입력 → 어디에 몇 박 가능한지
- 다크 테마, 금융 대시보드 느낌

## 예시 분석
"Elara 2BR Premier Platinum, 16,800pt, $6,000" 매물의 경우:
- MF/pt = $1,107 / 16,800 = $0.066 ✅ (목표 이하)
- 구매가/pt = $6,000 / 16,800 = $0.357
- 연간총비용 = ($6,000/10) + $1,107 = $1,707
- 하와이: Lagoon 1BR(7,000pt) → 16.8박 가능, 2BR OV(13,440pt) → 8.7박
- 손익분기 = ~3.5년 (vs 호텔 $2,450/주)
- ROFR: Medium

## 주의사항
- 스크래핑 후 실제 HTML 구조에 맞게 파서 조정 필요
- EOY 매물은 포인트를 /2로 환산하여 Annual과 동일 기준 비교
- 유지비는 매년 ~5% 인상 추세
- ROFR: 가격이 너무 낮으면 힐튼이 선매권 행사 (구매 불발)
- 가격 $0 "FREE" 매물도 존재 (유지비 부담만 인수)
