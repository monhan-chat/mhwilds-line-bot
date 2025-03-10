
import json
import os
import re
from flask import Flask, request, abort, jsonify
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage,
    ImageSendMessage, QuickReply, QuickReplyButton, MessageAction
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

# 画像URLを定義
WEAKNESS_IMAGE_URL = "https://github.com/monhan-chat/mhwilds-line-bot/blob/main/images/weakpoint.jpg?raw=true"
TEMPERED_IMAGE_URL = "https://github.com/monhan-chat/mhwilds-line-bot/blob/main/images/tempered.jpg?raw=true"

# ユーザーごとの設定を保存する辞書
# キー: ユーザーID、値: 設定辞書
user_settings = {}

# デフォルト設定
DEFAULT_SETTINGS = {
    "show_weakness_image": True,
    "show_tempered_image": True
}

# ユーザー設定を取得する関数
def get_user_settings(user_id):
    if user_id not in user_settings:
        # 新しいユーザーにはデフォルト設定をコピーして適用
        user_settings[user_id] = DEFAULT_SETTINGS.copy()
    return user_settings[user_id]

# JSONデータの読み込み
try:
    # ファイルパス候補
    skill_file_candidates = [
        'updated_mhwilds_skills.json',
        'mhwilds_skills.json',
        os.path.join('data', 'updated_mhwilds_skills.json'),
        os.path.join('data', 'mhwilds_skills.json'),
        '/opt/render/project/src/updated_mhwilds_skills.json',
        '/opt/render/project/src/mhwilds_skills.json'
    ]
    
    # 存在するファイルを使用
    skills_data = None
    used_file = None
    
    for file_path in skill_file_candidates:
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                skills_data = json.load(f)
                used_file = file_path
                print(f"スキルデータを読み込みました: {file_path}")
                break
    
    if skills_data is None:
        print("スキルデータファイルが見つかりません。")
        skills_data = []
    
    # 弱点データ
    weakness_data = {"モンスター情報": []}
    weakness_file_paths = [
        os.path.join('data', 'mhwilds_weakness.json'),
        'mhwilds_weakness.json',
        os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'mhwilds_weakness.json'),
        '/opt/render/project/src/mhwilds_weakness.json'
    ]
    
    for path in weakness_file_paths:
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                weakness_data = json.load(f)
            print(f"弱点データを読み込みました: {path}")
            break
    
    # 歴戦モンスターデータ
    tempered_data = {"モンスター一覧": []}
    tempered_file_paths = [
        os.path.join('data', 'mhwilds_tempered_monsters.json'),
        'mhwilds_tempered_monsters.json',
        os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'mhwilds_tempered_monsters.json'),
        '/opt/render/project/src/mhwilds_tempered_monsters.json'
    ]
    
    for path in tempered_file_paths:
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                tempered_data = json.load(f)
            print(f"歴戦データを読み込みました: {path}")
            break
    
    # データの概要を出力
    print(f"読み込まれたデータの概要:")
    print(f"- スキルデータ: {len(skills_data)} 件")
    print(f"- 弱点データ: {len(weakness_data.get('モンスター情報', []))} 件")
    print(f"- 歴戦データ: {len(tempered_data.get('モンスター一覧', []))} 件")
    
    # 現在のディレクトリ内のファイル一覧を表示（デバッグ用）
    print("現在のディレクトリ内のファイル:")
    for file in os.listdir('.'):
        print(f"- {file}")
    
    # dataディレクトリが存在する場合、その中も表示
    if os.path.exists('data'):
        print("dataディレクトリ内のファイル:")
        for file in os.listdir('data'):
            print(f"- {file}")
    
except Exception as e:
    print(f"データ読み込みエラー: {e}")
    import traceback
    traceback.print_exc()
    skills_data = []
    weakness_data = {"モンスター情報": []}
    tempered_data = {"モンスター一覧": []}

# 装飾品辞書の作成（装飾品名からスキル情報を検索できるように）
deco_to_skill = {}
try:
    if skills_data:
        for skill in skills_data:
            if "装飾品" in skill:
                for deco in skill["装飾品"]:
                    deco_name = deco.get("装飾品名", "")
                    if deco_name:
                        deco_to_skill[deco_name] = skill["スキル名"]
                        # 装飾品名のバリエーションも登録（「珠」を除いたものなど）
                        if "珠" in deco_name:
                            base_name = deco_name.replace("珠", "")
                            deco_to_skill[base_name] = skill["スキル名"]
        
        print(f"装飾品辞書を作成しました: {len(deco_to_skill)}件")
        # デバッグ用に一部表示
        sample_entries = list(deco_to_skill.items())[:10]
        print(f"装飾品辞書のサンプル: {sample_entries}")
    else:
        print("スキルデータがないため、装飾品辞書は空になります")
