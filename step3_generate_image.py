import os
import gc
import json
import time
import torch
from diffusers import StableDiffusionXLPipeline

# ----------------------------------------------------
# 1. 設定參數與路徑
# ----------------------------------------------------

# 🚨 模型本地資料夾路徑
SDXL_MODEL_PATH = r"\\MSI\sdxl_base"

# 檔案路徑
GLOBAL_INPUT_FILE = 'json/all_tasks_input.json'
GLOBAL_OUTPUT_FILE = 'json/all_tasks_output.json'

# 圖片輸出目錄
IMAGE_OUTPUT_DIR = os.path.join("images", "generated_images")

# ----------------------------------------------------
# 2. 輔助函數 (JSON讀寫 & 記憶體清理)
# ----------------------------------------------------

def flush_memory():
    """清理 CUDA 記憶體並運行 Python 垃圾回收"""
    if torch.cuda.is_available():
        try:
            torch.cuda.empty_cache()
        except Exception:
            pass
    gc.collect()

def read_json(file_name, default_if_missing):
    try:
        with open(file_name, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return default_if_missing
    except Exception as e:
        print(f"❌ 讀取錯誤 {file_name}: {e}")
        return default_if_missing

def write_json(file_name, data):
    try:
        os.makedirs(os.path.dirname(file_name), exist_ok=True)
        with open(file_name, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"❌ 寫入錯誤 {file_name}: {e}")
        return False

def check_model_exists(local_path):
    if os.path.exists(local_path) and os.listdir(local_path):
        return True
    return False

# ----------------------------------------------------
# 3. 主程式邏輯
# ----------------------------------------------------

if __name__ == "__main__":

    # --- 步驟 A: 準備環境 ---
    
    DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"--- 運算裝置: {DEVICE} ---")

    os.makedirs(IMAGE_OUTPUT_DIR, exist_ok=True)

    if not check_model_exists(SDXL_MODEL_PATH):
        print(f"❌ 錯誤: 找不到模型路徑 {SDXL_MODEL_PATH}")
        exit()

    # --- 步驟 B: 讀取資料 ---

    input_list = read_json(GLOBAL_INPUT_FILE, [])
    output_dict = read_json(GLOBAL_OUTPUT_FILE, {})

    if not input_list:
        print("💡 Input 檔案為空。")
        exit()

    # 篩選待處理任務：
    # 條件：image_status 為 False，且 Output 中已有該 task_id (表示已初始化)，且已有 Prompt
    tasks_to_process = []
    for t in input_list:
        tid = t.get('task_id')
        if t.get('image_status') is False and tid and tid in output_dict:
            # 確保已有 Prompt
            if output_dict[tid].get('positive_prompt'):
                tasks_to_process.append(t)

    if not tasks_to_process:
        print("\n==========================================================")
        print("💡 目前沒有需要生成圖片的任務 (條件: image_status=False 且已有 Prompt)。")
        print("==========================================================")
        exit()

    print(f"\n💡 識別到 {len(tasks_to_process)} 個待生成圖片的任務。準備載入模型...")

    # --- 步驟 C: 載入模型 (只載入一次) ---
    
    pipe_t2i = None
    try:
        print(f"--- 正在載入 SDXL 模型: {SDXL_MODEL_PATH} ---")
        
        # 1. 載入模型 (先不移動到 GPU，讓 enable_model_cpu_offload 處理)
        pipe_t2i = StableDiffusionXLPipeline.from_pretrained(
            SDXL_MODEL_PATH,
            torch_dtype=torch.float16 if DEVICE == "cuda" else torch.float32,
            use_safetensors=True,
        )

        if DEVICE == "cuda":
            print("🔧 啟用 Model CPU Offload (顯存優化)...")
            pipe_t2i.enable_model_cpu_offload()
            
            print("🔧 啟用 VAE Slicing & Tiling (解碼優化)...")
            pipe_t2i.enable_vae_slicing()
            pipe_t2i.enable_vae_tiling()
        else:
            pipe_t2i = pipe_t2i.to(DEVICE)

        print("✅ 模型載入完成。")
    except Exception as e:
        print(f"❌ 模型載入失敗: {e}")
        exit()

    # --- 步驟 D: 批次生成圖片 ---

    generated_count = 0

    print("\n=================================================")
    print("          🖼️ 批次圖像生成開始")
    print("=================================================")

    for task_input in input_list:
        
        tid = task_input.get('task_id')
        
        # 再次檢查條件 (針對原始列表迭代，只處理目標)
        # 1. image_status 為 False
        # 2. tid 存在且在 output_dict 中
        # 3. output_dict 中有 positive_prompt
        if (task_input.get('image_status') is False and 
            tid and tid in output_dict and 
            output_dict[tid].get('positive_prompt')):
            
            task_name = task_input.get('task_name', 'Unknown')
            
            # 從 Output Dict 取得 Prompt
            pos_prompt = output_dict[tid].get('positive_prompt', '')
            neg_prompt = output_dict[tid].get('negative_prompt', '')

            print(f"\n--- 正在生成: {task_name} ({tid}) ---")
            # print(f"Prompt: {pos_prompt[:50]}...") # 除錯用
            
            try:
                # 執行生成
                image = pipe_t2i(
                    prompt=pos_prompt,
                    negative_prompt=neg_prompt,
                    num_inference_steps=25,
                    guidance_scale=7.5
                ).images[0]

                # 定義儲存路徑
                filename = f"generated_image_{tid}.png"
                output_path = os.path.join(IMAGE_OUTPUT_DIR, filename)

                # 存檔
                image.save(output_path)
                print(f"   ✅ 儲存至: {output_path}")

                # A. 更新 Output (填入圖片路徑)
                output_dict[tid]['image_path'] = output_path
                
                # B. 更新 Input (更改 Status)
                task_input['image_status'] = True
                
                generated_count += 1
                
                # 手動清理一下 Python 記憶體
                gc.collect()

            except Exception as e:
                print(f"   ❌ 生成失敗: {e}")
                flush_memory()

    # --- 步驟 E: 釋放資源並儲存結果 ---

    print("\n--- 正在釋放模型記憶體 ---")
    del pipe_t2i
    flush_memory()

    if generated_count > 0:
        if write_json(GLOBAL_INPUT_FILE, input_list) and write_json(GLOBAL_OUTPUT_FILE, output_dict):
            print(f"\n🎉 成功生成 {generated_count} 張圖片。")
            print(f"💾 Input (Status) 與 Output (Path) 皆已更新。")
        else:
            print(f"❌ JSON 寫入失敗")
    else:
        print("\n💡 本次未生成任何圖片。")

    print("=================================================")