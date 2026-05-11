#!/usr/bin/env python3
import argparse
import email.utils
import hashlib
import html
import json
import re
import subprocess
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path('/root/.openclaw/workspace')
OPENCLAW_CONFIG = Path('/root/.openclaw/openclaw.json')
STATE_PATH = ROOT / 'agents' / 'lessrisk' / 'state' / 'market-alert-state.json'
PUBLIC_FEED_PATH = ROOT / 'agents' / 'lessrisk' / 'state' / 'market-news-feed.json'
PUBLIC_FEED_MAX = 12
SERVERMAC_FEED_PATH = '/opt/homebrew/var/www/lessrisk/news-feed.json'
CHAT_ID = '-1003955885540'
THREAD_ID = 223
AMS = ZoneInfo('Europe/Amsterdam')
MAX_ALERTS_PER_RUN = 3
DEDUP_HOURS = 36
UA = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136 Safari/537.36'

NEWS_FEEDS = [
    {
        'kind': 'news',
        'label': 'Google News Gold',
        'url': 'https://news.google.com/rss/search?' + urllib.parse.urlencode({'q': 'gold OR XAUUSD OR Fed OR Treasury yields when markets', 'hl': 'en-US', 'gl': 'US', 'ceid': 'US:en'})
    },
    {
        'kind': 'news',
        'label': 'Google News Nasdaq',
        'url': 'https://news.google.com/rss/search?' + urllib.parse.urlencode({'q': 'Nasdaq OR NAS100 OR QQQ OR Fed OR Treasury yields OR Nvidia', 'hl': 'en-US', 'gl': 'US', 'ceid': 'US:en'})
    },
]

TWEET_FEEDS = [
    ('WalterBloomberg', 'Walter Bloomberg'),
    ('DeItaone', 'Delta One'),
    ('financialjuice', 'FinancialJuice'),
    ('ForexLive', 'ForexLive'),
    ('unusual_whales', 'Unusual Whales'),
]

POSITIVE_XAU = ['gold rises', 'gold jumps', 'safe haven', 'dollar slips', 'yields fall', 'rate cut', 'geopolitical tension']
NEGATIVE_XAU = ['gold falls', 'gold drops', 'yields rise', 'dollar strengthens', 'hawkish fed', 'risk-on']
POSITIVE_NAS = ['nasdaq rises', 'stocks rally', 'yields fall', 'cooling inflation', 'rate cut', 'nvidia jumps', 'risk-on']
NEGATIVE_NAS = ['nasdaq falls', 'stocks slide', 'yields rise', 'hot inflation', 'hawkish fed', 'risk-off', 'tariff']

HIGH_IMPACT = [
    'fed', 'powell', 'fomc', 'cpi', 'inflation', 'nfp', 'payrolls', 'jobs report', 'pce', 'treasury yields', 'yield',
    'rate cut', 'rate hike', 'tariff', 'iran', 'israel', 'war', 'oil', 'nvidia', 'apple', 'microsoft', 'amazon', 'meta',
    'tesla', 'china', 'usd', 'dollar', 'gold', 'nasdaq', 'qqq', 'dow futures', 's&p futures'
]

XAU_KEYWORDS = ['gold', 'xau', 'xauusd', 'bullion', 'usd', 'dollar', 'yield', 'treasury', 'fed', 'powell', 'inflation', 'cpi', 'pce', 'nfp', 'oil', 'iran', 'israel']
NAS_KEYWORDS = ['nasdaq', 'nas100', 'qqq', 'tech', 'nvidia', 'apple', 'microsoft', 'amazon', 'meta', 'tesla', 'yield', 'treasury', 'fed', 'powell', 'inflation', 'cpi', 'pce']


def load_json(path: Path, default):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text())
    except Exception:
        return default


