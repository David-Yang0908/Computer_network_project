import schedular.services.task_input_tool
from schedular.services.scheduler_ai import SmartSchedulerGroq
from schedular.services.data_manager import DataManager
from datetime import datetime
import schedular.services.task_complete

# 初始化管理器 (只需一個實例)
# DataManager 包含了讀寫 JSON 和 GCal 服務
manager = DataManager()

def input_task(Name=None, Date=None, Is_fixed_input=None, Priority=None, Importance=None, Difficulty=None, Start_time=None, End_time=None, Estimated_time=None, Event_id=None):
    """
    新增單次任務。
    1. 收集資料 (task_input_tool)
    2. 存入 JSON 並同步 Google Calendar (manager)
    """
    print("\n--- 📝 呼叫新增單次任務 ---")
    new_task = schedular.services.task_input_tool.collect_task_input(
        Name, Date, Is_fixed_input, Priority, Importance, Difficulty, Start_time, End_time, Estimated_time, Event_id
    )
    manager.add_task_data(new_task)

def input_routine(Name=None, Date=None, Start_time=None, End_time=None, Priority=None, Importance=None, Difficulty=None):
    """
    新增例行公事。
    1. 收集資料
    2. 存入 JSON 並同步 Google Calendar (包含每週重複設定)
    """
    print("\n--- 📝 呼叫新增例行公事 ---")
    new_routine = schedular.services.task_input_tool.collect_routine_input(
        Name, Date, Start_time, End_time, Priority, Importance, Difficulty
    )
    manager.add_routine_data(new_routine)

def delete_event(event_id):
    """
    [任務 1 & 2 解法]
    直接輸入 ID，系統會自動判斷是 Routine 還是 Task，並同步刪除 GCal。
    """
    print(f"\n--- 🗑️ 正在刪除事件 ID: {event_id} ---")
    manager.delete_event_by_id(event_id)

def run_ai_decomposition():
    """[任務 3 解法] 執行 AI 任務拆解 (Phase 1)"""
    print("\n--- 🤖 執行 AI 任務拆解 (Phase 1) ---")
    scheduler = SmartSchedulerGroq()
    scheduler.execute_phase1_logic()

def run_ai_scheduling(target_date: str = None):
    """
    [任務 3 補完] 執行 AI 日排程 (Phase 2)
    可指定日期，若無則排程今天。
    """
    print(f"\n--- 🤖 執行 AI 日排程 (Phase 2) ---")
    scheduler = SmartSchedulerGroq()
    scheduler.execute_phase2_logic(target_date)

def complete_event(event_id: str, completion_status: float):
    """
    標記任務或例行公事的完成度。
    """
    print(f"\n--- ✅ 標記事件完成度 ID: {event_id} ---")
    schedular.services.task_complete.complete_task(event_id, completion_status)

# --- 測試與執行 ---
# if __name__ == '__main__':
#     # 測試 1: 新增單次任務 (會上傳 GCal)
#     # input_task("期末專題簡報", "2025-12-20", "y", 5, 5, 5, "14:00", "16:00")
    
#     # 測試 2: 新增例行公事 (會上傳 GCal 並每週重複)
#     input_routine("丟垃圾", "2025-12-15", "19:00", "20:00", 4, 2, 2)
    
#     # 測試 3: 刪除任務 (請填入真實存在的 ID)
#     # delete_event("62418f63ec4c3901")

#     # 測試 4: 執行 AI
#     # run_ai_decomposition()

#     # 測試 5: 排程今天的 To Do List
#     # run_ai_scheduling(datetime.now().strftime("%Y-%m-%d"))
#     # run_ai_scheduling('2025-12-15')

#     # 測試刪除功能
#     # delete_event("這裡填入_某個事件的_event_id")
#     pass