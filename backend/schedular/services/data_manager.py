import json
import os
from .google_service import GoogleCalendarService

# Determine BASE_DIR relative to this file
# data_manager.py is in backend/schedular/services/
# We want backend/schedular/dataset/
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATASET_DIR = os.path.join(BASE_DIR, "dataset")

TASKS_FILE = os.path.join(DATASET_DIR, "tasks.json")
ROUTINE_FILE = os.path.join(DATASET_DIR, "routine.json")
CALENDAR_FILE = os.path.join(DATASET_DIR, "calendar.json")

class DataManager:
    def __init__(self):
        # 初始化 Google Service
        self.gcal = GoogleCalendarService()

    def _read_json(self, filename_key: str, default_type='list'):
        """
        通用的 JSON 讀取函式。
        default_type='list'：tasks.json, routine.json (空時回傳 [])
        default_type='dict'：calendar.json (空時回傳 {})
        """
        # 根據傳入的鍵 (例如 "tasks.json") 獲取完整的檔案路徑
        if filename_key == "tasks.json":
            filename = TASKS_FILE
        elif filename_key == "routine.json":
            filename = ROUTINE_FILE
        elif filename_key == "calendar.json":
            filename = CALENDAR_FILE
        else:
            # 應急處理，如果傳入的不是已知的檔案名，則假設為相對路徑
            filename = filename_key
        if not os.path.exists(filename): 
            return [] if default_type == 'list' else {}
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                return json.load(f)
        except: 
            # 讀取失敗時，根據預設類型回傳空結構，避免程式崩潰
            return [] if default_type == 'list' else {}

    def _write_json(self, data, filename):
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
            return True
        except Exception as e:
            print(f"寫入 {filename} 失敗: {e}")
            return False

    # --- 新增功能 (Add) ---
    
    def add_task_data(self, task_dict):
        """新增單次任務: 寫入 tasks.json 並同步 Google Calendar"""
        # DataManager 讀取 tasks.json 預設為 list
        tasks = self._read_json(TASKS_FILE, default_type='list')
        tasks.append(task_dict)
        
        if self._write_json(tasks, TASKS_FILE):
            print(f"✅ [Local] 已儲存任務: {task_dict['name']}")
            
            if task_dict.get('start_time') and task_dict.get('end_time') and task_dict.get('date'):
                start_iso = f"{task_dict['date']}T{task_dict['start_time']}:00+08:00"
                end_iso = f"{task_dict['date']}T{task_dict['end_time']}:00+08:00"
                
                self.gcal.add_event(
                    summary=task_dict['name'],
                    start_dt=start_iso,
                    end_dt=end_iso,
                    event_id=task_dict['event_id']
                )
            else:
                print("ℹ️ 此任務無固定時間，僅儲存於本地待辦清單，不同步至日曆。")

    def add_routine_data(self, routine_dict):
        """新增例行公事: 寫入 routine.json 並同步 Google Calendar"""
        routines = self._read_json(ROUTINE_FILE, default_type='list')
        routines.append(routine_dict)

        if self._write_json(routines, ROUTINE_FILE):
            print(f"✅ [Local] 已儲存例行公事: {routine_dict['name']}")
            
            start_iso = f"{routine_dict['start_date']}T{routine_dict['start_time']}:00+08:00"
            end_iso = f"{routine_dict['start_date']}T{routine_dict['end_time']}:00+08:00"
            
            day_map = {
                "Monday": "MO", "Tuesday": "TU", "Wednesday": "WE", 
                "Thursday": "TH", "Friday": "FR", "Saturday": "SA", "Sunday": "SU"
            }
            day_code = day_map.get(routine_dict.get('day_of_week'), "MO")
            rrule = f"RRULE:FREQ=WEEKLY;BYDAY={day_code}"

            self.gcal.add_event(
                summary=routine_dict['name'],
                start_dt=start_iso,
                end_dt=end_iso,
                event_id=routine_dict['event_id'],
                recurrence_rule=rrule
            )

    # --- 刪除功能 (Delete by ID) ---
    
    def delete_event_by_id(self, target_id):
        """根據 ID，自動搜尋 routine 或 tasks 進行刪除，並同步刪除 Google Calendar 對應事件。"""
        
        # 1. 檢查 Routine
        routines = self._read_json(ROUTINE_FILE, default_type='list')
        new_routines = [r for r in routines if r.get('event_id') != target_id]
        
        if len(new_routines) < len(routines):
            self._write_json(new_routines, ROUTINE_FILE)
            self.gcal.delete_event(target_id)
            print(f"✅ 已從 Routine 與 Calendar 刪除 ID: {target_id}")
            return 

        # 2. 檢查 Tasks
        tasks = self._read_json(TASKS_FILE, default_type='list')
        
        target_task = next((t for t in tasks if t.get('event_id') == target_id), None)
        
        if target_task:
            ids_to_delete = {target_id}
            # 找出所有子任務
            children = [t for t in tasks if t.get('parent_id') == target_id]
            for child in children:
                ids_to_delete.add(child['event_id'])
            
            # 更新 tasks 列表
            new_tasks = [t for t in tasks if t.get('event_id') not in ids_to_delete]
            self._write_json(new_tasks, TASKS_FILE)
            
            # 同步刪除 GCal 
            print(f"✅ 從 Tasks 刪除 {len(ids_to_delete)} 筆資料 (含子任務)。正在同步刪除 Google Calendar...")
            for eid in ids_to_delete:
                self.gcal.delete_event(eid)
                
            return

        print(f"⚠️ 找不到 ID: {target_id}。請確認輸入是否正確。")