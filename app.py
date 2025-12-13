import os
import json
import time
import gc
from flask import Flask, jsonify, request, send_file
from werkzeug.utils import secure_filename
from datetime import datetime
import random

# --- 引入您核心腳本中的函數 ---
# 這裡假設您將所有腳本的核心函數複製到 app.py 中或作為輔助模組導入。
# 由於無法在一個檔案中引入多個上傳檔案的內容，這裡我們將關鍵邏輯複製進來。

# 警告: 這不是生產環境的最佳實踐，最佳實踐是將邏輯分離到模組中。

# 來自 step1_score_calculator.py 的函數
def generate_timestamp_id():
    prefix = "task" 
    now = datetime.now()
    timestamp = now.strftime("%Y%m%d_%H%M%S")
    microsecond = now.strftime("%f") 
    return f"{prefix}_{timestamp}_{microsecond}"

def calculate_plan_d_score(data):
    # (從 step1 複製過來，省略 details 以保持簡潔)
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

# ----------------------------------------------------
# 設定區塊 (從所有腳本中提取)
# ----------------------------------------------------

# 檔案路徑
GLOBAL_INPUT_FILE = 'json/all_tasks_input.json' 
GLOBAL_OUTPUT_FILE = 'json/all_tasks_output.json'
UNUSED_FILE = 'json/unused.json'

# 目錄路徑 (確保在 app 啟動時創建)
DIRS_TO_CREATE = [
    'json', 'images', 'images/generated_images', 'images/donut', 
    'images/donut_gray', 'images/donut_ratio', 'images/donut_cut', 
    'images/merged', 'images/not_complete', 'images/unused', 'images/masks'
]
MASK_PATH = 'images/masks/mask.png' 

# ----------------------------------------------------
# 通用 JSON 讀寫函數 (從 step1 複製)
# ----------------------------------------------------

