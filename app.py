import os
import urllib.parse
import asyncio
import aiohttp
from flask import Flask, jsonify, request, render_template
from flask_cors import CORS
import feedparser
from datetime import datetime, timezone
from dateutil import parser as date_parser

app = Flask(__name__)
CORS(app)

LANGUAGES = [
    {'lang': 'hi', 'ceid': 'IN:hi', 'hl': 'hi', 'label': 'Hindi'},
    {'lang': 'mr', 'ceid': 'IN:mr', 'hl': 'mr', 'label': 'Marathi'},
    {'lang': 'en', 'ceid': 'IN:en', 'hl': 'en-IN', 'label': 'English'}
]

def is_within_minutes(pub_date_str, max_minutes):
    """Parse feed item publication date and check if it was published within max_minutes."""
    if not pub_date_str:
        return False
    try:
        pub_dt = date_parser.parse(pub_date_str)
        if pub_dt.tzinfo is None:
            pub_dt = pub_dt.replace(tzinfo=timezone.utc)
        
        now = datetime.now(timezone.utc)
        diff_minutes = (now - pub_dt).total_seconds() / 60.0
        return 0 <= diff_minutes <= max_minutes
    except Exception as e:
        print(f"Date parsing error ({pub_date_str}): {e}")
        return True  # Fallback to keep item if date parse fails

async def fetch_feed_async(session, url, lang_label, minute_limit=None):
    try:
        async with session.get(url, timeout=6) as response:
            xml_data = await response.text()
            feed = feedparser.parse(xml_data)
            articles = []
            for entry in feed.entries:
                pub_date = getattr(entry, 'published', '')
                
                # Filter strictly by minutes if a minute limit is active
                if minute_limit and not is_within_minutes(pub_date, minute_limit):
                    continue

                articles.append({
                    'title': getattr(entry, 'title', 'No Title'),
                    'link': getattr(entry, 'link', '#'),
                    'source': getattr(entry, 'source', {}).get('title', 'Google News'),
                    'published': pub_date or 'Recently',
                    'lang': lang_label
                })
            return articles
    except Exception as e:
        print(f"Error fetching feed for {lang_label}: {e}")
        return []

async def fetch_all_feeds(topic, timeframe):
    async with aiohttp.ClientSession() as session:
        tasks = []
        is_trending = not topic or topic.strip().lower() in ['latest', 'trending', '']

        # Determine minute limits for strict filtering
        minute_limit = None
        rss_timeframe = timeframe
        if timeframe in ['2m', '5m', '10m']:
            minute_limit = int(timeframe.replace('m', ''))
            rss_timeframe = '1h'  # Query Google News for 1h and strictly filter in Python

        for lang_info in LANGUAGES:
            if is_trending:
                rss_url = f"https://news.google.com/rss?hl={lang_info['hl']}&gl=IN&ceid={lang_info['ceid']}"
            else:
                query = f"{topic.strip()} when:{rss_timeframe}"
                encoded_query = urllib.parse.quote(query)
                rss_url = f"https://news.google.com/rss/search?q={encoded_query}&hl={lang_info['hl']}&gl=IN&ceid={lang_info['ceid']}"

            tasks.append(fetch_feed_async(session, rss_url, lang_info['label'], minute_limit))

        results = await asyncio.gather(*tasks)
        
        all_articles = []
        for article_list in results:
            all_articles.extend(article_list)

        # Fallback if strict filter returned zero articles
        if not is_trending and len(all_articles) == 0 and not minute_limit:
            tasks_fallback = []
            for lang_info in LANGUAGES:
                query = topic.strip()
                encoded_query = urllib.parse.quote(query)
                rss_url = f"https://news.google.com/rss/search?q={encoded_query}&hl={lang_info['hl']}&gl=IN&ceid={lang_info['ceid']}"
                tasks_fallback.append(fetch_feed_async(session, rss_url, lang_info['label'], None))
            fallback_results = await asyncio.gather(*tasks_fallback)
            for article_list in fallback_results:
                all_articles.extend(article_list)

        return all_articles

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

        articles = asyncio.run(fetch_all_feeds(topic, timeframe))
        return jsonify({'articles': articles, 'count': len(articles)})
    except Exception as e:
        print(f"Error in get_news route: {e}")
        return jsonify({'error': str(e), 'articles': []}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
