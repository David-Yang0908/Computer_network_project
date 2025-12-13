from PIL import Image, ImageDraw
import json
import os
import math

# ----------------------------------------------------
# 設定區塊
# ----------------------------------------------------

# 檔案路徑
GLOBAL_INPUT_FILE = 'json/all_tasks_input.json'    # 狀態檢查與更新 (Array)
GLOBAL_OUTPUT_FILE = 'json/all_tasks_output.json'   # 內容、分數與路徑儲存 (Dict)

# 圖片目錄 (僅供建構輸出路徑，輸入路徑從 Output 檔讀取)
OUTPUT_RATIO_DIR = os.path.join("images", "donut_ratio")    # 合成圖輸出
OUTPUT_CUT_DIR = os.path.join("images", "donut_cut")        # 純裁切圖輸出

# 參數設定
FULL_SCORE = 300.0        # 滿分分數 (對應 360 度)
START_ANGLE_PIL = 270.0   # 起始角度 (PIL 角度 270 = 正上方 12 點鐘方向)
INNER_RADIUS_RATIO = 0.5  # 內圓半徑比例

# ----------------------------------------------------
# 輔助函數
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
        return default_if_missing

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

def create_sector_mask(image_size, start_angle, end_angle):
    """
    建立一個扇形遮罩：扇形區域為白(255)，其餘為黑(0)，中間內圓挖空(0)。
    """
    width, height = image_size
    mask = Image.new('L', (width, height), 0)
    draw = ImageDraw.Draw(mask)
    
    cx, cy = width // 2, height // 2
    R = min(width, height) // 2
    r = int(R * INNER_RADIUS_RATIO)
    
    if abs(start_angle - end_angle) > 0.01:
        # 處理滿圓 (360度)
        if abs(start_angle - end_angle) >= 360:
             draw.ellipse((cx - R, cy - R, cx + R, cy + R), fill=255)
        else:
            # 繪製扇形 (白色)
            draw.pieslice(
                (cx - R, cy - R, cx + R, cy + R), 
                start_angle, 
                end_angle, 
                fill=255
            )
        
    # 挖空中間 (黑色)
    draw.ellipse((cx - r, cy - r, cx + r, cy + r), fill=0)
    return mask

# ----------------------------------------------------
# 核心處理邏輯 (兩個功能函數)
# ----------------------------------------------------

def generate_cut_only_image(color_path, output_path, mask):
    """ 產生只有彩色扇形部分的圖片，其餘全透明。 """
    try:
        if not os.path.exists(color_path): return False
        img_color = Image.open(color_path).convert("RGBA")
        
        # 建立一個全透明的底圖
        transparent_bg = Image.new("RGBA", img_color.size, (0, 0, 0, 0))
        
        # 將彩色圖貼到透明底圖上，只顯示 mask 為白色的部分
        cut_img = transparent_bg.copy()
        cut_img.paste(img_color, (0, 0), mask)
        
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        cut_img.save(output_path, 'PNG')
        return True
    except Exception as e:
        print(f"   ❌ 純裁切圖生成失敗: {e}")
        return False

def generate_ratio_image(color_path, gray_path, output_path, mask):
    """ 產生灰底加上彩色扇形的圖片。 """
    try:
        if not os.path.exists(color_path) or not os.path.exists(gray_path): return False
        img_color = Image.open(color_path).convert("RGBA")
        img_gray = Image.open(gray_path).convert("RGBA")
        if img_color.size != img_gray.size:
            img_gray = img_gray.resize(img_color.size, Image.Resampling.LANCZOS)

        # 以灰階圖為底，貼上彩色扇形
        ratio_img = img_gray.copy()
        ratio_img.paste(img_color, (0, 0), mask)
        
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        ratio_img.save(output_path, 'PNG')
        return True
    except Exception as e:
        print(f"   ❌ 合成圖生成失敗: {e}")
        return False

# ----------------------------------------------------
# 主程式
# ----------------------------------------------------

