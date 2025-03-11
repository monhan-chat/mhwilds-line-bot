import os
import sys

def setup_data_directory():
    """データディレクトリとシンボリックリンクを作成"""
    # カレントディレクトリ
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # dataディレクトリのパス
    data_dir = os.path.join(current_dir, 'data')
    
    # dataディレクトリが存在しない場合は作成
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
        print(f"データディレクトリを作成しました: {data_dir}")
    else:
        print(f"データディレクトリは既に存在します: {data_dir}")
    
    print("\nJSONファイルを data/ ディレクトリに配置してください:")
    print("- updated_mhwilds_skills.json")
    print("- mhwilds_weakness.json")
    print("- mhwilds_tempered_monsters.json")

if __name__ == "__main__":
    setup_data_directory()
