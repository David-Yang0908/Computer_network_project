import os
import gc
import torch
from PIL import Image
from diffusers import StableDiffusionXLPipeline

# --- 1. 設定參數與路徑 ---

TASK = "task_20251213_045454"

# 🚨 模型本地資料夾路徑 (根據您的要求修改)
SDXL_MODEL_PATH = r"\\MSI\sdxl_base"

# 輸入檔案路徑 (與 .py 腳本相同目錄)
POSITIVE_PROMPT_INPUT_FILE = f"prompt\\positive\\positive_{TASK}.txt"
# 設定 Negative Prompt (可根據需求修改)
NEGATIVE_PROMPT_INPUT_FILE = f"prompt\\negative\\negative_{TASK}.txt"

# 輸出目錄路徑 (當前目錄下的 'image' 資料夾)
IMAGE_OUTPUT_FILENAME = f"images\\generated_images\\generated_image_{TASK}.png"

# --- 2. 環境準備與記憶體清理 ---

# 記憶體清理工具
def flush_memory():
    """清理 CUDA 記憶體並運行 Python 垃圾回收"""
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
    gc.collect()
    print("✅ 記憶體已清理。")

# 檢查 CUDA (GPU) 是否可用
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
if DEVICE == "cuda":
    print(f"--- 偵測到 GPU: {torch.cuda.get_device_name(0)}，將使用 GPU 運算。 ---")
else:
    print("--- 警告: 未偵測到 GPU，將使用 CPU 運算 (速度會慢很多)。 ---")



print(f"\n✅ 期望的 SDXL 模型路徑: {SDXL_MODEL_PATH}")
print(f"✅ 圖像輸出檔案: {IMAGE_OUTPUT_FILENAME}\n")


# --- 3. 模型存在性檢查 (不自動下載) ---
def check_model_exists(local_path):
    """檢查本地路徑是否存在模型，不存在則終止。"""
    if os.path.exists(local_path) and os.listdir(local_path):
        print(f"✅ 模型已存在: {local_path}")
        return True
    else:
        print(f"❌ 嚴重錯誤: 模型路徑 {local_path} 不存在或為空。")
        print("請確認您已手動將 Stable Diffusion XL 模型內容放到該目錄。")
        return False

if not check_model_exists(SDXL_MODEL_PATH):
    # 終止程式
    raise SystemExit("SDXL 模型未找到，程式終止。")

flush_memory() # 清理記憶體


# --- 4. 載入 SDXL 模型 ---

print("\n--- 正在載入 Stable Diffusion XL (T2I) 模型 ---")
try:
    # 從本地路徑載入模型
    pipe_t2i = StableDiffusionXLPipeline.from_pretrained(
        SDXL_MODEL_PATH,
        torch_dtype=torch.float16,
        use_safetensors=True,
    ).to(DEVICE) # 使用偵測到的裝置

    # 啟用 CPU Offload (如果使用 GPU 且記憶體不足，這是一個很好的優化)
    if DEVICE == "cuda":
        pipe_t2i.enable_model_cpu_offload()

    print("✅ Stable Diffusion XL 載入完成。")
except Exception as e:
    print(f"❌ 載入 SDXL 失敗: {e}")
    flush_memory()
    raise SystemExit("SDXL 模型載入失敗，程式終止。")


# --- 5. 圖像生成 (T2I) ---

print("\n=================================================")
print("          🖼️ 圖像生成 (T2I) 開始")
print("=================================================")

# 讀取 Prompt 檔案
try:
    with open(POSITIVE_PROMPT_INPUT_FILE, 'r', encoding='utf-8') as f:
        prompt_text = f.read().strip()
    
    if not prompt_text:
        raise ValueError("Prompt 檔案內容為空。")

except FileNotFoundError:
    print(f"❌ 錯誤: 找不到輸入檔案 {POSITIVE_PROMPT_INPUT_FILE}。請確保它與腳本在同一目錄下。")
    del pipe_t2i
    flush_memory()
    raise SystemExit("找不到 Prompt 檔案，程式終止。")
except Exception as e:
    print(f"❌ 讀取 Prompt 檔案失敗: {e}")
    del pipe_t2i
    flush_memory()
    raise SystemExit("Prompt 檔案讀取失敗，程式終止。")

print(f"✅ 讀取的 Prompt: '{prompt_text[:50]}...'")

# 執行圖像生成 (SDXL)
print("--- 正在生成圖像... ---")
try:
    image = pipe_t2i(
        prompt=prompt_text,
        negative_prompt=NEGATIVE_PROMPT_INPUT_FILE,
        num_inference_steps=25,
        guidance_scale=7.5
    ).images[0]

    # 儲存到輸出目錄
    output_path = IMAGE_OUTPUT_FILENAME
    image.save(output_path)
    print(f"\n✅ 圖像生成成功並儲存到: {output_path}")

except Exception as e:
    print(f"❌ 圖像生成失敗: {e}")

# 清理 SDXL 模型以釋放 VRAM
print("\n--- 正在釋放 SDXL 模型記憶體 ---")
del pipe_t2i
flush_memory()

print("\n=================================================")
print("          🎉 圖像生成腳本執行完畢 🎉")
print("=================================================")