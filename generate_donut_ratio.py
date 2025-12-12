from PIL import Image, ImageDraw
import json
import os
import math
import sys

# --- 1. 檔案路徑與設定 ---
TASK = "task_20251213_045454"

FULL_SCORE = 300
INNER_RADIUS_RATIO = 0.5 
START_ANGLE_PIL = 270.0 

# 輸入路徑
SCORE_DATA_PATH = f'json\\task\\{TASK}\\output.json' 
ORIGINAL_IMAGE_PATH = f'images\\donut\\donut_{TASK}.png' 
LOW_CONTRAST_IMAGE_PATH = f'images\\donut_gray\\donut_gray_{TASK}.png' 

# 輸出路徑 (移除 JSON 輸出路徑)
FILLED_SECTOR_PATH = f'images\\cutted_segment\\donut_cutted_segment_{TASK}.png' 
FINAL_ASSEMBLED_DONUT = f'images\\donut_ratio\\donut_donut_ratio_{TASK}.png'              

MISSING_SECTOR_TEMP = 'missing_sector_temp.png' 

# --- 2. 工具函數 ---

def create_output_dir(output_path):
    output_dir = os.path.dirname(output_path)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
    return True

def read_score(score_data_path):
    try:
        with open(score_data_path, 'r', encoding='utf-8') as f:
            score_data = json.load(f)
            total_score = score_data.get('total_score', 0.0)
            return max(0.0, float(total_score))
    except (FileNotFoundError, json.JSONDecodeError, TypeError, ValueError) as e:
        print(f"❌ 無法讀取分數，使用 0 分: {e}")
        return 0.0

# --- 3. 核心裁切邏輯 (逆時針版) ---

def crop_filled_sector(image_path, total_score, full_score, output_path):
    """
    裁切「已完成」的部分 (從 270 度 *逆時針* 生長)。
    """
    print("\n--- 步驟 1: 生成已完成扇形 (逆時針) ---")

    # 1. 計算角度
    score_for_calc = max(0, min(total_score, full_score))
    proportion = score_for_calc / full_score
    filled_degree = proportion * 360
    
    # --- 逆時針邏輯核心 ---
    start_angle = START_ANGLE_PIL - filled_degree
    end_angle = START_ANGLE_PIL
    
    # 規範化角度到 0-360 方便閱讀
    start_angle_norm = start_angle % 360
    end_angle_norm = end_angle % 360

    print(f"  總得分: {total_score:.2f} ({proportion*100:.1f}%)")
    print(f"  PIL 繪圖參數: Start={start_angle_norm:.1f} -> End={end_angle_norm:.1f} (順時針繪製形成逆時針扇形)")

    # (已移除 angle_results 的字典建構)
    
    # 2. 裁切處理
    if not os.path.exists(image_path):
        print(f"❌ 找不到圖片: {image_path}")
        return False
        
    try:
        img = Image.open(image_path).convert("RGBA")
        width, height = img.size
        
        mask = Image.new('L', (width, height), 0)
        draw = ImageDraw.Draw(mask)

        cx, cy = width // 2, height // 2
        R = min(width, height) // 2 
        r = int(R * INNER_RADIUS_RATIO) 

        if filled_degree > 0:
            draw.pieslice(
                (cx - R, cy - R, cx + R, cy + R), 
                start_angle, 
                end_angle, 
                fill=255
            )
        
        draw.ellipse((cx - r, cy - r, cx + r, cy + r), fill=0)

        img.putalpha(mask)
        
        create_output_dir(output_path)
        img.save(output_path, 'PNG')
        # (已移除 write_json 呼叫)
        print(f"  ✅ 已完成部分儲存至: {output_path}")
        return True
    except Exception as e:
        print(f"❌ 裁切已完成部分失敗: {e}")
        return False

