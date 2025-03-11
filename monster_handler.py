import json
import os

# データディレクトリを取得
data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')

# JSONデータの読み込み
try:
    # 弱点データ
    with open(os.path.join(data_dir, 'mhwilds_weakness.json'), 'r', encoding='utf-8') as f:
        weakness_data = json.load(f)
    
    # 歴戦モンスターデータ
    with open(os.path.join(data_dir, 'mhwilds_tempered_monsters.json'), 'r', encoding='utf-8') as f:
        tempered_data = json.load(f)
except Exception as e:
    print(f"モンスターデータ読み込みエラー: {e}")
    weakness_data = {"モンスター情報": [], "属性アイコン": {}, "弱点レベル": {}}
    tempered_data = {"モンスター一覧": [], "歴戦危険度説明": {}, "危険度1": [], "危険度2": [], "危険度3": []}

# モンスター名の高速検索用辞書
weakness_monsters = {monster["モンスター名"]: monster for monster in weakness_data.get("モンスター情報", [])}
tempered_monsters = {monster["モンスター名"]: monster for monster in tempered_data.get("モンスター一覧", [])}

def search_monster_weakness(monster_name):
    """
    モンスターの弱点を検索する
    """
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
                reply_text += f"このモンスターには {', '.join([attr_icons.get(attr, '') + attr for attr in effective_attrs])} が効果的です。"
            else:
                reply_text += "このモンスターには特に弱点となる属性がありません。物理攻撃を中心に戦いましょう。"
        
        # 歴戦レベル
        if tempered_level:
            reply_text += f"\n\n▼歴戦の個体危険度: {tempered_level}{'★' * tempered_level}\n"
        
        return reply_text
    else:
        return f"申し訳ありません、「{monster_name}」の弱点情報は見つかりませんでした。"

def search_by_weakness(element):
    """
    特定の属性に弱いモンスターを検索する
    """
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
        return f"{element}に弱いモンスターは見つかりませんでした。"

def search_tempered_monsters(level):
    """
    特定の歴戦レベルのモンスターを検索する
    """
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
        return f"歴戦の個体 危険度{level}のモンスターは見つかりませんでした。"

def search_tempered_monster(monster_name):
    """
    特定のモンスターの歴戦レベルを検索する
    """
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
        return f"「{monster_name}」の歴戦情報は見つかりませんでした。"