except Exception as e:
    print(f"装飾品辞書作成中にエラー: {e}")
    import traceback
    traceback.print_exc()

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
    user_id = event.source.user_id
    
    # 「画像オン」コマンドの処理 - 選択肢を表示
    if text == '画像オン':
        quick_reply = QuickReply(items=[
            QuickReplyButton(action=MessageAction(label="全ての画像をオン", text="画像表示オン")),
            QuickReplyButton(action=MessageAction(label="弱点画像のみオン", text="弱点画像オン")),
            QuickReplyButton(action=MessageAction(label="歴戦画像のみオン", text="歴戦画像オン"))
        ])
        
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(
                text="どの画像表示をオンにするニャ？",
                quick_reply=quick_reply
            )
        )
        return
    
    # 「画像オフ」コマンドの処理 - 選択肢を表示
    elif text == '画像オフ':
        quick_reply = QuickReply(items=[
            QuickReplyButton(action=MessageAction(label="全ての画像をオフ", text="画像表示オフ")),
            QuickReplyButton(action=MessageAction(label="弱点画像のみオフ", text="弱点画像オフ")),
            QuickReplyButton(action=MessageAction(label="歴戦画像のみオフ", text="歴戦画像オフ"))
        ])
        
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(
                text="どの画像表示をオフにするニャ？",
                quick_reply=quick_reply
            )
        )
        return
    
    # 「画像表示オン」コマンドの処理
    elif text == '画像表示オン':
        settings = get_user_settings(user_id)
        old_settings = settings.copy()  # 変更前の設定を保存
        
        settings["show_weakness_image"] = True
        settings["show_tempered_image"] = True
        
        # 変更内容を通知
        notification = "画像表示設定を変更しました:\n"
        if old_settings["show_weakness_image"] != settings["show_weakness_image"]:
            notification += "・弱点画像: オフ → オン\n"
        if old_settings["show_tempered_image"] != settings["show_tempered_image"]:
            notification += "・歴戦画像: オフ → オン"
        
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=notification)
        )
        return
    
    # 以下、各設定コマンドも同様に変更通知を追加
    elif text == '画像表示オフ':
        settings = get_user_settings(user_id)
        old_settings = settings.copy()
        
        settings["show_weakness_image"] = False
        settings["show_tempered_image"] = False
        
        notification = "画像表示設定を変更しました:\n"
        if old_settings["show_weakness_image"] != settings["show_weakness_image"]:
            notification += "・弱点画像: オン → オフ\n"
        if old_settings["show_tempered_image"] != settings["show_tempered_image"]:
            notification += "・歴戦画像: オン → オフ"
        
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=notification)
        )
        return
    
    elif text == '弱点画像オン':
        settings = get_user_settings(user_id)
        old_setting = settings["show_weakness_image"]
        settings["show_weakness_image"] = True
        
        if old_setting != settings["show_weakness_image"]:
            notification = "画像表示設定を変更しました:\n・弱点画像: オフ → オン"
        else:
            notification = "弱点画像表示はオンになってるニャ。"
        
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=notification)
        )
        return
    
    elif text == '弱点画像オフ':
        settings = get_user_settings(user_id)
        old_setting = settings["show_weakness_image"]
        settings["show_weakness_image"] = False
        
        if old_setting != settings["show_weakness_image"]:
            notification = "画像表示設定を変更しました:\n・弱点画像: オン → オフ"
        else:
            notification = "弱点画像表示はオフになってるニャ。"
        
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=notification)
        )
        return
    
    elif text == '歴戦画像オン':
        settings = get_user_settings(user_id)
        old_setting = settings["show_tempered_image"]
        settings["show_tempered_image"] = True
        
        if old_setting != settings["show_tempered_image"]:
            notification = "画像表示設定を変更しました:\n・歴戦画像: オフ → オン"
        else:
            notification = "歴戦画像表示はオンになってるニャ。"
        
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=notification)
        )
        return
    
    elif text == '歴戦画像オフ':
        settings = get_user_settings(user_id)
        old_setting = settings["show_tempered_image"]
        settings["show_tempered_image"] = False
        
        if old_setting != settings["show_tempered_image"]:
            notification = "画像表示設定を変更しました:\n・歴戦画像: オン → オフ"
        else:
            notification = "歴戦画像表示はオフになってるニャ。"
        
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=notification)
        )
        return
    
    # 設定確認コマンド
    elif text == '設定確認':
        settings = get_user_settings(user_id)
        settings_text = "【現在の設定】\n"
        settings_text += f"弱点画像表示: {'オン' if settings['show_weakness_image'] else 'オフ'}\n"
        settings_text += f"歴戦画像表示: {'オン' if settings['show_tempered_image'] else 'オフ'}"
        
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=settings_text)
        )
        return
    
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
        search_monster_weakness(event.reply_token, monster_name, user_id)
    elif weakness_match:
        element = weakness_match.group(1) + "属性"
        search_by_weakness(event.reply_token, element, user_id)
    elif tempered_match:
        level = int(tempered_match.group(1))
        search_tempered_monsters(event.reply_token, level, user_id)
    elif tempered_monster_match:
        monster_name = tempered_monster_match.group(1)
        search_tempered_monster(event.reply_token, monster_name, user_id)
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
        # 装飾品辞書に直接ある場合
        matching_decos = [deco for deco in deco_to_skill.keys() if text in deco]
        
        # 「珠」を追加した検索も試みる
        if not matching_decos and not text.endswith("珠"):
            text_with_suffix = text + "珠"
            matching_decos = [deco for deco in deco_to_skill.keys() if text_with_suffix in deco]
        
        if matching_decos:
            deco_name = matching_decos[0]  # 最初の一致した装飾品を使用
            skill_name = deco_to_skill[deco_name]
            for skill in skills_data:
                if skill["スキル名"] == skill_name:
                    result = skill
                    search_type = f"装飾品「{deco_name}」"
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
        
        # 防具情報がある場合
        if "装備" in result and result["装備"]:
            reply_text += "▼入手装備\n"
            # スキルレベルが高い順に並べ替え
            sorted_armors = sorted(result["装備"], key=lambda x: x.get("スキルレベル", 0), reverse=True)
            for armor in sorted_armors:  # 全ての装備を表示
                slot_info = ""
                if "スロット" in armor and armor["スロット"]:
                    slots = [str(s) for s in armor["スロット"]]
                    slot_info = f" [スロット:{','.join(slots)}]"
                reply_text += f"・{armor.get('防具名', '')} (Lv{armor.get('スキルレベル', '')}{slot_info})\n"
        
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

