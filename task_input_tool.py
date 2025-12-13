import uuid
import hashlib 
import time
from datetime import datetime

# --- ID 生成函式 ---
def generate_base32hex_id(length=16):
    if not 5 <= length <= 64: length = 16 
    data_to_hash = (str(uuid.uuid4()) + str(time.time())).encode('utf-8')
    hex_digest = hashlib.sha256(data_to_hash).hexdigest()
    return hex_digest[:length]

# --- 驗證函式 ---
def get_input(user_input, validator=None, default=None):
    while True:
        if not user_input and default is not None:
            return default
        if validator:
            try:
                return validator(user_input)
            except ValueError as e:
                print(f"輸入錯誤: {e}")
                # 如果是互動模式這裡會卡住，但在 functions.py 傳參模式下通常一次過
                return default 
        else:
            return user_input

def validate_date(date_str):
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
        return date_str
    except ValueError:
        raise ValueError("日期格式無效 (YYYY-MM-DD)")

def validate_time(time_str):
    try:
        datetime.strptime(time_str, "%H:%M")
        return time_str
    except ValueError:
        raise ValueError("時間格式無效 (HH:MM)")

def validate_int(int_str, min_val=1, max_val=5):
    try:
        val = int(int_str)
        if min_val <= val <= max_val: return val
        raise ValueError
    except:
        raise ValueError(f"請輸入 {min_val}-{max_val} 之間的整數")

def get_weekday_from_date(date_string: str) -> str:
    try:
        return datetime.strptime(date_string, '%Y-%m-%d').strftime('%A')
    except:
        return "Monday"

# --- 核心輸入函式 (只回傳 Dict，不寫檔) ---

def collect_task_input(Name, Date, Is_fixed_input, Priority, Importance, Difficulty, Start_time=None, End_time=None, Estimated_time=None):
    """回傳單次任務的資料字典"""
    name = get_input(Name)
    date = get_input(Date, validate_date)
    is_fixed = str(Is_fixed_input).lower() in ['y', 'yes', 'true']

    if is_fixed:
        start_time = get_input(Start_time, validate_time, default="09:00")
        end_time = get_input(End_time, validate_time, default="10:00")
        estimated_hours = 0 
    else:
        start_time = None
        end_time = None
        estimated_hours = get_input(Estimated_time, lambda x: float(x), default=1.0)

    priority = get_input(Priority, lambda x: validate_int(x), default=3)
    importance = get_input(Importance, lambda x: validate_int(x), default=3)
    difficulty = get_input(Difficulty, lambda x: validate_int(x), default=3)
    
    return {
        "event_id": generate_base32hex_id(), 
        "parent_id": None,
        "name": name,
        "date": date,
        "start_time": start_time,
        "end_time": end_time,
        "estimated_hours": float(estimated_hours),
        "priority": int(priority),
        "importance": int(importance),
        "difficulty": int(difficulty),
        "is_fixed": is_fixed,
        "status": "pending"
    }

def collect_routine_input(Name, Date, Start_time, End_time, Priority, Importance, Difficulty):
    """回傳例行公事的資料字典"""
    name = get_input(Name)
    date = get_input(Date, validate_date)
    start_time = get_input(Start_time, validate_time)
    end_time = get_input(End_time, validate_time)
    
    priority = get_input(Priority, lambda x: validate_int(x), default=3)
    importance = get_input(Importance, lambda x: validate_int(x), default=3)
    difficulty = get_input(Difficulty, lambda x: validate_int(x), default=3)
    
    return {
        "event_id": generate_base32hex_id(), 
        "name": name,
        "start_date": date,
        "day_of_week": get_weekday_from_date(date), 
        "start_time": start_time,
        "end_time": end_time,
        "priority": int(priority),
        "importance": int(importance),
        "difficulty": int(difficulty)
    }