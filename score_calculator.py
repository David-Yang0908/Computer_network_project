import math
import json
import os

TOPIC = "task_20251213_045454"

INPUT_FILE = f'json\\task\\{TOPIC}\\input.json'
OUTPUT_FILE = f'json\\task\\{TOPIC}\\output.json'

def calculate_plan_d_score(data):
    """
    Calculates the PLAN D score based on the Incentive and Penalty modules.
    
    激勵加分模組 (S) 公式: S = r * T_est * P * (1 + 0.15*(I-3)) * (1 + 0.05*(D-3)) * c^mu
    扣分模組 (P_behavior) 公式: P_behavior = -30 * T_distract - 6 * T_phone
    總得分: Score = S + P_behavior
    """
    try:
        # 讀取變數，若 JSON 檔案中沒有，則使用預設值
        r = data.get('r', 30.0)
        T_est = data.get('T_est', 0.0)
        P = data.get('P', 0.0)
        I = data.get('I', 3.0)
        D = data.get('D', 3.0)
        c = data.get('c', 0.0)
        mu = data.get('mu', 1.2)
        T_distract = data.get('T_distract', 0.0)
        T_phone = data.get('T_phone', 0.0)
        
        # 1. 激勵加分模組 (S)
        incentive_S = r * T_est * P * \
                      (1 + 0.15 * (I - 3)) * \
                      (1 + 0.05 * (D - 3)) * \
                      (c ** mu)
        
        # 2. 扣分模組 (P_behavior)
        penalty_P_behavior = (-30.0 * T_distract) + (-6.0 * T_phone)
        
        # 3. 總得分
        total_score = incentive_S + penalty_P_behavior
        
        # 輸出結果
        output_results = {
            "total_score": round(total_score, 2), # 總分
            "incentive_score": round(incentive_S, 2), # 加分 S
            "penalty_score": round(penalty_P_behavior, 2), # 扣分 P_behavior
            "input_parameters": {
                "r": r, "T_est": T_est, "P": P, "I": I, "D": D, "c": c, "mu": mu, 
                "T_distract": T_distract, "T_phone": T_phone
            },
            "description": "PLAN D 甜甜圈計畫 評分模型計算結果"
        }
        
        return output_results

    except Exception as e:
        return {"error": f"Calculation failed: {str(e)}"}

def read_json(file_name):
    """Reads data from a JSON file."""
    try:
        with open(file_name, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return {"error": f"Error: Input file '{file_name}' not found."}
    except json.JSONDecodeError:
        return {"error": f"Error: Failed to decode JSON from '{file_name}'."}

def write_json(file_name, results):
    """Writes results to a JSON file."""
    try:
        with open(file_name, 'w', encoding='utf-8') as f:
            # indent=4 讓 JSON 輸出格式更易讀
            json.dump(results, f, indent=4, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"Error writing output file: {e}")
        return False

# --- 主程式執行 ---
data = read_json(INPUT_FILE)

if "error" in data:
    print(data["error"])
else:
    results = calculate_plan_d_score(data)
    if "error" in results:
        print(results["error"])
    else:
        if write_json(OUTPUT_FILE, results):
            print(f"計算完成。結果已寫入 '{OUTPUT_FILE}' (JSON 格式)。")

