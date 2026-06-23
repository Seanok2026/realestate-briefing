import os
import json
import re
import datetime as dt
import feedparser
from anthropic import Anthropic

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
KEYWORDS = ["송파", "신축", "분양", "양도세", "다주택", "금리", "공급", "정책"]

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
