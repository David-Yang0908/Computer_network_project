import json
import os
import time
import gc # Step 2 原腳本中有使用，保持引入
from groq import Groq 
from groq import RateLimitError, APIError 
from groq.types.chat import ChatCompletionMessageParam # 確保類型提示正確

# ----------------------------------------------------
# 1. 核心設定 (來自 step2_generate_prompt.py)
# ----------------------------------------------------

MODEL_NAME = 'llama-3.1-8b-instant' 
MAX_WORDS_PER_PROMPT = 40  
# Groq Client 實例將在 execute_step2 中創建

# ----------------------------------------------------
# 2. Step 2 核心業務函數
# ----------------------------------------------------

def generate_sdxl_prompts(task_description: str, score: float, client: Groq):
    """
    連線到 Groq 服務，生成 SDXL T2I 模型的正負面 Prompt。
    (這是 step2_generate_prompt.py 的核心邏輯)
    
    Args:
        task_description (str): 任務名稱 (e.g., "洗衣服")
        score (float): 任務總分數
        client (Groq): 已初始化的 Groq 客戶端
    
    Returns:
        dict: 包含 'Positive_Prompt' 和 'Negative_Prompt' 或 'error' 訊息。
    """
    
    # 根據分數調整生成風格，讓高分任務獲得更精緻的 Prompt
    if score >= 200:
        style = "highly detailed, fantastical, epic, vibrant color, cinematic lighting"
    elif score >= 100:
        style = "clean vector art, minimalist, lo-fi aesthetic, detailed, high contrast"
    else:
        style = "simple, cute illustration, low-poly, soft colors, abstract"

    # Meta-Prompt (系統提示)
    system_prompt = (
        f"You are a **Token-Optimized Digital Art Director** specializing in creating highly concise, high-density prompts for SDXL. "
        f"The image should be an abstract or symbolic representation of the task, suitable for a donut chart slice texture. "
        f"Your output must adhere to the following **MAXIMUM DENSITY, MINIMUM LENGTH** protocol:\n\n"
        
        f"**【STRICT CONSTRAINTS】**\n"
        f"1. **LENGTH LIMIT**: Prompts MUST be under **{MAX_WORDS_PER_PROMPT} words**. This is critical.\n"
        f"2. **FORMAT**: Use **comma-separated keywords and short phrases**. NO full sentences. NO filler words.\n"
        f"3. **VISUAL STYLE**: Tech-Chic, Modern Vector Art, Lo-Fi Aesthetic, Geometric Abstraction, {style}.\n"
        f"4. **CONTENT FOCUS**: Abstract symbols, deconstructed objects, UI components, data visualization.\n"
        f"5. **FORBIDDEN**: Humans, photorealistic, 3D renders, faces, anatomy.\n\n"
        
        f"**【OUTPUT JSON FORMAT】**\n"
        f"The output must be a standard JSON object with keys: 'Positive_Prompt' and 'Negative_Prompt'.\n"
    )
    
    # 用戶請求
    user_request = (
        f"**TASK TO VISUALIZE**: '{task_description}'\n\n"
        f"Current Task Score: {score}. Please generate the prompts now."
    )
    
    messages: list[ChatCompletionMessageParam] = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_request}
    ]

    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=messages,
            temperature=0.8,
            response_format={"type": "json_object"} 
        )
        
        json_text = response.choices[0].message.content
        json_output = json.loads(json_text)
        
        return json_output

    except RateLimitError as e:
        return {"error": f"Groq 速率限制錯誤: {e}"}
    except APIError as e:
        return {"error": f"Groq API 錯誤: {e}"}
    except json.JSONDecodeError:
        return {"error": f"JSON 解析錯誤：模型輸出非標準 JSON。"}
    except Exception as e:
        return {"error": f"生成或連線發生未預期錯誤：{e}"}


# ----------------------------------------------------
# 3. Step 2 主執行函數 (供 app.py 呼叫)
# ----------------------------------------------------

def execute_step2(input_list, output_dict, api_key):
    """
    執行 Step 2 的核心邏輯：生成 Prompt 並更新狀態。

    Args:
        input_list (list): 來自 all_tasks_input.json 的列表。
        output_dict (dict): 來自 all_tasks_output.json 的字典。
        api_key (str): Groq API Key。

    Returns:
        tuple: (input_list, output_dict, generated_count, error_status)
    """
    if not api_key:
        return input_list, output_dict, 0, "GROQ_API_KEY 未設定。"
        
    try:
        client = Groq(api_key=api_key)
    except Exception as e:
        return input_list, output_dict, 0, f"Groq 客戶端初始化失敗: {e}"

    generated_count = 0
    
    for task_input in input_list:
        task_id = task_input.get('task_id')
        
        # 檢查條件：必須有 ID 且 prompt_status 必須為 False
        if task_id and task_input.get('prompt_status') is False:
            
            # 檢查 Output 中是否有分數 (確保 Step 1 已執行)
            if task_id not in output_dict or output_dict[task_id].get('total_score') is None:
                continue

            task_name = task_input.get('task_name', 'Unknown Task')
            score = output_dict[task_id]['total_score']
            
            # 呼叫 Groq API
            prompts = generate_sdxl_prompts(task_name, score, client)
            
            if 'error' in prompts:
                # 紀錄錯誤但繼續下一個任務
                print(f"   ❌ Prompt 生成失敗 ({task_name}): {prompts['error']}")
                continue
                
            pos_p = prompts.get('Positive_Prompt')
            neg_p = prompts.get('Negative_Prompt')
            
            if pos_p and neg_p:
                # A. 更新 Output (填入 Prompt)
                output_dict[task_id]['positive_prompt'] = pos_p
                output_dict[task_id]['negative_prompt'] = neg_p
                
                # B. 更新 Input (更改 Status)
                task_input['prompt_status'] = True
                
                generated_count += 1
                
                # 為了避免速率限制，短暫延遲
                time.sleep(0.5) 
            
    # 這裡只返回處理結果，不進行 JSON 寫入，寫入由 app.py 負責
    return input_list, output_dict, generated_count, None