import json
import os
import re
from flask import Flask, request, abort, jsonify
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage
)

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

# JSONデータの読み込み
try:
    data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
    
    # スキルデータ
    with open(os.path.join(data_dir, 'updated_mhwilds_skills.json'), 'r', encoding='utf-8') as f:
        skills_data = json.load(f)
    
    # 弱点データ
    with open(os.path.join(data_dir, 'mhwilds_weakness.json'), 'r', encoding='utf-8') as f:
        weakness_data = json.load(f)
    
    # 歴戦モンスターデータ
    with open(os.path.join(data_dir, 'mhwilds_tempered_monsters.json'), 'r', encoding='utf-8') as f:
        tempered_data = json.load(f)
except Exception as e:
    print(f"データ読み込みエラー: {e}")
    skills_data = []
    weakness_data = {"モンスター情報": []}
    tempered_data = {"モンスター一覧": []}

# 装飾品辞書の作成（装飾品名からスキル情報を検索できるように）
deco_to_skill = {}
# 装備辞書の作成（防具名からスキル情報を検索できるように）
armor_to_skill = {}

for skill in skills_data:
    # 装飾品から検索用辞書作成
    for deco in skill.get("装飾品", []):
        deco_name = deco.get("装飾品名", "")
        if deco_name:
            deco_to_skill[deco_name] = skill["スキル名"]
    
    # 装備から検索用辞書作成
    for armor in skill.get("装備", []):
        armor_name = armor.get("防具名", "")
        if armor_name:
            armor_to_skill[armor_name] = skill["スキル名"]

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
    
    # ヘルプメッセージ
    if text.lower() in ['ヘルプ', 'help', '使い方']:
        send_help_message(event.reply_token)
        return
    
    # モンスター弱点検索: 「弱点 チャタカブラ」「チャタカブラ 弱点」などのパターン
    monster_weakness_pattern = r'^(?:弱点\s*)?([ァ-ヶー・]+)(?:\s*弱点)?$'
    monster_weakness_match = re.match(monster_weakness_pattern, text)
    
    # 弱点属性検索: 「弱点 火」「弱点 水属性」「火属性」のようなパターン
    weakness_pattern = r'^(?:弱点\s*)?([火水雷氷龍])(?:属性)?$'
    weakness_match = re.match(weakness_pattern, text)
    
    # 歴戦検索: 「歴戦 1」「歴戦レベル2」のようなパターン
    tempered_pattern = r'^歴戦(?:レベル|の個体|危険度)?\s*([1-3])$'
    tempered_match = re.match(tempered_pattern, text)
    
    # 歴戦モンスター検索: 「歴戦 チャタカブラ」のようなパターン
    tempered_monster_pattern = r'^歴戦\s+([ァ-ヶー・]+)$'
    tempered_monster_match = re.match(tempered_monster_pattern, text)
    
    # 特定のパターンに基づいて処理
    if monster_weakness_match:
        monster_name = monster_weakness_match.group(1)
        search_monster_weakness(event.reply_token, monster_name)
    elif weakness_match:
        element = weakness_match.group(1) + "属性"
        search_by_weakness(event.reply_token, element)
    elif tempered_match:
        level = int(tempered_match.group(1))
        search_tempered_monsters(event.reply_token, level)
    elif tempered_monster_match:
        monster_name = tempered_monster_match.group(1)
        search_tempered_monster(event.reply_token, monster_name)
    else:
        # 上記パターンに合致しない場合は、スキル検索として処理
        search_skill(event.reply_token, text)

def search_skill(reply_token, text):
    # 検索結果
    result = None
    search_type = ""
    
    # スキル名で検索
    for skill in skills_data:
        if text in skill["スキル名"]:
            result = skill
            search_type = "スキル名"
            break
    
    # スキル名で見つからなければ装飾品名で検索（部分一致）
    if not result:
        matching_decos = [deco for deco in deco_to_skill.keys() if text in deco]
        if matching_decos:
            deco_name = matching_decos[0]  # 最初の一致した装飾品を使用
            skill_name = deco_to_skill[deco_name]
            for skill in skills_data:
                if skill["スキル名"] == skill_name:
                    result = skill
                    search_type = f"装飾品「{deco_name}」"
                    break
    
    # 装飾品で見つからなければ装備名で検索（部分一致）
    if not result:
        matching_armors = [armor for armor in armor_to_skill.keys() if text in armor]
        if matching_armors:
            armor_name = matching_armors[0]  # 最初の一致した防具を使用
            skill_name = armor_to_skill[armor_name]
            for skill in skills_data:
                if skill["スキル名"] == skill_name:
                    result = skill
                    search_type = f"装備「{armor_name}」"
                    break
    
    # 検索結果に応じてメッセージを返信
    if result:
        # スキル情報を整形して返信
        reply_text = f"【{search_type}での検索結果】\n"
        reply_text += f"スキル名: {result['スキル名']}\n\n"
        reply_text += f"▼効果\n{result['効果']}\n\n"
        reply_text += f"▼最大レベル: {result['最大レベル']}\n\n"
        
        # レベル別効果がある場合
        if result.get("レベル別効果"):
            reply_text += "▼レベル別効果\n"
            for effect in sorted(result["レベル別効果"], key=lambda x: x["レベル"]):
                reply_text += f"Lv{effect['レベル']}: {effect['効果']}\n"
            reply_text += "\n"
        
        # 装飾品情報がある場合
        if result.get("装飾品"):
            reply_text += "▼装飾品\n"
            for deco in result["装飾品"]:
                reply_text += f"・{deco.get('装飾品名', '')} (Lv{deco.get('装飾品Lv', '')})\n"
            reply_text += "\n"
        
        # 装備情報がある場合
        if result.get("装備"):
            reply_text += "▼入手装備(レベル/スロット数)\n"
            # スキルレベルが高い順、スロット数が多い順に並べ替え
            sorted_armors = sorted(
                result["装備"], 
                key=lambda x: (x.get('スキルレベル', 0), len(x.get('スロット', []))), 
                reverse=True
            )
            
            for armor in sorted_armors:
                # スロット情報の可視化
                slots = armor.get('スロット', [])
                
                # スロット情報を含めた表示
                if slots:
                    # スロットの数値をそのまま文字列に変換して表示
                    slot_str = '/'.join(map(str, slots))
                    reply_text += f"・{armor.get('防具名', '')} (Lv{armor.get('スキルレベル', '')}/{slot_str})\n"
                else:
                    reply_text += f"・{armor.get('防具名', '')} (Lv{armor.get('スキルレベル', '')})\n"
        
        line_bot_api.reply_message(
            reply_token,
            TextSendMessage(text=reply_text)
        )
    else:
        # 結果が見つからなかった場合
        line_bot_api.reply_message(
            reply_token,
            TextSendMessage(text=f"申し訳ありません、「{text}」に関する情報は見つかりませんでした。\nスキル名、装飾品名、モンスター名、または「ヘルプ」と入力してください。")
        )

# 以下の関数は前のコードと同じなので省略（search_monster_weakness, search_by_weakness, search_tempered_monsters, search_tempered_monster, send_help_message）

# サーバー起動
if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
