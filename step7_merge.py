from PIL import Image, ImageDraw
import json
import os
from datetime import datetime

# ----------------------------------------------------
# 設定區塊
# ----------------------------------------------------

# 檔案路徑
GLOBAL_INPUT_FILE = 'json/all_tasks_input.json'    # 任務狀態
GLOBAL_OUTPUT_FILE = 'json/all_tasks_output.json'   # 任務內容
UNUSED_FILE = 'json/unused.json'                    # [新增] 未用片段紀錄

# 輸出目錄
OUTPUT_DIR = os.path.join("images", "merged")
NOT_COMPLETE_DIR = os.path.join("images", "not_complete")
UNUSED_DIR = os.path.join("images", "unused")       # [新增] 未用片段圖片目錄

# 參數設定
FULL_SCORE = 300.0        # 滿分分數  (對應 360 度)
START_ANGLE_PIL = 270.0   # 起始角度 (PIL 角度 270 = 正上方)
INNER_RADIUS_RATIO = 0.5  # 內圓半徑比例

# ----------------------------------------------------
# 輔助函數
# ----------------------------------------------------

def generate_timestamp_str():
    return datetime.now().strftime("%Y%m%d_%H%M%S")

def generate_filename(prefix, ext="png"):
    return f"{prefix}_{generate_timestamp_str()}.{ext}"

