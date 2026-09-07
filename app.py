import os
import urllib.parse
from flask import Flask, jsonify, request, render_template
from flask_cors import CORS
import feedparser

app = Flask(__name__)
CORS(app)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/get-news', methods=['GET'])
def get_news():
    try:
        topic = request.args.get('topic', 'latest').strip()
        timeframe = request.args.get('hours', '2h').strip()
        
        # Valid options: 2h, 4h, 8h, 12h, 24h
        if timeframe not in ['2h', '4h', '8h', '12h', '24h']:
            timeframe = '2h'

        # Construct query with Google News time restriction parameter (e.g. "Cricket when:2h")
        if topic.lower() == 'latest':
            query = f"when:{timeframe}"
        else:
            query = f"{topic} when:{timeframe}"

        encoded_query = urllib.parse.quote(query)
        rss_url = f"https://news.google.com/rss/search?q={encoded_query}&hl=en-IN&gl=IN&ceid=IN:en"
        
        feed = feedparser.parse(rss_url)
        
        articles = []
        for entry in feed.entries[:20]:
            articles.append({
                'title': getattr(entry, 'title', 'No Title'),
                'link': getattr(entry, 'link', '#'),
                'source': getattr(entry, 'source', {}).get('title', 'Google News'),
                'published': getattr(entry, 'published', 'Recently')
            })
            
        return jsonify({'articles': articles, 'count': len(articles)})
    except Exception as e:
        print(f"Error fetching news: {e}")
        return jsonify({'error': str(e), 'articles': []}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)