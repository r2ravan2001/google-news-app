import time
import threading
import webview
from app import app

def run_flask():
    app.run(port=5000, host="127.0.0.1")

if __name__ == '__main__':
    t = threading.Thread(target=run_flask)
    t.daemon = True
    t.start()

    time.sleep(1.5)
    webview.create_window('India Newsroom Portal', 'http://127.0.0.1:5000', width=900, height=700)
    webview.start()