import os
import json
from flask import Flask, request, abort, jsonify
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage

from router import route_search

app = Flask(__name__)

# LINE API情報を環境変数から取得
line_bot_api = LineBotApi(os.environ.get('LINE_CHANNEL_ACCESS_TOKEN'))
handler = WebhookHandler(os.environ.get('LINE_CHANNEL_SECRET'))

# JSONデータの読み込み
def load_json_data():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(current_dir, 'data')
    
    try:
        # スキルデータ
        skills_path = os.path.join(data_dir, 'updated_mhwilds_skills.json')
        with open(skills_path, 'r', encoding='utf-8') as f:
            skills_data = json.load(f)
        
        # 弱点データ
        weakness_path = os.path.join(data_dir, 'mhwilds_weakness.json')
        with open(weakness_path, 'r', encoding='utf-8') as f:
            weakness_data = json.load(f)
        
        # 歴戦モンスターデータ
        tempered_path = os.path.join(data_dir, 'mhwilds_tempered_monsters.json')
        with open(tempered_path, 'r', encoding='utf-8') as f:
            tempered_data = json.load(f)
        
        return skills_data, weakness_data, tempered_data
    
    except Exception as e:
        print(f"データ読み込みエラー: {e}")
        return [], {"モンスター情報": []}, {"モンスター一覧": []}

# グローバル変数としてデータを読み込む
skills_data, weakness_data, tempered_data = load_json_data()

@app.route('/')
def index():
    return 'モンハンワイルズ 情報検索ボット'

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    
    return 'OK'

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    # 検索ルーターに処理を委譲
    route_search(
        event.message.text, 
        event.reply_token, 
        line_bot_api, 
        skills_data, 
        weakness_data, 
        tempered_data
    )

# サーバー起動
if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
