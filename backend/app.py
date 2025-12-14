import os
import json
import time
import sys
from datetime import datetime, timedelta
import random

# Flask 核心依賴
from flask import Flask, jsonify, request, send_file, send_from_directory
from werkzeug.utils import secure_filename
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS

# 圖像處理依賴
try:
    from PIL import Image
except ImportError:
    print("⚠️ 缺少 PIL (Pillow) 模組，圖像相關步驟將無法運行。", file=sys.stderr)
    pass

# --- 甜甜圈服務導入 ---
try:
    from generate_donut.score_service import execute_step1 
    from generate_donut.prompt_service import execute_step2 
    from generate_donut.image_service import execute_step3 
    from generate_donut.donut_service import execute_step4 
    from generate_donut.gray_service import execute_step5 
    from generate_donut.ratio_service import execute_step6 
    from generate_donut.merge_service import execute_step7 
except ImportError as e:
    print(f"⚠️ 導入甜甜圈服務模組失敗。請檢查 generate_donut 資料夾結構和 __init__.py: {e}", file=sys.stderr)

# --- 排程器服務導入 (保留) ---
try:
    from schedular import functions
    from schedular.services import task_complete
    from schedular.services.scheduler_ai import SmartSchedulerGroq
    from schedular.services.data_manager import DataManager, TASKS_FILE
except ImportError as e:
    print(f"⚠️ 導入排程器服務失敗。請檢查 schedular 資料夾結構: {e}", file=sys.stderr)


# ====================================================
# A. 應用程式初始化與配置
# ====================================================

app = Flask(__name__)
CORS(app)

# --- 甜甜圈服務配置 (JSON 檔案) ---
# 固定的導入來源檔案路徑 (新任務輸入)
IMPORT_SOURCE_FILE = 'schedular/dataset/task_input_sample.json' 
# 甜甜圈處理流程的實際輸入目標檔案
GLOBAL_INPUT_FILE = 'json/all_tasks_input.json' 
GLOBAL_OUTPUT_FILE = 'json/all_tasks_output.json'
UNUSED_FILE = 'json/unused.json'

DIRS_TO_CREATE = [
    'json', 'images', 'images/generated_images', 'images/donut', 
    'images/donut_gray', 'images/donut_ratio', 'images/donut_cut',
    'images/merged', 'images/not_complete', 'images/unused',
    'schedular/dataset' # 確保導入檔案的父目錄存在
]
MASK_PATH = os.path.join("images", "mask.png") 

# --- 排程器服務配置 (SQLite 資料庫 - 保留) ---
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///plan_d.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

db = SQLAlchemy(app)

# ====================================================
# B. 資料庫模型 (保留)
# ====================================================

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    score = db.Column(db.Integer, default=0)
    level = db.Column(db.Integer, default=1)

class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.String(50), unique=True, nullable=True) 
    parent_id = db.Column(db.String(50), nullable=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.String(500), nullable=True)
    date = db.Column(db.String(20), nullable=True)
    start_time = db.Column(db.String(10), nullable=True)
    end_time = db.Column(db.String(10), nullable=True)
    estimated_hours = db.Column(db.Float, default=0.0)
    priority = db.Column(db.Integer, default=3)
    importance = db.Column(db.Integer, default=3)
    difficulty = db.Column(db.Integer, default=3)
    is_fixed = db.Column(db.Boolean, default=False)
    status = db.Column(db.String(20), default='pending')
    score_value = db.Column(db.Integer, default=10)
    is_completed = db.Column(db.Boolean, default=False) 
    created_at = db.Column(db.DateTime, default=datetime.now)
    
    @property
    def deadline(self):
        if self.date and self.start_time:
             try:
                 return datetime.strptime(f"{self.date} {self.start_time}", "%Y-%m-%d %H:%M")
             except:
                 return None
        return None

