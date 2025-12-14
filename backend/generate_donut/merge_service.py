from PIL import Image, ImageDraw
import json
import os
import math
from datetime import datetime

# ----------------------------------------------------
# 1. 核心設定與路徑
# ----------------------------------------------------

UNUSED_FILE = 'json/unused.json'                    
OUTPUT_DIR = os.path.join("images", "merged")
NOT_COMPLETE_DIR = os.path.join("images", "not_complete")
UNUSED_DIR = os.path.join("images", "unused")       

FULL_SCORE = 300.0        
START_ANGLE_PIL = 270.0   
INNER_RADIUS_RATIO = 0.5  
CANVAS_SIZE = (1024, 1024)

# ----------------------------------------------------
# 2. 輔助函數
# ----------------------------------------------------

def generate_timestamp_str():
    return datetime.now().strftime("%Y%m%d_%H%M%S")

def generate_filename(prefix, ext="png"):
    return f"{prefix}_{generate_timestamp_str()}.{ext}"

def create_sector_mask(image_size, start_angle, end_angle):
    """建立精確的扇形遮罩"""
    width, height = image_size
    mask = Image.new('L', (width, height), 0)
    draw = ImageDraw.Draw(mask)
    
    cx, cy = width // 2, height // 2
    R = min(width, height) // 2
    r = int(R * INNER_RADIUS_RATIO)
    
    # PIL pieslice 繪製角度
    draw.pieslice(
        (cx - R, cy - R, cx + R, cy + R), 
        start_angle, 
        end_angle, 
        fill=255
    )
            
    # 內圓裁切 (製作甜甜圈)
    draw.ellipse((cx - r, cy - r, cx + r, cy + r), fill=0)
    return mask

# ----------------------------------------------------
# 3. Step 7 主執行函數
# ----------------------------------------------------

