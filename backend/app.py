import os
import json
import time
import sys
from datetime import datetime, timedelta
import random
import shutil 

from flask import Flask, request, jsonify, send_from_directory, redirect, url_for,send_file
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from datetime import datetime, timedelta


# Scheduler Imports
from schedular import functions
from schedular.services import task_complete
from schedular.services.scheduler_ai import SmartSchedulerGroq
from schedular.services.data_manager import DataManager, TASKS_FILE

# 圖像處理依賴
try:
    from PIL import Image
except ImportError:
    # 僅提醒，不強制停止 (Step 3/4/5/6/7 會失敗)
    print("⚠️ 缺少 PIL (Pillow) 模組，圖像相關步驟將無法運行。", file=sys.stderr)
    pass

# --- 甜甜圈服務導入 ---
try:
    # ⚠️ 確保 generate_donut 資料夾內有 __init__.py 檔案
    from generate_donut.score_service import execute_step1 
    from generate_donut.prompt_service import execute_step2 
    from generate_donut.image_service import execute_step3 
    from generate_donut.donut_service import execute_step4 
    from generate_donut.gray_service import execute_step5 
    from generate_donut.ratio_service import execute_step6 
    from generate_donut.merge_service import execute_step7 
except ImportError as e:
    print(f"⚠️ 導入甜甜圈服務模組失敗。請檢查 generate_donut 資料夾結構和 __init__.py: {e}", file=sys.stderr)



app = Flask(__name__)
CORS(app)

# --- 甜甜圈服務配置 (JSON 檔案) ---
# 實際處理流程的輸入檔案 (用於 Step 1~7)
GLOBAL_INPUT_FILE = 'json/all_tasks_input.json' 
GLOBAL_OUTPUT_FILE = 'json/all_tasks_output.json'
UNUSED_FILE = 'json/unused.json'
# 固定的導入來源檔案路徑 (新任務輸入)
IMPORT_SOURCE_FILE = 'schedular/dataset/task_input_sample.json' 
DIRS_TO_CREATE = [
    'json', 'images', 'images/generated_images', 'images/donut', 
    'images/donut_gray', 'images/donut_ratio', 'images/donut_cut',
    'images/merged', 'images/not_complete', 'images/unused'
]
MASK_PATH = os.path.join("images", "mask.png") 

# --- 排程器服務配置 (SQLite 資料庫) ---
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///plan_d.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024



db = SQLAlchemy(app)

#=========
# 要清除資料庫使用這個
# db.drop_all() 
#=========

# --- Models ---
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    score = db.Column(db.Integer, default=0)
    level = db.Column(db.Integer, default=1)

class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    # Scheduler Integration Fields
    event_id = db.Column(db.String(50), unique=True, nullable=True) 
    parent_id = db.Column(db.String(50), nullable=True)
    
    title = db.Column(db.String(200), nullable=False) # Maps to 'name'
    description = db.Column(db.String(500), nullable=True)
    
    # Scheduling fields
    date = db.Column(db.String(20), nullable=True) # YYYY-MM-DD
    start_time = db.Column(db.String(10), nullable=True) # HH:MM
    end_time = db.Column(db.String(10), nullable=True) # HH:MM
    estimated_hours = db.Column(db.Float, default=0.0)
    
    # Attributes
    priority = db.Column(db.Integer, default=3)
    importance = db.Column(db.Integer, default=3)
    difficulty = db.Column(db.Integer, default=3)
    is_fixed = db.Column(db.Boolean, default=False)
    status = db.Column(db.String(20), default='pending') # pending, completed
    
    # Legacy/Computed
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
            # 創建一個 1024x1024 的透明 PNG 佔位符
            Image.new('RGBA', (1024, 1024), color = (0, 0, 0, 0)).save(MASK_PATH)
            print(f"💡 創建了遮罩佔位符 {MASK_PATH}。")
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
    """通用輔助函數：將目前的數據狀態寫回 JSON 檔案"""
    success_input = write_json(GLOBAL_INPUT_FILE, input_list)
    success_output = write_json(GLOBAL_OUTPUT_FILE, output_dict)
    
    save_status = {"input": success_input, "output": success_output}
    
    if unused_data is not None:
        success_unused = write_json(UNUSED_FILE, unused_data)
        save_status["unused"] = success_unused
        
    return save_status


