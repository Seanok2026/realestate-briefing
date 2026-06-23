import os
import json
import re
import datetime as dt
import urllib.request
import urllib.parse
import feedparser
from anthropic import Anthropic

MOLIT_API_KEY = os.environ.get("MOLIT_API_KEY", "")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

# 서울 25개 구 법정동 코드
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
    url = "http://apis.data.go.kr/1613000/RTMSDataSvcAptTradeDev/getRTMSDataSvcAptTradeDev"
    params = {
        "serviceKey": MOLIT_API_KEY,
        "LAWD_CD": region_code,
        "DEAL_YMD": ym,
        "numOfRows": "100",
        "pageNo": "1"
    }
    try:
        full_url = url + "?" + urllib.parse.urlencode(params)
        with urllib.request.urlopen(full_url, timeout=10) as resp:
            data = resp.read().decode("utf-8")
        items = re.findall(r'<item>(.*?)</item>', data, re.DOTALL)
        trades = []
        for item in items:
            def g(tag):
                m = re.search(r'<' + tag + r'>\s*(.*?)\s*</' + tag + r'>', item)
                return m.group(1).strip() if m else ""
            try:
                price = int(g("dealAmount").replace(",", ""))
                area = float(g("excluUseAr"))
                sqm_price = round(price / (area / 3.305))
                trades.append({
                    "name": g("aptNm"),
                    "dong": g("umdNm"),
                    "area": area,
                    "price": price,
                    "sqm_price": sqm_price,
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
    bottom5 = sorted_up[-5:]
    top_trades = sorted(all_trades, key=lambda x: x["price"], reverse=True)[:5]
    songpa_trades = [t for t in all_trades if "송파" in t.get("dong", "") or "잠실" in t.get("dong", "") or "문정" in t.get("dong", "")]

    return {
        "total_count": len(all_trades),
        "total_districts": len(district_summary),
        "top5_districts": top5,
        "bottom5_districts": bottom5,
        "top5_trades": top_trades,
        "songpa_count": len(songpa_trades),
        "songpa_avg": sum(t["price"] for t in songpa_trades) // max(len(songpa_trades), 1)
    }, all_trades

# 유튜브 채널 모니터링
CHANNELS = [
    ("wolbu", "UCDSj40X9FFUAnx1nv7gQhcA"),
    ("buiknnam", "UC2QeHNJFfuQWB4cy3M-745g"),
    ("aforU", "UCK6bIuN3aDIV4F53QQ4__Ng"),
]
CHANNEL_NAMES = {
    "wolbu": "월급쟁이부자들TV",
    "buiknnam": "부읽남TV",
    "aforU": "아포유 AforU",
}
KEYWORDS = ["송파", "신축", "분양", "양도세", "다주택", "금리", "공급", "정책", "서울"]

videos = []
now = dt.datetime.now(dt.timezone.utc)
cutoff = now - dt.timedelta(hours=25)
for key, cid in CHANNELS:
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
            videos.append({"channel": CHANNEL_NAMES[key], "title": title, "link": e.get("link", "")})
    except Exception as ex:
        print("channel error: " + str(ex))

# 실거래가 데이터 수집
today = dt.date.today()
ym = today.strftime("%Y%m")
prev_ym = (today.replace(day=1) - dt.timedelta(days=1)).strftime("%Y%m")
print("실거래가 수집 중: " + ym)
summary, all_trades = analyze_seoul(ym)
if not summary:
    print("이번달 데이터 없음, 전월 조회: " + prev_ym)
    summary, all_trades = analyze_seoul(prev_ym)
    data_ym = prev_ym
else:
    data_ym = ym

# 브리핑 데이터 구성
briefing_data = {
    "date": today.strftime("%Y.%m.%d"),
    "data_month": data_ym[:4] + "년 " + data_ym[4:] + "월",
    "videos": [],
    "market": summary,
    "signals": [
        "수원 아파트: 보유 11.5년 → 장기보유 구간 진입, 매도 우호적",
        "송도 오피스텔: 보유 9.5년 → 장기보유공제 누적 중",
        "다주택 양도세 중과 재시행(2026.5.10~): 2주택 +20%p, 3주택 +30%p"
    ],
    "daily_check": "송파 30평대 신축 17~18억 형성 → 매수 타이밍 및 대출한도 점검 권장"
}

# 유튜브 요약
if videos:
    client = Anthropic()
    lines = ["[" + v["channel"] + "] " + v["title"] for v in videos]
    prompt = "부동산 유튜브 영상 목록:\n" + "\n".join(lines) + "\n\n"
    prompt += "각 영상을 JSON 배열로만 반환. 다른 텍스트 없이 JSON만.\n"
    prompt += '[{"channel":"채널명","title":"핵심내용 1줄","relevance":"긍정 또는 중립 또는 주의"}]'
    try:
        resp = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=500,
            messages=[{"role": "user", "content": prompt}]
        )
        text = "".join(b.text for b in resp.content if b.type == "text")
        match = re.search(r'\[.*\]', text, re.DOTALL)
        if match:
            briefing_data["videos"] = json.loads(match.group())
    except Exception as ex:
        print("claude error: " + str(ex))

with open('briefing.json', 'w', encoding='utf-8') as f:
    json.dump(briefing_data, f, ensure_ascii=False, indent=2)

print("완료: 서울 " + str(summary.get("total_count", 0)) + "건, 영상 " + str(len(briefing_data["videos"])) + "건")
                continue
            videos.append({
                "channel": CHANNEL_NAMES[key],
                "title": title,
                "link": e.get("link", "")
            })
    except Exception as ex:
        print("channel error: " + str(ex))

client = Anthropic()
briefing_data = {
    "date": dt.date.today().strftime("%Y.%m.%d"),
    "videos": [],
    "signals": [
        "수원 아파트: 보유 11.5년 → 장기보유 구간 진입, 매도 우호적",
        "송도 오피스텔: 보유 9.5년 → 장기보유공제 누적 중"
    ],
    "daily_check": "송파 30평대 신축 17~18억 형성 → 매수 타이밍 및 대출한도 점검 권장"
}

if videos:
    lines = []
    for v in videos:
        lines.append("[" + v["channel"] + "] " + v["title"])
    vid_text = "\n".join(lines)

    prompt = "부동산 유튜브 영상 목록:\n" + vid_text + "\n\n"
    prompt += "각 영상을 JSON 배열로만 반환하세요. 다른 텍스트 없이 JSON만.\n"
    prompt += '[{"channel":"채널명","title":"핵심내용 1줄","relevance":"긍정 또는 중립 또는 주의"}]'

    resp = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=500,
        messages=[{"role": "user", "content": prompt}]
    )
    text = "".join(b.text for b in resp.content if b.type == "text")
    try:
        match = re.search(r'\[.*\]', text, re.DOTALL)
        if match:
            briefing_data["videos"] = json.loads(match.group())
    except Exception as ex:
        print("json error: " + str(ex))

with open('briefing.json', 'w', encoding='utf-8') as f:
    json.dump(briefing_data, f, ensure_ascii=False, indent=2)

print("done: " + str(len(briefing_data["videos"])) + " videos")
