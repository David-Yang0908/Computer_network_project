from PIL import Image, ImageDraw
import json
import os
import math
from datetime import datetime

# ----------------------------------------------------
# 1. 核心設定與路徑 (從 step7_merge.py 提取)
# ----------------------------------------------------

# 檔案路徑 (用於 app.py 傳遞資料)
UNUSED_FILE = 'json/unused.json'                    

# 輸出目錄 (用於建構路徑)
OUTPUT_DIR = os.path.join("images", "merged")
NOT_COMPLETE_DIR = os.path.join("images", "not_complete")
UNUSED_DIR = os.path.join("images", "unused")       

# 參數設定 (與 Step 6 保持一致)
FULL_SCORE = 300.0        
START_ANGLE_PIL = 270.0   
INNER_RADIUS_RATIO = 0.5  

# ----------------------------------------------------
# 2. 輔助函數 (從 step7_merge.py 提取)
# ----------------------------------------------------

def generate_timestamp_str():
    return datetime.now().strftime("%Y%m%d_%H%M%S")

def generate_filename(prefix, ext="png"):
    return f"{prefix}_{generate_timestamp_str()}.{ext}"

def create_sector_mask(image_size, start_angle, end_angle):
    """建立精確的扇形遮罩 (與 services/ratio_service.py 中的邏輯相同)"""
    width, height = image_size
    mask = Image.new('L', (width, height), 0)
    draw = ImageDraw.Draw(mask)
    
    cx, cy = width // 2, height // 2
    R = min(width, height) // 2
    r = int(R * INNER_RADIUS_RATIO)
    
    angle_diff = abs(start_angle - end_angle)
    if angle_diff > 0.01:
        if angle_diff >= 360:
             draw.ellipse((cx - R, cy - R, cx + R, cy + R), fill=255)
        else:
            draw.pieslice(
                (cx - R, cy - R, cx + R, cy + R), 
                start_angle, 
                end_angle, 
                fill=255
            )
    draw.ellipse((cx - r, cy - r, cx + r, cy + r), fill=0)
    return mask

# ----------------------------------------------------
# 3. Step 7 主執行函數 (供 app.py 呼叫)
# ----------------------------------------------------

