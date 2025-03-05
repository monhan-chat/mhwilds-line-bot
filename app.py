import json
import os
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage, FlexSendMessage
)

app = Flask(__name__)

# 環境変数からLINE APIの認証情報を取得
# 後でデプロイ先で設定します
line_bot_api = LineBotApi(os.environ.get('LINE_CHANNEL_ACCESS_TOKEN'))
handler = WebhookHandler(os.environ.get('LINE_CHANNEL_SECRET'))

# スキルデータの読み込み
# こちらは実際のデプロイ時にはデプロイ先にJSONファイルをアップロードする必要があります
with open('mhwilds_skills.json', 'r', encoding='utf-8') as f:
    skills_data = json.load(f)

# 装飾品辞書の作成（装飾品名からスキル情報を検索できるように）
deco_to_skill = {}
for skill in skills_data:
    for deco in skill.get("装飾品", []):
        deco_name = deco.get("装飾品名", "")
        if deco_name:
            deco_to_skill[deco_name] = skill["スキル名"]

# Webhookからのリクエストを処理するルート
@app.route("/callback", methods=['POST'])
def callback():
    # X-Line-Signatureヘッダーを取得
    signature = request.headers['X-Line-Signature']
    
    # リクエストボディを取得
    body = request.get_data(as_text=True)
    
    try:
        # webhookの内容を処理
        handler.handle(body, signature)
    except InvalidSignatureError:
        # 署名が無効な場合は400エラーを返す
        abort(400)
    
    # 正常終了
    return 'OK'

# テキストメッセージを受信したときの処理
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    # 受信したテキスト
    text = event.message.text
    
    # スキル名で検索
    result = None
    for skill in skills_data:
        if text in skill["スキル名"]:
            result = skill
            break
    
    # スキル名で見つからなければ装飾品名で検索
    if not result:
        skill_name = deco_to_skill.get(text)
        if skill_name:
            for skill in skills_data:
                if skill["スキル名"] == skill_name:
                    result = skill
                    break
    
    # 検索結果に応じてメッセージを返信
    if result:
        # スキル情報を整形して返信
        reply_text = f"【{result['スキル名']}】\n\n"
        reply_text += f"▼効果\n{result['効果']}\n\n"
        reply_text += f"▼最大レベル: {result['最大レベル']}\n\n"
        
        # レベル別効果がある場合
        if result["レベル別効果"]:
            reply_text += "▼レベル別効果\n"
            for effect in result["レベル別効果"]:
                reply_text += f"Lv{effect['レベル']}: {effect['効果']}\n"
            reply_text += "\n"
        
        # 装飾品情報がある場合
        if result["装飾品"]:
            reply_text += "▼装飾品\n"
            for deco in result["装飾品"]:
                reply_text += f"・{deco['装飾品名']} (Lv{deco['装飾品Lv']})\n"
        
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=reply_text)
        )
    else:
        # 結果が見つからなかった場合
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=f"申し訳ありません、「{text}」に関する情報は見つかりませんでした。\nスキル名または装飾品名を入力してください。")
        )

# Herokuなどで実行する場合の設定
if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
