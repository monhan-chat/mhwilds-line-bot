# wsgi.py
import sys
import os

# カレントディレクトリをPYTHONPATHに追加
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# アプリケーションをインポート
from app import app as application

# Gunicornは'application'という名前の変数も探すので、両方定義しておく
app = application