def execute_step7(tasks_input, tasks_output, unused_data):
    """
    執行 Step 7 的核心邏輯：將扇形片段合併成圓環。

    Args:
        tasks_input (list): 任務狀態列表。
        tasks_output (dict): 任務內容/分數字典。
        unused_data (dict): 未用片段 (unused.json) 資料。

    Returns:
        tuple: (tasks_input, tasks_output, unused_data, processed_count, result_path, error_status)
    """
    canvas = None
    canvas_size = (1024, 1024) # 預設尺寸
    current_angle_cursor = START_ANGLE_PIL
    accumulated_score = 0.0
    processed_count = 0
    
    active_unused_key = None 
    
    # 紀錄本次循環中修改了 merged_status 的任務 (用於未滿時的回滾)
    tasks_modified_this_run = []
    is_circle_full = False
    
    
    # --- 步驟 1: 優先檢查並載入 Unused 片段 ---
    sorted_unused_keys = sorted(unused_data.keys())
    
    for key in sorted_unused_keys:
        item = unused_data[key]
        if item.get('reuse_status') is False:
            path = item.get('unused_path')
            score = float(item.get('score', 0.0))
            
            if path and os.path.exists(path) and score > 0.01:
                try:
                    img = Image.open(path).convert("RGBA")
                    canvas_size = img.size
                    canvas = Image.new('RGBA', canvas_size, (0, 0, 0, 0))
                    canvas.paste(img, (0, 0), img) # 貼上作為底圖
                    
                    accumulated_score += score
                    angle_span = (score / FULL_SCORE) * 360.0
                    current_angle_cursor -= angle_span
                    
                    active_unused_key = key
                    print(f"♻️  載入可重用片段: {key} (Score: {score:.2f})")
                    break 
                except Exception as e:
                    print(f"❌ 載入 Unused 圖片失敗: {e}，跳過此片段。")
            
    # 如果沒有 Unused，嘗試找一張 Cut 圖來定尺寸
    if canvas is None:
        for t in tasks_input:
            tid = t.get('task_id')
            if tid in tasks_output:
                path = tasks_output[tid].get('cut_path')
                if path and os.path.exists(path):
                    canvas_size = Image.open(path).size
                    break
        canvas = Image.new('RGBA', canvas_size, (0, 0, 0, 0))


    # --- 步驟 2: 遍歷新任務並合併 ---
    for task_input in tasks_input:
        
        # 僅處理尚未合併 (merged_status=False) 且 Cut 圖已準備好的任務
        if task_input.get('merge_status') is True:
            continue
            
        task_id = task_input.get('task_id')
        if task_id not in tasks_output: continue
        
        task_score = max(0.0, float(tasks_output[task_id].get('total_score', 0.0)))
        cut_path = tasks_output[task_id].get('cut_path')
        
        # 檢查資料完整性
        if not task_input.get('cut_status') or not cut_path or not os.path.exists(cut_path):
            continue

        remaining_score = FULL_SCORE - accumulated_score
        task_angle_span = (task_score / FULL_SCORE) * 360.0
        
        current_img = Image.open(cut_path).convert("RGBA")
        
        # 情境 A: 空間充足 (直接合併)
        if task_score <= remaining_score + 0.01: 
            
            draw_start = current_angle_cursor - task_angle_span
            draw_end = current_angle_cursor
            mask = create_sector_mask(canvas_size, draw_start, draw_end)
            
            canvas.paste(current_img, (0, 0), mask)
            
            # 更新狀態
            task_input['merge_status'] = True
            tasks_modified_this_run.append(task_input)
            
            accumulated_score += task_score
            current_angle_cursor -= task_angle_span
            processed_count += 1
            
            # 檢查是否剛好滿
            if abs(accumulated_score - FULL_SCORE) < 0.01:
                is_circle_full = True
                break
                
        # 情境 B: 空間不足 (溢出 -> 剪裁 -> 存 Unused)
        else:
            is_circle_full = True # 圓環在本輪填滿 (無論是剛好還是溢出)
            
            # 1. 填滿當前圓環
            fill_angle_span = (remaining_score / FULL_SCORE) * 360.0
            draw_end_fill = current_angle_cursor
            draw_start_fill = current_angle_cursor - fill_angle_span
            
            fill_mask = create_sector_mask(canvas_size, draw_start_fill, draw_end_fill)
            canvas.paste(current_img, (0, 0), fill_mask)
            
            task_input['merge_status'] = True
            tasks_modified_this_run.append(task_input)
            processed_count += 1
            
            # 2. 存檔 Unused 剩餘部分
            overflow_score = task_score - remaining_score
            overflow_angle_span = (overflow_score / FULL_SCORE) * 360.0
            
            # 製作溢出部分的遮罩 (理論上是緊接在 fill 之後的部分，但我們要用原圖來切)
            # 這裡需要一個 360度圓環的遮罩，用來從原圖中切出 overflow 的像素
            
            # 為了簡化，我們只使用原圖（current_img 是帶透明甜甜圈形狀），
            # 只需要在全透明畫布上用一個扇形遮罩切出「剩餘」的形狀
            
            # 製作 Unused 遮罩 (假設圓環重新開始，從 270度開始)
            next_circle_start = START_ANGLE_PIL
            next_circle_end = START_ANGLE_PIL - overflow_angle_span
            
            overflow_mask = create_sector_mask(canvas_size, next_circle_end, next_circle_start)

            # 建立 Unused 圖片
            unused_img = Image.new('RGBA', canvas_size, (0, 0, 0, 0))
            # 注意：這裡將原圖貼到 unused 畫布上，然後用 overflow_mask 摳出形狀
            unused_img.paste(current_img, (0, 0), overflow_mask)
            
            # 存檔 Unused
            os.makedirs(UNUSED_DIR, exist_ok=True)
            timestamp = generate_timestamp_str()
            unused_filename = f"unused_{timestamp}.png"
            unused_path = os.path.join(UNUSED_DIR, unused_filename)
            unused_img.save(unused_path, 'PNG')
            
            # 更新 unused.json
            new_unused_key = f"unused_{timestamp}"
            unused_data[new_unused_key] = {
                "unused_path": unused_path,
                "reuse_status": False,
                "score": round(overflow_score, 2)
            }
            break # 圓環已滿，結束本輪合併


    # --- 步驟 3: 結算與存檔 ---
    result_path = None
    if processed_count > 0 or active_unused_key:
        
        if is_circle_full:
            # A. 圓環已滿 -> 存檔 Merged
            os.makedirs(OUTPUT_DIR, exist_ok=True)
            final_filename = generate_filename("donut_merged")
            result_path = os.path.join(OUTPUT_DIR, final_filename)
            canvas.save(result_path, 'PNG')
            
            tasks_output['latest_merged_donut'] = result_path
            
            # 將本次使用的 Unused 標記為已使用
            if active_unused_key:
                unused_data[active_unused_key]['reuse_status'] = True
            
        else:
            # B. 圓環未滿 -> 存檔 Not Complete -> 回滾任務狀態
            os.makedirs(NOT_COMPLETE_DIR, exist_ok=True)
            final_filename = generate_filename("not_complete")
            result_path = os.path.join(NOT_COMPLETE_DIR, final_filename)
            canvas.save(result_path, 'PNG')
            
            # 回滾：將本次修改為 merged 的任務設回 False
            for t in tasks_modified_this_run:
                t['merge_status'] = False
                
            # active_unused_key 的 reuse_status 保持 False

    return tasks_input, tasks_output, unused_data, processed_count, result_path, None
