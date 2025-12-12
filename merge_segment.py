from PIL import Image, ImageDraw
import json
import os
import math
import sys
import datetime # <<< 新增：引入時間模組

# --- 全域配置 ---
INPUT_CONFIG_PATH = 'json/merge_input.json' 
FULL_SCORE = 300  
INNER_RADIUS_RATIO = 0.5 
START_ANGLE_PIL = 270.0 

# --- 1. 配置與工具函數 (保持不變) ---

def create_output_dir(output_path):
    """檢查並建立輸出路徑的目錄。"""
    output_dir = os.path.dirname(output_path)
    if output_dir:
        try:
            os.makedirs(output_dir, exist_ok=True)
            return True
        except Exception as e:
            print(f"❌ 錯誤: 無法建立輸出目錄 '{output_dir}'，儲存失敗: {e}")
            return False
    return True

def read_data(data_path):
    """從 JSON 檔案中讀取資料。"""
    try:
        with open(data_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"❌ 錯誤: 無法讀取或解析文件 {data_path}。錯誤: {e}")
        return None

def calculate_pil_angles(score, current_start_angle_pil, max_remaining_score, full_score=FULL_SCORE):
    # (保持不變)
    score_for_calc = max(0, score)
    is_full_circle = score_for_calc >= max_remaining_score
    effective_score = min(score_for_calc, max_remaining_score)
    proportion = effective_score / full_score
    filled_angle_degree = proportion * 360
    
    end_angle_pil = current_start_angle_pil - filled_angle_degree
    
    if is_full_circle:
        end_angle_pil = START_ANGLE_PIL
        
    while end_angle_pil < 0:
        end_angle_pil += 360
        
    return end_angle_pil, filled_angle_degree, is_full_circle

# --- 2. 核心功能：單一片段裁切 (保持不變) ---

def crop_single_segment(image_path, start_angle_pil, end_angle_pil):
    # (保持不變)
    if not os.path.exists(image_path):
        print(f"❌ 錯誤：裁切圖片時找不到輸入檔案 - {image_path}")
        return None
        
    try:
        img = Image.open(image_path).convert("RGBA")
    except Exception as e:
        print(f"❌ 處理圖片時發生錯誤: {e}")
        return None

    width, height = img.size
    cx, cy = width // 2, height // 2
    R = min(width, height) // 2 
    r = int(R * INNER_RADIUS_RATIO) 
    
    mask = Image.new('L', (width, height), 0)
    draw = ImageDraw.Draw(mask)

    draw.pieslice(
        (cx - R, cy - R, cx + R, cy + R), 
        end_angle_pil, start_angle_pil, fill=255 
    )
    
    draw.ellipse((cx - r, cy - r, cx + r, cy + r), fill=0)

    img.putalpha(mask)
    
    return img

# --- 3. 主合併函數 (保持不變) ---