def read_json(file_name, default_if_missing):
    try:
        with open(file_name, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return default_if_missing
    except Exception as e:
        print(f"❌ 讀取 JSON 錯誤 ({file_name}): {e}")
        return default_if_missing

def write_json(file_name, data):
    try:
        os.makedirs(os.path.dirname(file_name), exist_ok=True)
        with open(file_name, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"❌ 寫入 JSON 錯誤 ({file_name}): {e}")
        return False

def create_sector_mask(image_size, start_angle, end_angle):
    """建立精確的扇形遮罩"""
    width, height = image_size
    mask = Image.new('L', (width, height), 0)
    draw = ImageDraw.Draw(mask)
    
    cx, cy = width // 2, height // 2
    R = min(width, height) // 2
    r = int(R * INNER_RADIUS_RATIO)
    
    if abs(start_angle - end_angle) > 0.01:
        if abs(start_angle - end_angle) >= 360:
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
# 核心合併邏輯
# ----------------------------------------------------

def merge_all_segments(tasks_input, tasks_output, unused_data):
    print("\n--- 開始執行甜甜圈合併流程 (Unused 優先模式) ---")
    
    # 1. 變數初始化
    canvas = None
    canvas_size = (1024, 1024) # 預設，稍後更新
    
    current_angle_cursor = START_ANGLE_PIL
    accumulated_score = 0.0
    processed_count = 0
    
    active_unused_key = None  # 紀錄當前正在使用的 unused key
    active_unused_info = None
    
    # 2. 【優先檢查】是否有 Unused (Reused=False) 的片段
    # 邏輯：遍歷 unused.json，找第一個 reuse_status == False
    sorted_unused_keys = sorted(unused_data.keys()) # 依時間排序確保順序
    
    for key in sorted_unused_keys:
        item = unused_data[key]
        if item.get('reuse_status') is False:
            path = item.get('unused_path')
            # 這裡必須要有一個 score 欄位來知道它佔了多少，否則無法計算剩餘空間
            # 如果 json 沒有 score，我們只能假設... 不，必須要有。
            # 為防萬一，若讀不到 score，則無法使用該片段 (或視為 0 但這樣會有 bug)
            score = float(item.get('score', 0.0))
            
            if path and os.path.exists(path):
                print(f"♻️  發現可重用片段: {key} (Score: {score:.2f})")
                try:
                    img = Image.open(path).convert("RGBA")
                    canvas_size = img.size
                    canvas = Image.new('RGBA', canvas_size, (0, 0, 0, 0))
                    canvas.paste(img, (0, 0), img) # 貼上作為底圖
                    
                    accumulated_score += score
                    angle_span = (score / FULL_SCORE) * 360.0
                    current_angle_cursor -= angle_span
                    
                    active_unused_key = key
                    active_unused_info = item
                    break # 只取一個最舊的來接續
                except Exception as e:
                    print(f"❌ 載入 Unused 圖片失敗: {e}")
            else:
                print(f"⚠️ Unused 紀錄存在但檔案遺失: {path}")

    # 如果沒有 Unused，則初始化空白畫布
    if canvas is None:
        # 嘗試找一張圖來定尺寸
        for t in tasks_input:
            tid = t.get('task_id')
            if tid in tasks_output:
                path = tasks_output[tid].get('cut_path')
                if path and os.path.exists(path):
                    canvas_size = Image.open(path).size
                    break
        canvas = Image.new('RGBA', canvas_size, (0, 0, 0, 0))

    # 紀錄本次循環中修改了 merged_status 的任務 (用於回滾)
    tasks_modified_this_run = []
    is_circle_full = False
    
    # 3. 遍歷任務 (只處理 merged_status = False)
    for task_input in tasks_input:
        
        # 跳過已合併的任務 (這裡不畫歷史任務，因為我們假設每一輪都是新的拼圖)
        # 如果是 Unused 模式，Unused 圖片本身就包含了之前的歷史殘留
        if task_input.get('merge_status') is True:
            continue
            
        task_id = task_input.get('task_id')
        task_name = task_input.get('task_name', 'Unknown')
        
        # 檢查資料完整性
        if task_id not in tasks_output: continue
        
        task_score = max(0.0, float(tasks_output[task_id].get('total_score', 0.0)))
        cut_path = tasks_output[task_id].get('cut_path')
        
        # 檢查 cut_status 是否完成
        if not task_input.get('cut_status') or not cut_path or not os.path.exists(cut_path):
            continue

        print(f"\n👉 處理新任務: {task_name} ({task_id})")
        
        # 計算空間
        remaining_score = FULL_SCORE - accumulated_score
        angle_span = (task_score / FULL_SCORE) * 360.0
        
        current_img = Image.open(cut_path).convert("RGBA")
        
        # ==========================================================
        # 情境 A: 空間充足 (直接合併)
        # ==========================================================
        if task_score <= remaining_score + 0.01: # 0.01 浮點數容錯
            print(f"   ✅ 加入合併 (Score: {task_score:.2f})")
            
            draw_start = current_angle_cursor - angle_span
            draw_end = current_angle_cursor
            mask = create_sector_mask(canvas_size, draw_start, draw_end)
            
            canvas.paste(current_img, (0, 0), mask)
            
            # 更新狀態
            task_input['merge_status'] = True
            tasks_modified_this_run.append(task_input)
            
            accumulated_score += task_score
            current_angle_cursor -= angle_span
            processed_count += 1
            
            # 檢查是否剛好滿
            if abs(accumulated_score - FULL_SCORE) < 0.01:
                is_circle_full = True
                print("   🏁 圓環剛好填滿！")
                break
                
        # ==========================================================
        # 情境 B: 空間不足 (溢出 -> 剪裁 -> 存 Unused)
        # ==========================================================
        else:
            print(f"   🛑 空間不足 (剩 {remaining_score:.2f} / 需 {task_score:.2f})，觸發溢出處理。")
            is_circle_full = True
            
            # 1. 【填滿】 當前圓環
            fill_angle_span = (remaining_score / FULL_SCORE) * 360.0
            draw_end_fill = current_angle_cursor
            draw_start_fill = current_angle_cursor - fill_angle_span
            
            print(f"      ✂️  修剪並填滿圓環。")
            fill_mask = create_sector_mask(canvas_size, draw_start_fill, draw_end_fill)
            canvas.paste(current_img, (0, 0), fill_mask)
            
            # 標記當前任務為已合併 (雖然只畫了一半，但在 input list 裡算處理完了)
            task_input['merge_status'] = True
            tasks_modified_this_run.append(task_input)
            processed_count += 1
            
            # 2. 【存檔 Unused】 剩餘部分
            overflow_score = task_score - remaining_score
            overflow_angle_span = (overflow_score / FULL_SCORE) * 360.0
            
            # 這裡我們要從「原圖」中切出剩下的部分
            # 原圖的位置：它是基於 task 自己的角度生成的 cut_path。
            # 但在這裡，我們只需要它的「形狀」。
            # 為了簡單，我們計算出剩餘部分在圓環上的遮罩，但這遮罩的位置
            # 應該是緊接在 fill 之後 (也就是下一圈的開頭)。
            # 下一圈開頭 = START_ANGLE_PIL (270度)。
            
            next_circle_start = START_ANGLE_PIL
            next_circle_end = START_ANGLE_PIL - overflow_angle_span
            
            # 製作遮罩 (用於從原圖摳出像素)
            # 注意：原圖 (current_img) 是已經裁切好的扇形。
            # 這裡的邏輯有點複雜：原圖的 cut_path 是基於「該任務在該輪次」的預期位置生成的。
            # 如果我們直接用上面的 mask 去摳，可能會摳不到東西 (如果原圖位置不對)。
            # **更穩健的做法**：
            # 我們應該利用 `generate_donut_ratio.py` 裡的邏輯，重新對該任務的原始 generated_image 
            # 進行裁切。但這裡我們沒有 generated_image 的路徑。
            
            # **替代方案**：
            # 我們假設 `current_img` 是包含該任務像素的圖。
            # 我們的 fill_mask 是切掉了前半段。
            # 我們需要的 overflow_mask 是切掉後半段？
            # 不，我們需要的是「在原圖中，屬於 overflow 的那部分像素」。
            # 因為角度是連續的，我們可以用當前 cursor 繼續往下推算的 mask 來切原圖。
            
            draw_end_remain = draw_start_fill
            draw_start_remain = draw_start_fill - overflow_angle_span
            overflow_mask_on_canvas = create_sector_mask(canvas_size, draw_start_remain, draw_end_remain)
            
            # 建立 Unused 圖片
            unused_img = Image.new('RGBA', canvas_size, (0, 0, 0, 0))
            unused_img.paste(current_img, (0, 0), overflow_mask_on_canvas)
            
            # 存檔 Unused
            os.makedirs(UNUSED_DIR, exist_ok=True)
            timestamp = generate_timestamp_str()
            unused_filename = f"unused_{timestamp}.png"
            unused_path = os.path.join(UNUSED_DIR, unused_filename)
            unused_img.save(unused_path, 'PNG')
            print(f"      💾 Unused 片段已儲存: {unused_path}")
            
            # 更新 unused.json
            new_unused_key = f"unused_{timestamp}"
            unused_data[new_unused_key] = {
                "unused_path": unused_path,
                "reuse_status": False,
                "score": round(overflow_score, 2) # 重要：紀錄分數
            }
            
            break

    # 4. 結算與存檔
    if processed_count > 0 or active_unused_key:
        
        # A. 圓環已滿 -> 存檔 Merged -> 更新 Unused 狀態
        if is_circle_full:
            os.makedirs(OUTPUT_DIR, exist_ok=True)
            final_path = os.path.join(OUTPUT_DIR, generate_filename("donut_merged"))
            canvas.save(final_path, 'PNG')
            
            tasks_output['latest_merged_donut'] = final_path
            
            # 將本次使用的 Unused 標記為已使用
            if active_unused_key:
                unused_data[active_unused_key]['reuse_status'] = True
                print(f"      🔄 更新 Unused 狀態: {active_unused_key} -> Reused")

            print(f"\n====================== 合併完成 (圓環已滿) =======================")
            print(f"✅ 圖片: {final_path}")
            
        # B. 圓環未滿 -> 存檔 Not Complete -> 回滾任務狀態 -> Unused 保持 False
        else:
            os.makedirs(NOT_COMPLETE_DIR, exist_ok=True)
            final_path = os.path.join(NOT_COMPLETE_DIR, generate_filename("not_complete"))
            canvas.save(final_path, 'PNG')
            
            print(f"\n====================== 進度暫存 (圓環未滿) =======================")
            print(f"⚠️ 累積分數 {accumulated_score:.2f} < 300，等待更多任務。")
            print(f"📁 圖片: {final_path}")
            
            # 回滾：將本次修改為 merged 的任務設回 False
            print(f"🔙 回滾 {len(tasks_modified_this_run)} 個任務狀態。")
            for t in tasks_modified_this_run:
                t['merge_status'] = False
                
            # 注意：active_unused_key 的 reuse_status 保持 False，下次會再次被讀取

        # 寫入所有 JSON
        write_json(GLOBAL_INPUT_FILE, tasks_input)
        write_json(GLOBAL_OUTPUT_FILE, tasks_output)
        write_json(UNUSED_FILE, unused_data)
        
    else:
        print("\n💡 沒有進行任何合併操作。")

# ----------------------------------------------------
# 主程式
# ----------------------------------------------------

if __name__ == "__main__":
    tasks_input = read_json(GLOBAL_INPUT_FILE, []) 
    tasks_output = read_json(GLOBAL_OUTPUT_FILE, {})
    unused_data = read_json(UNUSED_FILE, {}) # 讀取 Unused 檔案
    
    if not tasks_input:
        print("❌ 無法讀取 Input 檔案。")
        exit()
        
    for t in tasks_input:
        if 'merge_status' not in t: t['merge_status'] = False

    merge_all_segments(tasks_input, tasks_output, unused_data)