def crop_missing_sector(full_image_path, total_score, full_score, output_path):
    """
    裁切「缺失/剩餘」的部分 (佔據圓的其他部分)。
    """
    print("\n--- 步驟 2: 生成缺失扇形 (逆時針剩餘部分) ---")
    
    # 1. 計算角度
    score_for_calc = max(0, min(total_score, full_score))
    proportion = score_for_calc / full_score
    filled_degree = proportion * 360

    # --- 逆時針邏輯核心 ---
    start_angle = START_ANGLE_PIL
    end_angle = START_ANGLE_PIL - filled_degree
    
    start_angle_norm = start_angle % 360
    end_angle_norm = end_angle % 360

    print(f"  缺失比例: {(1-proportion)*100:.1f}%")
    print(f"  PIL 繪圖參數: Start={start_angle_norm:.1f} -> End={end_angle_norm:.1f}")

    if not os.path.exists(full_image_path):
        print(f"❌ 找不到圖片: {full_image_path}")
        return None

    try:
        img = Image.open(full_image_path).convert("RGBA")
        width, height = img.size
        
        mask = Image.new('L', (width, height), 0)
        draw = ImageDraw.Draw(mask)

        cx, cy = width // 2, height // 2
        R = min(width, height) // 2 
        r = int(R * INNER_RADIUS_RATIO) 

        if proportion < 1.0:
            draw.pieslice(
                (cx - R, cy - R, cx + R, cy + R), 
                start_angle, 
                end_angle, 
                fill=255
            )
        
        draw.ellipse((cx - r, cy - r, cx + r, cy + r), fill=0)
        
        img.putalpha(mask)
        
        create_output_dir(output_path)
        img.save(output_path, 'PNG')
        print(f"  ✅ 缺失部分儲存至暫存: {output_path}")
        return output_path
    except Exception as e:
        print(f"❌ 裁切缺失部分失敗: {e}")
        return None

def merge_donut_parts(part1_path, part2_path, output_path):
    """
    合併：part1 (已完成/彩色) 在上層，part2 (缺失/灰色) 在下層。
    """
    print("\n--- 步驟 3: 合併圖片 ---")
    try:
        if not os.path.exists(part1_path) or not os.path.exists(part2_path):
            print("❌ 錯誤: 合併來源檔案缺失。")
            return None

        img_top = Image.open(part1_path).convert("RGBA")  # 彩色
        img_bottom = Image.open(part2_path).convert("RGBA") # 灰色
        
        # 建立底圖
        canvas = Image.new('RGBA', img_top.size, (0, 0, 0, 0))
        
        # 先貼灰色 (背景)
        if img_bottom.size != canvas.size:
            img_bottom = img_bottom.resize(canvas.size, Image.Resampling.LANCZOS)
        canvas.paste(img_bottom, (0, 0), img_bottom)
        
        # 再貼彩色 (前景)
        canvas.paste(img_top, (0, 0), img_top)

        create_output_dir(output_path)
        canvas.save(output_path, 'PNG')
        print(f"  ✅ 最終合成圖片儲存至: {output_path}")
        return output_path
    except Exception as e:
        print(f"❌ 合併失敗: {e}")
        return None

# --- 4. 主流程 ---

def main():
    score = read_score(SCORE_DATA_PATH)
    
    # 呼叫時移除 json_output_path 參數
    filled_ok = crop_filled_sector(
        ORIGINAL_IMAGE_PATH, score, FULL_SCORE, 
        FILLED_SECTOR_PATH
    )

    missing_path = crop_missing_sector(
        LOW_CONTRAST_IMAGE_PATH, score, FULL_SCORE, 
        MISSING_SECTOR_TEMP
    )

    if filled_ok and missing_path:
        merge_donut_parts(FILLED_SECTOR_PATH, missing_path, FINAL_ASSEMBLED_DONUT)
    else:
        print("❌ 無法執行合併，因為裁切步驟失敗。")

    if os.path.exists(MISSING_SECTOR_TEMP):
        try:
            os.remove(MISSING_SECTOR_TEMP)
            print("  🗑️  清理暫存檔完成")
        except:
            pass

if __name__ == "__main__":
    print(f"--- 開始製作甜甜圈圖 ({TASK}) ---")
    print("--- 模式: 統一逆時針 ---")
    main()
    print("--- 結束 ---")