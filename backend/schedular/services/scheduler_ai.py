# scheduler_ai.py
import os
import json
import uuid
import time
from groq import Groq
from datetime import datetime, timedelta
from dotenv import load_dotenv
from .data_manager import DataManager 

load_dotenv()
# 請替換為您的 Groq API Key
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
QWEN_MODEL_NAME = os.getenv("GROQ_MODEL") 

CALENDAR_FILE_NAME  = "./backend/schedular/dataset/calendar.json"

class SmartSchedulerGroq:
    def __init__(self):
        if not GROQ_API_KEY or GROQ_API_KEY == "gsk_...":
            print("❌ Error: Missing GROQ_API_KEY in scheduler_ai.py")
            self.client = None
        else:
            self.client = Groq(api_key=GROQ_API_KEY)
            
        self.model_name = QWEN_MODEL_NAME if QWEN_MODEL_NAME else "llama3-70b-8192"

    def _get_json_response(self, system_prompt, user_prompt):
        """通用 Groq 呼叫函式，要求 JSON 輸出"""
        if not self.client: return {}
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

    def analyze_user_input(self, user_text: str):
        """
        使用 Groq LLM 分析使用者輸入，嘗試提取任務資訊。
        """
        if not self.client:
            return {"success": False, "message": "Server configuration error: API Key missing."}
        
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M")
        
        system_prompt = f"""
You are an intelligent task scheduling assistant. Your goal is to parse user natural language input into a structured JSON task object. 
        
Current Time: {current_time}
        
        ### Output Format (JSON Only):
        If the user input contains enough information (at least a Task Name and a rough Date/Time indication), output a VALID JSON object with this exact structure:
        {{
            "event_id": "task<TIMESTAMP>", 
            "parent_id": null,
            "name": "Task Name",
            "date": "YYYY-MM-DD",
            "start_time": "HH:MM" (24h format) or null,
            "end_time": "HH:MM" (24h format) or null,
            "estimated_hours": float (e.g. 1.5) or 0.0 if fixed time,
            "priority": int (1-5, 5 is highest),
            "importance": int (1-5),
            "difficulty": int (1-5),
            "is_fixed": boolean (true if specific start/end time provided, else false),
            "status": "pending",
            "missing_info": null
        }}
        
        ### Rules:
        1. **Inference**: If the user says "tomorrow", calculate the date based on Current Time.
        2. **Defaults**: 
           - If no time is specified but date is, assume is_fixed=false and estimated_hours=1.0.
           - Priority/Importance/Difficulty default to 3 if not implied.
        3. **Missing Info**: If the input is too vague (e.g., just "study"), DO NOT create a task. Instead, output JSON with "missing_info": "Please specify when you want to do this."
        4. **Language**: The user may speak Chinese or English. Parse correctly.
        
        ### Example 1:
        User: "明天早上九點要開會，大概一小時"
        Output: {{ ..., "name": "開會", "date": "2025-12-15", "start_time": "09:00", "end_time": "10:00", "is_fixed": true, ... }}
        
        ### Example 2:
        User: "幫我排一個讀書計畫"
        Output: {{ "missing_info": "請問您想在哪一天讀書？大約需要多久時間？" }}
        """

        try:
            completion = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_text}
                ],
                temperature=0.1,
                response_format={"type": "json_object"}
            )
            
            result_content = completion.choices[0].message.content
            print(f"🤖 LLM Response: {result_content}")
            
            parsed_result = json.loads(result_content)
            
            if parsed_result.get("missing_info"):
                return {
                    "success": False, 
                    "message": parsed_result["missing_info"],
                    "data": None
                }
                
            if "event_id" not in parsed_result or "<TIMESTAMP>" in parsed_result["event_id"]:
                parsed_result["event_id"] = f"task{int(time.time()*1000)}"
                
            return {
                "success": True,
                "message": "Task parsed successfully.",
                "data": parsed_result
            }

        except Exception as e:
            print(f"❌ AI Analysis Failed: {e}")
            return {"success": False, "message": f"AI Error: {e}"}

    # --- Phase 1: 任務拆解 ---
    def phase1_decompose_tasks(self, event, current_date_str):
        print(f"--- AI 正在分析任務: {event['name']} ---")
        parent_id = event['event_id']
        
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
            task['is_fixed'] = False 
            task.pop('start_time', None)
            task.pop('end_time', None)
            task['status'] = 0.0 
            if 'estimated_hours' not in task or not task['estimated_hours']:
                 task['estimated_hours'] = 1.0 
            
            final_subtasks.append(task)
            
        return final_subtasks

    def execute_phase1_logic(self):
        """執行 Phase 1: 任務拆解與 GCal 同步"""
        manager = DataManager()
        # Ensure tasks.json reading
        try:
            all_tasks = manager._read_json(manager.TASKS_FILE, default_type='list') 
        except:
            # Fallback if TASKS_FILE path logic is tricky inside DataManager instance vs class
            # Assuming DataManager handles it correctly via self.TASKS_FILE if properly initialized
            # But let's try standard way if manager._read_json uses filename string
            # Check DataManager.TASKS_FILE availability
            all_tasks = manager._read_json("tasks.json", default_type='list')

        targets = [t for t in all_tasks if t.get('difficulty', 0) >= 4 and t.get('status', 0.0) < 1.0 and t.get('parent_id') == None]
        
        if targets:
            for target in targets:
                if target.get('has_generated_subtasks'):
                    print(f"ℹ️ 任務 '{target['name']}' 已分解過。")
                    continue

                today = datetime.now().strftime("%Y-%m-%d")
                new_subtasks = self.phase1_decompose_tasks(target, today)
                
                if new_subtasks:
                    print(f"🤖 AI 生成了 {len(new_subtasks)} 個子任務，正在同步至 Google Calendar...")
                    for sub in new_subtasks:
                        manager.add_task_data(sub) 
                    
                    # Update original task status
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

    # --- Phase 2: 日排程生成 ---
    def phase2_daily_schedule(self, fixed_events: list, todo_tasks: list, target_date: str):
        print(f"--- AI 正在生成 {target_date} 的排程表 ---")
        
        fixed_info = json.dumps([{"id": e['event_id'], "name": e['name'], "start": e['start_time'], "end": e['end_time']} for e in fixed_events], ensure_ascii=False)
        todo_info = json.dumps([{"id": t['event_id'], "name": t['name'], "estimated_hours": t['estimated_hours'], "priority": t['priority']} for t in todo_tasks], ensure_ascii=False)
        
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
        
        id_map = {item.get('event_id'): item for item in fixed_events + todo_tasks if item.get('event_id')}
        
        for entry in daily_schedule:
            if 'id' not in entry or not entry['id']:
                original_event = next((e for e in id_map.values() if e.get('name') == entry['name']), None)
                if original_event:
                    entry['id'] = original_event['event_id']
                else:
                    entry['id'] = str(uuid.uuid4().hex)[:16] 
            
        return daily_schedule

    def execute_phase2_logic(self, target_date: str = None):
        """
        執行 Phase 2: 日排程生成，將結果寫入 calendar.json
        """
        manager = DataManager()
        
        if not target_date:
            target_date = datetime.now().strftime("%Y-%m-%d")
        weekday_name = datetime.strptime(target_date, "%Y-%m-%d").strftime("%A")
        
        all_tasks = manager._read_json("tasks.json", default_type='list')
        all_routines = manager._read_json("routine.json", default_type='list')
        
        fixed_events = [
            t for t in all_tasks 
            if t.get('date') == target_date and t.get('is_fixed') and t.get('start_time')
        ]
        fixed_events.extend([
            r for r in all_routines 
            if r.get('day_of_week') == weekday_name and r.get('event_id')
        ])
        
        todo_tasks = [
            t for t in all_tasks 
            if t.get('date') == target_date and not t.get('is_fixed') and t.get('status', 0.0) < 1.0 and t.get('estimated_hours')
        ]
        
        if not fixed_events and not todo_tasks:
            print(f"ℹ️ {target_date} 沒有任何排程或待辦事項。")
            self.update_calendar_for_date(target_date, [])
            return

        try:
            calendar_entries = self.phase2_daily_schedule(fixed_events, todo_tasks, target_date)
        except Exception as e:
            print(f"❌ AI 排程失敗: {e}")
            return

        self.update_calendar_for_date(target_date, calendar_entries)

        print(f"\n✅ {target_date} 的最終排程已寫入 {CALENDAR_FILE_NAME}。")
        for item in calendar_entries:
            item_id = item.get('id', 'N/A')
            print(f"{item['start_time']}-{item['end_time']} | {item['name']} (ID: {item_id[:8]}...)")

    def update_calendar_for_date(self, target_date, new_entries):
        """讀取 calendar.json，更新或寫入特定日期的排程"""
        temp_manager = DataManager()
        # Use filename relative to dataset logic inside DataManager if possible, 
        # or rely on temp_manager knowing the path.
        # Assuming DataManager._read_json handles filename correctly if just "calendar.json" is passed 
        # (based on previous file content logic)
        calendar_data = temp_manager._read_json("calendar.json", default_type='dict') 
            
        target_date_key = target_date.replace('/', '-') 
        calendar_data[target_date_key] = new_entries
        
        temp_manager._write_json(calendar_data, "calendar.json")
