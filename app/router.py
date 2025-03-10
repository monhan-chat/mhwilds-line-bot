import re
from linebot.models import TextSendMessage

from skill_search import search_skill
from monster_search import (
    search_monster_weakness, 
    search_by_weakness, 
    search_tempered_monsters, 
    search_tempered_monster
)

def send_help_message(reply_token, line_bot_api):
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

※「ヘルプ」と入力するといつでもこの使い方が表示されます。"""

    line_bot_api.reply_message(
        reply_token,
        TextSendMessage(text=help_text)
    )

def route_search(text, reply_token, line_bot_api, skills_data, weakness_data, tempered_data):
    # ヘルプメッセージ
    if text.lower() in ['ヘルプ', 'help', '使い方']:
        send_help_message(reply_token, line_bot_api)
        return
    
    # モンスター名のリストを作成（モンスター一覧から）
    monster_names = [monster["モンスター名"] for monster in tempered_data.get("モンスター一覧", [])]
    
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
        # モンスター名リストに存在する場合のみ弱点検索
        if monster_name in monster_names:
            search_monster_weakness(
                reply_token, 
                monster_name, 
                line_bot_api, 
                weakness_data, 
                tempered_data
            )
        else:
            search_skill(
                reply_token, 
                text, 
                line_bot_api, 
                skills_data
            )
    elif weakness_match:
        element = weakness_match.group(1) + "属性"
        search_by_weakness(
            reply_token, 
            element, 
            line_bot_api, 
            weakness_data
        )
    elif tempered_match:
        level = int(tempered_match.group(1))
        search_tempered_monsters(
            reply_token, 
            level, 
            line_bot_api, 
            tempered_data
        )
    elif tempered_monster_match:
        monster_name = tempered_monster_match.group(1)
        # モンスター名リストに存在する場合のみ歴戦検索
        if monster_name in monster_names:
            search_tempered_monster(
                reply_token, 
                monster_name, 
                line_bot_api, 
                tempered_data
            )
        else:
            search_skill(
                reply_token, 
                text, 
                line_bot_api, 
                skills_data
            )
    else:
        # 上記パターンに合致しない場合は、スキル検索として処理
        search_skill(
            reply_token, 
            text, 
            line_bot_api, 
            skills_data
        )
