import json
import os
from datetime import datetime
import time
import random

# --- 設定區塊 ---
GLOBAL_INPUT_FILE = 'json/all_tasks_input.json' 
GLOBAL_OUTPUT_FILE = 'json/all_tasks_output.json' 

def generate_timestamp_id():
    """
    生成唯一 Task ID。
    為了防止同一秒內生成重複 ID，加入微秒 (microseconds) 作為區別。
    格式範例: task_20251213_210530_123456
    """
    prefix = "task" 
    now = datetime.now()
    timestamp = now.strftime("%Y%m%d_%H%M%S")
    microsecond = now.strftime("%f") # 6位數微秒
    return f"{prefix}_{timestamp}_{microsecond}"

def calculate_plan_d_score(data):
    """計算 PLAN D 分數"""
    try:
        r = data.get('r', 30.0)
        T_est = data.get('T_est', 0.0)
        P = data.get('P', 0.0)
        I = data.get('I', 3.0)
        D = data.get('D', 3.0)
        c = data.get('c', 0.0)
        mu = data.get('mu', 1.2)
        T_distract = data.get('T_distract', 0.0)
        T_phone = data.get('T_phone', 0.0)
        
        incentive_S = r * T_est * P * (1 + 0.15 * (I - 3)) * (1 + 0.05 * (D - 3)) * (c ** mu)
        penalty_P_behavior = (-30.0 * T_distract) + (-6.0 * T_phone)
        total_score = incentive_S + penalty_P_behavior
        
        return {
            "total_score": round(total_score, 2), 
            "incentive_score": round(incentive_S, 2), 
            "penalty_score": round(penalty_P_behavior, 2)
        }
    except Exception as e:
        return {"error": str(e)}

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

# --- 主程式 ---
def main():
    # 1. 讀取資料
    input_list = read_json(GLOBAL_INPUT_FILE, []) # Array
    output_dict = read_json(GLOBAL_OUTPUT_FILE, {}) # Dict

    print(f"💡 讀取到 {len(input_list)} 個任務輸入。")
    
    updated_count = 0
    
    # 2. 遍歷 Input List
    for task_input in input_list:
        
        # 檢查是否需要初始化 (沒有 task_id)
        if not task_input.get('task_id'):
            
            # A. 生成 ID (加入微秒保證唯一)
            new_id = generate_timestamp_id()
            
            # 確保 ID 真的不重複 (極端情況防護)
            while new_id in output_dict:
                time.sleep(0.001) 
                new_id = generate_timestamp_id()
            
            # 更新 Input
            task_input['task_id'] = new_id
            task_name = task_input.get('task_name', 'Unknown')
            
            print(f"\n--- 初始化新任務: {task_name} -> {new_id} ---")
            
            # B. 計算分數
            scores = calculate_plan_d_score(task_input)
            
            if "error" in scores:
                print(f"   ❌ 分數計算失敗: {scores['error']}")
                continue

            # C. 在 Output 中建立初始條目
            output_dict[new_id] = {
                "task_id": new_id,
                "task_name": task_name,
                
                # 分數 (只存這三個，如您所要求)
                "total_score": scores['total_score'],
                "incentive_score": scores['incentive_score'],
                "penalty_score": scores['penalty_score'],
                
                # 內容路徑與 Prompt (初始化為 null)
                "positive_prompt": None,
                "negative_prompt": None,
                "image_path": None,
                "donut_path": None,
                "gray_path": None,
                "ratio_path": None,
                "cut_path": None
            }
            
            print(f"   ✅ 分數計算完成: {scores['total_score']}")
            updated_count += 1

    # 3. 儲存變更
    if updated_count > 0:
        # 寫回 Input (為了保存生成的 task_id)
        if write_json(GLOBAL_INPUT_FILE, input_list):
            print(f"💾 Input 狀態已更新 (IDs)。")
            
        # 寫回 Output (保存分數)
        if write_json(GLOBAL_OUTPUT_FILE, output_dict):
             print(f"💾 Output 資料已儲存 ({updated_count} 筆新資料)。")
             
        print(f"\n🎉 成功處理 {updated_count} 個新任務。")
    else:
        print("\n💡 沒有發現需要初始化的新任務。")

if __name__ == "__main__":
    main()