# --- Init DB ---
def init_db():
    with app.app_context():
        # Drop tables to ensure schemale update (Dev only)
        # db.drop_all() 
        # Note: If schema changes, you might need to delete plan_d.db manually
        db.create_all()
        
        if not User.query.first():
            new_user = User(score=1250, level=5)
            db.session.add(new_user)
            # Default rewards removed as per user request
            db.session.commit()

            db.session.add(Reward(title="休息 30 分鐘", cost=30, icon='💤'))
            db.session.commit()

# --- Helper Functions ---
def calculate_score(estimated_hours, priority, importance, difficulty, start_time=None, end_time=None):
    """
    Calculate score based on user formula:
    30 * Hours * Priority * (1 + 0.15 * (Imp - 3)) * (1 + 0.05 * (Diff - 3))
    """
    hours = float(estimated_hours)
    
    # If estimated_hours is 0, try to calculate from start/end time
    if hours <= 0 and start_time and end_time:
        try:
            fmt = "%H:%M"
            t1 = datetime.strptime(start_time, fmt)
            t2 = datetime.strptime(end_time, fmt)
            diff = (t2 - t1).total_seconds() / 3600
            if diff > 0:
                hours = diff
        except:
            pass
            
    # Fallback if still 0
    if hours <= 0:
        hours = 1.0
        
    p = int(priority)
    i = int(importance)
    d = int(difficulty)
    
    score = 30 * hours * 1.3 * (1 + 0.15 * (i - 3)) * (1 + 0.05 * (d - 3))
    return int(score)

# --- Routes ---