def search_monster_weakness(reply_token, monster_name, user_id):
    # ユーザー設定を取得
    settings = get_user_settings(user_id)
    show_image = settings["show_weakness_image"]
    
    # 弱点データから検索
    weakness_info = None
    for monster in weakness_data.get("モンスター情報", []):
        if monster["モンスター名"] == monster_name:
            weakness_info = monster
            break
    
    # 歴戦データから検索
    tempered_level = None
    for monster in tempered_data.get("モンスター一覧", []):
        if monster["モンスター名"] == monster_name:
            tempered_level = monster["歴戦危険度"]
            break
    
    if weakness_info:
        # モンスター情報を作成
        reply_text = f"【{monster_name}の弱点情報】\n\n"
        
        # 弱点情報
        if "弱点" in weakness_info:
            reply_text += "▼弱点属性\n"
            for element, value in weakness_info["弱点"].items():
                reply_text += f"{element}: {value}\n"
            reply_text += "\n"
        
        # 歴戦レベル
        if tempered_level:
            reply_text += f"▼歴戦の個体危険度: {tempered_level}{'★' * tempered_level}\n"
        
        # 画像表示設定に基づいて応答を作成
        if show_image:
            # テキストメッセージと画像メッセージを送信
            line_bot_api.reply_message(
                reply_token,
                [
                    TextSendMessage(text=reply_text),
                    ImageSendMessage(
                        original_content_url=WEAKNESS_IMAGE_URL,
                        preview_image_url=WEAKNESS_IMAGE_URL
                    )
                ]
            )
        else:
            # テキストのみを送信
            line_bot_api.reply_message(
                reply_token,
                TextSendMessage(text=reply_text)
            )
    else:
        line_bot_api.reply_message(
            reply_token,
            TextSendMessage(text=f"申し訳ないニャ、「{monster_name}」の弱点情報が見つけられなかったニャ…")
        )

