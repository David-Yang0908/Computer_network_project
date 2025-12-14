# task_complete.py
import json
import os
from datetime import datetime
from .data_manager import DataManager
from datetime import datetime, timedelta

# Determine BASE_DIR relative to this file
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATASET_DIR = os.path.join(BASE_DIR, "dataset")

TASKS_FILE = os.path.join(DATASET_DIR, "tasks.json")
ROUTINE_FILE = os.path.join(DATASET_DIR, "routine.json")
PROMPT_FILE = os.path.join(DATASET_DIR, "task_input_sample.json")

# --- 內部輔助函式：計算時間差 ---

def _calculate_duration_hours(start_time_str: str, end_time_str: str) -> float:
    """計算 HH:MM 格式的起訖時間差（以小時為單位）。"""
    try:
        if not start_time_str or not end_time_str:
            return 0.0

        # 解析時間字串，使用基礎日期避免日期錯誤
        time_format = "%H:%M"
        start_dt = datetime.strptime(start_time_str, time_format)
        end_dt = datetime.strptime(end_time_str, time_format)

        # 處理跨午夜情況 (例如 23:00-01:00)
        if end_dt < start_dt:
            end_dt += timedelta(days=1)

        duration = end_dt - start_dt
        # 轉換為小時 (總秒數 / 3600)
        return duration.total_seconds() / 3600.0
    except ValueError as e:
        print(f"⚠️ 時間格式錯誤 ({start_time_str} 或 {end_time_str}): {e}")
        return 0.0

def _write_to_input_sample(event_id: str, found_event: dict, completion_status: float, is_routine: bool):
    """
    將完成的事件資訊轉換為 task_input_sample.json 格式並寫入檔案。
    """
    # --- NEW LOGIC: T_est 計算 ---
    estimated_hours = found_event.get("estimated_hours")
    t_est_value = 1 # 預設值為 1 小時

    if estimated_hours is None or estimated_hours == 0.0 or estimated_hours == 0:
        # 當 estimated_hours 缺失或為 0 時，使用 start_time 和 end_time 計算
        start_time = found_event.get("start_time")
        end_time = found_event.get("end_time")
        
        calculated_duration = _calculate_duration_hours(start_time, end_time)
        t_est_value = calculated_duration
    else:
        # 使用 event 中原有的 estimated_hours (並確保是整數且至少為 1)
        # 這裡假設 estimated_hours 已經是小時為單位
        t_est_value = float(estimated_hours)

    # 根據 task_input_sample.json 的正確欄位名稱建立新項目
    new_item = {
        "task_name": found_event.get("name"),
        # 將 EID 改為 task_id
        "task_id": None,
        
        # 補齊 task_input_sample.json 中所需的狀態和常數欄位
        "prompt_status": False,
        "image_status": False,
        "donut_status": False,
        "gray_status": False,
        "ratio_status": False,
        "cut_status": False,
        "merge_status": False, # 使用 task_input_sample.json 觀察到的標準欄位
        "r": 30.0,
        
        # 使用 estimated_hours 欄位對應 T_est
        # 確保取值後轉換為整數 (int)
        "T_est": t_est_value, # 使用計算後的值"T_est": t_est_value, # 使用計算後的值
        
        "P": found_event.get("priority", 3),          # 對應 priority
        "I": found_event.get("importance", 3),        # 對應 importance
        "D": found_event.get("difficulty", 3),        # 對應 difficulty
        "c": completion_status,                       # 傳入的完成度 (0~1)
        
        # mu, T_distract, T_phone 保持不變
        "mu": 1.2,                                    
        "T_distract": 0,                              
        "T_phone": 0                                  
        
        # 移除 is_routine 欄位，它不在 task_input_sample.json 的標準結構中
    }
    
    # 讀取現有數據或初始化為空列表
    try:
        if os.path.exists(PROMPT_FILE):
            # 讀取檔案時必須是 'r' 模式
            with open(PROMPT_FILE, 'r', encoding='utf-8') as f:
                sample_data = json.load(f)
        else:
            sample_data = []
    except (FileNotFoundError, json.JSONDecodeError):
        print(f"⚠️ 檔案 {PROMPT_FILE} 讀取失敗或格式錯誤，將重新創建。")
        sample_data = []

    # 新增新項目並寫回檔案
    try:
        sample_data.append(new_item)
        with open(PROMPT_FILE, 'w', encoding='utf-8') as f:
            json.dump(sample_data, f, ensure_ascii=False, indent=4)
        
        print(f"✅ 成功將事件 '{new_item['task_name']}'寫入 {PROMPT_FILE} 進行後續處理。")
        return True
    except Exception as e:
        print(f"❌ 寫入 {PROMPT_FILE} 失敗: {e}")
        return False




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
# if __name__ == '__main__':
#     print("\n--- 任務完成功能測試 ---")
    
#     # 範例測試 ID (請替換為您 tasks.json 或 routine.json 中真實存在的 event_id)
#     # 假設 tasks.json 中有一個 event_id="372c9f9682d12f51" 的任務 (來自 snippet)
#     TEST_TASK_ID = "372c9f9682d12f51"
    
#     # 模擬完成該任務 75%
#     # complete_task(TEST_TASK_ID, 0.75)
    
#     # 模擬完成一個不存在的 ID
#     # complete_task("non_existent_id", 1.0)
    
#     # 模擬完成 100%
#     # 假設 routine.json 中有一個 event_id="353ad5819af09d72" 的例行公事
#     # TEST_ROUTINE_ID = "353ad5819af09d72" 
#     # complete_task(TEST_ROUTINE_ID, 1.0)
#     pass