def read_json(file_name, default_if_missing):
    # (從 step1 複製過來，省略 details 以保持簡潔)
    try:
        with open(file_name, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return default_if_missing
    except Exception as e:
        return {"error": str(e)}

def write_json(file_name, data):
    # (從 step1 複製過來，省略 details 以保持簡潔)
    try:
        os.makedirs(os.path.dirname(file_name), exist_ok=True)
        with open(file_name, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        return True
    except Exception as e:
        return False
        
def create_initial_dirs():
    """創建所有必要的目錄"""
    for d in DIRS_TO_CREATE:
        os.makedirs(d, exist_ok=True)
    # 創建一個空的 mask.png 佔位符，讓前端知道要上傳
    if not os.path.exists(MASK_PATH):
        try:
            # 建立一個全白的 1024x1024 圖片作為預設佔位符
            from PIL import Image
            Image.new('RGBA', (1024, 1024), color = 'white').save(MASK_PATH)
            print(f"💡 創建了佔位符 {MASK_PATH}。請確保它被替換為您的甜甜圈遮罩圖。")
        except:
            pass # 可能是 PIL 沒裝，不影響 JSON 讀寫

# ----------------------------------------------------
# Flask 應用程式初始化
# ----------------------------------------------------

app = Flask(__name__)
create_initial_dirs()
app.config['UPLOAD_FOLDER'] = 'json'

# ----------------------------------------------------
# API 路由定義
# ----------------------------------------------------

@app.route('/', methods=['GET'])
def index():
    """根目錄，返回API概覽"""
    return jsonify({
        "message": "歡迎使用甜甜圈任務排程 API",
        "endpoints": {
            "/api/tasks": "GET: 獲取所有任務; POST: 上傳新任務",
            "/api/tasks/calculate": "POST: 執行 Step 1 - 分數計算與初始化",
            "/api/tasks/prompt": "POST: 執行 Step 2 - 生成 Prompt (需 Groq Key)",
            "/api/tasks/image": "POST: 執行 Step 3 - 生成圖片 (需 SDXL 模型)",
            "/api/tasks/donut": "POST: 執行 Step 4 - 甜甜圈遮罩",
            "/api/tasks/gray": "POST: 執行 Step 5 - 灰階化",
            "/api/tasks/ratio": "POST: 執行 Step 6 - 扇形裁切與合成",
            "/api/tasks/merge": "POST: 執行 Step 7 - 合併甜甜圈",
            "/api/status": "GET: 獲取系統狀態和最新合併圖路徑",
            "/upload_mask": "POST: 上傳 mask.png 遮罩圖"
        }
    })

# --- 1. 任務管理 ---

@app.route('/api/tasks', methods=['GET', 'POST'])
def handle_tasks():
    """
    GET: 獲取所有任務的 Input 和 Output 資料。
    POST: 上傳新的任務列表 (覆蓋或新增到 input.json)。
    """
    if request.method == 'GET':
        input_data = read_json(GLOBAL_INPUT_FILE, [])
        output_data = read_json(GLOBAL_OUTPUT_FILE, {})
        return jsonify({
            "input_tasks": input_data,
            "output_results": output_data
        })
        
    elif request.method == 'POST':
        # 預期接收一個包含任務列表的 JSON
        new_tasks = request.get_json()
        if not isinstance(new_tasks, list):
            return jsonify({"error": "Payload 必須是任務列表 (JSON Array)"}), 400
            
        current_input = read_json(GLOBAL_INPUT_FILE, [])
        
        # 簡單地將新任務加入，讓 Step 1 處理 ID
        current_input.extend(new_tasks)
        
        if write_json(GLOBAL_INPUT_FILE, current_input):
             return jsonify({"message": f"成功新增 {len(new_tasks)} 個任務到 input 列表。", "count": len(new_tasks)}), 200
        else:
             return jsonify({"error": "寫入 input.json 失敗"}), 500

# --- 2. 流程控制端點 (step1 到 step7) ---

@app.route('/api/tasks/calculate', methods=['POST'])
def step1_calculate():
    """Step 1: 計算分數並初始化 Output"""
    
    input_list = read_json(GLOBAL_INPUT_FILE, []) 
    output_dict = read_json(GLOBAL_OUTPUT_FILE, {}) 
    
    updated_count = 0
    
    for task_input in input_list:
        if not task_input.get('task_id'):
            # 執行 step1_score_calculator.py 的核心邏輯
            new_id = generate_timestamp_id()
            while new_id in output_dict:
                time.sleep(0.001) 
                new_id = generate_timestamp_id()
            
            task_input['task_id'] = new_id
            task_name = task_input.get('task_name', 'Unknown')
            scores = calculate_plan_d_score(task_input)
            
            if "error" in scores: continue

            output_dict[new_id] = {
                "task_id": new_id, "task_name": task_name,
                "total_score": scores['total_score'],
                "incentive_score": scores['incentive_score'],
                "penalty_score": scores['penalty_score'],
                "positive_prompt": None, "negative_prompt": None,
                "image_path": None, "donut_path": None, 
                "gray_path": None, "ratio_path": None, "cut_path": None
            }
            updated_count += 1
            
    if updated_count > 0:
        write_json(GLOBAL_INPUT_FILE, input_list)
        write_json(GLOBAL_OUTPUT_FILE, output_dict)
        return jsonify({"message": f"Step 1 完成：初始化並計算了 {updated_count} 個新任務的分數。", "count": updated_count}), 200
    else:
        return jsonify({"message": "Step 1 完成：沒有發現需要初始化的新任務。", "count": 0}), 200

# (以下 Step 2 到 Step 7 由於需要依賴大量的外部庫和函數，
#  我將用「預期行為」來代替實際複雜的實現，並提供調用說明。)

@app.route('/api/tasks/prompt', methods=['POST'])
def step2_prompt():
    """
    Step 2: 生成 Prompt (需 Groq Client)
    🚨 實作時需要將 step2_generate_prompt.py 的 Groq 邏輯完整複製到這裡。
    """
    # 這裡應該是 step2_generate_prompt.py 的核心邏輯
    # ... 載入 Groq Client ...
    # ... 遍歷 input_list 呼叫 generate_sdxl_prompts ...
    # ... 更新 input_list (prompt_status=True) 和 output_dict (positive/negative_prompt) ...
    
    # 模擬結果
    return jsonify({
        "message": "Step 2: Prompt 生成請求已處理。",
        "note": "請確保您的 Groq API 金鑰已設定，並且 Groq 相關代碼已引入。實際處理結果請查看 JSON 文件。",
        "tasks_affected": 0 # 假設本次沒有新增
    }), 200


@app.route('/api/tasks/image', methods=['POST'])
def step3_image():
    """
    Step 3: 生成圖片 (需 SDXL 模型)
    🚨 實作時需要將 step3_generate_image.py 的 StableDiffusionXLPipeline 邏輯完整複製到這裡。
    """
    # 這裡應該是 step3_generate_image.py 的核心邏輯
    # ... 載入 StableDiffusionXLPipeline ...
    # ... 遍歷 input_list 呼叫 pipe_t2i() ...
    # ... 更新 input_list (image_status=True) 和 output_dict (image_path) ...
    # ... 清理顯存 ...
    
    # 模擬結果
    return jsonify({
        "message": "Step 3: 圖片生成請求已處理。",
        "note": "請確保 SDXL 模型已載入且有足夠的 GPU 資源。實際處理結果請查看 JSON 文件。",
        "tasks_affected": 0 # 假設本次沒有新增
    }), 200

# ... (Step 4 到 Step 7 依此類推，將原腳本邏輯包裝到對應的路由中) ...

@app.route('/api/tasks/donut', methods=['POST'])
def step4_donut():
    """Step 4: 合併遮罩並裁切成甜甜圈圖"""
    # 這裡應該是 step4_generate_donut.py 的核心邏輯
    # ... 依賴 PIL.Image, MASK_PATH ...
    return jsonify({"message": "Step 4: 甜甜圈裁切請求已處理。", "tasks_affected": 0}), 200

@app.route('/api/tasks/gray', methods=['POST'])
def step5_gray():
    """Step 5: 灰階化並降低對比度"""
    # 這裡應該是 step5_generate_gray.py 的核心邏輯
    # ... 依賴 PIL.Image, ImageEnhance ...
    return jsonify({"message": "Step 5: 灰階化請求已處理。", "tasks_affected": 0}), 200

@app.route('/api/tasks/ratio', methods=['POST'])
def step6_ratio():
    """Step 6: 扇形裁切與合成 (Ratio/Cut 圖)"""
    # 這裡應該是 step6_generate_ratio.py 的核心邏輯
    # ... 依賴 PIL.Image, 角度計算 ...
    return jsonify({"message": "Step 6: 扇形圖生成請求已處理。", "tasks_affected": 0}), 200

@app.route('/api/tasks/merge', methods=['POST'])
def step7_merge():
    """Step 7: 合併所有扇形為最終甜甜圈"""
    # 這裡應該是 step7_merge.py 的核心邏輯
    # ... 依賴 PIL.Image, unused.json, 角度計算 ...
    # ... 返回 latest_merged_donut 路徑 ...
    
    # 模擬結果
    output_data = read_json(GLOBAL_OUTPUT_FILE, {})
    latest_path = output_data.get('latest_merged_donut', 'N/A')
    
    return jsonify({
        "message": "Step 7: 合併甜甜圈請求已處理。", 
        "tasks_affected": 0, 
        "latest_merged_donut": latest_path
    }), 200

# --- 3. 圖片和狀態查詢 ---

@app.route('/api/status', methods=['GET'])
def get_status():
    """獲取系統狀態和最新合併圖路徑"""
    output_data = read_json(GLOBAL_OUTPUT_FILE, {})
    latest_path = output_data.get('latest_merged_donut')
    
    return jsonify({
        "message": "系統狀態良好",
        "latest_merged_donut_path": latest_path,
        "tasks_in_input": len(read_json(GLOBAL_INPUT_FILE, [])),
        "tasks_in_output": len([k for k in output_data if k not in ['latest_merged_donut']])
    })

@app.route('/images/<path:filename>')
def serve_image(filename):
    """用於提供 images/ 目錄下的所有圖片文件"""
    # 這裡假設 images 目錄與 app.py 在同一層
    # 由於您的路徑是 'images\\generated_images\\...'，這裡需要正確解析
    # 為了安全，我們只允許訪問 'images' 目錄
    full_path = os.path.join(os.getcwd(), 'images', filename)
    
    # 檢查路徑是否有效且在 'images' 目錄下
    if os.path.exists(full_path) and full_path.startswith(os.path.join(os.getcwd(), 'images')):
        return send_file(full_path)
    return jsonify({"error": "圖片未找到或路徑無效"}), 404

# --- 4. 遮罩上傳 ---

@app.route('/upload_mask', methods=['POST'])
def upload_mask():
    """上傳 mask.png 文件"""
    if 'file' not in request.files:
        return jsonify({"error": "請求中沒有 'file' 部分"}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "未選擇文件"}), 400
    
    if file and file.filename.endswith('.png'):
        # 覆蓋固定的 mask.png
        file.save(MASK_PATH)
        return jsonify({
            "message": "遮罩圖片 (mask.png) 上傳成功，將在 Step 4 中使用。",
            "path": MASK_PATH
        }), 200
    
    return jsonify({"error": "只接受 PNG 格式的文件"}), 400

# ----------------------------------------------------
# 運行應用程式
# ----------------------------------------------------

if __name__ == '__main__':
    # 啟動命令: python app.py
    # 或是使用 Flask CLI: flask run
    print("Flask App 啟動中...")
    app.run(debug=True, host='0.0.0.0', port=5000)