def search_by_weakness(reply_token, element, user_id):
    # ユーザー設定を取得
    settings = get_user_settings(user_id)
    show_image = settings["show_weakness_image"]
    
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
        
        # 画像表示設定に基づいて応答を作成
        if show_image:
            # テキストメッセージと画像メッセージを送信
            line_bot_api.reply_message(
                reply_token,
                [
                    TextSendMessage(text=reply_text),
                    ImageSendMessage(
                        original_content_url=WEAKNESS_IMAGE_URL,
                        preview_image_url=WEAKNESS_IMAGE_URL
                    )
                ]
            )
        else:
            # テキストのみを送信
            line_bot_api.reply_message(
                reply_token,
                TextSendMessage(text=reply_text)
            )
    else:
        line_bot_api.reply_message(
            reply_token,
            TextSendMessage(text=f"{element}に弱いモンスターは見つかりませんでしたニャ。")
        )

def search_tempered_monsters(reply_token, level, user_id):
    # ユーザー設定を取得
    settings = get_user_settings(user_id)
    show_image = settings["show_tempered_image"]
    
    # 歴戦レベルに合致するモンスターを検索
    tempered_monsters = []
    
    for monster in tempered_data.get("モンスター一覧", []):
        if monster["歴戦危険度"] == level:
            tempered_monsters.append(monster["モンスター名"])
    
    if tempered_monsters:
        reply_text = f"【歴戦の個体 危険度{level}{'★' * level}】\n\n"
        reply_text += "・" + "\n・".join(sorted(tempered_monsters))
        
        # 画像表示設定に基づいて応答を作成
        if show_image:
            # テキストメッセージと画像メッセージを送信
            line_bot_api.reply_message(
                reply_token,
                [
                    TextSendMessage(text=reply_text),
                    ImageSendMessage(
                        original_content_url=TEMPERED_IMAGE_URL,
                        preview_image_url=TEMPERED_IMAGE_URL
                    )
                ]
            )
        else:
            # テキストのみを送信
            line_bot_api.reply_message(
                reply_token,
                TextSendMessage(text=reply_text)
            )
    else:
        line_bot_api.reply_message(
            reply_token,
            TextSendMessage(text=f"歴戦の個体 危険度{level}のモンスターはいないニャ！たぶん…")
        )

def search_tempered_monster(reply_token, monster_name, user_id):
    # ユーザー設定を取得
    settings = get_user_settings(user_id)
    show_image = settings["show_tempered_image"]
    
    # 特定のモンスターの歴戦レベルを検索
    tempered_level = None
    
    for monster in tempered_data.get("モンスター一覧", []):
        if monster["モンスター名"] == monster_name:
            tempered_level = monster["歴戦危険度"]
            break
    
    if tempered_level:
        reply_text = f"【{monster_name}】\n\n"
        reply_text += f"▼歴戦の個体危険度: {tempered_level}{'★' * tempered_level}\n"
        
        # 画像表示設定に基づいて応答を作成
        if show_image:
            # テキストメッセージと画像メッセージを送信
            line_bot_api.reply_message(
                reply_token,
                [
                    TextSendMessage(text=reply_text),
                    ImageSendMessage(
                        original_content_url=TEMPERED_IMAGE_URL,
                        preview_image_url=TEMPERED_IMAGE_URL
                    )
                ]
            )
        else:
            # テキストのみを送信
            line_bot_api.reply_message(
                reply_token,
                TextSendMessage(text=reply_text)
            )
    else:
        line_bot_api.reply_message(
            reply_token,
            TextSendMessage(text=f"「{monster_name}」の歴戦情報はわからないニャ。アップデートを待つニャ")
        )

def send_help_message(reply_token):
    help_text = """【モンハンワイルズ情報検索ボット】

■ 使い方
・スキル/装飾品検索: スキル名や装飾品名を入力
 例: 攻撃、見切り、匠珠

・モンスター弱点検索: モンスター名を入力
 例: チャタカブラ、リオレウス

・属性弱点検索: 「弱点 属性」と入力
 例: 弱点 火、弱点 雷

・歴戦モンスター検索: 「歴戦 レベル」と入力
 例: 歴戦 1、歴戦 3

■ 設定コマンド
・「画像オン」: 画像表示設定を選択
・「画像オフ」: 画像非表示設定を選択
・「設定確認」: 現在の設定を確認

※「ヘルプ」と入力するといつでもこの使い方が表示されます。"""

    line_bot_api.reply_message(
        reply_token,
        TextSendMessage(text=help_text)
    )

# サーバー起動
if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