@app.route('/api/donut_image')
def get_donut_image():
    # 1. Try to serve the specifically marked "current" donut
    current_donut = os.path.join(app.root_path, 'images', 'current_donut.png')
    if os.path.exists(current_donut):
        print("Use Current Donut")
        return send_file(current_donut)

    # 2. Target directory for "Goal" donuts (Fallback)
    target_dir = os.path.join(app.root_path, 'images', 'not_complete')
    
    # Create dir if not exists (safety check)
    if not os.path.exists(target_dir):
        os.makedirs(target_dir)
        
    files = [f for f in os.listdir(target_dir) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
    
    if files:
        # Sort by modification time (newest first)
        files.sort(key=lambda x: os.path.getmtime(os.path.join(target_dir, x)), reverse=True)
        selected_image = files[0]
        print("Use Newest Donut")
        return send_from_directory(target_dir, selected_image)
    
    # 3. Ultimate Fallback
    print("Use Default Donut")
    return send_from_directory(os.path.join(app.root_path, 'images'), 'donut1.png')

@app.route('/api/donuts/gallery', methods=['GET'])
def get_donut_gallery():
    directory = os.path.join(app.root_path, 'images', 'merged')
    if not os.path.exists(directory):
        return jsonify([])
        
    files = [f for f in os.listdir(directory) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
    files.sort(key=lambda x: os.path.getctime(os.path.join(directory, x)), reverse=True)
    return jsonify(files)

@app.route('/api/donuts/gallery/<path:filename>')
def get_gallery_image(filename):
    return send_from_directory(os.path.join(app.root_path, 'images', 'merged'), filename)

@app.route('/api/user', methods=['GET'])
def get_user():
    user = User.query.first()
    return jsonify({
        "score": user.score,
        "level": user.level
    })



@app.route('/api/analyze', methods=['POST'])
def analyze_input():
    data = request.json
    text = data.get('text', '')
    if not text:
        return jsonify({"error": "No text provided"}), 400
        
    # Call Groq AI
    scheduler = SmartSchedulerGroq()
    result = scheduler.analyze_user_input(text)
    
    if result.get("success") and result.get("data"):
        task_data = result["data"]
        
        # 1. Add to Scheduler (Logic Layer)
        functions.input_task(
            Name=task_data.get('name'),
            Date=task_data.get('date'),
            Is_fixed_input='y' if task_data.get('is_fixed') else 'n',
            Priority=task_data.get('priority'),
            Importance=task_data.get('importance'),
            Difficulty=task_data.get('difficulty'),
            Start_time=task_data.get('start_time'),
            End_time=task_data.get('end_time'),
            Estimated_time=task_data.get('estimated_hours'),
            Event_id=task_data.get('event_id')
        )
        
        # 2. Add to SQLite (Presentation Layer)
        new_task = Task(
            event_id=task_data.get('event_id'),
            parent_id=task_data.get('parent_id'),
            title=task_data.get('name'),
            date=task_data.get('date'),
            start_time=task_data.get('start_time'),
            end_time=task_data.get('end_time'),
            estimated_hours=float(task_data.get('estimated_hours', 0)),
            priority=int(task_data.get('priority', 3)),
            importance=int(task_data.get('importance', 3)),
            difficulty=int(task_data.get('difficulty', 3)),
            is_fixed=task_data.get('is_fixed', False),
            status='pending',
            score_value= (int(task_data.get('priority', 3)) + int(task_data.get('difficulty', 3))) * 5
        )
        db.session.add(new_task)
        db.session.commit()
        
        return jsonify({
            "message": "Task created successfully!",
            "suggestions": [task_data] # Keep format compatible with frontend
        })
        
    else:
        # Missing info or Error
        msg = result.get("message", "Could not understand task.")
        return jsonify({
            "message": msg,
            "suggestions": [] # No task created
        })

@app.route('/api/tasks/confirm', methods=['POST'])
def confirm_tasks():
    # This is for the AI Chat interface confirmation
    data = request.json
    tasks_data = data.get('tasks', [])
    saved_tasks = []
    for t in tasks_data:
        deadline_dt = datetime.fromisoformat(t['deadline']) if t.get('deadline') else None
        # Simple mapping for chat-created tasks
        new_task = Task(
            title=t['title'],
            description=t.get('description', ''),
            date=deadline_dt.strftime("%Y-%m-%d") if deadline_dt else None,
            start_time=deadline_dt.strftime("%H:%M") if deadline_dt else None,
            score_value=t.get('score_value', 10),
            status='pending'
        )
        db.session.add(new_task)
        saved_tasks.append(new_task)
    db.session.commit()
    return jsonify({"message": "Tasks scheduled successfully", "count": len(saved_tasks)})

@app.route('/api/tasks', methods=['GET'])
def get_tasks():
    # Fetch tasks for list view
    tasks = Task.query.filter_by(status='pending', is_completed=False).all()
    # Sort roughly by date/time
    # In production, do proper SQL sorting. Here python sort is fine for prototype.
    tasks.sort(key=lambda x: (x.date or '9999', x.start_time or '99:99'))
    
    result = []
    for t in tasks:
        deadline_str = None
        if t.date and t.start_time:
            deadline_str = f"{t.date}T{t.start_time}:00"
        elif t.deadline:
            deadline_str = t.deadline.isoformat()

        result.append({
            "id": t.id,
            "event_id": t.event_id,
            "title": t.title,
            "description": t.description,
            "deadline": deadline_str,
            "date": t.date,
            "start_time": t.start_time,
            "score_value": t.score_value,
            "is_completed": t.is_completed,
            "status": t.status,
            "priority": t.priority,
            "difficulty": t.difficulty
        })
    return jsonify(result)

@app.route('/api/tasks/<string:event_id>/subtasks', methods=['GET'])
def get_subtasks(event_id):
    # Fetch tasks where parent_id matches the given event_id
    subtasks = Task.query.filter_by(parent_id=event_id).all()
    
    # Sort by date/time
    subtasks.sort(key=lambda x: (x.date or '9999', x.start_time or '99:99'))
    
    result = []
    for t in subtasks:
        deadline_str = None
        if t.date and t.start_time:
            deadline_str = f"{t.date}T{t.start_time}:00"
        elif t.deadline:
            deadline_str = t.deadline.isoformat()

        result.append({
            "id": t.id,
            "event_id": t.event_id,
            "parent_id": t.parent_id,
            "title": t.title,
            "description": t.description,
            "deadline": deadline_str,
            "date": t.date,
            "start_time": t.start_time,
            "score_value": t.score_value,
            "is_completed": t.is_completed,
            "status": t.status,
            "priority": t.priority,
            "difficulty": t.difficulty
        })
    return jsonify(result)


@app.route('/api/tasks/calendar', methods=['GET'])
def get_calendar_tasks():
    tasks = Task.query.all()
    result = []
    for t in tasks:
        date_str = t.date
        deadline_str = None
        if not date_str and t.deadline:
            date_str = t.deadline.date().isoformat()
            deadline_str = t.deadline.isoformat()
        
        # Format start time for full deadline string if needed
        if date_str and t.start_time:
            deadline_str = f"{date_str}T{t.start_time}:00"

        if date_str:
            result.append({
                "id": t.id,
                "event_id": t.event_id,
                "parent_id": t.parent_id,
                "title": t.title,
                "description": t.description,
                "date": date_str,
                "start_time": t.start_time,
                "end_time": t.end_time,
                "deadline": deadline_str,
                "score_value": t.score_value,
                "priority": t.priority,
                "importance": t.importance,
                "difficulty": t.difficulty,
                "is_fixed": t.is_fixed,
                "status": t.status,
                "is_completed": t.is_completed or t.status == 'completed'
            })
    return jsonify(result)

@app.route('/api/stats/weekly', methods=['GET'])
def get_weekly_stats():
    today = datetime.now().date()
    stats = []
    print(f"\n--- 📊 Calculating Weekly Stats (Today: {today}) ---")
    
    for i in range(6, -1, -1):
        day = today - timedelta(days=i)
        day_str = day.strftime("%Y-%m-%d")
        
        # Log query
        tasks = Task.query.filter(Task.date == day_str, (Task.is_completed == True) | (Task.status == 'completed')).all()
        
        daily_score = sum(t.score_value for t in tasks)
        print(f"Date: {day_str} | Tasks Found: {len(tasks)} | Score: {daily_score}")
        
        stats.append({"day": day.strftime("%a"), "score": daily_score})
    
    return jsonify(stats)

@app.route('/api/tasks/history', methods=['GET'])
def get_task_history():
    tasks = Task.query.filter((Task.is_completed == True) | (Task.status == 'completed')).order_by(Task.date.desc()).all()
    result = []
    for t in tasks:
        result.append({
            "id": t.id,
            "title": t.title,
            "date": t.date,
            "score_value": t.score_value
        })
    return jsonify(result)

@app.route('/api/rewards', methods=['GET'])
def get_rewards():
    rewards = Reward.query.all()
    return jsonify([{"id": r.id, "title": r.title, "cost": r.cost, "icon": r.icon} for r in rewards])

@app.route('/api/rewards', methods=['POST'])
def add_reward():
    data = request.json
    new_reward = Reward(
        title=data['title'],
        cost=data['cost'],
        icon=data.get('icon', '🎁')
    )
    db.session.add(new_reward)
    db.session.commit()
    return jsonify({"message": "Reward added"})

@app.route('/api/rewards/<int:reward_id>/redeem', methods=['POST'])
def redeem_reward(reward_id):
    reward = Reward.query.get(reward_id)
    user = User.query.first()
    if not reward or not user:
        return jsonify({"error": "Data error"}), 404
    if user.score >= reward.cost:
        user.score -= reward.cost
        db.session.commit()
        return jsonify({"message": "Redeemed successfully", "new_score": user.score})
    else:
        return jsonify({"error": "Not enough points"}), 400

# ==========================================
# Scheduler Integration Routes
# ==========================================

@app.route('/api/add_task', methods=['POST'])
def add_task_route():
    try:
        data = request.json 
        
        # 1. Call Scheduler Function (Logic Layer)
        functions.input_task(
            Name=data.get('name'),
            Date=data.get('date'),
            Is_fixed_input='y' if data.get('is_fixed') else 'n',
            Priority=data.get('priority'),
            Importance=data.get('importance'),
            Difficulty=data.get('difficulty'),
            Start_time=data.get('start_time'),
            End_time=data.get('end_time'),
            Estimated_time=data.get('estimated_hours'),
            Event_id=data.get('event_id') # Pass the frontend generated ID
        )
        
        # 2. Save to SQLite (Presentation Layer)
        new_task = Task(
            event_id=data.get('event_id'),
            parent_id=data.get('parent_id'),
            title=data.get('name'),
            date=data.get('date'),
            start_time=data.get('start_time'),
            end_time=data.get('end_time'),
            estimated_hours=data.get('estimated_hours', 0.0),
            priority=data.get('priority', 3),
            importance=data.get('importance', 3),
            difficulty=data.get('difficulty', 3),
            is_fixed=data.get('is_fixed', False),
            status=data.get('status', 'pending'),
            score_value=calculate_score(
                data.get('estimated_hours', 0),
                data.get('priority', 3),
                data.get('importance', 3),
                data.get('difficulty', 3),
                data.get('start_time'),
                data.get('end_time')
            )
        )
        
        db.session.add(new_task)
        db.session.commit()
        
        return jsonify({"success": True, "message": "Task added to Scheduler and Database"}), 200
        
    except Exception as e:
        print(f"Error adding task: {e}")
        return jsonify({"success": False, "message": f"新增任務失敗: {e}"}), 500

@app.route('/api/run_ai_decompose', methods=['GET'])
def run_ai_decomposition_route():
    try:
        # 1. Run AI Decomposition (Updates tasks.json)
        functions.run_ai_decomposition()
        
        # 2. Sync JSON to SQLite
        manager = DataManager()
        json_tasks = manager._read_json(TASKS_FILE, default_type='list')
        
        synced_count = 0
        for jt in json_tasks:
            event_id = jt.get('event_id')
            if not event_id: continue
            
            # Check if exists in DB
            existing_task = Task.query.filter_by(event_id=event_id).first()
            
            if not existing_task:
                # Create new task from JSON data
                new_task = Task(
                    event_id=event_id,
                    parent_id=jt.get('parent_id'),
                    title=jt.get('name', 'Untitled'),
                    description=jt.get('description', ''),
                    date=jt.get('date'),
                    start_time=jt.get('start_time'),
                    end_time=jt.get('end_time'),
                    estimated_hours=float(jt.get('estimated_hours', 0)),
                    priority=int(jt.get('priority', 3)),
                    importance=int(jt.get('importance', 3)),
                    difficulty=int(jt.get('difficulty', 3)),
                    is_fixed=jt.get('is_fixed', False),
                    status=str(jt.get('status', 'pending')),
                    score_value=calculate_score(
                        jt.get('estimated_hours', 0),
                        jt.get('priority', 3),
                        jt.get('importance', 3),
                        jt.get('difficulty', 3),
                        jt.get('start_time'),
                        jt.get('end_time')
                    )
                )
                db.session.add(new_task)
                synced_count += 1
                
        db.session.commit()
        
        return jsonify({
            "success": True, 
            "message": f"AI 任務分解完成，並同步了 {synced_count} 個新任務到資料庫。"
        }), 200
    except Exception as e:
        print(f"Error in run_ai_decompose: {e}")
        return jsonify({"success": False, "message": f"AI 任務分解失敗: {e}"}), 500

@app.route('/api/run_ai_schedule', methods=['GET'])
def run_ai_scheduling_route():
    try:
        target_date = request.args.get('date', datetime.now().strftime("%Y-%m-%d"))
        functions.run_ai_scheduling(target_date)
        return jsonify({"success": True, "message": f"AI 日排程 (Phase 2) 已為 {target_date} 完成。"}), 200
    except Exception as e:
        return jsonify({"success": False, "message": f"AI 排程失敗: {e}"}), 500

@app.route('/api/delete_event', methods=['POST'])
def delete_event_route():
    try:
        # Supports JSON or Form
        event_id = request.json.get('event_id') if request.is_json else request.form.get('event_id')
        if not event_id:
            return jsonify({"success": False, "message": "缺少 event_id 參數"}), 400
        
        functions.delete_event(event_id)
        
        # Also remove from Local DB (Cascade Delete)
        # 1. Delete all subtasks first
        subtasks = Task.query.filter_by(parent_id=event_id).all()
        for sub in subtasks:
            db.session.delete(sub)
            
        # 2. Delete the main task
        task = Task.query.filter_by(event_id=event_id).first()
        if task:
            db.session.delete(task)
            
        db.session.commit()
            
        return jsonify({"success": True, "message": f"事件 ID {event_id} 及其子任務已刪除。"}), 200
    except Exception as e:
        return jsonify({"success": False, "message": f"刪除事件失敗: {e}"}), 500

@app.route('/api/complete_event', methods=['POST'])
def complete_event_route():
    try:
        data = request.json if request.is_json else request.form
        event_id = data.get('event_id')
        task_id = data.get('id')
        status_str = data.get('completion_status')
        
        # Default to 1.0 (100%) if not provided
        completion_status = float(status_str) if status_str is not None else 1.0

        functions.complete_event(event_id, completion_status)
        
        task = None
        if event_id:
            task = Task.query.filter_by(event_id=event_id).first()
        elif task_id:
            task = db.session.get(Task, task_id) # Updated for SQLAlchemy 2.0
            if task: event_id = task.event_id 
            
        if not task:
            return jsonify({"success": False, "message": "Task not found"}), 404
            
        # 1. Update Scheduler Logic (Only if event_id exists and is valid)
        if event_id and str(event_id).lower() not in ['none', 'null', '']:
            try:
                functions.complete_event(event_id, completion_status)
            except Exception as sched_err:
                print(f"Scheduler update failed (ignoring): {sched_err}")
        
        # 2. Update Local DB
        earned_score = 0
        if completion_status >= 1.0:
            if not task.is_completed:
                task.is_completed = True
                task.status = 'completed'
                
                # Add score logic
                user = User.query.first()
                if user:
                    user.score += task.score_value
                    earned_score = task.score_value
        else:
            # Partial completion logic if needed
            task.status = 'in_progress'
            
        db.session.commit()
        
        user = User.query.first()
        return jsonify({
            "success": True, 
            "message": f"Task completed!", 
            "new_score": user.score if user else 0,
            "earned": earned_score
        }), 200
        
    except ValueError:
        return jsonify({"success": False, "message": "Invalid completion_status"}), 400
    except Exception as e:
        return jsonify({"success": False, "message": f"Error completing event: {e}"}), 500


# ----------------------------------------------------
# E2. 甜甜圈/圖像生成服務路由 (/api/donut/...)
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

    #Step 7
    print("--- 正在執行 Step 7: 合併圓環 ---")
    results = execute_step7(input_list, output_dict, unused_data)
    input_list, output_dict, unused_data, processed_count, result_path, error_status = results
    final_result_path = result_path
    
    # Update current donut for dashboard
    if final_result_path and os.path.exists(final_result_path):
        try:
            current_donut_path = os.path.join(app.root_path, 'images', 'current_donut.png')
            shutil.copy2(final_result_path, current_donut_path)
            print(f"✅ 更新首頁甜甜圈: {current_donut_path}")
        except Exception as e:
            print(f"⚠️ 無法更新首頁甜甜圈: {e}")
    
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
    



if __name__ == '__main__':
    init_db()
    app.run(debug=True, host='0.0.0.0', port=5000)
