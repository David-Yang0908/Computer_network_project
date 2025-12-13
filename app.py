import os
import json
import time
import gc
from datetime import datetime

# Flask 相關
from flask import Flask, jsonify, request, send_file
from werkzeug.utils import secure_filename

# 圖像處理依賴 (主要在 services 模組中使用，但為了通用工具函數和類型提示保留)
try:
    from PIL import Image
except ImportError:
    pass

# --- 導入服務模組 ---
# 確保您的 services 目錄下有這些檔案
from services.score_service import execute_step1 
from services.prompt_service import execute_step2 
from services.image_service import execute_step3 
from services.donut_service import execute_step4 
from services.gray_service import execute_step5 
from services.ratio_service import execute_step6 
from services.merge_service import execute_step7 

# ----------------------------------------------------
# 1. 核心設定與路徑
# ----------------------------------------------------

# 檔案路徑
GLOBAL_INPUT_FILE = 'json/all_tasks_input.json' 
GLOBAL_OUTPUT_FILE = 'json/all_tasks_output.json'
UNUSED_FILE = 'json/unused.json'

# 輸出目錄 (用於 app 啟動時創建)
DIRS_TO_CREATE = [
    'json', 'images', 'images/generated_images', 'images/donut', 
    'images/donut_gray', 'images/donut_ratio', 'images/donut_cut', 
    'images/merged', 'images/not_complete', 'images/unused', 'images/masks'
]
MASK_PATH = 'images/masks/mask.png' 


# ----------------------------------------------------
# 2. 通用 I/O 函數 (由 app.py 負責處理，供所有路由使用)
# ----------------------------------------------------

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

def create_initial_dirs():
    """創建所有必要的目錄和遮罩佔位符"""
    for d in DIRS_TO_CREATE:
        os.makedirs(d, exist_ok=True)
    if not os.path.exists(MASK_PATH):
        try:
            # 建立一個全透明的 1024x1024 圖片作為預設佔位符
            Image.new('RGBA', (1024, 1024), color = (0, 0, 0, 0)).save(MASK_PATH)
            print(f"💡 創建了遮罩佔位符 {MASK_PATH}。")
        except:
            pass # 可能 PIL 沒裝


# ----------------------------------------------------
# 3. Flask 應用程式初始化
# ----------------------------------------------------

app = Flask(__name__)
create_initial_dirs() # 確保目錄結構存在

# ----------------------------------------------------
# 4. API 路由定義
# ----------------------------------------------------

@app.route('/', methods=['GET'])
def index():
    """根目錄，返回 API 概覽"""
    return jsonify({
        "message": "歡迎使用甜甜圈任務排程 API",
        "endpoints": {
            "/api/tasks": "GET/POST: 任務列表管理",
            "/api/tasks/calculate": "POST: Step 1 - 分數計算",
            "/api/tasks/prompt": "POST: Step 2 - Prompt 生成 (Groq)",
            "/api/tasks/image": "POST: Step 3 - 圖片生成 (SDXL)",
            "/api/tasks/donut": "POST: Step 4 - 甜甜圈裁切",
            "/api/tasks/gray": "POST: Step 5 - 灰階化",
            "/api/tasks/ratio": "POST: Step 6 - 扇形裁切與合成",
            "/api/tasks/merge": "POST: Step 7 - 合併圓環",
            "/images/<path:filename>": "GET: 圖片服務",
            "/upload_mask": "POST: 遮罩上傳"
        }
    })

# --- A. 任務管理 ---

@app.route('/api/tasks', methods=['GET', 'POST'])
def handle_tasks():
    """GET: 獲取所有任務; POST: 上傳新任務"""
    if request.method == 'GET':
        input_data = read_json(GLOBAL_INPUT_FILE, [])
        output_data = read_json(GLOBAL_OUTPUT_FILE, {})
        return jsonify({"input_tasks": input_data, "output_results": output_data})
        
    elif request.method == 'POST':
        new_tasks = request.get_json()
        if not isinstance(new_tasks, list):
            return jsonify({"error": "Payload 必須是任務列表 (JSON Array)"}), 400
            
        current_input = read_json(GLOBAL_INPUT_FILE, [])
        if isinstance(current_input, dict) and 'error' in current_input:
            return jsonify({"error": "讀取 input.json 失敗"}), 500

        # 清理並重置新任務的狀態
        cleaned_tasks = []
        for task in new_tasks:
            base_task = {k: v for k, v in task.items() if k in ['task_name', 'r', 'T_est', 'P', 'I', 'D', 'c', 'mu', 'T_distract', 'T_phone']}
            base_task.update({
                "task_id": None, "prompt_status": False, "image_status": False,
                "donut_status": False, "gray_status": False, "ratio_status": False,
                "cut_status": False, "merged_status": False
            })
            cleaned_tasks.append(base_task)

        current_input.extend(cleaned_tasks)
        
        if write_json(GLOBAL_INPUT_FILE, current_input):
             return jsonify({"message": f"成功新增 {len(cleaned_tasks)} 個任務到 input 列表，等待 Step 1 處理。", "count": len(cleaned_tasks)}), 200
        else:
             return jsonify({"error": "寫入 input.json 失敗"}), 500


# --- B. 流程控制端點 (Step 1 - Step 7) ---

