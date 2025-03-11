import json
import os

# データディレクトリを取得
data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')

# JSONデータの読み込み
try:
    # スキルデータ
    with open(os.path.join(data_dir, 'updated_mhwilds_skills.json'), 'r', encoding='utf-8') as f:
        skills_data = json.load(f)
except Exception as e:
    print(f"スキルデータ読み込みエラー: {e}")
    skills_data = []

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

def search_skill(text):
    """
    スキル名、装飾品名、または防具名から情報を検索
    """
    if not text:
        return "検索するスキル名、装飾品名、または防具名を入力してください。"
    
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
        return f"申し訳ありません、「{text}」に関する情報は見つかりませんでした。\nスキル名、装飾品名、または防具名を入力してください。"
