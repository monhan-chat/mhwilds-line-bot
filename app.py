import json
import os
import re
from flask import Flask, request, abort, jsonify
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage

# 以下の行を必ず保持してください - gunicornはこの変数を探します
app = Flask(__name__)

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

# JSONデータの読み込み用のディレクトリパス
data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')

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

※「ヘルプ」と入力するといつでもこの使い方が表示されるニャ！"""

    line_bot_api.reply_message(
        reply_token,
        TextSendMessage(text=help_text)
    )

# スキルデータ検索関数
def search_skill(text):
    """
    スキル名、装飾品名、または防具名から情報を検索
    """
    if not text:
        return "検索するスキル名、装飾品名、または防具名を入力してください。"
    
    try:
        # スキルデータの読み込み
        with open(os.path.join(data_dir, 'updated_mhwilds_skills.json'), 'r', encoding='utf-8') as f:
            skills_data = json.load(f)
            
        # 装飾品辞書と装備辞書を作成
        deco_to_skill = {}
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
            if result["レベル別効果"]:
                reply_text += "▼レベル別効果\n"
                for effect in sorted(result["レベル別効果"], key=lambda x: x["レベル"]):
                    reply_text += f"Lv{effect['レベル']}: {effect['効果']}\n"
                reply_text += "\n"
            
            # 装飾品情報がある場合
            if result["装飾品"]:
                reply_text += "▼装飾品\n"
                for deco in result["装飾品"]:
                    reply_text += f"・{deco.get('装飾品名', '')} (Lv{deco.get('装飾品Lv', '')})\n"
                reply_text += "\n"
            
            # 装備情報がある場合
            if "装備" in result and result["装備"]:
                reply_text += f"▼{result['スキル名']}が発動する装備(レベル/スロット数)\n"
                
                # スキルレベルが高い順に並べ替え
                sorted_armors = sorted(result["装備"], key=lambda x: x.get("スキルレベル", 0), reverse=True)
                for armor in sorted_armors:  # 全ての装備を表示
                    # スロット情報の取得
                    slots = armor.get('スロット', [])
                    
                    # スロット情報を含めた表示
                    if slots:
                        # スロットの数値をそのまま文字列に変換して表示
                        slot_str = '/'.join(map(str, slots))
                        reply_text += f"・{armor.get('防具名', '')} (Lv{armor.get('スキルレベル', '')}/{slot_str})\n"
                    else:
                        reply_text += f"・{armor.get('防具名', '')} (Lv{armor.get('スキルレベル', '')})\n"
            
            return reply_text
        else:
            # 結果が見つからなかった場合
            return f"ごめんニャ、「{text}」に関する情報が見つかんないニャ。寝不足かもなのニャ…\nスキル名、装飾品名、または防具名を入れてみるニャ！"
    except Exception as e:
        print(f"スキル検索エラー: {e}")
        return f"ごめんニャ、検索中にエラーが発生したニャ。"

# モンスターの弱点を検索
def search_monster_weakness(monster_name):
    try:
        with open(os.path.join(data_dir, 'mhwilds_weakness.json'), 'r', encoding='utf-8') as f:
            weakness_data = json.load(f)
            
        with open(os.path.join(data_dir, 'mhwilds_tempered_monsters.json'), 'r', encoding='utf-8') as f:
            tempered_data = json.load(f)
            
        # モンスター名の高速検索用辞書を作成
        weakness_monsters = {monster["モンスター名"]: monster for monster in weakness_data.get("モンスター情報", [])}
        tempered_monsters = {monster["モンスター名"]: monster for monster in tempered_data.get("モンスター一覧", [])}
        
        if not monster_name:
            return "モンスター名を入力してください。"
        
        # 完全一致検索
        weakness_info = weakness_monsters.get(monster_name)
        
        # 完全一致で見つからなければ部分一致検索
        if not weakness_info:
            matching_monsters = [monster for name, monster in weakness_monsters.items() if monster_name in name]
            if matching_monsters:
                weakness_info = matching_monsters[0]
        
        # 歴戦データから検索
        tempered_level = None
        if weakness_info:
            monster_name = weakness_info["モンスター名"]  # 正確なモンスター名を取得
            tempered_monster = tempered_monsters.get(monster_name)
            if tempered_monster:
                tempered_level = tempered_monster["歴戦危険度"]
        
        if weakness_info:
            # モンスター情報を作成
            reply_text = f"【{monster_name}の弱点情報】\n\n"
            
            # 弱点情報
            if "弱点" in weakness_info:
                # 属性アイコンと弱点レベルの辞書を取得
                attr_icons = weakness_data["属性アイコン"]
                weakness_levels = weakness_data["弱点レベル"]
                
                # 属性別の弱点を表示（強い弱点順にソート）
                sorted_weaknesses = sorted(
                    weakness_info["弱点"].items(),
                    key=lambda x: weakness_levels.get(x[1], 0),
                    reverse=True
                )
                
                # 弱点レベル記号の読み替え
                weakness_symbols = {
                    "◎": "特効",
                    "○": "弱点",
                    "△": "やや有効",
                    "×": "耐性",
                    "-": "不明"
                }
                
                reply_text += "▼弱点属性\n"
                for attr, level in sorted_weaknesses:
                    icon = attr_icons.get(attr, "")
                    level_text = weakness_symbols.get(level, level)
                    reply_text += f"{icon} {attr}: {level} ({level_text})\n"
                reply_text += "\n"
                
                # 装備推奨の補足情報を追加
                reply_text += "【攻略ヒント】\n"
                
                # 弱点が高い属性を抽出
                effective_attrs = [attr for attr, level in sorted_weaknesses if level in ["◎", "○"]]
                
                if effective_attrs:
                    reply_text += f"このモンスターには {', '.join([attr_icons.get(attr, '') + attr for attr in effective_attrs])} が効果的ニャ！"
                else:
                    reply_text += "このモンスターには特に弱点となる属性が見当たらないニャァ。。ま、なんとかなるニャ！"
            
            # 歴戦レベル
            if tempered_level:
                reply_text += f"\n\n▼歴戦の個体危険度: {tempered_level}{'★' * tempered_level}\n"
            
            return reply_text
        else:
            return f"ごめんニャ、「{monster_name}」の弱点情報が見つけられないニャ。"
    
    except Exception as e:
        print(f"モンスター弱点検索エラー: {e}")
        return "モンスター弱点情報の検索中にエラーが発生したニャ。"

# 属性に弱いモンスターを検索
def search_by_weakness(element):
    try:
        with open(os.path.join(data_dir, 'mhwilds_weakness.json'), 'r', encoding='utf-8') as f:
            weakness_data = json.load(f)
            
        # 弱点属性を持つモンスターを検索
        weak_monsters = []
        very_weak_monsters = []
        
        for monster in weakness_data.get("モンスター情報", []):
            if "弱点" in monster and element in monster["弱点"]:
                weakness_level = monster["弱点"][element]
                if weakness_level == "◎":
                    very_weak_monsters.append(monster["モンスター名"])
                elif weakness_level == "○":
                    weak_monsters.append(monster["モンスター名"])
        
        if weak_monsters or very_weak_monsters:
            reply_text = f"【{element}に弱いモンスター】\n\n"
            
            if very_weak_monsters:
                reply_text += "▼特効(◎)\n"
                reply_text += "・" + "\n・".join(sorted(very_weak_monsters)) + "\n\n"
            
            if weak_monsters:
                reply_text += "▼弱点(○)\n"
                reply_text += "・" + "\n・".join(sorted(weak_monsters))
            
            return reply_text
        else:
            return f"[{element}]に弱いモンスターはいないニャ…変だニャ…"
    
    except Exception as e:
        print(f"属性弱点検索エラー: {e}")
        return "属性弱点の検索中にエラーが発生したニャ。"

# 歴戦モンスターを検索
def search_tempered_monsters(level):
    try:
        with open(os.path.join(data_dir, 'mhwilds_tempered_monsters.json'), 'r', encoding='utf-8') as f:
            tempered_data = json.load(f)
            
        # 歴戦レベルに合致するモンスターを検索
        tempered_monsters_list = []
        
        for monster in tempered_data.get("モンスター一覧", []):
            if monster["歴戦危険度"] == level:
                tempered_monsters_list.append(monster["モンスター名"])
        
        if tempered_monsters_list:
            danger_desc = tempered_data["歴戦危険度説明"].get(str(level), f"危険度{level}")
            reply_text = f"【歴戦の個体 {danger_desc}】\n\n"
            reply_text += "・" + "\n・".join(sorted(tempered_monsters_list))
            
            return reply_text
        else:
            return f"歴戦の個体 危険度{level}のモンスターはいないのニャ。"
    
    except Exception as e:
        print(f"歴戦モンスター検索エラー: {e}")
        return "歴戦モンスターの検索中にエラーが発生したニャ。"

# 特定のモンスターの歴戦データを検索
def search_tempered_monster(monster_name):
    try:
        with open(os.path.join(data_dir, 'mhwilds_tempered_monsters.json'), 'r', encoding='utf-8') as f:
            tempered_data = json.load(f)
            
        # モンスター名の高速検索用辞書を作成
        tempered_monsters = {monster["モンスター名"]: monster for monster in tempered_data.get("モンスター一覧", [])}
        
        # 完全一致検索
        tempered_info = tempered_monsters.get(monster_name)
        
        # 完全一致で見つからなければ部分一致検索
        if not tempered_info:
            matching_monsters = [monster for name, monster in tempered_monsters.items() if monster_name in name]
            if matching_monsters:
                tempered_info = matching_monsters[0]
                monster_name = tempered_info["モンスター名"]  # 正確なモンスター名を取得
        
        if tempered_info:
            tempered_level = tempered_info["歴戦危険度"]
            danger_desc = tempered_data["歴戦危険度説明"].get(str(tempered_level), f"危険度{tempered_level}")
            
            reply_text = f"【{monster_name}の歴戦データ】\n\n"
            reply_text += f"▼歴戦の個体危険度: {tempered_level} {danger_desc}\n\n"
            
            # 同じ危険度のモンスターを表示
            same_level_monsters = [monster["モンスター名"] for monster in tempered_data["モンスター一覧"] 
                                  if monster["歴戦危険度"] == tempered_level and monster["モンスター名"] != monster_name]
            
            if same_level_monsters:
                reply_text += f"▼同じ危険度{tempered_level}のモンスター\n"
                reply_text += "・" + "\n・".join(sorted(same_level_monsters))
            
            return reply_text
        else:
            return f"「{monster_name}」の歴戦情報が見つからないニャ～。待ってみるニャ。"
    
    except Exception as e:
        print(f"歴戦モンスターデータ検索エラー: {e}")
        return "歴戦モンスターデータの検索中にエラーが発生したニャ。"

# サーバー起動（直接実行する場合のみ）
if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
