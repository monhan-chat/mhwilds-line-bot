from linebot.models import TextSendMessage

def search_monster_weakness(reply_token, monster_name, line_bot_api, weakness_data, tempered_data):
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
        
        line_bot_api.reply_message(
            reply_token,
            TextSendMessage(text=reply_text)
        )
    else:
        line_bot_api.reply_message(
            reply_token,
            TextSendMessage(text=f"申し訳ありません、「{monster_name}」の弱点情報は見つかりませんでした。")
        )

def search_by_weakness(reply_token, element, line_bot_api, weakness_data):
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
        
        line_bot_api.reply_message(
            reply_token,
            TextSendMessage(text=reply_text)
        )
    else:
        line_bot_api.reply_message(
            reply_token,
            TextSendMessage(text=f"{element}に弱いモンスターは見つかりませんでした。")
        )

def search_tempered_monsters(reply_token, level, line_bot_api, tempered_data):
    # 歴戦レベルに合致するモンスターを検索
    tempered_monsters = []
    
    for monster in tempered_data.get("モンスター一覧", []):
        if monster["歴戦危険度"] == level:
            tempered_monsters.append(monster["モンスター名"])
    
    if tempered_monsters:
        reply_text = f"【歴戦の個体 危険度{level}{'★' * level}】\n\n"
        reply_text += "・" + "\n・".join(sorted(tempered_monsters))
        
        line_bot_api.reply_message(
            reply_token,
            TextSendMessage(text=reply_text)
        )
    else:
        line_bot_api.reply_message(
            reply_token,
            TextSendMessage(text=f"歴戦の個体 危険度{level}のモンスターは見つかりませんでした。")
        )

def search_tempered_monster(reply_token, monster_name, line_bot_api, tempered_data):
    # 特定のモンスターの歴戦レベルを検索
    tempered_level = None
    
    for monster in tempered_data.get("モンスター一覧", []):
        if monster["モンスター名"] == monster_name:
            tempered_level = monster["歴戦危険度"]
            break
    
    if tempered_level:
        reply_text = f"【{monster_name}】\n\n"
        reply_text += f"▼歴戦の個体危険度: {tempered_level}{'★' * tempered_level}\n"
        
        line_bot_api.reply_message(
            reply_token,
            TextSendMessage(text=reply_text)
        )
    else:
        line_bot_api.reply_message(
            reply_token,
            TextSendMessage(text=f"「{monster_name}」の歴戦情報は見つかりませんでした。")
        )