def save_json(path: Path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\n')
    tmp.replace(path)


def load_bot_token() -> str:
    cfg = json.loads(OPENCLAW_CONFIG.read_text())
    return cfg['channels']['telegram']['accounts']['lessrisk']['botToken']


def fetch(url: str) -> str:
    req = urllib.request.Request(url, headers={'User-Agent': UA})
    with urllib.request.urlopen(req, timeout=20) as r:
        return r.read().decode('utf-8', 'ignore')


def normalize_space(s: str) -> str:
    s = html.unescape(s or '')
    s = re.sub(r'<[^>]+>', ' ', s)
    s = re.sub(r'\s+', ' ', s).strip()
    return s


def parse_rss(url: str, source_label: str, kind: str):
    xml_text = fetch(url)
    root = ET.fromstring(xml_text)
    channel = root.find('channel')
    items = []
    if channel is None:
        return items
    for item in channel.findall('item')[:12]:
        title = normalize_space(item.findtext('title', ''))
        link = normalize_space(item.findtext('link', ''))
        desc = normalize_space(item.findtext('description', ''))
        pub = normalize_space(item.findtext('pubDate', ''))
        items.append({
            'kind': kind,
            'source': source_label,
            'title': title,
            'link': link,
            'summary': desc,
            'published': pub,
        })
    return items


def classify_market(text: str):
    t = text.lower()
    xau = sum(1 for kw in XAU_KEYWORDS if kw in t)
    nas = sum(1 for kw in NAS_KEYWORDS if kw in t)
    if xau > nas and xau >= 2:
        return 'XAUUSD'
    if nas > xau and nas >= 2:
        return 'NAS100'
    if xau >= 2 and nas >= 2:
        return 'MULTI'
    return None


def score_item(item):
    blob = f"{item.get('title','')} {item.get('summary','')} {item.get('source','')}".lower()
    market = classify_market(blob)
    if not market:
        return 0, None
    score = 0
    for kw in HIGH_IMPACT:
        if kw in blob:
            score += 2
    if item['kind'] == 'tweet':
        score += 2
    if any(name in blob for name in ['reuters', 'bloomberg', 'cnbc', 'forexlive', 'financialjuice', 'walter bloomberg', 'delta one']):
        score += 1
    if len(item.get('title','')) > 20:
        score += 1
    if market == 'MULTI':
        score += 1
    return score, market


def parse_published(value: str):
    if not value:
        return None
    try:
        dt = email.utils.parsedate_to_datetime(value)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        return None


def is_recent(item):
    dt = parse_published(item.get('published', ''))
    if not dt:
        return True
    age_hours = (datetime.now(timezone.utc) - dt).total_seconds() / 3600
    limit = 8 if item.get('kind') == 'tweet' else 14
    return age_hours <= limit


def market_bias(market: str, text: str) -> str:
    t = text.lower()
    if market == 'XAUUSD':
        pos = sum(1 for w in POSITIVE_XAU if w in t)
        neg = sum(1 for w in NEGATIVE_XAU if w in t)
    else:
        pos = sum(1 for w in POSITIVE_NAS if w in t)
        neg = sum(1 for w in NEGATIVE_NAS if w in t)
    if pos > neg:
        return 'bullish'
    if neg > pos:
        return 'bearish'
    return 'gemengd'


def hash_item(item):
    base = f"{item.get('kind','')}|{item.get('source','')}|{item.get('title','')}|{item.get('link','')}"
    return hashlib.sha256(base.encode()).hexdigest()[:20]


def load_state():
    return load_json(STATE_PATH, {'sent': []})


def prune_state(state):
    cutoff = time.time() - DEDUP_HOURS * 3600
    state['sent'] = [x for x in state.get('sent', []) if x.get('ts', 0) >= cutoff]
    return state


def seen_recent(state, item_hash):
    return any(x.get('id') == item_hash for x in state.get('sent', []))


def mark_sent(state, item_hash, item):
    state.setdefault('sent', []).append({
        'id': item_hash,
        'ts': int(time.time()),
        'title': item.get('title', ''),
        'source': item.get('source', ''),
    })


def prune_public_feed(feed):
    items = feed.get('items') or []
    feed['items'] = items[:PUBLIC_FEED_MAX]
    feed['updatedAtUtc'] = datetime.now(timezone.utc).isoformat()
    return feed


def nl_time_now():
    return datetime.now(timezone.utc).astimezone(AMS).strftime('%d %b %Y %H:%M Amsterdam')


def build_message(item, market):
    blob = f"{item.get('title','')} {item.get('summary','')}"
    bias = market_bias(market if market != 'MULTI' else 'NAS100', blob)
    prefix = '🐦 TWEET ALERT' if item['kind'] == 'tweet' else '📰 NIEUWS ALERT'
    market_label = 'XAUUSD + NAS100' if market == 'MULTI' else market
    title = item.get('title') or 'Belangrijke update'
    summary = item.get('summary') or ''
    summary = re.sub(r'\s+', ' ', summary).strip()
    if len(summary) > 220:
        summary = summary[:217].rstrip() + '...'
    impact_label = {
        'bullish': 'Impact: bullish / risk-on',
        'bearish': 'Impact: bearish / risk-off',
        'gemengd': 'Impact: gemengd',
    }[bias]
    if market == 'MULTI':
        lower = blob.lower()
        if any(x in lower for x in ['hawkish', 'rate increase', 'yields rise', 'inflation', 'powell', 'tariff']):
            impact_label = 'Impact: hawkish / risk-off'
        elif any(x in lower for x in ['rate cut', 'yields fall', 'cooling inflation', 'stocks rally']):
            impact_label = 'Impact: dovish / risk-on'
    source = item.get('source', '-')
    link = item.get('link', '')
    lines = [
        f"{prefix} — {market_label}",
        f"{nl_time_now()}",
        '',
        f"{title}",
        '',
    ]
    if summary:
        lines.append(f"Kern: {summary}")
        lines.append('')
    lines.append(f"{impact_label} | Bron: {source}")
    if link:
        lines.append(link)
    return '\n'.join(lines).strip()


def build_feed_entry(item, market):
    blob = f"{item.get('title','')} {item.get('summary','')}"
    if market == 'MULTI':
        lower = blob.lower()
        if any(x in lower for x in ['hawkish', 'rate increase', 'yields rise', 'inflation', 'powell', 'tariff']):
            bias = 'hawkish / risk-off'
        elif any(x in lower for x in ['rate cut', 'yields fall', 'cooling inflation', 'stocks rally']):
            bias = 'dovish / risk-on'
        else:
            bias = 'mixed'
        market_label = 'XAUUSD + NAS100'
    else:
        bias = market_bias(market, blob)
        market_label = market
    summary = re.sub(r'\s+', ' ', item.get('summary', '')).strip()
    return {
        'id': hash_item(item),
        'kind': item.get('kind', 'news'),
        'market': market,
        'marketLabel': market_label,
        'bias': bias,
        'source': item.get('source', ''),
        'title': item.get('title', ''),
        'summary': summary[:320] + ('...' if len(summary) > 320 else ''),
        'link': item.get('link', ''),
        'published': item.get('published', ''),
        'createdAtUtc': datetime.now(timezone.utc).isoformat(),
    }


def build_public_feed(items):
    ranked = []
    for item in items:
        if not is_recent(item):
            continue
        score, market = score_item(item)
        if score < 4 or not market:
            continue
        ranked.append((score, item.get('source', ''), item, market))
    ranked.sort(key=lambda x: (-x[0], x[1]))
    dedup = set()
    out = []
    for score, _source, item, market in ranked:
        item_id = hash_item(item)
        if item_id in dedup:
            continue
        dedup.add(item_id)
        entry = build_feed_entry(item, market)
        entry['score'] = score
        out.append(entry)
        if len(out) >= PUBLIC_FEED_MAX:
            break
    return prune_public_feed({'items': out})


def deploy_public_feed(feed):
    save_json(PUBLIC_FEED_PATH, feed)
    try:
        subprocess.run(['ssh', 'macagent', 'mkdir', '-p', '/opt/homebrew/var/www/lessrisk'], check=False, capture_output=True, text=True)
        subprocess.run(['scp', str(PUBLIC_FEED_PATH), f'macagent:{SERVERMAC_FEED_PATH}'], check=False, capture_output=True, text=True)
    except Exception as exc:
        print(f'warn: public feed deploy failed: {exc}')


def telegram_send(text: str):
    cmd = [
        'openclaw', 'message', 'send',
        '--channel', 'telegram',
        '--account', 'lessrisk',
        '--target', CHAT_ID,
        '--thread-id', str(THREAD_ID),
        '--message', text,
        '--json',
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip() or 'openclaw message send failed')
    payload = json.loads(result.stdout)
    inner = payload.get('payload') or {}
    if not inner.get('ok'):
        raise RuntimeError(str(payload))
    return inner


def collect_items():
    items = []
    for feed in NEWS_FEEDS:
        try:
            items.extend(parse_rss(feed['url'], feed['label'], feed['kind']))
        except Exception:
            continue
    for account, label in TWEET_FEEDS:
        try:
            items.extend(parse_rss(f'https://nitter.net/{account}/rss', label, 'tweet'))
        except Exception:
            continue
    return items


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dry-run', action='store_true')
    args = ap.parse_args()

    state = prune_state(load_state())
    items = collect_items()
    public_feed = build_public_feed(items)

    candidates = []
    for item in items:
        if not is_recent(item):
            continue
        score, market = score_item(item)
        if score < 6:
            continue
        item_hash = hash_item(item)
        if seen_recent(state, item_hash):
            continue
        candidates.append((score, market, item_hash, item))

    candidates.sort(key=lambda x: (-x[0], x[3].get('source', '')))
    sent_count = 0
    for score, market, item_hash, item in candidates[:MAX_ALERTS_PER_RUN]:
        msg = build_message(item, market)
        if args.dry_run:
            print(json.dumps({'score': score, 'market': market, 'source': item.get('source'), 'title': item.get('title'), 'message': msg}, ensure_ascii=False, indent=2))
        else:
            result = telegram_send(msg)
            if not result.get('ok'):
                raise SystemExit(f"telegram send failed: {result}")
            mark_sent(state, item_hash, item)
            sent_count += 1
            print(f"sent: {item.get('source')} | {item.get('title')[:90]}")

    if not args.dry_run:
        save_json(STATE_PATH, state)
        deploy_public_feed(public_feed)
    print(f'done candidates={len(candidates)} sent={sent_count}')


if __name__ == '__main__':
    main()
