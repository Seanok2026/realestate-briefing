import os
import json
import re
import datetime as dt
import urllib.request
import urllib.parse
import feedparser

MOLIT_API_KEY = os.environ.get("MOLIT_API_KEY", "")

SEOUL_DISTRICTS = {
    "강남구": "11680", "강동구": "11740", "강북구": "11305", "강서구": "11500",
    "관악구": "11620", "광진구": "11215", "구로구": "11530", "금천구": "11545",
    "노원구": "11350", "도봉구": "11320", "동대문구": "11230", "동작구": "11590",
    "마포구": "11440", "서대문구": "11410", "서초구": "11650", "성동구": "11200",
    "성북구": "11290", "송파구": "11710", "양천구": "11470", "영등포구": "11560",
    "용산구": "11170", "은평구": "11380", "종로구": "11110", "중구": "11140",
    "중랑구": "11260"
}

def get_apt_trades(region_code, ym):
    base = "http://apis.data.go.kr/1613000/RTMSDataSvcAptTrade/getRTMSDataSvcAptTrade"
    encoded_key = urllib.parse.quote(MOLIT_API_KEY, safe="")
    full_url = (
        base
        + "?serviceKey=" + encoded_key
        + "&LAWD_CD=" + region_code
        + "&DEAL_YMD=" + ym
        + "&numOfRows=100&pageNo=1"
    )
    try:
        with urllib.request.urlopen(full_url, timeout=10) as resp:
            data = resp.read().decode("utf-8")
        items = re.findall(r"<item>(.*?)</item>", data, re.DOTALL)
        trades = []
        for item in items:
            def g(tag):
                m = re.search(r"<" + tag + r">\s*(.*?)\s*</" + tag + r">", item)
                return m.group(1).strip() if m else ""
            try:
                price = int(g("dealAmount").replace(",", ""))
                area = float(g("excluUseAr"))
                trades.append({
                    "name": g("aptNm"),
                    "dong": g("umdNm"),
                    "area": area,
                    "price": price,
                    "floor": g("floor"),
                    "date": g("dealYear") + "." + g("dealMonth").zfill(2) + "." + g("dealDay").zfill(2)
                })
            except:
                pass
        return trades
    except Exception as ex:
        print("API error " + region_code + ": " + str(ex))
        return []

def analyze_seoul(ym):
    all_trades = []
    district_summary = {}
    for dname, code in SEOUL_DISTRICTS.items():
        trades = get_apt_trades(code, ym)
        if trades:
            prices = [t["price"] for t in trades]
            avg = sum(prices) // len(prices)
            mx = max(trades, key=lambda x: x["price"])
            district_summary[dname] = {
                "count": len(trades),
                "avg": avg,
                "max_price": mx["price"],
                "max_name": mx["name"]
            }
            all_trades.extend(trades)
    if not district_summary:
        return {}, []
    sorted_up = sorted(district_summary.items(), key=lambda x: x[1]["avg"], reverse=True)
    top5 = sorted_up[:5]
    top_trades = sorted(all_trades, key=lambda x: x["price"], reverse=True)[:5]
    songpa_trades = [t for t in all_trades if t.get("dong", "") in [
        "신천동", "잠실동", "문정동", "가락동", "송파동", "방이동", "오금동", "거여동", "마천동"
    ]]
    return {
        "total_count": len(all_trades),
        "total_districts": len(district_summary),
        "top5_districts": top5,
        "top5_trades": top_trades,
        "songpa_count": len(songpa_trades),
        "songpa_avg": sum(t["price"] for t in songpa_trades) // max(len(songpa_trades), 1)
    }, all_trades

CHANNELS = [
    ("월급쟁이부자들TV", "UCDSj40X9FFUAnx1nv7gQhcA"),
    ("부읽남TV", "UC2QeHNJFfuQWB4cy3M-745g"),
    ("아포유 AforU", "UCK6bIuN3aDIV4F53QQ4__Ng"),
]
KEYWORDS = ["송파","신축","분양","양도세","다주택","금리","공급","정책","서울","아파트","부동산","집값","전세","청약","재건축","재개발","투자","매매","규제","대출","취득세","보유세","종부세"]

videos = []
now = dt.datetime.now(dt.timezone.utc)
cutoff = now - dt.timedelta(days=30)
for name, cid in CHANNELS:
    url = "https://www.youtube.com/feeds/videos.xml?channel_id=" + cid
    try:
        feed = feedparser.parse(url)
        for e in feed.entries:
            pub = getattr(e, "published_parsed", None)
            if not pub:
                continue
            pub_dt = dt.datetime(*pub[:6], tzinfo=dt.timezone.utc)
            if pub_dt < cutoff:
                continue
            title = e.get("title", "")
            if not any(k in title for k in KEYWORDS):
                continue
            videos.append({
                "channel": name,
                "title": title,
                "link": e.get("link", ""),
                "pub_ts": pub_dt.timestamp(),
                "pub_date": pub_dt.strftime("%m/%d")
            })
    except Exception as ex:
        print("channel error: " + str(ex))

videos = sorted(videos, key=lambda x: x.get("pub_ts", 0), reverse=True)[:15]
print("유튜브 영상: " + str(len(videos)) + "건")

today = dt.date.today()
ym = today.strftime("%Y%m")
prev_ym = (today.replace(day=1) - dt.timedelta(days=1)).strftime("%Y%m")
print("실거래가 수집: " + ym)
summary, all_trades = analyze_seoul(ym)
if not summary:
    print("전월 조회: " + prev_ym)
    summary, all_trades = analyze_seoul(prev_ym)
    data_ym = prev_ym
else:
    data_ym = ym

briefing_data = {
    "date": today.strftime("%Y.%m.%d"),
    "data_month": data_ym[:4] + "년 " + data_ym[4:] + "월",
    "videos": videos,
    "market": summary,
    "signals": [
        "수원 아파트: 보유 11.5년 → 장기보유 구간 진입, 매도 우호적",
        "송도 오피스텔: 보유 9.5년 → 장기보유공제 누적 중",
        "다주택 양도세 중과 재시행(2026.5.10~): 2주택 +20%p, 3주택 +30%p"
    ],
    "daily_check": "송파 30평대 신축 17~18억 형성 → 매수 타이밍 및 대출한도 점검 권장"
}

with open("briefing.json", "w", encoding="utf-8") as f:
    json.dump(briefing_data, f, ensure_ascii=False, indent=2)

print("완료: 서울 " + str(summary.get("total_count", 0)) + "건, 영상 " + str(len(videos)) + "건")
