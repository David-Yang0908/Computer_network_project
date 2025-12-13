import os
import json
import math
from PIL import Image, ImageDraw, ImageOps

# ----------------------------------------------------
# 1. 核心設定與路徑 (從 step6_generate_ratio.py 提取)
# ----------------------------------------------------

# 輸出目錄 (用於建構路徑)
OUTPUT_RATIO_DIR = os.path.join("images", "donut_ratio")    # 合成圖輸出
OUTPUT_CUT_DIR = os.path.join("images", "donut_cut")        # 純裁切圖輸出

# 參數設定
FULL_SCORE = 300.0        # 滿分分數 (對應 360 度)
START_ANGLE_PIL = 270.0   # 起始角度 (PIL 角度 270 = 正上方 12 點鐘方向)
INNER_RADIUS_RATIO = 0.5  # 內圓半徑比例

# ----------------------------------------------------
# 2. 圖像處理函數 (核心邏輯)
# ----------------------------------------------------

def create_sector_mask(image_size, start_angle, end_angle):
    """
    建立一個扇形遮罩：扇形區域為白(255)，其餘為黑(0)，中間內圓挖空(0)。
    (來自 step6_generate_ratio.py)
    """
    width, height = image_size
    mask = Image.new('L', (width, height), 0)
    draw = ImageDraw.Draw(mask)
    
    cx, cy = width // 2, height // 2
    R = min(width, height) // 2
    r = int(R * INNER_RADIUS_RATIO)
    
    # 處理角度範圍
    angle_diff = abs(start_angle - end_angle)
    if angle_diff > 0.01:
        # 繪製扇形 (白色)
        if angle_diff >= 360:
             draw.ellipse((cx - R, cy - R, cx + R, cy + R), fill=255)
        else:
            draw.pieslice(
                (cx - R, cy - R, cx + R, cy + R), 
                start_angle, 
                end_angle, 
                fill=255
            )
        
    # 挖空中間 (黑色)
    draw.ellipse((cx - r, cy - r, cx + r, cy + r), fill=0)
    return mask

def generate_cut_only_image(color_path, output_path, mask):
    """ 產生只有彩色扇形部分的圖片，其餘全透明。 (來自 step6_generate_ratio.py) """
    try:
        if not os.path.exists(color_path): return False, "彩色圖檔案遺失"
        img_color = Image.open(color_path).convert("RGBA")
        
        # 建立一個全透明的底圖
        transparent_bg = Image.new("RGBA", img_color.size, (0, 0, 0, 0))
        
        # 將彩色圖貼到透明底圖上，只顯示 mask 為白色的部分 (即扇形)
        cut_img = transparent_bg.copy()
        cut_img.paste(img_color, (0, 0), mask)
        
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        cut_img.save(output_path, 'PNG')
        return True, None
    except Exception as e:
        return False, f"純裁切圖生成失敗: {e}"

def generate_ratio_image(color_path, gray_path, output_path, mask):
    """ 產生灰底加上彩色扇形的圖片。 (來自 step6_generate_ratio.py) """
    try:
        if not os.path.exists(color_path): return False, "彩色圖檔案遺失"
        if not os.path.exists(gray_path): return False, "灰階圖檔案遺失"
        
        img_color = Image.open(color_path).convert("RGBA")
        img_gray = Image.open(gray_path).convert("RGBA")
        
        # 確保尺寸一致
        if img_color.size != img_gray.size:
            img_gray = img_gray.resize(img_color.size, Image.Resampling.LANCZOS)

        # 以灰階圖為底，貼上彩色扇形
        ratio_img = img_gray.copy()
        ratio_img.paste(img_color, (0, 0), mask)
        
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        ratio_img.save(output_path, 'PNG')
        return True, None
    except Exception as e:
        return False, f"合成圖生成失敗: {e}"

# ----------------------------------------------------
# 3. Step 6 主執行函數 (供 app.py 呼叫)
# ----------------------------------------------------

def execute_step6(input_list, output_dict):
    """
    執行 Step 6 的核心邏輯：根據分數計算角度，生成 Cut 圖和 Ratio 圖。

    Args:
        input_list (list): 任務狀態列表 (用於檢查狀態)。
        output_dict (dict): 任務內容/分數字典 (用於讀取分數和路徑)。

    Returns:
        tuple: (input_list, output_dict, processed_count, error_status)
    """
    processed_count = 0
    
    # 初始化角度游標：從 12 點鐘方向開始
    current_angle_cursor = START_ANGLE_PIL
    
    # 遍歷 Input List (順序很重要，角度會累積)
    for task_input in input_list:
        
        task_id = task_input.get('task_id')
        task_name = task_input.get('task_name', 'Unknown')
        
        angle_span = 0.0
        is_score_available = False

        # 1. 角度計算 (必須首先執行)
        if task_id in output_dict:
            task_score_data = output_dict[task_id]
            total_score = float(task_score_data.get('total_score', 0.0))
            valid_score = max(0.0, min(total_score, FULL_SCORE))
            angle_span = (valid_score / FULL_SCORE) * 360.0
            is_score_available = True
        
        # 繪圖範圍：從當前游標回推
        draw_start = current_angle_cursor - angle_span
        draw_end = current_angle_cursor
        
        # 2. 狀態檢查與生成 (條件：有灰階圖且尚未生成 Ratio/Cut 圖)
        needs_processing = (task_input.get('gray_status') is True) and \
                           (not task_input.get('ratio_status') or not task_input.get('cut_status')) and \
                           is_score_available

        if needs_processing:
            
            input_color = output_dict[task_id].get('donut_path') 
            input_gray = output_dict[task_id].get('gray_path')
            
            if not input_color or not input_gray:
                 print(f"⚠️ 任務 {task_id} 狀態已達標，但缺少素材路徑。跳過。")
                 
            else:
                output_ratio = os.path.join(OUTPUT_RATIO_DIR, f"donut_ratio_{task_id}.png")
                output_cut = os.path.join(OUTPUT_CUT_DIR, f"donut_cut_{task_id}.png")

                # 確保圖片尺寸 (用於建立遮罩)
                try:
                    img_size = Image.open(input_color).size
                except FileNotFoundError:
                    print(f"   ❌ 找不到輸入圖片 {input_color}，跳過。")
                    continue 
                
                # 建立共用遮罩
                mask = create_sector_mask(img_size, draw_start, draw_end)
                
                # A. 生成純裁切圖 (Cut)
                cut_success, cut_error = generate_cut_only_image(input_color, output_cut, mask)
                if cut_success:
                    task_input['cut_status'] = True
                    output_dict[task_id]['cut_path'] = output_cut
                else:
                    print(f"   ❌ 純裁切圖生成失敗: {cut_error}")
                    
                # B. 生成合成圖 (Ratio)
                ratio_success, ratio_error = generate_ratio_image(input_color, input_gray, output_ratio, mask)
                if ratio_success:
                    task_input['ratio_status'] = True
                    output_dict[task_id]['ratio_path'] = output_ratio
                else:
                    print(f"   ❌ 合成圖生成失敗: {ratio_error}")
                    
                if cut_success or ratio_success:
                    processed_count += 1

        # 3. 累積角度更新 (必須在每次循環結束時執行，無論是否處理圖片)
        if is_score_available:
            current_angle_cursor -= angle_span
            
    return input_list, output_dict, processed_count, None