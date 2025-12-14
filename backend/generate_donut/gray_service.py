import os
from PIL import Image, ImageOps, ImageEnhance
import json

# ----------------------------------------------------
# 1. 核心設定與路徑 (從 step5_generate_gray.py 提取)
# ----------------------------------------------------

# 輸出目錄 (用於建構路徑)
GRAY_OUTPUT_DIR = os.path.join("images", "donut_gray")      

# 影像處理參數
CONTRAST_REDUCTION = 0.5    # 0.5 = 減少 50% 對比度

# ----------------------------------------------------
# 2. 圖像處理函數 (核心邏輯)
# ----------------------------------------------------

def convert_and_reduce_contrast(input_path, output_path, contrast_factor=CONTRAST_REDUCTION):
    """
    讀取圖片，將其轉換為灰度圖，減少對比度，並保留 Alpha (透明度) 通道。
    (來自 step5_generate_gray.py)
    """
    if not os.path.exists(input_path):
        return False, f"找不到輸入檔案: {input_path}"

    try:
        # 確保輸出目錄存在
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        # 1. 讀取圖片並分離 Alpha 通道
        img = Image.open(input_path).convert("RGBA")
        R, G, B, A = img.split()
        
        # 2. 將 RGB 部分轉為灰階 (L 模式)
        rgb_img = Image.merge("RGB", (R, G, B))
        grayscale_img_L = rgb_img.convert('L') 
        
        # 3. 調整對比度
        enhancer = ImageEnhance.Contrast(grayscale_img_L)
        adjusted_img_L = enhancer.enhance(contrast_factor) 
        
        # 4. 轉回 RGB 格式 (保留灰階顏色)
        final_grayscale_rgb = ImageOps.colorize(
            adjusted_img_L, 
            black="black", 
            white="white"
        ).convert("RGB")
        
        # 5. 合併回去 (RGB + 原始 Alpha)
        final_img = Image.merge('RGBA', final_grayscale_rgb.split()[:3] + (A,))
        
        # 6. 儲存結果
        final_img.save(output_path, 'PNG')
        return True, None

    except Exception as e:
        return False, f"處理圖片失敗: {e}"

# ----------------------------------------------------
# 3. Step 5 主執行函數 (供 app.py 呼叫)
# ----------------------------------------------------

def execute_step5(input_list, output_dict):
    """
    執行 Step 5 的核心邏輯：將彩色甜甜圈圖轉換為灰階低對比度圖。

    Args:
        input_list (list): 任務狀態列表。
        output_dict (dict): 任務內容/分數字典。

    Returns:
        tuple: (input_list, output_dict, processed_count, error_status)
    """
    processed_count = 0
    
    for task_input in input_list:
        tid = task_input.get('task_id')
        
        # 檢查條件：donut_status=True 且 gray_status=False
        if (task_input.get('donut_status') is True and 
            not task_input.get('gray_status') and 
            tid in output_dict):
            
            task_name = task_input.get('task_name', 'Unknown')
            input_donut_path = output_dict[tid].get('donut_path')
            
            if not input_donut_path:
                print(f"⚠️ 任務 {tid} 狀態為 'donut_status=True' 但缺少 donut_path。跳過。")
                continue
            
            # 輸出路徑
            output_gray_path = os.path.join(GRAY_OUTPUT_DIR, f"donut_gray_{tid}.png")

            print(f"--- 正在處理灰階化: {task_name} ({tid}) ---")

            # 執行轉換
            success, error_msg = convert_and_reduce_contrast(input_donut_path, output_gray_path)
            
            if success:
                # 1. 更新 Input (Status)
                task_input['gray_status'] = True
                
                # 2. 更新 Output (Path)
                output_dict[tid]['gray_path'] = output_gray_path
                
                processed_count += 1
            else:
                print(f"   ❌ 處理失敗: {error_msg}")
                
    return input_list, output_dict, processed_count, None