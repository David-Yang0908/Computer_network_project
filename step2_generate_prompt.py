import groq # 引入 Groq 函式庫
import json 
import os      
import gc      
import time
from groq import Groq # 引入 Groq 客戶端
from groq import RateLimitError
from groq import APIError
from groq.types.chat import ChatCompletionMessageParam
# --- 設定區塊 ---

MODEL_NAME = 'llama-3.1-8b-instant' 
MAX_WORDS_PER_PROMPT = 40  

GLOBAL_INPUT_FILE = 'json/all_tasks_input.json' 
GLOBAL_OUTPUT_FILE = 'json/all_tasks_output.json' 

client = None 

# --- 輔助函數 ---

def initialize_groq_client():
    global client
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        print("❌ 錯誤：GROQ_API_KEY 未設定。")
        return False
    try:
        client = Groq(api_key=api_key)
        print("✅ Groq API 初始化成功。")
        return True
    except Exception as e:
        print(f"❌ Groq 初始化失敗: {e}")
        return False

def flush_memory():
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

# --- Prompt 生成邏輯 ---

def generate_sdxl_prompts(task_description: str):
    """
    連線到 Groq 服務，生成 SDXL T2I 模型的正負面 Prompt，包含自動重試。
    """
    global client
    if not client:
        return {"Error": "Groq API 客戶端未初始化。", "Note": "請先設定環境變數 GROQ_API_KEY。"}

    # Meta-Prompt (系統提示)：
    system_prompt = (
        f"You are a **Token-Optimized Digital Art Director** specializing in creating highly concise, high-density prompts for SDXL. "
        f"Your output must adhere to the following **MAXIMUM DENSITY, MINIMUM LENGTH** protocol and the user's visualization requirements:\n\n"
        
        f"**【STRICT CONSTRAINTS】**\n"
        f"1. **LENGTH LIMIT**: Prompts MUST be under **{MAX_WORDS_PER_PROMPT} words**. This is critical.\n"
        f"2. **FORMAT**: Use **comma-separated keywords and short phrases**. NO full sentences. NO filler words.\n"
        f"3. **VISUAL STYLE**: **Vector Art Style**, **Flat Design**, **Digital Illustration**, **Line Art**, **Minimalist**. AVOID photorealism and deep 3D shading.\n"
        f"4. **CONTENT FOCUS**: The image must be **fully detailed and filled to the edges** (全圖填充). Deconstruct the user's task into relevant **Abstract symbols, UI/UX components, Data visualization, stylized organic/inorganic elements**.\n"
        f"5. **FORBIDDEN**: Humans, photorealistic, 3D renders, faces, anatomy, blurry, low-resolution.\n\n"
        
        f"**【OUTPUT JSON FORMAT】**\n"
        f"The output must be a standard JSON object with keys: 'Positive_Prompt' and 'Negative_Prompt'.\n"
    )

    # 用戶請求
    user_request = (
        f"**TASK TO VISUALIZE**: '{task_description}'\n\n"
        f"Generate ONE single string for 'Positive_Prompt' and ONE single string for 'Negative_Prompt'. "
        f"Example Negative Prompt: 'photorealistic, 3d render, realistic, photograph, human, person, face, blurry, low quality, pixelated, ugly, empty background, watermark, text, signature'.\n\n"
        f"**Response Language**: English Only."
    )
    
    # Groq/OpenAI 風格的 Chat Messages 結構
    messages: list[ChatCompletionMessageParam] = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_request}
    ]

    print(f"--- 嘗試使用 Groq 模型 {MODEL_NAME} 生成 SDXL Prompt (高密度模式) ---")

    # --- 自動重試機制 (針對 Groq 的 Rate Limit 錯誤) ---
    max_retries = 3
    base_wait_time = 10  # Groq 的速率限制通常更高，所以等待時間可以縮短，但仍保留安全間隔。

    for attempt in range(max_retries + 1):
        try:
            # 使用 Groq 的 Chat Completions API
            response = client.chat.completions.create(
                model=MODEL_NAME,
                messages=messages,
                temperature=0.8,
                # Groq 使用 response_format 來要求 JSON 輸出
                response_format={"type": "json_object"} 
            )
            
            # Groq 的回應內容在 choices[0].message.content
            json_text = response.choices[0].message.content
            json_output = json.loads(json_text)
            
            return json_output

        #  直接捕捉新的 RateLimitError 類別
        except RateLimitError as e:
            if attempt < max_retries:
                print(f"⚠️ 觸發 Groq 速率限制 (429)。")
                print(f"   ⏳ 正在冷卻 {base_wait_time} 秒後進行第 {attempt + 1} 次重試...")
                time.sleep(base_wait_time)
                continue
            else:
                return {"Error": f"重試 {max_retries} 次後仍然失敗：{e}", "Note": "請稍後再試或檢查 Groq 配額。"}
        
        # 捕捉 Groq SDK 的其他 API 錯誤，使用頂層的 APIError
        except APIError as e:
            # 處理 Groq SDK 的其他一般 API 錯誤
            return {"Error": f"Groq API 錯誤：{e}", "Note": "請確認 API 金鑰有效或模型名稱正確。"}
        
        except json.JSONDecodeError:
            return {"Error": "JSON 解析錯誤：模型輸出非標準 JSON。", "Note": f"模型的原始輸出為: {json_text[:200]}..."}
        
        except Exception as e:
            return {"Error": f"生成或連線發生未預期錯誤：{e}", "Note": "請檢查網路連線或其他設定。"}
            
    return {"Error": "未知錯誤", "Note": "重試迴圈異常結束。"}

