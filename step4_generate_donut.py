import os
import json
from PIL import Image, ImageDraw

# ----------------------------------------------------
# 設定區塊
# ----------------------------------------------------

# 檔案路徑
GLOBAL_INPUT_FILE = 'json/all_tasks_input.json'   # 狀態檢查與更新
GLOBAL_OUTPUT_FILE = 'json/all_tasks_output.json' # 內容寫入 (Path)

# 固定遮罩圖片路徑 (前景)
MASK_PATH = os.path.join("images", "mask.png")

# 資料夾路徑
GENERATED_IMAGE_DIR = os.path.join("images", "generated_images") # 來源圖
DONUT_OUTPUT_DIR = os.path.join("images", "donut")  # 輸出圖

# ----------------------------------------------------
# 輔助函數 (JSON 讀寫 - 支援 Dict 和 Array)
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

def merge_images_with_mask(target_image_path, mask_path):
    """
    將遮罩圖片疊加到目標圖片上。回傳合併後的 PIL Image 物件。
    """
    try:
        if not os.path.exists(target_image_path):
            print(f"   ❌ 找不到背景圖片: {target_image_path}")
            return None
            
        target_img = Image.open(target_image_path).convert("RGBA")
        target_size = target_img.size

        if not os.path.exists(mask_path):
            print(f"   ❌ 找不到遮罩圖片: {mask_path}")
            return None

        mask_img = Image.open(mask_path).convert("RGBA")
        resized_mask = mask_img.resize(target_size, Image.Resampling.LANCZOS)
        merged_img = Image.alpha_composite(target_img, resized_mask)
        
        return merged_img

    except Exception as e:
        print(f"   ❌ 圖片合併失敗: {e}")
        return None


def crop_to_donut(pil_image, output_path, outer_radius=None, inner_radius_ratio=0.5):
    """ 
    將 PIL Image 物件裁剪成甜甜圈形狀並存檔。
    """
    try:
        img = pil_image.convert("RGBA")
        width, height = img.size

        if outer_radius is None:
            R = min(width, height) // 2
        else:
            R = outer_radius
            
        r = int(R * inner_radius_ratio)
        cx = width // 2
        cy = height // 2
        
        mask = Image.new('L', (width, height), 0)
        draw = ImageDraw.Draw(mask)
        
        draw.ellipse((cx - R, cy - R, cx + R, cy + R), fill=255)
        draw.ellipse((cx - r, cy - r, cx + r, cy + r), fill=0)
        
        img.putalpha(mask)
        
        crop_area = (cx - R, cy - R, cx + R, cy + R)
        cropped_img = img.crop(crop_area)
        
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        cropped_img.save(output_path, 'PNG')
        return True
        
    except Exception as e:
        print(f"   ❌ 甜甜圈裁切失敗: {e}")
        return False

# ----------------------------------------------------
# 主程式
# ----------------------------------------------------

if __name__ == "__main__":
    
    # 1. 讀取資料
    all_tasks_input = read_json(GLOBAL_INPUT_FILE, []) # Array
    all_tasks_output = read_json(GLOBAL_OUTPUT_FILE, {}) # Dict
    
    if isinstance(all_tasks_input, dict) and "error" in all_tasks_input: exit()
    if isinstance(all_tasks_output, dict) and "error" in all_tasks_output: exit()

    # 檢查遮罩是否存在
    if not os.path.exists(MASK_PATH):
        print(f"❌ 嚴重錯誤：找不到遮罩圖片 '{MASK_PATH}'。請先準備該圖片。")
        exit()

    # 篩選待處理任務：
    # 條件：image_status 為 true (有圖可切) 且 donut_status 為 false (還沒切)
    tasks_to_process = [
        t for t in all_tasks_input 
        if t.get('image_status') is True and not t.get('donut_status') and t.get('task_id') in all_tasks_output
    ]

    if not tasks_to_process:
        print("\n==========================================================")
        print("💡 目前沒有需要製作甜甜圈圖的任務。")
        print("   (條件：image_status=True 且 donut_status=False)")
        print("==========================================================")
        exit()

    print(f"\n💡 識別到 {len(tasks_to_process)} 個待處理任務。")
    processed_count = 0
    updated_input = False
    updated_output = False

    # 2. 迭代處理
    for task_data in all_tasks_input:
        
        tid = task_data.get('task_id')
        
        # 檢查是否符合處理條件
        if task_data.get('image_status') is True and not task_data.get('donut_status') and tid in all_tasks_output:
            
            task_name = task_data.get('task_name')
            
            # 從 Output 取得圖片路徑
            image_path_in_output = all_tasks_output[tid].get('image_path')
            
            # 建構輸入路徑 (如果 output.json 中沒有 image_path，則使用預設規則)
            input_image_path = image_path_in_output if image_path_in_output else os.path.join(GENERATED_IMAGE_DIR, f"generated_image_{tid}.png")
            
            # 輸出路徑
            output_donut_path = os.path.join(DONUT_OUTPUT_DIR, f"donut_{tid}.png")

            print(f"\n--- 正在處理: {task_name} ({tid}) ---")

            # 步驟 A: 合併遮罩
            merged_img_obj = merge_images_with_mask(input_image_path, MASK_PATH)
            
            if merged_img_obj:
                print("   ✅ 遮罩合併完成")
                
                # 步驟 B: 裁切甜甜圈
                success = crop_to_donut(merged_img_obj, output_donut_path)
                
                if success:
                    print(f"   ✅ 甜甜圈輸出成功: {output_donut_path}")
                    
                    # 1. 更新 Input (Status)
                    task_data['donut_status'] = True
                    updated_input = True
                    
                    # 2. 更新 Output (Path)
                    all_tasks_output[tid]['donut_path'] = output_donut_path
                    updated_output = True

                    processed_count += 1
                else:
                    print("   ❌ 裁切過程發生錯誤")
            else:
                print("   ⚠️ 跳過：無法讀取原始圖片或遮罩")

    # 3. 寫入更新
    if processed_count > 0:
        success_input = write_json(GLOBAL_INPUT_FILE, all_tasks_input)
        success_output = write_json(GLOBAL_OUTPUT_FILE, all_tasks_output)
        
        print(f"\n====================== 批次處理結果 =======================")
        print(f"🍩 成功製作 {processed_count} 個甜甜圈圖。")
        print(f"💾 Input 狀態更新: {'成功' if success_input else '失敗'}")
        print(f"💾 Output 路徑更新: {'成功' if success_output else '失敗'}")
        print("==========================================================")
    else:
        print("\n💡 本次沒有成功產出新的甜甜圈圖。")