if __name__ == "__main__":
    
    # 1. 讀取資料
    tasks_input = read_json(GLOBAL_INPUT_FILE, [])          # Array for Status
    tasks_output = read_json(GLOBAL_OUTPUT_FILE, {})      # Dict for Scores/Paths
    
    if isinstance(tasks_input, dict) and "error" in tasks_input: exit()
    if isinstance(tasks_output, dict) and "error" in tasks_output: exit()

    print(f"💡 讀取到 {len(tasks_input)} 個任務。開始處理...")

    current_angle_cursor = START_ANGLE_PIL
    processed_count = 0
    
    # 2. 迭代處理
    for task_input in tasks_input:
        
        task_id = task_input.get('task_id')
        task_name = task_input.get('task_name', 'Unknown')
        
        angle_span = 0.0
        is_score_available = False

        # --- 1. 角度計算 (必須首先執行) ---
        if task_id in tasks_output:
            task_score_data = tasks_output[task_id] # Scores are in output dict
            total_score = float(task_score_data.get('total_score', 0.0))
            valid_score = max(0.0, min(total_score, FULL_SCORE))
            angle_span = (valid_score / FULL_SCORE) * 360.0
            is_score_available = True
        
        draw_start = current_angle_cursor - angle_span
        draw_end = current_angle_cursor
        
        # --- 2. 狀態檢查與生成 ---
        # 條件：gray_status 為 true，且 (合成圖 或 裁切圖) 尚未生成，且分數存在
        needs_processing = (task_input.get('gray_status') is True) and \
                           (not task_input.get('ratio_status') or not task_input.get('cut_status')) and \
                           is_score_available

        if needs_processing:
            print(f"\n--- 正在處理: {task_name} ({task_id}) ---")
            print(f"   角度範圍: {draw_start % 360:.1f}° -> {draw_end % 360:.1f}° (跨度 {angle_span:.1f}°)")
            
            # 取得路徑
            input_color = tasks_output[task_id].get('donut_path') 
            input_gray = tasks_output[task_id].get('gray_path')
            
            # 輸出路徑
            output_ratio = os.path.join(OUTPUT_RATIO_DIR, f"donut_ratio_{task_id}.png")
            output_cut = os.path.join(OUTPUT_CUT_DIR, f"donut_cut_{task_id}.png")

            if input_color and input_gray:
                
                # 建立共用遮罩 (Needs image size)
                try:
                    img_size = Image.open(input_color).size
                except FileNotFoundError:
                    print(f"   ❌ 找不到輸入圖片 {input_color}，跳過。")
                    # Angle cursor is updated below
                    continue 
                
                mask = create_sector_mask(img_size, draw_start, draw_end)
                
                # A. 生成純裁切圖 (Cut)
                if generate_cut_only_image(input_color, output_cut, mask):
                    print(f"   ✅ 純裁切圖生成成功: {output_cut}")
                    task_input['cut_status'] = True
                    tasks_output[task_id]['cut_path'] = output_cut
                    
                # B. 生成合成圖 (Ratio)
                if generate_ratio_image(input_color, input_gray, output_ratio, mask):
                    print(f"   ✅ 合成圖生成成功: {output_ratio}")
                    task_input['ratio_status'] = True
                    tasks_output[task_id]['ratio_path'] = output_ratio
                    
                processed_count += 1
            else:
                print(f"   ⚠️ 任務 {task_id} 狀態已達標，但 Output 中缺少素材路徑 (donut_path/gray_path)，跳過。")

        # --- 3. 累積角度更新 (必須在每次循環結束時執行) ---
        if is_score_available:
            current_angle_cursor -= angle_span


    # 4. 儲存更新
    if processed_count > 0:
        success_input = write_json(GLOBAL_INPUT_FILE, tasks_input)
        success_output = write_json(GLOBAL_OUTPUT_FILE, tasks_output)
        
        print(f"\n====================== 批次處理結果 =======================")
        print(f"📊 成功處理 {processed_count} 個任務 (產生裁切圖與合成圖)。")
        print(f"💾 Input 狀態更新: {'成功' if success_input else '失敗'}")
        print(f"💾 Output 路徑更新: {'成功' if success_output else '失敗'}")
        print("==========================================================")
    else:
        print("\n💡 沒有新的圖片被生成。")