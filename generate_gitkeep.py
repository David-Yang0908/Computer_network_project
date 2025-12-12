import os

def create_empty_txt_for_ignored_folders(root_dir):
    # 定義被 gitignore 忽略的副檔名
    ignored_extensions = {'.png', '.jpg', '.jpeg', '.gif', '.bmp'}
    
    print("--- 開始掃描資料夾並補充 empty.txt ---")
    
    for dirpath, dirnames, filenames in os.walk(root_dir):
        # 排除 .git, venv, __pycache__ 等系統或環境目錄
        if '.git' in dirpath or 'venv' in dirpath or '__pycache__' in dirpath:
            continue
            
        # 判斷該資料夾是否包含「有效追蹤檔案」
        has_tracked_files = False
        
        for filename in filenames:
            # 如果檔案是 mask.png 或 empty.txt，視為有效檔案
            if filename == 'mask.png' or filename == 'empty.txt':
                has_tracked_files = True
                break # 只要有一個有效檔案，這個資料夾就安全，不用再檢查
            
            # 檢查副檔名是否在忽略清單中
            ext = os.path.splitext(filename)[1].lower()
            if ext not in ignored_extensions:
                # 發現一個非圖片的檔案 (如 .json, .py)，視為有效檔案
                has_tracked_files = True
                break
        
        # 如果資料夾內沒有任何「有效追蹤檔案」（即：全是忽略的圖片，或是完全空的）
        # 則產生 empty.txt
        if not has_tracked_files:
            empty_txt_path = os.path.join(dirpath, 'empty.txt')
            if not os.path.exists(empty_txt_path):
                try:
                    with open(empty_txt_path, 'w', encoding='utf-8') as f:
                        f.write("此檔案用於確保 Git 追蹤此空資料夾 (This file keeps this folder in git).")
                    print(f"✅ 已建立: {empty_txt_path}")
                except Exception as e:
                    print(f"❌ 無法建立 {empty_txt_path}: {e}")

if __name__ == "__main__":
    # 執行掃描當前目錄
    create_empty_txt_for_ignored_folders('.')
    print("--- 完成 ---")