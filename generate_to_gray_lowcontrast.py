from PIL import Image, ImageOps, ImageEnhance
import os

# --- 範例使用 ---
TASK = "task_20251213_045454"

INPUT_IMAGE = f'images\donut\donut_{TASK}.png'
OUTPUT_IMAGE = f'images\donut_gray\donut_gray_{TASK}.png'
CONTRAST_REDUCTION = 0.5    # 0.5 = 減少 50% 對比度

def convert_and_reduce_contrast(input_path, output_path, contrast_factor=0.5):
    """
    讀取圖片，將其轉換為灰度圖 (飽和度 0%)，減少對比度，並保留 Alpha (透明度) 通道。
    如果輸出路徑的目錄不存在，則自動建立。
    
    Args:
        input_path (str): 輸入圖片的路徑。
        output_path (str): 輸出圖片的路徑。
        contrast_factor (float): 對比度調整係數。1.0 為不變，0.5 為減少 50% 對比度。
    """
    if not os.path.exists(input_path):
        print(f"❌ 錯誤: 輸入檔案 '{input_path}' 不存在。請檢查路徑。")
        return

    # --- 關鍵修改：檢查並建立輸出路徑的目錄 ---
    try:
        output_dir = os.path.dirname(output_path)
        if output_dir: # 檢查是否為當前目錄 (空字串)
             # exist_ok=True 確保目錄存在時不報錯
             os.makedirs(output_dir, exist_ok=True)
    except Exception as e:
        print(f"❌ 錯誤: 無法建立輸出目錄 '{output_dir}'，可能為權限問題: {e}")
        return
    # --- 關鍵修改結束 ---

    try:
        # 1. 開啟圖片並確保它有 Alpha 通道 (轉換為 RGBA)
        img = Image.open(input_path).convert("RGBA")
        
        # 2. 分離 RGBA 通道
        R, G, B, A = img.split()
        
        # 3. 對 RGB 部分進行灰度轉換 ('L' 模式)
        rgb_img = Image.merge("RGB", (R, G, B))
        grayscale_img_L = rgb_img.convert('L') 
        
        # --- 新增步驟：對比度調整 ---
        print(f"    正在減少 {((1 - contrast_factor) * 100):.0f}% 對比度...")
        
        # 4. 使用 ImageEnhance 調整對比度
        enhancer = ImageEnhance.Contrast(grayscale_img_L)
        adjusted_img_L = enhancer.enhance(contrast_factor) 
        
        # 5. 準備合併：將 L 模式的灰度圖轉換為 RGB (即 R=G=B)
        final_grayscale_rgb = ImageOps.colorize(
            adjusted_img_L, 
            black="black", 
            white="white"
        ).convert("RGB")
        
        # 6. 合併對比度調整後的灰度 RGB 和原始 Alpha 通道 (A)
        final_img = Image.merge('RGBA', final_grayscale_rgb.split()[:3] + (A,))
        
        # 7. 儲存結果
        final_img.save(output_path, 'PNG')
        
        print(f"✅ 圖片已成功轉換為灰度、對比度已調整並保留透明背景，儲存至: {output_path}")

    except Exception as e:
        print(f"❌ 處理圖片時發生錯誤: {e}")

print("--- 圖片處理開始：灰度 + 對比度減少 50% ---")
convert_and_reduce_contrast(INPUT_IMAGE, OUTPUT_IMAGE, CONTRAST_REDUCTION)