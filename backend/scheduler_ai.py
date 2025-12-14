# scheduler_ai.py
import os
import json
import uuid
from groq import Groq
from datetime import datetime
from dotenv import load_dotenv
# 假設 DataManager 已經修復路徑問題
from backend.data_manager import DataManager 

load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
QWEN_MODEL_NAME = os.getenv("GROQ_MODEL") 

CALENDAR_FILE_NAME = "calendar.json" # 僅檔名，由 DataManager 處理路徑

class SmartSchedulerGroq:
    def __init__(self):
        if not GROQ_API_KEY:
            raise ValueError("未找到 GROQ_API_KEY 環境變數。")
            
        self.client = Groq(api_key=GROQ_API_KEY)
        self.model_name = QWEN_MODEL_NAME if QWEN_MODEL_NAME else "mixtral-8x7b-32768"

    def _get_json_response(self, system_prompt, user_prompt):
        """通用 Groq 呼叫函式，要求 JSON 輸出"""
        try:
            chat_completion = self.client.chat.completions.create(
                messages=[
                    {"role": "system", "content": system_prompt + "\nOutput strictly valid JSON."},
                    {"role": "user", "content": user_prompt}
                ],
                model=self.model_name,
                response_format={"type": "json_object"},
                temperature=0.3, 
            )
            return json.loads(chat_completion.choices[0].message.content)
        except Exception as e:
            print(f"Groq API Error: {e}")
            return {}

    # --- Phase 1: 任務拆解 (已修改) ---
    def phase1_decompose_tasks(self, event, current_date_str):
        print(f"--- AI 正在分析任務: {event['name']} ---")
        parent_id = event['event_id']
        
        # [修改 1A] 修改系統提示，要求輸出預估小時 (estimated_hours)
        system_prompt = "你是專案經理。將任務拆解為3-5個子任務，並為每個子任務分配預估工時。輸出JSON: { 'decomposed_tasks': [ { 'name': '...', 'date': 'YYYY-MM-DD', 'estimated_hours': 1.5 } ] }"
        user_prompt = f"任務: {event['name']}, 原始截止日期: {event['date']}。請安排在 {current_date_str} 之後的日期。"
        
        result = self._get_json_response(system_prompt, user_prompt)
        subtasks = result.get("decomposed_tasks", [])
        
        final_subtasks = []
        for task in subtasks:
            task['event_id'] = str(uuid.uuid4().hex)[:16]
            task['parent_id'] = parent_id
            task['priority'] = event.get('priority', 3)
            task['importance'] = event.get('importance', 3)
            task['difficulty'] = event.get('difficulty', 3)
            
            # [修改 1B] 核心：將 is_fixed 設為 False
            task['is_fixed'] = False 
            
            # 移除時間欄位
            task.pop('start_time', None)
            task.pop('end_time', None)
            
            # 使用 0.0 表示 pending (未完成)
            task['status'] = 0.0 
            
            # 確保 estimated_hours 存在
            if 'estimated_hours' not in task or not task['estimated_hours']:
                 task['estimated_hours'] = 1.0 
            
            final_subtasks.append(task)
            
        return final_subtasks

    # --- Phase 2: 日排程生成 (已修改) ---
    def phase2_daily_schedule(self, fixed_events: list, todo_tasks: list, target_date: str):
        print(f"--- AI 正在生成 {target_date} 的排程表 ---")
        
        # [修改 2A] 準備 AI 提示內容：傳遞 event_id
        fixed_info = json.dumps([{"id": e['event_id'], "name": e['name'], "start": e['start_time'], "end": e['end_time']} for e in fixed_events], ensure_ascii=False)
        todo_info = json.dumps([{"id": t['event_id'], "name": t['name'], "estimated_hours": t['estimated_hours'], "priority": t['priority']} for t in todo_tasks], ensure_ascii=False)
        
        # [修改 2B] 修改系統提示，要求輸出必須包含 'id' (原始事件 ID)
        system_prompt = (
            "你是排程大師。根據固定行程和待辦任務，將待辦任務填入空檔。將結果輸出為 JSON 格式: "
            "{'daily_schedule': [{'id': '原始事件ID', 'name': '...', 'start_time': 'HH:MM', 'end_time': 'HH:MM'}]}"
            "排程範圍為 08:00 到 22:00。"
        )
        user_prompt = (
            f"日期: {target_date}\n"
            f"固定行程 (不可移動): {fixed_info}\n"
            f"待辦任務 (需排入空檔): {todo_info}\n"
            "請為所有待辦任務分配時間區間，並將它們與固定行程合併，按照時間順序輸出。確保時間不衝突，且結果中的 'id' 必須是原始事件的 ID。"
        )
        
        result = self._get_json_response(system_prompt, user_prompt)
        daily_schedule = result.get("daily_schedule", [])
        
        # [修改 2C] 確保 ID 不遺失 (備用邏輯)
        id_map = {item.get('event_id'): item for item in fixed_events + todo_tasks if item.get('event_id')}
        
        for entry in daily_schedule:
            if 'id' not in entry or not entry['id']:
                # 如果 AI 遺失 ID，嘗試根據名稱找回
                original_event = next((e for e in id_map.values() if e.get('name') == entry['name']), None)
                if original_event:
                    entry['id'] = original_event['event_id']
                else:
                    entry['id'] = str(uuid.uuid4().hex)[:16] # 仍找不到則生成一個新的
            
            # 例行公事的 ID 應該是它的 event_id，但 calendar.json 舊格式使用 'R_' 前綴，
            # 這裡我們保持使用傳遞進來的 event_id (即固定行程或待辦任務的 ID)。

        return daily_schedule

