from PIL import Image, ImageDraw, ImageOps
import os

# --- 1. 圖片合併功能 (來自 merge.py) ---

def merge_images_with_mask(target_image_path, mask_path, output_path):
    """
    將遮罩圖片 (mask_path) 調整大小後，疊加到目標圖片 (target_image_path) 上。
    這個函數會處理 RGBA 轉換和透明度疊加。

    Args:
        target_image_path (str): 目標基礎圖片的路徑。
        mask_path (str): 輸入的遮罩圖片路徑。
        output_path (str): 儲存合併圖片的路徑。

    Returns:
        str: 成功合併的圖片路徑，若失敗則回傳 None。
    """
    print("--- 步驟 1: 執行圖片合併 (套用偵照) ---")
    try:
        # 1. 開啟目標圖片 (背景)
        target_img = Image.open(target_image_path).convert("RGBA")
        target_size = target_img.size
        print(f"   目標圖片尺寸 (Target): {target_size}")

        # 2. 開啟作為前景的遮罩圖片
        mask_img = Image.open(mask_path).convert("RGBA")
        print(f"   原始遮罩尺寸 (Original Mask): {mask_img.size}")

    except FileNotFoundError as e:
        print(f"   錯誤：找不到圖片文件 - {e.filename}")
        return None
    except Exception as e:
        print(f"   處理圖片時發生錯誤: {e}")
        return None

    # 3. 調整遮罩圖片大小以符合目標尺寸
    # 使用 Image.Resampling.LANCZOS 進行高品質重採樣
    resized_mask = mask_img.resize(target_size, Image.Resampling.LANCZOS)
    print(f"   遮罩已調整至目標尺寸: {resized_mask.size}")

    # 4. 執行圖片疊加/合併 (透明度疊加)
    # 這裡假設遮罩圖片的 Alpha 通道已經正確定義了其透明區域。
    merged_img = Image.alpha_composite(target_img, resized_mask)

    # 5. 儲存結果
    merged_img.save(output_path, "PNG")
    print(f"   ✅ 合併圖片暫存於：{output_path}")
    return output_path


# --- 2. 甜甜圈裁切功能 (來自 generate_donut.py) ---

def crop_to_donut(image_path, output_path, outer_radius=None, inner_radius_ratio=0.5):
    """
    將指定路徑的圖片裁剪成甜甜圈形狀，並儲存為 PNG 格式。
    
    Args:
        image_path (str): 輸入圖片的路徑。
        output_path (str): 輸出甜甜圈圖片的路徑 (必須是 .png 結尾)。
        outer_radius (int, optional): 甜甜圈的外圓半徑。如果為 None，則取圖片較短邊長的一半。
        inner_radius_ratio (float): 內圓半徑與外圓半徑的比例（預設為 0.5）。
    """
    print("--- 步驟 2: 執行甜甜圈裁切 ---")
    try:
        # 1. 開啟圖片並轉換為 RGBA 模式以支援透明度
        img = Image.open(image_path).convert("RGBA")
    except FileNotFoundError:
        print(f"   錯誤：找不到圖片文件 - {image_path}")
        return

    width, height = img.size

    # 2. 決定半徑和圓心
    if outer_radius is None:
        R = min(width, height) // 2
    else:
        R = outer_radius
        
    r = int(R * inner_radius_ratio)
    cx = width // 2
    cy = height // 2
    
    # 3. 創建遮罩
    mask = Image.new('L', (width, height), 0)
    draw = ImageDraw.Draw(mask)
    
    # a. 繪製白色大圓 (保留)
    draw.ellipse((cx - R, cy - R, cx + R, cy + R), fill=255)
    
    # b. 繪製黑色小圓 (移除/變透明)
    draw.ellipse((cx - r, cy - r, cx + r, cy + r), fill=0)
    
    # 4. 將遮罩應用於圖片的 Alpha 通道
    img.putalpha(mask)
    
    # 5. 裁剪圖片到最小邊界框
    crop_area = (cx - R, cy - R, cx + R, cy + R)
    cropped_img = img.crop(crop_area)
    
    # 6. 儲存結果
    cropped_img.save(output_path, 'PNG')
    
    print(f"   ✅ 圖片已成功裁切為甜甜圈形狀並儲存到：{output_path}")


# --- 主執行流程 ---

def main_process(target_image_path, mask_path, final_output_path, temp_output_path='temp_merged_image.png'):
    """
    依照指定的順序執行圖片處理：
    1. 合併圖片 (套用偵照/遮罩)。
    2. 裁切為甜甜圈形狀。
    
    Args:
        target_image_path (str): 作為背景的圖片路徑 (原始圖片)。
        mask_path (str): 作為前景的遮罩圖片路徑 (偵照)。
        final_output_path (str): 最終甜甜圈圖片的輸出路徑。
        temp_output_path (str): 步驟 1 中間結果的暫存路徑。
    """
    
    # 1. 執行圖片合併
    merged_file = merge_images_with_mask(target_image_path, mask_path, temp_output_path)
    
    if merged_file is None:
        print("❌ 合併步驟失敗，終止程式。")
        return

    # 2. 執行甜甜圈裁切 (對合併後的圖片進行裁切)
    crop_to_donut(merged_file, final_output_path)

    # 3. 清理暫存文件
    try:
        if os.path.exists(temp_output_path):
            os.remove(temp_output_path)
            print(f"--- 清理: 已移除暫存文件 {temp_output_path}")
    except OSError as e:
        print(f"清理暫存文件失敗: {e}")


# --- 範例使用 (請務必將路徑替換成您實際的檔案路徑) ---

# 您的輸入檔案
IMAGE_PATH = 'C:\Computer_network\image\generated_image_2.png' # 原始圖片 (背景)
MASK_PATH = 'mask.png' # 遮罩圖片 (前景/偵照)

# 輸出檔案
FINAL_OUTPUT = 'final_donut_with_mask.png' # 最終成品

# 執行主程序
main_process(IMAGE_PATH, MASK_PATH, FINAL_OUTPUT)