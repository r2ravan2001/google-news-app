import os
import sys
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

# 1. Helper function to find index.html when packaged in .exe
def get_base_path():
    if hasattr(sys, "_MEIPASS"):
        return sys._MEIPASS
    return os.path.dirname(os.path.abspath(__file__))

app = Flask(__name__)
CORS(app)

# 2. Add this route so Flask serves index.html at http://127.0.0.1:5000/
@app.route("/")
def serve_index():
    base_dir = get_base_path()
    return send_from_directory(base_dir, "index.html")

# --- YOUR EXISTING API CODE GOES HERE ---
# @app.route("/api/news")
# def get_news():
#     ...