# app.py
from flask import Flask, render_template, request, redirect, url_for, jsonify
from datetime import datetime
import functions # 引入我們整理好的 functions.py 介面

app = Flask(__name__)

# --- 1. 任務/行程顯示頁面 (Root Route) ---
@app.route('/')
def index():
    """
    根目錄：顯示系統狀態、排程結果或提供操作介面。
    這裡可以讀取 calendar.json 顯示今天的排程。
    """
    # 這裡可以呼叫 DataManager 讀取 calendar.json 的資料
    # 為了簡化，我們先傳遞一個預設標題
    return render_template('index.html', 
                           title="排程器主控台",
                           today_date=datetime.now().strftime("%Y-%m-%d"))

# --- 2. 新增單次任務 (POST) ---
@app.route('/add_task', methods=['POST'])
def add_task_route():
    try:
        data = request.form
        
        # Flask 路由接收參數並傳遞給 functions.py
        # 注意：我們需要從 request.form/json 拿到所有 task_input_tool 需要的參數
        
        functions.input_task(
            Name=data.get('name'),
            Date=data.get('date'),
            Is_fixed_input=data.get('is_fixed', 'n'), # 預設為非固定
            Priority=data.get('priority'),
            Importance=data.get('importance'),
            Difficulty=data.get('difficulty'),
            Start_time=data.get('start_time'),
            End_time=data.get('end_time'),
            Estimated_time=data.get('estimated_time')
        )
        
        # 新增成功後導回主頁
        return redirect(url_for('index'))
    except Exception as e:
        # 返回 JSON 錯誤訊息，方便除錯
        return jsonify({"success": False, "message": f"新增單次任務失敗: {e}"}), 500

# --- 3. 執行 AI 任務分解 (GET) ---
@app.route('/run_ai_decompose', methods=['GET'])
def run_ai_decomposition_route():
    try:
        functions.run_ai_decomposition()
        return jsonify({"success": True, "message": "AI 任務分解 (Phase 1) 已啟動並同步到 GCal。"}), 200
    except Exception as e:
        return jsonify({"success": False, "message": f"AI 任務分解失敗: {e}"}), 500

# --- 4. 執行 AI 日排程 (GET) ---
@app.route('/run_ai_schedule', methods=['GET'])
def run_ai_scheduling_route():
    try:
        target_date = request.args.get('date', datetime.now().strftime("%Y-%m-%d"))
        functions.run_ai_scheduling(target_date)
        return jsonify({"success": True, "message": f"AI 日排程 (Phase 2) 已為 {target_date} 完成排程，並寫入 calendar.json。"}), 200
    except Exception as e:
        return jsonify({"success": False, "message": f"AI 排程失敗: {e}"}), 500

# --- 5. 刪除事件 (POST) ---
@app.route('/delete_event', methods=['POST'])
def delete_event_route():
    try:
        event_id = request.form.get('event_id')
        if not event_id:
            return jsonify({"success": False, "message": "缺少 event_id 參數"}), 400
        
        functions.delete_event(event_id)
        return jsonify({"success": True, "message": f"事件 ID {event_id} 已嘗試刪除 (本地與 GCal 同步)。"}), 200
    except Exception as e:
        return jsonify({"success": False, "message": f"刪除事件失敗: {e}"}), 500


if __name__ == '__main__':
    # 在執行前，建議先在 functions.py 確保 DataManager 已經初始化
    print("--- 啟動 Flask 應用程式 ---")
    app.run(debug=True)