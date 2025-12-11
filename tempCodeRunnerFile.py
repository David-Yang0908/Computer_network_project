from PIL import Image

def adjust_image_intensity(input_path, output_path, intensity_factor):
    """
    將圖片轉換為 HSV 模型，調整 V 通道（強度/亮度），然後再轉回 RGB 儲存。

    Args:
        input_path (str): 輸入圖片的路徑。
        output_path (str): 輸出圖片的路徑 (.png 或 .jpg)。
        intensity_factor (float): 強度調整因子。
                                  > 1.0 會增加強度/亮度 (例如 1.5 會增加 50%)。
                                  < 1.0 會降低強度/亮度 (例如 0.5 會減少 50%)。
    """
    try:
        # 1. 開啟圖片並轉換為 RGB (如果原始圖片不是 RGB)
        img = Image.open(input_path).convert("RGB")
    except FileNotFoundError:
        print(f"錯誤：找不到圖片文件 - {input_path}")
        return

    # 2. 將 RGB 圖片轉換為 HSV 模式
    # Pillow 使用 'HSV' 模式來處理色相、飽和度和強度
    hsv_img = img.convert("HSV")

    # 3. 取得 HSV 通道數據
    # hsv_img.split() 會返回三個 Image 物件，分別代表 H, S, V 通道
    h, s, v = hsv_img.split()

    # 4. 調整 V 通道 (強度/亮度)
    # 獲取 V 通道的像素數據
    v_data = v.getdata()
    
    new_v_data = []
    
    # 遍歷 V 通道的所有像素值 (範圍通常為 0 到 255)
    for value in v_data:
        # 應用調整因子
        new_value = int(value * intensity_factor)
        
        # 確保新的像素值在有效範圍 [0, 255] 內
        if new_value > 255:
            new_value = 255
        elif new_value < 0:
            new_value = 0
            
        new_v_data.append(new_value)

    # 5. 將調整後的數據寫回 V 通道
    v.putdata(new_v_data)

    # 6. 將 H、S、新的 V 通道合併回 HSV 圖片
    adjusted_hsv_img = Image.merge("HSV", (h, s, v))

    # 7. 將 HSV 圖片轉換回 RGB 模式
    final_rgb_img = adjusted_hsv_img.convert("RGB")
    
    # 8. 儲存結果
    final_rgb_img.save(output_path)
    
    print(f"圖片強度已調整 (因子: {intensity_factor})，並儲存到：{output_path}")

# --- 範例使用 ---
input_file = 'original_mask.png'
output_file_brighter = 'output_image_brighter.jpg'
output_file_darker = 'output_image_darker.jpg'

# 增加亮度/強度 50%
adjust_image_intensity(input_file, output_file_brighter, intensity_factor=1.5)

# 減少亮度/強度 30%
adjust_image_intensity(input_file, output_file_darker, intensity_factor=0.7)