def merge_segments(segments_list, final_output_path):
    """依序處理並合併多個甜甜圈扇形片段，並在達到或超過總分時停止。"""
    if not segments_list:
        print("❌ 錯誤：片段列表為空，無法合併。")
        return None
        
    print("--- 甜甜圈片段合併程式啟動 ---")
    
    # 1. 初始化畫布、角度和累計分數追蹤器
    first_image_path = segments_list[0]['image_path']
    try:
        base_img = Image.open(first_image_path)
    except Exception as e:
        print(f"❌ 錯誤: 無法開啟第一個圖片檔案 '{first_image_path}' 來初始化畫布: {e}")
        return None
        
    final_canvas = Image.new('RGBA', base_img.size, (0, 0, 0, 0)) # 透明畫布
    current_start_angle_pil = START_ANGLE_PIL 
    accumulated_score = 0.0

    # 2. 依序處理每個片段
    for i, segment in enumerate(segments_list):
        if accumulated_score >= FULL_SCORE:
            print(f"\n✅ 總分已達 {FULL_SCORE} 分或更高，停止處理後續片段。")
            break
            
        img_path = segment['image_path']
        json_path = segment['score_json_path']
        segment_name = f"片段 {i+1} ({os.path.basename(img_path)})"
        
        print(f"\n--- 處理 {segment_name} ---")
        
        # 2a. 讀取得分
        score_data = read_data(json_path)
        if score_data is None:
            print(f"❗ 跳過 {segment_name}：無法讀取得分 JSON。")
            continue
            
        score = score_data.get('total_score', 0.0)
        max_remaining_score = FULL_SCORE - accumulated_score
        
        # 2b. 計算裁切角度
        end_angle_pil, filled_degree, is_full_circle = calculate_pil_angles(
            score, current_start_angle_pil, max_remaining_score
        )
        
        print(f" 原始得分: {score:.2f} 點")
        print(f" 裁切度數: {filled_degree:.2f}°")
        print(f" PIL 角度範圍: [{end_angle_pil:.2f}°] (終點) 到 [{current_start_angle_pil:.2f}°] (起點)")
        
        # 2c. 裁切圖片片段
        if filled_degree > 0:
            segment_img = crop_single_segment(img_path, current_start_angle_pil, end_angle_pil)
            
            if segment_img is None:
                print(f"❗ 跳過 {segment_name}：無法裁切圖片。")
                accumulated_score += min(score, max_remaining_score)
                current_start_angle_pil = end_angle_pil
                continue
                
            # 2d. 疊加到最終畫布
            final_canvas.paste(segment_img, (0, 0), segment_img)
            
            # 2e. 更新累計分數和下一個片段的起始角度
            accumulated_score += filled_degree / 360 * FULL_SCORE
            current_start_angle_pil = end_angle_pil
            
        else:
            print(f"❗ {segment_name} 的得分 {score:.2f} 已經被前面片段填滿，無需繪製。")
        
        # 2f. 檢查是否滿分，如果是則跳出迴圈
        if is_full_circle:
             print(f"✅ {segment_name} 繪製完畢，圖形已圓滿填滿 (360°)。")
             break

    # 3. 儲存最終結果
    print("\n--- 儲存最終結果 ---")
    if not create_output_dir(final_output_path):
        return None

    try:
        final_canvas.save(final_output_path, 'PNG')
        print(f"✅ 所有片段已成功合併，儲存至: {final_output_path}")
    except Exception as e:
        print(f"❌ 儲存最終合併圖片時發生錯誤: {e}")
        return None

# --- 4. 範例執行設定 (修改重點) ---

def load_config_and_prepare_segments(config_path):
    """
    從配置 JSON 檔案中讀取並解析所有片段的資料，並生成帶有時間戳記的輸出路徑。
    """
    config_data = read_data(config_path)
    if config_data is None:
        print(f"❌ 載入配置失敗: 請確保 {config_path} 存在且格式正確。")
        return None, None
        
    output_template = config_data.get('output_file_template') # <<< 修改：讀取模板
    segments_config = config_data.get('segments', [])
    
    if not output_template:
        print("❌ 配置檔案中缺少 'output_file_template' 欄位。")
        return None, None
        
    if not segments_config:
        print("❌ 配置檔案中 'segments' 列表為空。")
        return None, None

    # --- 生成時間戳記和最終輸出路徑 ---
    # 格式化時間 (年-月-日_時分秒)
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    final_output = output_template.format(timestamp=timestamp)
    print(f"⏳ 正在生成輸出檔名: {final_output}")
    # --- 結束生成時間戳記和最終輸出路徑 ---
    
    prepared_segments = []
    
    for seg_data in segments_config:
        topic_id = seg_data.get('topic_id')
        img_tmpl = seg_data.get('image_path_template')
        json_tmpl = seg_data.get('score_json_template')
        
        if not (topic_id and img_tmpl and json_tmpl):
            print(f"❗ 警告: 跳過一個不完整的片段配置: {seg_data}")
            continue
            
        prepared_segments.append({
            'image_path': img_tmpl.format(topic_id=topic_id),
            'score_json_path': json_tmpl.format(topic_id=topic_id)
        })
        
    return prepared_segments, final_output

if __name__ == "__main__":
    
    if len(sys.argv) > 1:
        custom_config_path = sys.argv[1]
        print(f"🔍 使用命令行參數指定的配置檔案: {custom_config_path}")
    else:
        custom_config_path = INPUT_CONFIG_PATH
        print(f"🔍 使用預設配置檔案: {custom_config_path}")
    
    segments_to_merge, final_output = load_config_and_prepare_segments(custom_config_path)
    
    if segments_to_merge and final_output:
        # 執行合併
        merge_segments(segments_to_merge, final_output)
    
    print("\n--- 程式執行完畢 ---")