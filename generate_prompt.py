import google.genai as genai
import json 
import os      
import gc      
from datetime import datetime 
from google.genai.errors import APIError

# ----------------------------------------------------
# 設定區塊：請確保這些資訊正確
# ----------------------------------------------------

# 您將使用的 Gemini 模型名稱
MODEL_NAME = 'gemini-2.5-flash' 

# SDXL Prompt 限制
MAX_WORDS_PER_PROMPT = 77  

# 範例輸入：使用者完成的任務代辦事項
TASK = "寫演算法程式作業"

# 任務簡短名稱，將用於檔案命名
TASK_SHORTNAME = "" 

#-----------------------------------------------------
# 檔案儲存設定區塊
# ----------------------------------------------------
BASE_PROMPT_DIR = "prompt" 
POSITIVE_SUB_DIR = "positive"
NEGATIVE_SUB_DIR = "negative"

# 全域變數用於存放 Gemini 客戶端
client = None 

# ----------------------------------------------------
# 輔助函數：環境變數設定與客戶端初始化
# ----------------------------------------------------

def initialize_gemini_client():
    """
    檢查 GEMINI_API_KEY 環境變數並初始化 Gemini 客戶端。
    """
    global client
    
    # 檢查環境變數
    api_key = os.getenv("GEMINI_API_KEY")
    
    if not api_key:
        print("❌ 錯誤：GEMINI_API_KEY 環境變數未設定。")
        print("💡 請先執行以下指令 (根據您的作業系統)：")
        print("   - Linux/macOS: export GEMINI_API_KEY=\"[您的金鑰]\"")
        print("   - Windows CMD: set GEMINI_API_KEY=[您的金鑰]")
        return False
    
    try:
        # 使用 os.getenv 取得的金鑰字串來初始化客戶端
        client = genai.Client(api_key=api_key)
        print("✅ Gemini API 客戶端初始化成功。")
        return True
    except Exception as e:
        print(f"❌ Gemini 客戶端初始化失敗。錯誤詳情: {e}")
        return False


# ----------------------------------------------------
# 輔助函數：生成檔名 / 記憶體清理 (與原版相同)
# ----------------------------------------------------

def generate_timestamp_name(task_description: str):
    """
    生成一個基於時間戳記的唯一檔名。
    """
    prefix = "task" 
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{prefix}_{timestamp}"


def flush_memory():
    """運行 Python 垃圾回收，清理 CPU 記憶體"""
    gc.collect()
    print("✅ CPU 記憶體 (gc) 已清理。")


# ----------------------------------------------------
# 函數：使用 Gemini 服務生成 SDXL 專用的正負面 Prompt
# ----------------------------------------------------

def generate_sdxl_prompts(task_description: str):
    """
    連線到 Gemini 服務，生成 SDXL T2I 模型的正負面 Prompt。
    """
    global client
    if not client:
        return {"Error": "Gemini API 客戶端未初始化。", "Note": "請先設定環境變數 GEMINI_API_KEY。"}

    # Meta-Prompt (系統提示)：與原來的嚴格限制一致
    system_prompt = (
        f"You are a master SDXL prompt engineer, specializing in creating **highly effective 2D design and illustration prompts**. "
        f"Your images must be **non-human, non-animal, and strictly in a flat, 2D style (no 3D rendering or realistic photography)**. "
        f"Your single goal is to transform the user's completed task description into a pair of 'Positive_Prompt' and 'Negative_Prompt'."
        f"**【STRICT FORMATTING REQUIREMENT】**\n"
        f"1. **LANGUAGE**: ALL final output text (including the prompts) **MUST BE IN ENGLISH**.\n"
        f"2. **OUTPUT STRUCTURE**: The output **MUST** be a valid, standard JSON object containing exactly two keys: 'Positive_Prompt' and 'Negative_Prompt'.\n"
        f"**【CORE CONTENT RESTRICTIONS】**\n"
        f"3. **ABSOLUTELY FORBIDDEN**: You **MUST NOT** generate any imagery containing **Humans (person, people, human, figure, portrait)** or **Animals (animal, pet, dog, cat, etc.)**.\n"
        f"4. **FOCUS**: The image should concentrate on **relevant abstract symbols, flat graphic objects, patterns, and simplified scenes** related to the task.\n"
        f"5. **STYLE CHOICE**: The image style **MUST** be chosen from one of these five 2D options: **'Flat Vector Illustration', 'Minimalist Iconography', 'Vibrant Geometric Pattern', 'Cute Cartoon Style', or 'Clean Line Art'**.\n"
        f"6. **LENGTH**: Both Positive and Negative prompts **MUST NOT exceed {MAX_WORDS_PER_PROMPT} words**.\n"
    )
    
    # 用戶請求
    user_request = (
        f"Please generate the required pair of Positive and Negative Prompts for the following completed task:\n"
        f"Task Description: '{task_description}'\n"
        f"\n**Positive Prompt Guidance:**\n"
        f"* **MUST** use a **2D design style** (e.g., 'Flat Vector Illustration style').\n"
        f"* **MUST** include a clear, specific, and descriptive flat object or abstract representation of the task (e.g., 'a stylized swimming icon, flat design').\n"
        f"* **MUST** include keywords for color, simplified background, and texture (e.g., 'deep blue and cyan palette', 'smooth shading, white background').\n"
        f"\n**Negative Prompt Guidance:**\n"
        f"* **MUST** be comprehensive and explicitly include all exclusion keywords: "
        f"`person, people, human, woman, man, child, baby, animal, pet, dog, cat, swimmer, figure, portrait, blurry, deformed, poorly drawn, ugly, artifacts, wrong anatomy, 3D render, photorealistic, realistic lighting`.\n"
        f"**REMINDER: ALL OUTPUT MUST BE IN ENGLISH AND IN JSON FORMAT.**" 
    )

    print(f"--- 嘗試使用 Gemini 模型 {MODEL_NAME} 生成 SDXL Prompt ---")

    try:
        response = client.models.generate_content(
            model=MODEL_NAME,  
            contents=[
                {'role': 'user', 'parts': [{'text': system_prompt + user_request}]}
            ],
            config=genai.types.GenerateContentConfig(
                temperature=0.8,
                response_mime_type="application/json" 
            )
        )
        
        # 解析 JSON 輸出
        json_output = json.loads(response.text)
        
        return json_output

    except APIError as e:
        return {"Error": f"Gemini API 錯誤：{e}", "Note": "請確認 API 金鑰有效、模型名稱正確且有足夠的配額。"}
    except json.JSONDecodeError:
        return {"Error": "JSON 解析錯誤：模型輸出非標準 JSON。", "Note": f"模型的原始輸出為: {response.text[:200]}..."}
    except Exception as e:
        return {"Error": f"生成或連線發生未預期錯誤：{e}", "Note": "請檢查網路連線或其他設定。"}