class Reward(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    cost = db.Column(db.Integer, nullable=False)
    icon = db.Column(db.String(10), default='🎁')

# ====================================================
# C. 通用 I/O 函數 (甜甜圈服務所需)
# ====================================================

def ensure_dirs():
    """創建所有必要的目錄和遮罩佔位符"""
    for dir_name in DIRS_TO_CREATE:
        os.makedirs(dir_name, exist_ok=True)
        
    if not os.path.exists(MASK_PATH):
        try:
            Image.new('RGBA', (1024, 1024), color = (0, 0, 0, 0)).save(MASK_PATH)
        except:
            pass

def read_json(file_name, default_if_missing):
    """讀取 JSON 檔案"""
    try:
        if not os.path.exists(file_name):
            return default_if_missing
        with open(file_name, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error reading JSON file {file_name}: {e}", file=sys.stderr)
        return {"error": str(e)}

def write_json(file_name, data):
    """寫入 JSON 檔案"""
    try:
        os.makedirs(os.path.dirname(file_name), exist_ok=True)
        with open(file_name, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        return True
    except Exception as e:
        print(f"Error writing JSON file {file_name}: {e}", file=sys.stderr)
        return False

def _read_and_write_json(input_list, output_dict, unused_data=None):
    """將目前的數據狀態寫回 JSON 檔案。"""
    success_input = write_json(GLOBAL_INPUT_FILE, input_list)
    success_output = write_json(GLOBAL_OUTPUT_FILE, output_dict)
    
    save_status = {"input": success_input, "output": success_output}
    
    if unused_data is not None:
        success_unused = write_json(UNUSED_FILE, unused_data)
        save_status["unused"] = success_unused
        
    return save_status

# ====================================================
# D. 應用程式啟動/初始化函數 (保留)
# ====================================================

def init_db():
    """初始化 SQLite 資料庫"""
    with app.app_context():
        db.create_all()
        
        if not User.query.first():
            new_user = User(score=1250, level=5)
            db.session.add(new_user)
            db.session.add(Reward(title="休息 30 分鐘", cost=30, icon='💤'))
            db.session.commit()

# ====================================================
# E. 路由定義 (整合所有 API)
# ====================================================

# --- E1. 根目錄 ---
@app.route('/', methods=['GET'])
def index():
    """根目錄，返回 API 概覽"""
    return jsonify({
        "message": "歡迎使用整合排程器與甜甜圈視覺化 API",
        "endpoints_donut": {
            "/api/donut/full_pipeline": "POST: 導入新任務並執行 Step 1~7 (唯一甜甜圈入口)",
        },
        "endpoints_scheduler": {
            "/api/tasks": "GET: 排程器 - 獲取所有待辦任務",
            "/api/user": "GET: 排程器 - 獲取用戶分數/等級",
            "/api/analyze": "POST: 排程器 - AI 語義分析並創建任務",
            "/api/run_ai_schedule": "GET: 排程器 - 執行 AI 日排程",
        }
    })


# ----------------------------------------------------
# E2. 甜甜圈/圖像生成服務路由 (已修改)
# ----------------------------------------------------

def import_tasks_from_fixed_file():
    """
    從固定的 IMPORT_SOURCE_FILE 讀取任務，並將其追加到 GLOBAL_INPUT_FILE 中。
    執行成功後，將來源檔案清空。
    """
    try:
        new_tasks = read_json(IMPORT_SOURCE_FILE, [])
        
        if not new_tasks or isinstance(new_tasks, dict) or 'error' in new_tasks:
            return 0, None # 沒有新任務

        if not isinstance(new_tasks, list):
            return 0, "來源檔案內容不是有效的 JSON 任務列表 (JSON Array)"

        current_input = read_json(GLOBAL_INPUT_FILE, [])
        if isinstance(current_input, dict) and 'error' in current_input:
            return 0, "讀取目標輸入檔案失敗"

        cleaned_tasks = []
        for task in new_tasks:
            base_task = {k: task.get(k) for k in [
                'task_name', 'r', 'T_est', 'P', 'I', 'D', 'c', 'mu', 'T_distract', 'T_phone'
            ]}
            base_task.update({
                "task_id": None, "prompt_status": False, "image_status": False,
                "donut_status": False, "gray_status": False, "ratio_status": False,
                "cut_status": False, "merged_status": False
            })
            if base_task.get('task_name'):
                 cleaned_tasks.append(base_task)

        if not cleaned_tasks:
            return 0, "來源檔案中沒有有效的任務數據可以導入。"

        # 1. 寫入新的任務到輸入隊列
        current_input.extend(cleaned_tasks)
        if not write_json(GLOBAL_INPUT_FILE, current_input):
             return 0, "寫入 GLOBAL_INPUT_FILE 失敗"

        # 2. 清空來源檔案，防止重複導入
        write_json(IMPORT_SOURCE_FILE, []) 
        
        return len(cleaned_tasks), None
        
    except Exception as e:
        return 0, f"導入任務失敗: {e}"


@app.route('/api/donut/full_pipeline', methods=['POST'])
def full_pipeline():
    """
    Step 0 (自動導入任務) 到 Step 7 的一鍵自動化流程。
    """
    if 'execute_step1' not in globals():
        return jsonify({"error": "甜甜圈服務模組未成功導入，無法執行全流程。"}), 500

    # --- Step 0: 自動導入任務 ---
    imported_count, import_error = import_tasks_from_fixed_file()
    if import_error:
        return jsonify({"error": f"Step 0 (導入任務) 失敗: {import_error}"}), 500

    # 1. 初始化資料
    input_list = read_json(GLOBAL_INPUT_FILE, []) 
    output_dict = read_json(GLOBAL_OUTPUT_FILE, {}) 
    unused_data = read_json(UNUSED_FILE, {})
    
    if isinstance(input_list, dict) and 'error' in input_list: return jsonify({"error": "讀取 Input 失敗"}), 500
    if isinstance(output_dict, dict) and 'error' in output_dict: output_dict = {}
    if isinstance(unused_data, dict) and 'error' in unused_data: unused_data = {}
    
    # 檢查是否還有任何任務或未用片段需要處理
    if not any(t.get('merged_status') is False for t in input_list) and not any(v.get('reuse_status') is False for v in unused_data.values()):
        return jsonify({
            "message": f"所有任務已完成，且無新導入任務 ({imported_count}) 或未用片段可供處理。",
            "tasks_total_processed": 0,
            "final_path": output_dict.get('latest_merged_donut'),
            "save_status": {"input": True, "output": True, "unused": True}
        }), 200

    groq_api_key = os.getenv("GROQ_API_KEY")

    total_processed_count = 0
    final_result_path = None
    
    pipeline_steps = [
        ("Step 1: 計算分數", execute_step1, ()), 
        ("Step 2: 生成 Prompt", execute_step2, (groq_api_key,)),
        ("Step 3: 生成圖片", execute_step3, ()),
        ("Step 4: 甜甜圈裁切", execute_step4, ()),
        ("Step 5: 灰階化", execute_step5, ()),
        ("Step 6: 扇形裁切與合成", execute_step6, ()),
    ]
    
    for step_name, step_func, step_args in pipeline_steps:
        if step_func == execute_step2 and not groq_api_key:
             return jsonify({"error": "環境變數 GROQ_API_KEY 未設定，無法執行 Step 2"}), 500

        print(f"--- 正在執行 {step_name} ---")
        try:
            results = step_func(input_list, output_dict, *step_args)
        except Exception as e:
            # 捕獲所有步驟執行時的異常
            return jsonify({"error": f"{step_name} 執行時發生未預期錯誤: {str(e)}", "count": total_processed_count}), 500

        input_list, output_dict, processed_count, error_status = results
        total_processed_count += processed_count

        if error_status:
            print(f"❌ {step_name} 失敗: {error_status}")
            _read_and_write_json(input_list, output_dict)
            return jsonify({"error": f"{step_name} 失敗: {error_status}", "count": total_processed_count}), 500
            
        _read_and_write_json(input_list, output_dict)
        print(f"✅ {step_name} 成功，處理了 {processed_count} 個任務。")

    # Step 7
    print("--- 正在執行 Step 7: 合併圓環 ---")
    results = execute_step7(input_list, output_dict, unused_data)
    input_list, output_dict, unused_data, processed_count_step7, result_path, error_status = results
    final_result_path = result_path
    
    if error_status:
        _read_and_write_json(input_list, output_dict, unused_data)
        return jsonify({"error": f"Step 7 失敗: {error_status}", "count": total_processed_count}), 500

    save_status = _read_and_write_json(input_list, output_dict, unused_data)
    
    message = f"全流程完成。導入新任務 {imported_count} 個。"
    if final_result_path:
        is_full = "merged" in final_result_path
        message += f" 圓環狀態 {'已滿' if is_full else '進度暫存'}。"
        
    return jsonify({
        "message": message,
        "tasks_total_processed": total_processed_count,
        "final_path": final_result_path,
        "save_status": save_status
    }), 200

# ----------------------------------------------------
# E3. 資源與排程器/資料庫服務路由 (保留)
# ----------------------------------------------------

@app.route('/images/<path:filename>')
def serve_image(filename):
    """通用圖片服務 (甜甜圈輸出)"""
    full_path = os.path.join(os.getcwd(), 'images', filename)
    
    if os.path.exists(full_path) and full_path.startswith(os.path.join(os.getcwd(), 'images')):
        return send_file(full_path, mimetype='image/png', max_age=0) 
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
                "message": "遮罩圖片 (mask.png) 上傳成功", 
                "path": MASK_PATH
            }), 200
        except Exception as e:
            return jsonify({"error": f"儲存檔案失敗: {e}"}), 500
    
    return jsonify({"error": "只接受 .png 格式的文件"}), 400


@app.route('/api/user', methods=['GET'])
def get_user():
    """獲取用戶分數/等級"""
    user = User.query.first()
    if not user:
         init_db()
         user = User.query.first()
    return jsonify({
        "score": user.score,
        "level": user.level
    })

@app.route('/api/analyze', methods=['POST'])
def analyze_input():
    """AI 語義分析並創建任務"""
    data = request.json
    text = data.get('text', '')
    if not text:
        return jsonify({"error": "No text provided"}), 400
        
    scheduler = SmartSchedulerGroq()
    result = scheduler.analyze_user_input(text)
    
    if result.get("success") and result.get("data"):
        task_data = result["data"]
        
        functions.input_task(
            Name=task_data.get('name'), Date=task_data.get('date'),
            Is_fixed_input='y' if task_data.get('is_fixed') else 'n',
            Priority=task_data.get('priority'), Importance=task_data.get('importance'),
            Difficulty=task_data.get('difficulty'), Start_time=task_data.get('start_time'),
            End_time=task_data.get('end_time'), Estimated_time=task_data.get('estimated_hours'),
            Event_id=task_data.get('event_id')
        )
        
        new_task = Task(
            event_id=task_data.get('event_id'), parent_id=task_data.get('parent_id'),
            title=task_data.get('name'), date=task_data.get('date'),
            start_time=task_data.get('start_time'), end_time=task_data.get('end_time'),
            estimated_hours=float(task_data.get('estimated_hours', 0)),
            priority=int(task_data.get('priority', 3)), importance=int(task_data.get('importance', 3)),
            difficulty=int(task_data.get('difficulty', 3)), is_fixed=task_data.get('is_fixed', False),
            status='pending', score_value= (int(task_data.get('priority', 3)) + int(task_data.get('difficulty', 3))) * 5
        )
        db.session.add(new_task)
        db.session.commit()
        
        return jsonify({"message": "Task created successfully!", "suggestions": [task_data]})
        
    else:
        msg = result.get("message", "Could not understand task.")
        return jsonify({"message": msg, "suggestions": []})

@app.route('/api/tasks', methods=['GET'])
def get_tasks():
    """獲取待辦任務列表"""
    tasks = Task.query.filter_by(status='pending', is_completed=False).all()
    tasks.sort(key=lambda x: (x.date or '9999', x.start_time or '99:99'))
    
    result = []
    for t in tasks:
        deadline_str = None
        if t.date and t.start_time:
            deadline_str = f"{t.date}T{t.start_time}:00"
        elif t.deadline:
            deadline_str = t.deadline.isoformat()

        result.append({
            "id": t.id, "event_id": t.event_id, "title": t.title, "description": t.description,
            "deadline": deadline_str, "date": t.date, "start_time": t.start_time,
            "score_value": t.score_value, "is_completed": t.is_completed, "status": t.status,
            "priority": t.priority, "difficulty": t.difficulty
        })
    return jsonify(result)

@app.route('/api/tasks/<int:task_id>/complete', methods=['POST'])
def complete_task(task_id):
    """完成任務並增加分數"""
    task = Task.query.get(task_id)
    if not task:
        return jsonify({"error": "Task not found"}), 404
        
    if not task.is_completed:
        task.is_completed = True
        task.status = 'completed'
        user = User.query.first()
        user.score += task.score_value
        db.session.commit()
        
    return jsonify({"message": "Task completed", "new_score": User.query.first().score, "earned": task.score_value})

@app.route('/api/run_ai_schedule', methods=['GET'])
def run_ai_scheduling_route():
    """執行 AI 日排程 (Phase 2)"""
    try:
        target_date = request.args.get('date', datetime.now().strftime("%Y-%m-%d"))
        functions.run_ai_scheduling(target_date)
        return jsonify({"success": True, "message": f"AI 日排程 (Phase 2) 已為 {target_date} 完成。"}), 200
    except Exception as e:
        return jsonify({"success": False, "message": f"AI 排程失敗: {e}"}), 500

# (此處省略了其他排程器路由如 /api/stats/weekly, /api/rewards, /api/add_task, /api/delete_event, 等，請根據您實際需要的完整功能來添加)


# ====================================================
# F. 啟動 APP
# ====================================================

if __name__ == '__main__':
    ensure_dirs()
    # 僅在 app.py 啟動時運行資料庫初始化 (確保排程器功能完整)
    with app.app_context():
        init_db() 
        
    print("--- 整合後的 Flask 應用程式啟動中 ---")
    app.run(debug=True, host='0.0.0.0', port=5000)