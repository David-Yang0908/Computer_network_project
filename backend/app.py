from flask import Flask, request, jsonify, send_from_directory, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from datetime import datetime, timedelta
import random
import os

# Scheduler Imports
from schedular import functions
from schedular.services import task_complete
from schedular.services.data_manager import DataManager, TASKS_FILE

app = Flask(__name__)
CORS(app)

# Configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///plan_d.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

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

# --- Routes ---

@app.route('/api/donut_image')
def get_donut_image():
    # Assumes 'images' folder is in the same directory as app.py
    return send_from_directory(os.path.join(app.root_path, 'images'), 'donut1.png')

@app.route('/api/user', methods=['GET'])
def get_user():
    user = User.query.first()
    return jsonify({
        "score": user.score,
        "level": user.level
    })

# Scheduler Imports
from schedular import functions
from schedular.services import task_complete
from schedular.services.scheduler_ai import SmartSchedulerGroq
from schedular.services.data_manager import DataManager, TASKS_FILE

# ... (Previous code) ...

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

@app.route('/api/tasks/<int:task_id>/complete', methods=['POST'])
def complete_task(task_id):
    # Local completion (Dashboard checkbox)
    task = Task.query.get(task_id)
    if not task:
        return jsonify({"error": "Task not found"}), 404
        
    if not task.is_completed:
        task.is_completed = True
        task.status = 'completed'
        
        user = User.query.first()
        user.score += task.score_value
        
        db.session.commit()
        
    return jsonify({
        "message": "Task completed",
        "new_score": User.query.first().score,
        "earned": task.score_value
    })

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
            score_value= (data.get('priority',1) + data.get('difficulty',1)) * 5
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
                    score_value= (int(jt.get('priority',1)) + int(jt.get('difficulty',1))) * 5
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
        status_str = data.get('completion_status')
        
        if not event_id or status_str is None:
            return jsonify({"success": False, "message": "缺少 event_id 或 completion_status 參數"}), 400
        
        completion_status = float(status_str)
        
        # 1. Update Scheduler Logic
        functions.complete_event(event_id, completion_status)
        
        # 2. Update Local DB
        task = Task.query.filter_by(event_id=event_id).first()
        if task:
            if completion_status >= 1.0:
                task.is_completed = True
                task.status = 'completed'
                # Add score if fully complete
                user = User.query.first()
                if user and not task.is_completed: # Prevent double scoring
                    user.score += task.score_value
            db.session.commit()
        
        return jsonify({"success": True, "message": f"事件 ID {event_id} 完成度更新為 {completion_status*100:.0f}%。"}), 200
    except ValueError:
        return jsonify({"success": False, "message": "completion_status 必須是數字 (0.0~1.0)"}), 400
    except Exception as e:
        return jsonify({"success": False, "message": f"標記完成失敗: {e}"}), 500

if __name__ == '__main__':
    init_db()
    app.run(debug=True, host='0.0.0.0', port=5000)
