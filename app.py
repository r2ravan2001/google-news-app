import os
import urllib.parse
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor
from flask import Flask, jsonify, request, render_template
from flask_cors import CORS
import feedparser
from dateutil import parser as date_parser

app = Flask(__name__)
CORS(app)

LANGUAGES = [
    {'lang': 'hi', 'ceid': 'IN:hi', 'hl': 'hi', 'label': 'Hindi'},
    {'lang': 'mr', 'ceid': 'IN:mr', 'hl': 'mr', 'label': 'Marathi'},
    {'lang': 'en', 'ceid': 'IN:en', 'hl': 'en-IN', 'label': 'English'}
]

def is_within_minutes(pub_date_str, max_minutes):
    if not pub_date_str:
        return True
    try:
        pub_dt = date_parser.parse(pub_date_str)
        if pub_dt.tzinfo is None:
            pub_dt = pub_dt.replace(tzinfo=timezone.utc)
        
        now = datetime.now(timezone.utc)
        diff_minutes = (now - pub_dt).total_seconds() / 60.0
        return 0 <= diff_minutes <= max_minutes
    except Exception:
        return True

def fetch_single_feed(lang_info, topic, timeframe, force_fallback=False):
    try:
        is_trending = not topic or topic.strip().lower() in ['latest', 'trending', '']
        
        minute_limit = None
        rss_timeframe = timeframe
        
        if timeframe in ['2m', '5m', '10m'] and not force_fallback:
            minute_limit = int(timeframe.replace('m', ''))
            rss_timeframe = '1h'
        elif timeframe in ['2m', '5m', '10m'] and force_fallback:
            rss_timeframe = '1h'

        if is_trending:
            rss_url = f"https://news.google.com/rss?hl={lang_info['hl']}&gl=IN&ceid={lang_info['ceid']}"
        else:
            query = f"{topic.strip()} when:{rss_timeframe}"
            encoded_query = urllib.parse.quote(query)
            rss_url = f"https://news.google.com/rss/search?q={encoded_query}&hl={lang_info['hl']}&gl=IN&ceid={lang_info['ceid']}"

        feed = feedparser.parse(rss_url)
        articles = []

        for entry in feed.entries:
            pub_date = getattr(entry, 'published', '')
            
            # Apply strict minute filter if active
            if minute_limit and not is_within_minutes(pub_date, minute_limit):
                continue

            articles.append({
                'title': getattr(entry, 'title', 'No Title'),
                'link': getattr(entry, 'link', '#'),
                'source': getattr(entry, 'source', {}).get('title', 'Google News'),
                'published': pub_date or 'Recently',
                'lang': lang_info['label']
            })

        return articles
    except Exception as e:
        print(f"Error fetching {lang_info['label']}: {e}")
        return []

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/get-news', methods=['GET'])
def get_news():
    try:
        topic = request.args.get('topic', '').strip()
        timeframe = request.args.get('hours', '4h').strip()

        valid_timeframes = ['2m', '5m', '10m', '2h', '4h', '8h', '12h', '24h']
        if timeframe not in valid_timeframes:
            timeframe = '4h'

        # Fetch feeds across Hindi, Marathi, English
        all_articles = []
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = [
                executor.submit(fetch_single_feed, lang, topic, timeframe, False) 
                for lang in LANGUAGES
            ]
            for future in futures:
                all_articles.extend(future.result())

        # Fallback: If 0 articles found for 2m/5m/10m, fetch standard recent news
        is_fallback = False
        if len(all_articles) == 0 and timeframe in ['2m', '5m', '10m']:
            is_fallback = True
            with ThreadPoolExecutor(max_workers=3) as executor:
                futures = [
                    executor.submit(fetch_single_feed, lang, topic, timeframe, True) 
                    for lang in LANGUAGES
                ]
                for future in futures:
                    all_articles.extend(future.result())

        return jsonify({'articles': all_articles, 'count': len(all_articles), 'fallback': is_fallback})
    except Exception as e:
        print(f"Error in get_news: {e}")
        return jsonify({'error': str(e), 'articles': []}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