# ----------------------------------------------------
# 函數：儲存 Prompt 到檔案 (與原版相同)
# ----------------------------------------------------

def save_prompts_to_files(prompts: dict, short_name: str):
    """
    將 Positive 和 Negative Prompt 儲存到指定路徑的檔案中。
    """
    
    pos_dir = os.path.join(BASE_PROMPT_DIR, POSITIVE_SUB_DIR)
    neg_dir = os.path.join(BASE_PROMPT_DIR, NEGATIVE_SUB_DIR)

    os.makedirs(pos_dir, exist_ok=True)
    os.makedirs(neg_dir, exist_ok=True)

    pos_prompt = prompts.get('Positive_Prompt', '')
    neg_prompt = prompts.get('Negative_Prompt', '')

    pos_filename = os.path.join(pos_dir, f"positive_{short_name}.txt")
    neg_filename = os.path.join(neg_dir, f"negative_{short_name}.txt")

    print(f"\n--- 儲存 Prompt 至檔案 ---")

    try:
        with open(pos_filename, 'w', encoding='utf-8') as f:
            f.write(pos_prompt)
        print(f"✅ Positive Prompt 已儲存至: {pos_filename}")

        with open(neg_filename, 'w', encoding='utf-8') as f:
            f.write(neg_prompt)
        print(f"✅ Negative Prompt 已儲存至: {neg_filename}")

        return True
    except Exception as e:
        print(f"❌ 儲存檔案失敗: {e}")
        return False


# ----------------------------------------------------
# 主程式執行區塊
# ----------------------------------------------------
if __name__ == "__main__":

    # 1. 初始化客戶端：檢查環境變數是程式的第一步
    if not initialize_gemini_client():
        # 如果初始化失敗（即金鑰未設定），則程式停止執行
        exit() 

    # 2. 生成 TASK_SHORTNAME (純時間戳記)
    TASK_SHORTNAME = generate_timestamp_name(TASK)
    print(f"\n💡 生成的 TASK_SHORTNAME (含時間戳記): **{TASK_SHORTNAME}**")
    
    # 3. 呼叫函數並輸出結果 (生成 SDXL Prompt)
    prompts = generate_sdxl_prompts(TASK)

    print("\n================ 🤖 模型生成的 SDXL Prompt ================")
    
    if "Error" in prompts:
        print(f"狀態：失敗")
        print(f"錯誤詳情：{prompts['Error']}")
        print(f"備註：{prompts['Note']}")
    else:
        print(f"狀態：成功")
        pos_p = prompts.get('Positive_Prompt', 'N/A')
        neg_p = prompts.get('Negative_Prompt', 'N/A')

        print("Positive Prompt:")
        print(pos_p)
        print("\nNegative Prompt (用於排除不想要的元素):")
        print(neg_p)

        # 4. 儲存 Prompt 到檔案
        save_prompts_to_files(prompts, TASK_SHORTNAME)

    flush_memory() 

    print("==========================================================")