# --- 主程式 ---
# (main 函數保持不變，但記得將初始化函數的呼叫名稱從 initialize_gemini_client 替換為 initialize_groq_client)

def main():
    #  呼叫新的初始化函數
    if not initialize_groq_client(): 
        exit()

    # 1. 讀取資料
    input_list = read_json(GLOBAL_INPUT_FILE, []) 
    output_dict = read_json(GLOBAL_OUTPUT_FILE, {}) 

    if not input_list:
        print("💡 Input 檔案為空。")
        exit()

    # 2. 篩選待處理任務
    tasks_to_process = [
        t for t in input_list 
        if t.get('prompt_status') is False and t.get('task_id')
    ]

    if not tasks_to_process:
        print("\n==========================================================")
        print("💡 所有已初始化的任務皆已生成 Prompt。")
        print("==========================================================")
        exit()

    print(f"\n💡 識別到 {len(tasks_to_process)} 個待生成 Prompt 的任務。")
    generated_count = 0

    # 3. 迭代處理
    for task_input in input_list:
        
        if task_input.get('prompt_status') is False and task_input.get('task_id'):
            
            task_id = task_input['task_id']
            task_name = task_input.get('task_name', 'Unknown')
            
            if task_id not in output_dict:
                print(f"⚠️ 警告: Output 中找不到 ID {task_id}，跳過。")
                continue

            print(f"\n--- 正在生成 Prompt: {task_name} ({task_id}) ---")
            
            prompts = generate_sdxl_prompts(task_name)
            
            if "Error" in prompts:
                print(f"   ❌ 生成失敗: {prompts['Error']}")
            else:
                pos_p = prompts.get('Positive_Prompt', '')
                neg_p = prompts.get('Negative_Prompt', '')
                
                print("   ✅ 生成成功。")
                
                # --- 終端機輸出顯示 ---
                print("-" * 50)
                print(f"🔹 \033[96mPositive Prompt:\033[0m\n{pos_p}\n")
                print(f"🔹 \033[96mNegative Prompt:\033[0m\n{neg_p}")
                print("-" * 50)
                # -----------------------------

                # A. 更新 Output (填入 Prompt)
                output_dict[task_id]['positive_prompt'] = pos_p
                output_dict[task_id]['negative_prompt'] = neg_p
                
                # B. 更新 Input (更改 Status)
                task_input['prompt_status'] = True
                
                generated_count += 1
                
                print("   ⏳ 暫停 1 秒...")
                time.sleep(1) # Groq 速度快且速率限制高，可縮短等待時間
                
            flush_memory()

    # 4. 儲存變更
    if generated_count > 0:
        if write_json(GLOBAL_INPUT_FILE, input_list) and write_json(GLOBAL_OUTPUT_FILE, output_dict):
            print(f"\n====================== 批次生成結果 =======================")
            print(f"🎉 成功生成 {generated_count} 個任務的 Prompt。")
            print(f"💾 Input (Status) 與 Output (Content) 皆已更新。")
            print("==========================================================")
    else:
        print("\n❌ 本次未成功更新任何 Prompt。")


if __name__ == "__main__":
    main()