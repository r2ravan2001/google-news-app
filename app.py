from flask import Flask, jsonify, request, render_template
from flask_cors import CORS
import feedparser
import urllib.parse

app = Flask(__name__)
CORS(app)  # Enables cross-origin requests for all computers

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/get-news', methods=['GET'])
def get_news():
    topic = request.args.get('topic', 'latest')
    
    # Example Google News RSS Fetching Logic
    encoded_topic = urllib.parse.quote(topic)
    rss_url = f"https://news.google.com/rss/search?q={encoded_topic}&hl=en-IN&gl=IN&ceid=IN:en"
    
    feed = feedparser.parse(rss_url)
    articles = []
    
    for entry in feed.entries[:10]:
        articles.append({
            'title': entry.get('title', 'No Title'),
            'link': entry.get('link', '#'),
            'source': entry.get('source', {}).get('title', 'Google News'),
            'published': entry.get('published', 'Recently')
        })
        
    return jsonify({'articles': articles})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)