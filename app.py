import json
import os
import re
from flask import Flask, request, abort, jsonify
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage

# スキル検索モジュールのインポート
from skills_handler import search_skill
from monster_handler import (search_monster_weakness, search_by_weakness,
                          search_tempered_monsters, search_tempered_monster)

# モンスター名リストの定義
MONSTER_NAMES = [
    "チャタカブラ", "ケマトリス", "ラバラ・バリナ", "ババコンガ", "バーラハーラ",
    "ドシャグマ", "ウズトゥナ", "ププロポル", "レ・ダウ", "ネルスキュラ",
    "ヒラバミ", "アジャラカン", "ヌ・エグドラ", "護竜ドシャグマ", "護竜リオレウス",
    "護竜アルシュベルド", "ジン・ダハド", "護竜オドガロン亜種", "シーウー", "ゾ・シア",
    "イャンクック", "ゲリョス", "リオレイア", "リオレウス", "ドドブランゴ",
    "グラビモス", "護竜アンジャナフ亜種", "ゴア・マガラ", "アルシュベルド", "タマミツネ"
]

# 属性リスト
ELEMENTS = ["火", "水", "雷", "氷", "龍"]

app = Flask(__name__)

# 基本的なルート設定
@app.route('/')
def index():
    return 'モンハンワイルズ 情報検索ボット（スキル・装飾品・弱点・歴戦モンスター）'

# 明示的な404ハンドラー
@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Not found'}), 404

# LINE API情報を環境変数から取得
line_bot_api = LineBotApi(os.environ.get('LINE_CHANNEL_ACCESS_TOKEN'))
handler = WebhookHandler(os.environ.get('LINE_CHANNEL_SECRET'))

@app.route("/callback", methods=['POST'])
def callback():
    # 署名検証
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    
    return 'OK'

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    text = event.message.text
    reply_token = event.reply_token
    
    # ヘルプメッセージ
    if text.lower() in ['ヘルプ', 'help', '使い方']:
        send_help_message(reply_token)
        return
    
    # 1. 明示的なコマンド構文を最初にチェック
    
    # 弱点検索: 「弱点:チャタカブラ」のようなパターン
    if text.startswith('弱点:') or text.startswith('弱点：'):
        monster_name = text[3:].strip()
        result = search_monster_weakness(monster_name)
        line_bot_api.reply_message(reply_token, TextSendMessage(text=result))
        return
        
    # 歴戦検索: 「歴戦:リオレウス」のようなパターン
    if text.startswith('歴戦:') or text.startswith('歴戦：'):
        monster_name = text[3:].strip()
        result = search_tempered_monster(monster_name)
        line_bot_api.reply_message(reply_token, TextSendMessage(text=result))
        return
    
    # 2. 単一ワードの場合はマッチングを試みる
    
    # モンスター名が直接入力された場合 (リストに存在する場合のみ)
    if text in MONSTER_NAMES:
        result = search_monster_weakness(text)
        line_bot_api.reply_message(reply_token, TextSendMessage(text=result))
        return
    
    # 3. パターンマッチングによる検索
    
    # モンスター弱点検索: 「チャタカブラ 弱点」などのパターン
    monster_weakness_pattern = r'^([ァ-ヶー・]+)\s*弱点$'
    monster_weakness_match = re.match(monster_weakness_pattern, text)
    
    # 弱点属性検索: 「弱点 火」「弱点 水属性」「火属性弱点」「火属性 弱い」「火 弱点」のようなパターン
    weakness_pattern = r'^(?:弱点\s+([火水雷氷龍])(?:属性)?|([火水雷氷龍])(?:\s*属性)?\s*(?:弱点|弱い))
    
    # 歴戦検索: 「歴戦 1」「歴戦レベル2」のようなパターン
    tempered_pattern = r'^歴戦(?:レベル|の個体|危険度)?\s*([1-3])$'
    tempered_match = re.match(tempered_pattern, text)
    
    # 歴戦モンスター検索: 「歴戦 チャタカブラ」のようなパターン
    tempered_monster_pattern = r'^歴戦\s+([ァ-ヶー・]+)$'
    tempered_monster_match = re.match(tempered_monster_pattern, text)
    
    # パターンマッチング結果に基づく処理
    if monster_weakness_match:
        monster_name = monster_weakness_match.group(1)
        result = search_monster_weakness(monster_name)
        line_bot_api.reply_message(reply_token, TextSendMessage(text=result))
    elif weakness_match:
        # 第1グループまたは第2グループのいずれかに属性名が含まれる
        element_name = weakness_match.group(1) or weakness_match.group(2)
        element = element_name + "属性"
        result = search_by_weakness(element)
        line_bot_api.reply_message(reply_token, TextSendMessage(text=result))
    elif tempered_match:
        level = int(tempered_match.group(1))
        result = search_tempered_monsters(level)
        line_bot_api.reply_message(reply_token, TextSendMessage(text=result))
    elif tempered_monster_match:
        monster_name = tempered_monster_match.group(1)
        result = search_tempered_monster(monster_name)
        line_bot_api.reply_message(reply_token, TextSendMessage(text=result))
    else:
        # 他のパターンに一致しない場合はスキル検索を実行
        result = search_skill(text)
        line_bot_api.reply_message(reply_token, TextSendMessage(text=result))

