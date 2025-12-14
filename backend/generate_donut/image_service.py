import os
import json
import gc
import time
import torch
from diffusers import StableDiffusionXLPipeline
from PIL import Image

# ----------------------------------------------------
# 1. 核心設定 (來自 step3_generate_image.py)
# ----------------------------------------------------

# 🚨 請確保在 app.py 或您的環境中定義了這個路徑
SDXL_MODEL_PATH = r"\\MSI\sdxl_base"

# 輸出目錄 (用於建構路徑，實際寫入由 app.py 控制)
IMAGE_OUTPUT_DIR = os.path.join("images", "generated_images")

# 全域模型實例 (用於延遲載入，避免每次呼叫都重新載入)
pipe_t2i = None

# ----------------------------------------------------
# 2. 輔助函數
# ----------------------------------------------------

def flush_memory():
    """清理 CUDA 記憶體並運行 Python 垃圾回收 (來自 step3_generate_image.py)"""
    if torch.cuda.is_available():
        try:
            torch.cuda.empty_cache()
        except Exception:
            pass
    gc.collect()

def check_model_exists(local_path):
    """檢查模型資料夾是否存在且不為空"""
    if os.path.exists(local_path) and os.listdir(local_path):
        return True
    return False

def load_sdxl_pipe(model_path):
    """
    載入 SDXL 模型並進行優化。
    只在模型未載入時執行。
    """
    global pipe_t2i
    if pipe_t2i is not None:
        return pipe_t2i, None # 已載入，直接返回
        
    if not check_model_exists(model_path):
        return None, f"找不到 SDXL 模型路徑: {model_path}"

    DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
    
    try:
        print(f"--- 首次載入 SDXL 模型 ({DEVICE}) ---")
        
        # 載入模型
        pipe_t2i = StableDiffusionXLPipeline.from_pretrained(
            model_path,
            torch_dtype=torch.float16 if DEVICE == "cuda" else torch.float32,
            use_safetensors=True,
        )

        if DEVICE == "cuda":
            # 啟用顯存優化
            pipe_t2i.enable_model_cpu_offload()
            pipe_t2i.enable_vae_slicing()
            pipe_t2i.enable_vae_tiling()
        else:
            pipe_t2i = pipe_t2i.to(DEVICE)
            
        print("✅ 模型載入成功。")
        return pipe_t2i, None
        
    except Exception as e:
        # 載入失敗時，清理並將模型設為 None
        pipe_t2i = None 
        flush_memory()
        return None, f"模型載入失敗: {e}"


# ----------------------------------------------------
# 3. Step 3 主執行函數 (供 app.py 呼叫)
# ----------------------------------------------------

def execute_step3(input_list, output_dict):
    """
    執行 Step 3 的核心邏輯：生成圖片並更新狀態。

    Args:
        input_list (list): 任務狀態列表。
        output_dict (dict): 任務內容/分數字典。

    Returns:
        tuple: (input_list, output_dict, generated_count, error_status)
    """
    if StableDiffusionXLPipeline is None or torch is None:
        return input_list, output_dict, 0, "缺少 'torch' 或 'diffusers' 函式庫。"
        
    # 載入模型 (延遲載入)
    pipe, model_error = load_sdxl_pipe(SDXL_MODEL_PATH)
    if model_error:
        return input_list, output_dict, 0, model_error

    generated_count = 0
    
    for task_input in input_list:
        tid = task_input.get('task_id')
        
        # 檢查條件：image_status=False, 已有 ID, 且 Output 中已有 Positive Prompt
        if (task_input.get('image_status') is False and 
            tid and tid in output_dict and 
            output_dict[tid].get('positive_prompt')):
            
            task_name = task_input.get('task_name', 'Unknown')
            pos_prompt = output_dict[tid]['positive_prompt']
            neg_prompt = output_dict[tid]['negative_prompt']

            print(f"--- 正在生成圖片: {task_name} ({tid}) ---")
            
            try:
                # 執行生成
                image = pipe(
                    prompt=pos_prompt,
                    negative_prompt=neg_prompt,
                    num_inference_steps=25,
                    guidance_scale=7.5
                ).images[0]

                # 定義並創建儲存路徑
                filename = f"generated_image_{tid}.png"
                output_path = os.path.join(IMAGE_OUTPUT_DIR, filename)
                os.makedirs(IMAGE_OUTPUT_DIR, exist_ok=True) # 確保目錄存在
                
                # 存檔
                image.save(output_path)
                
                # 更新 Output 和 Input
                output_dict[tid]['image_path'] = output_path
                task_input['image_status'] = True
                
                generated_count += 1
                flush_memory() # 清理 CUDA 緩存

            except Exception as e:
                print(f"   ❌ 任務 {task_name} 生成失敗: {e}")
                flush_memory()
                continue
            
    return input_list, output_dict, generated_count, None