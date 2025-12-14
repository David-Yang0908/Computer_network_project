import json
import os
import time
from datetime import datetime

# ----------------------------------------------------
# 1. 核心變數 (與 app.py 保持同步)
# ----------------------------------------------------

GLOBAL_INPUT_FILE = 'json/all_tasks_input.json' 
GLOBAL_OUTPUT_FILE = 'json/all_tasks_output.json' 

# ----------------------------------------------------
# 2. 輔助函數 (Utility Functions - 通常這些函數會被移到一個單獨的 utils.py 中，但為了簡化模組數量，暫時保留在這裡)
# ----------------------------------------------------

# 注意：這些函數在導入時會與 app.py 中的同名函數衝突，
# 在實際導入時，我們將只從這個模組中導入 score_service 相關的執行函數，
# 而 app.py 中仍需保留通用的 JSON 讀寫函數。
# 但為了讓此模組獨立運行測試，我們還是將其保留。

def read_json(file_name, default_if_missing):
    """讀取 JSON 檔案"""
    try:
        with open(file_name, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return default_if_missing
    except Exception as e:
        return {"error": str(e)} 

def write_json(file_name, data):
    """寫入 JSON 檔案"""
    try:
        os.makedirs(os.path.dirname(file_name), exist_ok=True)
        with open(file_name, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        return True
    except Exception as e:
        return False

def generate_timestamp_id():
    """生成唯一 Task ID (來自 step1_score_calculator.py)"""
    prefix = "task" 
    now = datetime.now()
    timestamp = now.strftime("%Y%m%d_%H%M%S")
    microsecond = now.strftime("%f") 
    return f"{prefix}_{timestamp}_{microsecond}"

# ----------------------------------------------------
# 3. Step 1 核心業務函數
# ----------------------------------------------------

def calculate_plan_d_score(data):
    """計算 PLAN D 分數 (來自 step1_score_calculator.py)"""
    try:
        # 從輸入資料中獲取參數，並設定預設值以防 Key 缺失
        r = data.get('r', 30.0)
        T_est = data.get('T_est', 0.0)
        P = data.get('P', 0.0)
        I = data.get('I', 3.0)
        D = data.get('D', 3.0)
        c = data.get('c', 0.0)
        mu = data.get('mu', 1.2)
        T_distract = data.get('T_distract', 0.0)
        T_phone = data.get('T_phone', 0.0)
        
        # 執行分數計算公式
        incentive_S = r * T_est * 1.3 * (1 + 0.15 * (I - 3)) * (1 + 0.05 * (D - 3)) * (c ** mu)
        penalty_P_behavior = (-30.0 * T_distract) + (-6.0 * T_phone)
        total_score = incentive_S + penalty_P_behavior
        
        return {
            "total_score": round(total_score, 2), 
            "incentive_score": round(incentive_S, 2), 
            "penalty_score": round(penalty_P_behavior, 2)
        }
    except Exception as e:
        return {"error": str(e)}

# ----------------------------------------------------
# 4. Step 1 主執行函數 (供 app.py 呼叫)
# ----------------------------------------------------

def execute_step1(input_list, output_dict):
    """
    執行 Step 1 的核心邏輯：計算分數、生成 ID、初始化 Output 字典。

    Args:
        input_list (list): 來自 all_tasks_input.json 的列表。
        output_dict (dict): 來自 all_tasks_output.json 的字典。

    Returns:
        tuple: (input_list, output_dict, updated_count)
    """
    updated_count = 0
    
    # 遍歷 Input List，尋找 task_id 為空的新任務
    for task_input in input_list:
        
        if not task_input.get('task_id'):
            
            # 1. 生成 ID
            new_id = generate_timestamp_id()
            # 確保 ID 唯一 (防止極端情況下的時間戳衝突)
            while new_id in output_dict:
                time.sleep(0.001) 
                new_id = generate_timestamp_id()
            
            # 2. 計算分數
            scores = calculate_plan_d_score(task_input)
            
            if "error" in scores:
                # 計算失敗，不初始化 ID，跳過此任務
                continue

            # 3. 更新 Input 和 Output
            task_name = task_input.get('task_name', 'Unknown')
            task_input['task_id'] = new_id
            
            output_dict[new_id] = {
                "task_id": new_id,
                "task_name": task_name,
                
                # 分數
                "total_score": scores['total_score'],
                "incentive_score": scores['incentive_score'],
                "penalty_score": scores['penalty_score'],
                
                # 內容路徑與 Prompt (初始化為 None，等待後續步驟填入)
                "positive_prompt": None,
                "negative_prompt": None,
                "image_path": None,
                "donut_path": None,
                "gray_path": None,
                "ratio_path": None,
                "cut_path": None
            }
            
            updated_count += 1
            
    return input_list, output_dict, updated_count, None