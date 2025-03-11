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

# モンスター名の正規化マッピング
MONSTER_ALIASES = {
    # "・"を除去したエイリアス
    "ラバラバリナ": "ラバラ・バリナ",
    "レダウ": "レ・ダウ",
    "ヌエグドラ": "ヌ・エグドラ",
    "ゾシア": "ゾ・シア",
    "ジンダハド": "ジン・ダハド",
    "ゴアマガラ": "ゴア・マガラ",
    
    # "亜種"を除去したエイリアス
    "護竜オドガロン": "護竜オドガロン亜種",
    "護竜アンジャナフ": "護竜アンジャナフ亜種"
}

# 自動的にエイリアスをさらに生成する
additional_aliases = {}
for name in MONSTER_NAMES:
    # "・"を含む名前には、"・"を除去したエイリアスを追加
    if "・" in name:
        alias = name.replace("・", "")
        if alias not in MONSTER_ALIASES and alias not in MONSTER_NAMES:
            additional_aliases[alias] = name
    
    # "亜種"を含む名前には、"亜種"を除去したエイリアスを追加
    if "亜種" in name:
        alias = name.replace("亜種", "")
        if alias not in MONSTER_ALIASES and alias not in MONSTER_NAMES:
            additional_aliases[alias] = name

# 手動定義したエイリアスを優先しつつ追加エイリアスを統合
MONSTER_ALIASES.update(additional_aliases)

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
    
    # モンスター名のエイリアス処理
    normalized_monster_name = MONSTER_ALIASES.get(text)
    if normalized_monster_name and normalized_monster_name in MONSTER_NAMES:
        result = search_monster_weakness(normalized_monster_name)
        line_bot_api.reply_message(reply_token, TextSendMessage(text=result))
        return
    
    # 3. 特定のパターンでの検索
    
    # 半角/全角スペースを半角に統一
    normalized_text = text.replace('　', ' ')
    
    # 弱点 属性のパターン
    if normalized_text.startswith('弱点 '):
        element_text = normalized_text[3:].strip()
        for element in ELEMENTS:
            if element_text == element or element_text == element + "属性":
                result = search_by_weakness(element + "属性")
                line_bot_api.reply_message(reply_token, TextSendMessage(text=result))
                return
    
    # 属性 弱点のパターン
    for element in ELEMENTS:
        # 火属性 弱点、火 弱点などのパターン
        if (normalized_text.startswith(element + "属性 弱") or 
            normalized_text.startswith(element + " 弱") or 
            normalized_text == element + "属性弱点" or 
            normalized_text == element + "弱点"):
            result = search_by_weakness(element + "属性")
            line_bot_api.reply_message(reply_token, TextSendMessage(text=result))
            return
    
    # 歴戦 1, 歴戦 2, 歴戦 3のパターン
    if normalized_text.startswith('歴戦 ') and len(normalized_text) >= 4:
        level_text = normalized_text[3]
        if level_text in ['1', '2', '3']:
            level = int(level_text)
            result = search_tempered_monsters(level)
            line_bot_api.reply_message(reply_token, TextSendMessage(text=result))
            return
    
    # 歴戦 モンスター名のパターン
    if normalized_text.startswith('歴戦 '):
        monster_name = normalized_text[3:].strip()
        # 正確なモンスター名のチェック
        for name in MONSTER_NAMES:
            if monster_name == name:
                result = search_tempered_monster(monster_name)
                line_bot_api.reply_message(reply_token, TextSendMessage(text=result))
                return
        
        # エイリアスのチェック
        normalized_monster_name = MONSTER_ALIASES.get(monster_name)
        if normalized_monster_name and normalized_monster_name in MONSTER_NAMES:
            result = search_tempered_monster(normalized_monster_name)
            line_bot_api.reply_message(reply_token, TextSendMessage(text=result))
            return
    
    # モンスター名 弱点のパターン
    for name in MONSTER_NAMES:
        if normalized_text == name + " 弱点" or normalized_text == name + "弱点":
            result = search_monster_weakness(name)
            line_bot_api.reply_message(reply_token, TextSendMessage(text=result))
            return
    
    # モンスター名のエイリアス + 弱点のパターン
    for alias, actual_name in MONSTER_ALIASES.items():
        if normalized_text == alias + " 弱点" or normalized_text == alias + "弱点":
            result = search_monster_weakness(actual_name)
            line_bot_api.reply_message(reply_token, TextSendMessage(text=result))
            return
    
    # 上記のどのパターンにも一致しない場合はスキル検索
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