def execute_step7(tasks_input, tasks_output, unused_data):
    """
    執行 Step 7 的核心邏輯：將扇形片段合併成圓環，可重複運行直到輸入列表耗盡。

    Args:
        tasks_input (list): 任務狀態列表。
        tasks_output (dict): 任務內容/分數字典。
        unused_data (dict): 未用片段 (unused.json) 資料。

    Returns:
        tuple: (tasks_input, tasks_output, unused_data, total_processed_count, final_result_path, error_status)
    """
    total_processed_count = 0
    final_result_path = None
    
    # --- 外部主迴圈：持續嘗試生成圓環 ---
    while True:
        
        # 迴圈初始化/重置
        canvas = Image.new('RGBA', CANVAS_SIZE, (0, 0, 0, 0))
        current_angle_cursor = START_ANGLE_PIL
        accumulated_score = 0.0
        processed_this_run = 0
        active_unused_key = None 
        tasks_modified_this_run = []
        is_circle_full = False
        
        # --- 步驟 1: 優先檢查並載入 Unused 片段 (如果存在) ---
        can_reuse = False
        sorted_unused_keys = sorted(unused_data.keys())
        
        for key in sorted_unused_keys:
            item = unused_data[key]
            if item.get('reuse_status') is False: # 找到一個未使用的片段
                path = item.get('unused_path')
                score = float(item.get('score', 0.0))
                
                if path and os.path.exists(path) and score > 0.01:
                    try:
                        img = Image.open(path).convert("RGBA")
                        canvas.paste(img, (0, 0), img) # 貼上作為底圖
                        
                        accumulated_score += score
                        angle_span = (score / FULL_SCORE) * 360.0
                        current_angle_cursor -= angle_span
                        
                        active_unused_key = key
                        can_reuse = True
                        print(f"♻️  載入可重用片段: {key} (Score: {score:.2f})")
                        break 
                    except Exception as e:
                        print(f"❌ 載入 Unused 圖片失敗: {e}，跳過此片段。")
        
        # 🚨 關鍵修正 1: 解決無限迴圈。如果成功載入了 Unused 片段，立即將其標記為已使用，以便下一輪不會重複載入。
        if active_unused_key:
            unused_data[active_unused_key]['reuse_status'] = True
            print(f"   -> 片段 {active_unused_key} 已標記為已使用。")
        
        
        # --- 步驟 2: 遍歷新任務並合併 ---
        
        # 尋找所有尚未合併 (merged_status=False) 且 Cut 圖已準備好的任務
        task_indices_to_process = [
            i for i, t in enumerate(tasks_input) 
            # 🚨 關鍵修正 2: 修正狀態欄位名稱為 'merged_status'
            if t.get('merged_status') is False and t.get('cut_status') is True
        ]
        
        made_progress_this_run = can_reuse
        
        
        for i in task_indices_to_process:
            task_input = tasks_input[i]
            task_id = task_input.get('task_id')
            
            if task_id not in tasks_output: continue
            task_score = max(0.0, float(tasks_output[task_id].get('total_score', 0.0)))
            cut_path = tasks_output[task_id].get('cut_path')
            
            if task_score <= 0.01 or not cut_path or not os.path.exists(cut_path):
                continue

            remaining_score = FULL_SCORE - accumulated_score
            task_angle_span = (task_score / FULL_SCORE) * 360.0
            current_img = Image.open(cut_path).convert("RGBA")
            
            # 情境 A: 空間充足 (直接合併)
            if task_score <= remaining_score + 0.01: 
                
                draw_end = current_angle_cursor
                draw_start = current_angle_cursor - task_angle_span
                mask = create_sector_mask(CANVAS_SIZE, draw_start, draw_end)
                
                canvas.paste(current_img, (0, 0), mask)
                
                # 🚨 關鍵修正 3: 修正狀態欄位名稱為 'merged_status'
                tasks_input[i]['merged_status'] = True
                tasks_modified_this_run.append(tasks_input[i])
                
                accumulated_score += task_score
                current_angle_cursor -= task_angle_span
                processed_this_run += 1
                made_progress_this_run = True
                
                # 檢查是否剛好滿
                if abs(accumulated_score - FULL_SCORE) < 0.01:
                    is_circle_full = True
                    break
                    
            # 情境 B: 空間不足 (溢出 -> 剪裁 -> 存 Unused)
            else:
                is_circle_full = True # 圓環在本輪填滿
                
                # 1. 填滿當前圓環的剩餘空間
                fill_angle_span = (remaining_score / FULL_SCORE) * 360.0
                draw_end_fill = current_angle_cursor
                draw_start_fill = current_angle_cursor - fill_angle_span
                
                fill_mask = create_sector_mask(CANVAS_SIZE, draw_start_fill, draw_end_fill)
                canvas.paste(current_img, (0, 0), fill_mask)
                
                # 🚨 關鍵修正 4: 修正狀態欄位名稱為 'merged_status'
                tasks_input[i]['merged_status'] = True
                tasks_modified_this_run.append(tasks_input[i])
                processed_this_run += 1
                made_progress_this_run = True
                
                # 2. 存檔 Unused 剩餘部分
                overflow_score = task_score - remaining_score
                overflow_angle_span = (overflow_score / FULL_SCORE) * 360.0
                
                next_circle_end = START_ANGLE_PIL
                next_circle_start = START_ANGLE_PIL - overflow_angle_span
                
                overflow_mask = create_sector_mask(CANVAS_SIZE, next_circle_start, next_circle_end)

                unused_img = Image.new('RGBA', CANVAS_SIZE, (0, 0, 0, 0))
                unused_img.paste(current_img, (0, 0), overflow_mask)
                
                # 存檔 Unused
                os.makedirs(UNUSED_DIR, exist_ok=True)
                timestamp = generate_timestamp_str()
                unused_filename = f"unused_{timestamp}.png"
                unused_path = os.path.join(UNUSED_DIR, unused_filename)
                unused_img.save(unused_path, 'PNG')
                
                # 更新 unused.json (reuse_status 初始為 False)
                new_unused_key = f"unused_{timestamp}"
                unused_data[new_unused_key] = {
                    "unused_path": unused_path,
                    "reuse_status": False,
                    "score": round(overflow_score, 2)
                }
                break # 圓環已滿，結束本輪合併


        # --- 步驟 3: 結算與存檔 (每個圓環結束時) ---
        
        if is_circle_full:
            total_processed_count += processed_this_run
            
            # A. 圓環已滿 -> 存檔 Merged
            os.makedirs(OUTPUT_DIR, exist_ok=True)
            final_filename = generate_filename("donut_merged")
            current_result_path = os.path.join(OUTPUT_DIR, final_filename)
            canvas.save(current_result_path, 'PNG')
            
            tasks_output['latest_merged_donut'] = current_result_path
            final_result_path = current_result_path # 更新最終回傳路徑
            
            # 繼續下一輪 while 迴圈
            continue 
            
        # 步驟 4: 退出判斷
        # 如果本輪沒有任何進度，且沒有可處理的任務 (即：tasks_input 耗盡)，則退出
        if not made_progress_this_run and not task_indices_to_process:
            break
            
        # 如果任務列表掃描完畢，但圓環未滿，則退出，進入步驟 5 處理未滿圓環
        if processed_this_run > 0 and not is_circle_full:
             break


    # --- 步驟 5: 處理最終未滿的圓環 (如果存在) ---
    
    # 如果迴圈結束時，累積了分數但圓環未滿
    if accumulated_score > 0.01 and not is_circle_full:
        os.makedirs(NOT_COMPLETE_DIR, exist_ok=True)
        final_filename = generate_filename("not_complete")
        current_result_path = os.path.join(NOT_COMPLETE_DIR, final_filename)
        canvas.save(current_result_path, 'PNG')
        
        tasks_output['latest_merged_donut'] = current_result_path
        final_result_path = current_result_path
        
        # 🚨 關鍵修正 5: 修正狀態欄位名稱為 'merged_status'
        # 回滾：將本次在未滿圓環中修改為 merged 的任務設回 False
        for t in tasks_modified_this_run:
            t['merged_status'] = False

    
    return tasks_input, tasks_output, unused_data, total_processed_count, final_result_path, None