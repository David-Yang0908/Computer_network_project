# task_complete.py
import json
import os
from backend.data_manager import DataManager

# 假定您希望寫入的另一個 JSON 檔案名
PROMPT_FILE = 'task_input_sample.json' 
TASKS_FILE = "tasks.json"
ROUTINE_FILE = "routine.json"

# --- 內部輔助函式 (來自 input_json_generator.py 的邏輯) ---

def _write_to_input_sample(event_id: str, found_event: dict, completion_status: float, is_routine: bool):
    """
    將完成的事件資訊轉換為 task_input_sample.json 格式並寫入檔案。
    這個格式通常用於 AI 模型提示或後續分析。
    """
    
    # 根據 user_derived_content (found_event) 建立新項目
    new_item = {
        "task_name": found_event.get("name"),
        "EID": event_id,
        "P": found_event.get("priority", 3),          # 對應 priority
        "I": found_event.get("importance", 3),        # 對應 importance
        "D": found_event.get("difficulty", 3),        # 對應 difficulty
        "c": completion_status,                       # 傳入的完成度 (0~1)
        "is_routine": is_routine,                     # 標記是否為例行公事
        "mu": 1.2,                                    # 保持不變
        "T_distract": 0,                              # 保持不變
        "T_phone": 0                                  # 保持不變
    }
    
    # 讀取現有數據或初始化為空列表
    try:
        if os.path.exists(PROMPT_FILE):
            with open(PROMPT_FILE, 'r+', encoding='utf-8') as f:
                sample_data = json.load(f)
        else:
            sample_data = []
    except (FileNotFoundError, json.JSONDecodeError):
        sample_data = []

    # 新增新項目並寫回檔案
    try:
        sample_data.append(new_item)
        with open(PROMPT_FILE, 'w', encoding='utf-8') as f:
            json.dump(sample_data, f, ensure_ascii=False, indent=4)
        
        print(f"✅ 成功將事件 '{new_item['task_name']}' 寫入 {PROMPT_FILE} 進行後續處理。")
        return True
    except Exception as e:
        print(f"❌ 寫入 {PROMPT_FILE} 失敗: {e}")
        return False


# --- 核心功能函式 ---

def complete_task(event_id: str, completion_status: float):
    """
    根據 ID 查找任務/例行公事，更新其狀態，並將完成紀錄寫入 task_input_sample.json。
    
    Args:
        event_id (str): 事件的唯一 ID。
        completion_status (float): 事件的完成度，介於 0.0 到 1.0。
    """
    manager = DataManager()
    found = False
    is_routine = False
    
    # 1. 驗證完成度
    try:
        status = float(completion_status)
        if not (0.0 <= status <= 1.0):
            print("❌ 錯誤：完成度必須是 0.0 到 1.0 之間的小數或整數。")
            return
    except ValueError:
        print("❌ 錯誤：完成度必須是有效的數字。")
        return

    # 2. 搜尋並更新 tasks.json
    tasks = manager._read_json(TASKS_FILE, default_type='list')
    for task in tasks:
        if task.get("event_id") == event_id:
            task['status'] = status
            manager._write_json(tasks, TASKS_FILE)
            print(f"✅ [Tasks] 任務 '{task['name']}' (ID: {event_id}) 狀態已更新為：{status*100:.0f}% 完成。")
            found_event = task
            found = True
            break
    
    # 3. 如果在 tasks.json 找不到，搜尋並更新 routine.json
    if not found:
        routines = manager._read_json(ROUTINE_FILE, default_type='list')
        for routine in routines:
            if routine.get("event_id") == event_id:
                routine['status'] = status # 假設 routine 也有 status 欄位
                manager._write_json(routines, ROUTINE_FILE)
                print(f"✅ [Routine] 例行公事 '{routine['name']}' (ID: {event_id}) 狀態已更新為：{status*100:.0f}% 完成。")
                found_event = routine
                found = True
                is_routine = True
                break

    # 4. 處理結果
    if found:
        # 將完成的資訊寫入 task_input_sample.json
        _write_to_input_sample(event_id, found_event, status, is_routine)
    else:
        print(f"⚠️ 找不到 ID 為 {event_id} 的任務或例行公事。")


# --- 測試區 (可直接執行此檔案測試) ---
if __name__ == '__main__':
    print("\n--- 任務完成功能測試 ---")
    
    # 範例測試 ID (請替換為您 tasks.json 或 routine.json 中真實存在的 event_id)
    # 假設 tasks.json 中有一個 event_id="372c9f9682d12f51" 的任務 (來自 snippet)
    TEST_TASK_ID = "372c9f9682d12f51"
    
    # 模擬完成該任務 75%
    # complete_task(TEST_TASK_ID, 0.75)
    
    # 模擬完成一個不存在的 ID
    # complete_task("non_existent_id", 1.0)
    
    # 模擬完成 100%
    # 假設 routine.json 中有一個 event_id="353ad5819af09d72" 的例行公事
    # TEST_ROUTINE_ID = "353ad5819af09d72" 
    # complete_task(TEST_ROUTINE_ID, 1.0)
    pass