import os
import json
import datetime as dt
import feedparser
from anthropic import Anthropic

CHANNELS = [
    ("월급쟁이부자들TV", "UCDSj40X9FFUAnx1nv7gQhcA"),
    ("부읽남TV", "UC2QeHNJFfuQWB4cy3M-745g"),
    ("아포유 AforU", "UCK6bIuN3aDIV4F53QQ4__Ng"),
]
KEYWORDS = ["송파", "신축", "분양", "양도세", "다주택", "금리", "공급", "정책"]

videos = []
now = dt.datetime.now(dt.timezone.utc)
cutoff = now - dt.timedelta(hours=25)

for name, cid in CHANNELS:
    url = f"https://www.youtube.com/feeds/videos.xml?channel_id={cid}"
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
                "link": e.get("link", "")
            })
    except Exception as ex:
        print(f"채널 오류 {name}: {ex}")

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
    vid_text = "\n".join(f"[{v['channel']}] {v['title']
