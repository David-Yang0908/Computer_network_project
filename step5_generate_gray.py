from PIL import Image, ImageOps, ImageEnhance
import os
import json

# ----------------------------------------------------
# 設定區塊
# ----------------------------------------------------

# 檔案路徑
GLOBAL_INPUT_FILE = 'json/all_tasks_input.json'      # 狀態檢查與更新
GLOBAL_OUTPUT_FILE = 'json/all_tasks_output.json'    # 路徑讀取與寫入

# 路徑設定
# 來源路徑現在主要從 Output 檔中讀取，此處僅定義目錄名
GRAY_OUTPUT_DIR = os.path.join("images", "donut_gray")      # 輸出 (灰階低對比圖)

# 影像處理參數
CONTRAST_REDUCTION = 0.5    # 0.5 = 減少 50% 對比度

# ----------------------------------------------------
# 輔助函數 (JSON 讀寫)
# ----------------------------------------------------

def read_json(file_name, default_if_missing):
    """讀取 JSON 檔案，支援 Dict 或 Array 預設值"""
    try:
        with open(file_name, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return default_if_missing
    except Exception as e:
        print(f"❌ 讀取 JSON 錯誤 ({file_name}): {e}")
        return {"error": str(e)}

def write_json(file_name, data):
    """寫入 JSON 檔案"""
    try:
        os.makedirs(os.path.dirname(file_name), exist_ok=True)
        with open(file_name, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"❌ 寫入 JSON 錯誤 ({file_name}): {e}")
        return False

# ----------------------------------------------------
# 影像處理函數 (保持不變)
# ----------------------------------------------------

def convert_and_reduce_contrast(input_path, output_path, contrast_factor=0.5):
    """
    讀取圖片，將其轉換為灰度圖，減少對比度，並保留 Alpha (透明度) 通道。
    """
    if not os.path.exists(input_path):
        print(f"   ❌ 找不到輸入檔案: {input_path}")
        return False

    try:
        # 確保輸出目錄存在
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        img = Image.open(input_path).convert("RGBA")
        
        R, G, B, A = img.split()
        
        rgb_img = Image.merge("RGB", (R, G, B))
        grayscale_img_L = rgb_img.convert('L') 
        
        # 調整對比度
        enhancer = ImageEnhance.Contrast(grayscale_img_L)
        adjusted_img_L = enhancer.enhance(contrast_factor) 
        
        # 轉回 RGB (灰階)
        final_grayscale_rgb = ImageOps.colorize(
            adjusted_img_L, 
            black="black", 
            white="white"
        ).convert("RGB")
        
        # 合併回去 (RGB + 原始 Alpha)
        final_img = Image.merge('RGBA', final_grayscale_rgb.split()[:3] + (A,))
        
        # 儲存結果
        final_img.save(output_path, 'PNG')
        return True

    except Exception as e:
        print(f"   ❌ 處理圖片失敗: {e}")
        return False

# ----------------------------------------------------
# 主程式
# ----------------------------------------------------

if __name__ == "__main__":
    
    # 1. 讀取資料
    all_tasks_input = read_json(GLOBAL_INPUT_FILE, [])          # Array
    all_tasks_output = read_json(GLOBAL_OUTPUT_FILE, {})      # Dict
    
    if isinstance(all_tasks_input, dict) and "error" in all_tasks_input: exit()
    if isinstance(all_tasks_output, dict) and "error" in all_tasks_output: exit()


    # 篩選待處理任務：
    # 條件：donut_status 為 true (有圖可轉) 且 gray_status 為 false (還沒轉)
    tasks_to_process_count = 0
    
    for t in all_tasks_input:
        tid = t.get('task_id')
        # 確保有 donut_status=True, gray_status=False 且 Output 中有 donut_path
        if t.get('donut_status') is True and not t.get('gray_status') and tid in all_tasks_output:
            if all_tasks_output[tid].get('donut_path'):
                tasks_to_process_count += 1

    if tasks_to_process_count == 0:
        print("\n==========================================================")
        print("💡 目前沒有需要轉換灰階的任務。")
        print("   (條件：donut_status=True 且 gray_status=False 且 Output 中有路徑)")
        print("==========================================================")
        exit()

    print(f"\n💡 識別到 {tasks_to_process_count} 個待處理任務。")
    processed_count = 0

    # 2. 迭代處理
    for task_data in all_tasks_input:
        
        tid = task_data.get('task_id')
        
        # 檢查是否符合處理條件
        if task_data.get('donut_status') is True and not task_data.get('gray_status') and tid in all_tasks_output:
            
            task_name = task_data.get('task_name')
            
            # 從 Output 取得輸入路徑
            input_donut_path = all_tasks_output[tid].get('donut_path')
            
            # 輸出路徑
            output_gray_path = os.path.join(GRAY_OUTPUT_DIR, f"donut_gray_{tid}.png")
            
            # 確保輸入路徑存在
            if not input_donut_path:
                print(f"⚠️ 任務 {tid}: Output 中缺少 donut_path，跳過。")
                continue

            print(f"\n--- 正在處理: {task_name} ({tid}) ---")

            # 執行轉換
            success = convert_and_reduce_contrast(input_donut_path, output_gray_path, CONTRAST_REDUCTION)
            
            if success:
                print(f"   ✅ 灰階轉換成功: {output_gray_path}")
                
                # 1. 更新 Input (Status)
                task_data['gray_status'] = True
                
                # 2. 更新 Output (Path)
                all_tasks_output[tid]['gray_path'] = output_gray_path
                
                processed_count += 1
            else:
                print("  ❌ 處理過程發生錯誤")

    # 3. 寫入更新
    if processed_count > 0:
        success_input = write_json(GLOBAL_INPUT_FILE, all_tasks_input)
        success_output = write_json(GLOBAL_OUTPUT_FILE, all_tasks_output)
        
        print(f"\n====================== 批次處理結果 =======================")
        print(f"🌑 成功轉換 {processed_count} 張灰階低對比圖。")
        print(f"💾 Input 狀態更新: {'成功' if success_input else '失敗'}")
        print(f"💾 Output 路徑更新: {'成功' if success_output else '失敗'}")
        print("==========================================================")
    else:
        print("\n💡 本次沒有成功產出新的灰階圖。")