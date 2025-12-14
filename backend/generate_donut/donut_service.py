import os
import json
from PIL import Image, ImageDraw, ImageOps
import time

# ----------------------------------------------------
# 1. 核心設定與路徑 (從 step4_generate_donut.py 提取)
# ----------------------------------------------------

# 固定遮罩圖片路徑 (前景)
MASK_PATH = os.path.join("images", "mask.png")

# 輸出目錄 (用於建構路徑，實際寫入由 app.py 控制)
DONUT_OUTPUT_DIR = os.path.join("images", "donut")  

# 參數設定 (從 step4/6/7 統一)
INNER_RADIUS_RATIO = 0.5  # 內圓半徑比例

# ----------------------------------------------------
# 2. 圖像處理函數 (核心邏輯)
# ----------------------------------------------------

def merge_images_with_mask(target_image_path, mask_path):
    """
    將遮罩圖片疊加到目標圖片上。回傳合併後的 PIL Image 物件。
    (來自 step4_generate_donut.py)
    """
    try:
        if not os.path.exists(target_image_path):
            return None, f"找不到背景圖片: {target_image_path}"
            
        target_img = Image.open(target_image_path).convert("RGBA")
        target_size = target_img.size

        if not os.path.exists(mask_path):
            return None, f"找不到遮罩圖片: {mask_path}"

        mask_img = Image.open(mask_path).convert("RGBA")
        
        # 確保遮罩與目標圖片尺寸相同
        if mask_img.size != target_size:
            resized_mask = mask_img.resize(target_size, Image.Resampling.LANCZOS)
        else:
            resized_mask = mask_img
            
        # 使用 Alpha 通道合成
        merged_img = Image.alpha_composite(target_img, resized_mask)
        
        return merged_img, None

    except Exception as e:
        return None, f"圖片合併失敗: {e}"


def crop_to_donut(pil_image, output_path, inner_radius_ratio=INNER_RADIUS_RATIO):
    """ 
    將 PIL Image 物件裁剪成甜甜圈形狀並存檔。
    (來自 step4_generate_donut.py)
    """
    try:
        img = pil_image.convert("RGBA")
        width, height = img.size

        R = min(width, height) // 2
        r = int(R * inner_radius_ratio)
        cx = width // 2
        cy = height // 2
        
        # 建立甜甜圈形狀的 Alpha 遮罩
        mask = Image.new('L', (width, height), 0)
        draw = ImageDraw.Draw(mask)
        
        # 繪製外圓 (白色 255)
        draw.ellipse((cx - R, cy - R, cx + R, cy + R), fill=255)
        # 挖空內圓 (黑色 0)
        draw.ellipse((cx - r, cy - r, cx + r, cy + r), fill=0)
        
        # 將遮罩應用為圖片的 Alpha 通道
        img.putalpha(mask)
        
        # 裁切到甜甜圈邊界
        crop_area = (cx - R, cy - R, cx + R, cy + R)
        cropped_img = img.crop(crop_area)
        
        # 儲存
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        cropped_img.save(output_path, 'PNG')
        return True, None
        
    except Exception as e:
        return False, f"甜甜圈裁切失敗: {e}"

# ----------------------------------------------------
# 3. Step 4 主執行函數 (供 app.py 呼叫)
# ----------------------------------------------------

def execute_step4(input_list, output_dict):
    """
    執行 Step 4 的核心邏輯：合併遮罩並裁切成甜甜圈圖。

    Args:
        input_list (list): 任務狀態列表。
        output_dict (dict): 任務內容/分數字典。

    Returns:
        tuple: (input_list, output_dict, processed_count, error_status)
    """
    processed_count = 0
    
    for task_input in input_list:
        tid = task_input.get('task_id')
        
        # 檢查條件：image_status=True 且 donut_status=False
        if (task_input.get('image_status') is True and 
            not task_input.get('donut_status') and 
            tid in output_dict):
            
            task_name = task_input.get('task_name', 'Unknown')
            input_image_path = output_dict[tid].get('image_path')
            
            if not input_image_path:
                print(f"⚠️ 任務 {tid} 狀態為 'image_status=True' 但缺少 image_path。跳過。")
                continue
            
            # 輸出路徑
            output_donut_path = os.path.join(DONUT_OUTPUT_DIR, f"donut_{tid}.png")

            print(f"--- 正在處理甜甜圈: {task_name} ({tid}) ---")

            # 步驟 A: 合併遮罩
            merged_img_obj, merge_error = merge_images_with_mask(input_image_path, MASK_PATH)
            
            if merge_error:
                print(f"   ❌ 遮罩合併失敗: {merge_error}")
                continue
                
            # 步驟 B: 裁切甜甜圈
            success, crop_error = crop_to_donut(merged_img_obj, output_donut_path)
            
            if success:
                # 1. 更新 Input (Status)
                task_input['donut_status'] = True
                
                # 2. 更新 Output (Path)
                output_dict[tid]['donut_path'] = output_donut_path
                
                processed_count += 1
            else:
                print(f"   ❌ 裁切失敗: {crop_error}")
                
    return input_list, output_dict, processed_count, None