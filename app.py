import os
import sys
import asyncio
import feedparser
import urllib.parse
import aiohttp
from datetime import datetime
from email.utils import parsedate_to_datetime
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

def get_base_path():
    if hasattr(sys, "_MEIPASS"):
        return sys._MEIPASS
    return os.path.dirname(os.path.abspath(__file__))

app = Flask(__name__)
CORS(app)

LANGUAGES = [
    {'lang': 'English', 'hl': 'en-IN', 'gl': 'IN', 'ceid': 'IN:en'},
    {'lang': 'Hindi', 'hl': 'hi-IN', 'gl': 'IN', 'ceid': 'IN:hi'},
    {'lang': 'Marathi', 'hl': 'mr-IN', 'gl': 'IN', 'ceid': 'IN:mr'}
]

@app.route("/")
def serve_index():
    base_dir = get_base_path()
    return send_from_directory(base_dir, "index.html")

async def fetch_feed(session, topic, hours, lang_info):
    search_query = f"{topic} when:{hours}"
    encoded_query = urllib.parse.quote(search_query)
    
    url = f"https://news.google.com/rss/search?q={encoded_query}&hl={lang_info['hl']}&gl={lang_info['gl']}&ceid={lang_info['ceid']}"
    
    async with session.get(url) as response:
        content = await response.text()
        feed = feedparser.parse(content)
        
        articles = []
        for entry in feed.entries:
            pub_date = None
            if hasattr(entry, 'published'):
                try:
                    pub_date = parsedate_to_datetime(entry.published).timestamp()
                except Exception:
                    pub_date = 0

            articles.append({
                'title': entry.title,
                'link': entry.link,
                'published': getattr(entry, 'published', 'Recently'),
                'source': entry.source.title if 'source' in entry else 'India News',
                'language': lang_info['lang'],
                'timestamp': pub_date or 0
            })
        return articles

@app.route('/api/news', methods=['GET'])
def get_multilingual_news():
    topic = request.args.get('q', 'latest')
    hours = request.args.get('hours', '4h')

    async def gather_all():
        async with aiohttp.ClientSession() as session:
            tasks = [fetch_feed(session, topic, hours, lang) for lang in LANGUAGES]
            results = await asyncio.gather(*tasks)
            all_articles = [article for sublist in results for article in sublist]
            return all_articles

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    articles = loop.run_until_complete(gather_all())

    articles.sort(key=lambda x: x['timestamp'], reverse=True)

    return jsonify({
        'status': 'success',
        'query': topic,
        'country': 'India',
        'languages': ['English', 'Hindi', 'Marathi'],
        'timeframe': hours,
        'total_results': len(articles),
        'articles': articles
    })

if __name__ == '__main__':
    app.run(port=5000, debug=True)