def _execute_step(step_func, *args):
    """通用步驟執行器，處理 I/O、錯誤和狀態回傳"""
    input_list = read_json(GLOBAL_INPUT_FILE, []) 
    output_dict = read_json(GLOBAL_OUTPUT_FILE, {}) 
    
    if isinstance(input_list, dict) and 'error' in input_list: return jsonify(input_list), 500
    if isinstance(output_dict, dict) and 'error' in output_dict: output_dict = {}

    # 執行服務模組的核心邏輯
    # 服務函數返回: (input_list, output_dict, count, error_status) 或 (input_list, output_dict, unused_data, count, path, error_status)
    results = step_func(input_list, output_dict, *args)
    
    # 判斷結果結構 (Step 7 vs Step 1-6)
    is_merge_step = len(results) == 6 
    
    if is_merge_step:
        # Step 7 結構: (input_list, output_dict, unused_data, processed_count, result_path, error_status)
        input_list, output_dict, unused_data, processed_count, result_path, error_status = results
    else:
        # Step 1-6 結構: (input_list, output_dict, processed_count, error_status)
        input_list, output_dict, processed_count, error_status = results
        unused_data = None # Step 1-6 不需要處理 unused

    if error_status:
        return jsonify({"error": error_status, "count": 0}), 500
        
    if processed_count > 0 or (is_merge_step and result_path):
        success_input = write_json(GLOBAL_INPUT_FILE, input_list)
        success_output = write_json(GLOBAL_OUTPUT_FILE, output_dict)
        save_status = {"input": success_input, "output": success_output}
        
        if is_merge_step:
            success_unused = write_json(UNUSED_FILE, unused_data)
            save_status["unused"] = success_unused
            is_full = result_path and "merged" in result_path
            
            return jsonify({
                "message": f"Step 7 完成：圓環狀態 {'已滿' if is_full else '進度暫存'}。",
                "tasks_added": processed_count,
                "final_path": result_path,
                "save_status": save_status
            }), 200

        return jsonify({
            "message": f"Step {step_func.__name__[-1]} 成功完成：處理了 {processed_count} 個任務。",
            "count": processed_count,
            "save_status": save_status
        }), 200
    else:
        return jsonify({
            "message": f"Step {step_func.__name__[-1]} 完成：沒有發現需要處理的任務。",
            "count": 0
        }), 200


@app.route('/api/tasks/calculate', methods=['POST'])
def step1_calculate():
    """Step 1: 計算分數 (Score_Service)"""
    return _execute_step(execute_step1)

@app.route('/api/tasks/prompt', methods=['POST'])
def step2_prompt():
    """Step 2: 生成 Prompt (Prompt_Service)"""
    api_key = os.getenv("GROQ_API_KEY")
    return _execute_step(execute_step2, api_key)

@app.route('/api/tasks/image', methods=['POST'])
def step3_image():
    """Step 3: 生成圖片 (Image_Service)"""
    return _execute_step(execute_step3)

@app.route('/api/tasks/donut', methods=['POST'])
def step4_donut():
    """Step 4: 甜甜圈裁切 (Donut_Service)"""
    return _execute_step(execute_step4)

@app.route('/api/tasks/gray', methods=['POST'])
def step5_gray():
    """Step 5: 灰階化 (Gray_Service)"""
    return _execute_step(execute_step5)

@app.route('/api/tasks/ratio', methods=['POST'])
def step6_ratio():
    """Step 6: 扇形裁切與合成 (Ratio_Service)"""
    return _execute_step(execute_step6)

@app.route('/api/tasks/merge', methods=['POST'])
def step7_merge():
    """Step 7: 合併圓環 (Merge_Service)"""
    # Step 7 需要額外讀取 unused.json
    unused_data = read_json(UNUSED_FILE, {}) 
    if isinstance(unused_data, dict) and 'error' in unused_data: unused_data = {}
    
    return _execute_step(execute_step7, unused_data)


# --- C. 圖片和遮罩服務 ---

@app.route('/images/<path:filename>')
def serve_image(filename):
    """用於提供 images/ 目錄下的所有圖片文件"""
    # 確保圖片服務路徑正確且安全
    full_path = os.path.join(os.getcwd(), 'images', filename)
    
    # 簡單的安全檢查
    if os.path.exists(full_path) and full_path.startswith(os.path.join(os.getcwd(), 'images')):
        return send_file(full_path)
    return jsonify({"error": "圖片未找到或路徑無效"}), 404

@app.route('/upload_mask', methods=['POST'])
def upload_mask():
    """上傳 mask.png 文件，供 Step 4 使用"""
    if 'file' not in request.files:
        return jsonify({"error": "請求中沒有 'file' 部分"}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "未選擇文件"}), 400
    
    if file and file.filename.endswith('.png'):
        try:
            file.save(MASK_PATH)
            return jsonify({
                "message": "遮罩圖片 (mask.png) 上傳成功，請確保它是一張圓形透明遮罩。",
                "path": MASK_PATH
            }), 200
        except Exception as e:
            return jsonify({"error": f"儲存檔案失敗: {e}"}), 500
    
    return jsonify({"error": "只接受 PNG 格式的文件"}), 400


# ----------------------------------------------------
# 5. 運行應用程式
# ----------------------------------------------------

if __name__ == '__main__':
    print("Flask App 啟動中...")
    app.run(debug=True, host='0.0.0.0', port=5000)