# --- 執行函式 (Phase 1) ---

def execute_phase1_logic():
    """執行 Phase 1: 任務拆解與 GCal 同步"""
    manager = DataManager()
    all_tasks = manager._read_json("tasks.json", default_type='list') 
    
    # 找一個難度高且未拆解的任務作為目標
    targets = [t for t in all_tasks if t.get('difficulty', 0) >= 4 and t.get('status', 0.0) < 1.0 and t.get('parent_id') == None]
    
    if targets:
        for target in targets:
            # 檢查是否已存在子任務，避免重複分解 (如果 tasks.json 中沒有 has_generated_subtasks 欄位)
            if target.get('has_generated_subtasks'):
                print(f"ℹ️ 任務 '{target['name']}' 已分解過。")
                continue

            today = datetime.now().strftime("%Y-%m-%d")
            scheduler = SmartSchedulerGroq()
            new_subtasks = scheduler.phase1_decompose_tasks(target, today)
            
            if new_subtasks:
                print(f"🤖 AI 生成了 {len(new_subtasks)} 個子任務，正在同步至 Google Calendar...")
                for sub in new_subtasks:
                    manager.add_task_data(sub) 
                
                # 更新原任務狀態，標記已拆解
                tasks_now = manager._read_json("tasks.json", default_type='list')
                for t in tasks_now:
                    if t['event_id'] == target['event_id']:
                        t['has_generated_subtasks'] = True
                manager._write_json(tasks_now, "tasks.json")
                print("✅ Phase 1 任務拆解完成。")
            else:
                print("AI 未生成任何子任務。")
        return
    else:
        print("ℹ️ 目前沒有需要拆解的高難度任務。")

# --- 執行函式 (Phase 2) ---

def execute_phase2_logic(target_date: str = None):
    """
    執行 Phase 2: 日排程生成，將結果寫入 calendar.json
    """
    manager = DataManager()
    
    if not target_date:
        target_date = datetime.now().strftime("%Y-%m-%d")
    weekday_name = datetime.strptime(target_date, "%Y-%m-%d").strftime("%A")
    
    all_tasks = manager._read_json("tasks.json", default_type='list')
    all_routines = manager._read_json("routine.json", default_type='list')
    
    # 過濾出當天的固定行程 (Fixed Events) - 必須有 start_time, end_time
    fixed_events = [
        t for t in all_tasks 
        if t.get('date') == target_date and t.get('is_fixed') and t.get('start_time')
    ]
    # 例行公事也被視為固定行程 (Routine 必須有 event_id 欄位才能傳給 AI)
    fixed_events.extend([
        r for r in all_routines 
        if r.get('day_of_week') == weekday_name and r.get('event_id')
    ])
    
    # 過濾出當天的待辦任務 (To-do Tasks) - 必須是 is_fixed=False, 且未完成
    todo_tasks = [
        t for t in all_tasks 
        if t.get('date') == target_date and not t.get('is_fixed') and t.get('status', 0.0) < 1.0 and t.get('estimated_hours')
    ]
    
    if not fixed_events and not todo_tasks:
        print(f"ℹ️ {target_date} 沒有任何排程或待辦事項。")
        update_calendar_for_date(target_date, [])
        return

    try:
        scheduler = SmartSchedulerGroq()
        calendar_entries = scheduler.phase2_daily_schedule(fixed_events, todo_tasks, target_date)
    except Exception as e:
        print(f"❌ AI 排程失敗: {e}")
        return

    update_calendar_for_date(target_date, calendar_entries)

    print(f"\n✅ {target_date} 的最終排程已寫入 {CALENDAR_FILE_NAME}。")
    for item in calendar_entries:
        item_id = item.get('id', 'N/A')
        print(f"{item['start_time']}-{item['end_time']} | {item['name']} (ID: {item_id[:8]}...)")

# --- 檔案寫入函式 (無需修改) ---

def update_calendar_for_date(target_date, new_entries):
    """讀取 calendar.json，更新或寫入特定日期的排程"""
    temp_manager = DataManager()
    
    calendar_data = temp_manager._read_json(CALENDAR_FILE_NAME, default_type='dict') 
        
    target_date_key = target_date.replace('/', '-') 
    calendar_data[target_date_key] = new_entries
    
    temp_manager._write_json(calendar_data, CALENDAR_FILE_NAME)