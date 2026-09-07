import os
import urllib.parse
from flask import Flask, jsonify, request, render_template
from flask_cors import CORS
import feedparser

app = Flask(__name__)
CORS(app)

@app.route('/')
def home():
    # Renders index.html from the /templates folder
    return render_template('index.html')

@app.route('/get-news', methods=['GET'])
def get_news():
    try:
        topic = request.args.get('topic', 'latest')
        encoded_topic = urllib.parse.quote(topic)
        
        rss_url = f"https://news.google.com/rss/search?q={encoded_topic}&hl=en-IN&gl=IN&ceid=IN:en"
        feed = feedparser.parse(rss_url)
        
        articles = []
        for entry in feed.entries[:15]:
            articles.append({
                'title': getattr(entry, 'title', 'No Title'),
                'link': getattr(entry, 'link', '#'),
                'source': getattr(entry, 'source', {}).get('title', 'Google News'),
                'published': getattr(entry, 'published', 'Recently')
            })
            
        return jsonify({'articles': articles})
    except Exception as e:
        print(f"Error fetching news: {e}")
        return jsonify({'error': str(e), 'articles': []}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)