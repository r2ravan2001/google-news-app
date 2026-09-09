import os
import urllib.parse
import asyncio
import aiohttp
from flask import Flask, jsonify, request, render_template
from flask_cors import CORS
import feedparser

app = Flask(__name__)
CORS(app)

# Google News RSS endpoints configurations for 3 languages
LANGUAGES = [
    {'lang': 'hi', 'ceid': 'IN:hi', 'hl': 'hi', 'label': 'Hindi'},
    {'lang': 'mr', 'ceid': 'IN:mr', 'hl': 'mr', 'label': 'Marathi'},
    {'lang': 'en', 'ceid': 'IN:en', 'hl': 'en-IN', 'label': 'English'}
]

async def fetch_feed_async(session, url, lang_label):
    try:
        async with session.get(url, timeout=5) as response:
            xml_data = await response.text()
            feed = feedparser.parse(xml_data)
            articles = []
            for entry in feed.entries[:15]:
                articles.append({
                    'title': getattr(entry, 'title', 'No Title'),
                    'link': getattr(entry, 'link', '#'),
                    'source': getattr(entry, 'source', {}).get('title', 'Google News'),
                    'published': getattr(entry, 'published', 'Recently'),
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

        for lang_info in LANGUAGES:
            if is_trending:
                # Top trending headlines feed per language
                rss_url = f"https://news.google.com/rss?hl={lang_info['hl']}&gl=IN&ceid={lang_info['ceid']}"
            else:
                # Search topic feed with time window across languages
                query = f"{topic.strip()} when:{timeframe}"
                encoded_query = urllib.parse.quote(query)
                rss_url = f"https://news.google.com/rss/search?q={encoded_query}&hl={lang_info['hl']}&gl=IN&ceid={lang_info['ceid']}"

            tasks.append(fetch_feed_async(session, rss_url, lang_info['label']))

        results = await asyncio.gather(*tasks)
        
        # Combine articles from Hindi, Marathi, and English
        all_articles = []
        for article_list in results:
            all_articles.extend(article_list)

        # Fallback if strict timeframe (e.g. 2h) returned zero articles during keyword search
        if not is_trending and len(all_articles) == 0:
            tasks_fallback = []
            for lang_info in LANGUAGES:
                query = topic.strip()
                encoded_query = urllib.parse.quote(query)
                rss_url = f"https://news.google.com/rss/search?q={encoded_query}&hl={lang_info['hl']}&gl=IN&ceid={lang_info['ceid']}"
                tasks_fallback.append(fetch_feed_async(session, rss_url, lang_info['label']))
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

        if timeframe not in ['2h', '4h', '8h', '12h', '24h']:
            timeframe = '4h'

        articles = asyncio.run(fetch_all_feeds(topic, timeframe))
        return jsonify({'articles': articles, 'count': len(articles)})
    except Exception as e:
        print(f"Error in get_news route: {e}")
        return jsonify({'error': str(e), 'articles': []}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)