def send_help_message(reply_token):
    help_text = """【モンハンワイルズ情報検索ボット】

■ 使い方
・スキル/装飾品検索: スキル名や装飾品名を入力
 例: 攻撃、見切り、匠珠、アイテム、火属性

・モンスター弱点検索: モンスター名を入力
 例: チャタカブラ、リオレウス
 または「弱点:モンスター名」と入力

・属性弱点検索: 属性＋弱点の組み合わせで入力
 例: 弱点 火、火 弱点、火弱点、火属性弱点、火属性 弱い

・歴戦モンスター検索: 「歴戦 レベル」と入力
 例: 歴戦 1、歴戦 3
 または「歴戦 モンスター名」と入力

※「ヘルプ」と入力するといつでもこの使い方が表示されます。"""

    line_bot_api.reply_message(
        reply_token,
        TextSendMessage(text=help_text)
    )

# サーバー起動
if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)

    weakness_match = re.match(weakness_pattern, text)
    
    # 歴戦検索: 「歴戦 1」「歴戦レベル2」のようなパターン
    tempered_pattern = r'^歴戦(?:レベル|の個体|危険度)?\s*([1-3])$'
    tempered_match = re.match(tempered_pattern, text)
    
    # 歴戦モンスター検索: 「歴戦 チャタカブラ」のようなパターン
    tempered_monster_pattern = r'^歴戦\s+([ァ-ヶー・]+)$'
    tempered_monster_match = re.match(tempered_monster_pattern, text)
    
    # パターンマッチング結果に基づく処理
    if monster_weakness_match:
        monster_name = monster_weakness_match.group(1)
        result = search_monster_weakness(monster_name)
        line_bot_api.reply_message(reply_token, TextSendMessage(text=result))
    elif weakness_match:
        # 第1グループまたは第2グループのいずれかに属性名が含まれる
        element = (weakness_match.group(1) or weakness_match.group(2)) + "属性"
        result = search_by_weakness(element)
        line_bot_api.reply_message(reply_token, TextSendMessage(text=result))
    elif tempered_match:
        level = int(tempered_match.group(1))
        result = search_tempered_monsters(level)
        line_bot_api.reply_message(reply_token, TextSendMessage(text=result))
    elif tempered_monster_match:
        monster_name = tempered_monster_match.group(1)
        result = search_tempered_monster(monster_name)
        line_bot_api.reply_message(reply_token, TextSendMessage(text=result))
    else:
        # 他のパターンに一致しない場合はスキル検索を実行
        result = search_skill(text)
        line_bot_api.reply_message(reply_token, TextSendMessage(text=result))

def send_help_message(reply_token):
    help_text = """【モンハンワイルズ情報検索ボット】

■ 使い方
・スキル/装飾品検索: スキル名や装飾品名を入力
 例: 攻撃、見切り、匠珠、アイテム、火属性

・モンスター弱点検索: モンスター名を入力
 例: チャタカブラ、リオレウス
 または「弱点:モンスター名」と入力

・属性弱点検索: 属性＋弱点の組み合わせで入力
 例: 弱点 火、火属性弱点、火属性 弱い

・歴戦モンスター検索: 「歴戦 レベル」と入力
 例: 歴戦 1、歴戦 3
 または「歴戦 モンスター名」と入力

※「ヘルプ」と入力するといつでもこの使い方が表示されます。"""

    line_bot_api.reply_message(
        reply_token,
        TextSendMessage(text=help_text)
    )

# サーバー起動
if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
