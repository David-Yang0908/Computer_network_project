# Plan D App - AI-Powered Smart Scheduler 🚀

![Flutter](https://img.shields.io/badge/Flutter-3.0%2B-02569B?style=for-the-badge&logo=flutter)
![Python](https://img.shields.io/badge/Python-3.9%2B-3776AB?style=for-the-badge&logo=python)
![Flask](https://img.shields.io/badge/Flask-2.0%2B-000000?style=for-the-badge&logo=flask)
![Groq](https://img.shields.io/badge/AI-Groq%20Llama3-F05032?style=for-the-badge)

**Plan D** 是一款結合 **AI 智慧排程**、**Google Calendar 同步** 與 **遊戲化獎勵機制** 的全方位生產力工具。不再只是死板的待辦清單，Plan D 透過 AI 自動分析您的自然語言輸入，將任務拆解並安排到最合適的時間段，助您達成高效生活。

---

## ✨ 核心功能 (Key Features)

*   **🧠 AI 智慧輸入**: 支援自然語言對話（如：「明天早上幫我排個一小時讀書計畫」），AI 自動解析並建立任務。
*   **📅 智慧排程與拆解**:
    *   **Phase 1**: 自動將大任務拆解為可執行的小步驟。
    *   **Phase 2**: 根據您現有的 Google Calendar 行程，自動尋找空檔填入任務。
*   **🔗 Google Calendar 同步**: 所有排程即時雙向同步，確保行程不衝突。
*   **🎮 遊戲化獎勵系統**: 完成任務獲得積分，累積積分可兌換自定義獎勵（如：看電影、喝飲料），讓執行力變有趣。
*   **📊 視覺化圖表**: 提供每週執行成效分析圖表與歷史紀錄。
*   **💎 玻璃擬態 UI**: 採用現代化的 Glassmorphism 設計風格，提供極致的視覺體驗。

---

## 🛠️ 技術架構 (Tech Stack)

### Frontend (Mobile App)
*   **Framework**: Flutter (Dart)
*   **State Management**: Stateful Widgets & API Services
*   **UI Library**: `glass_container` (Custom), `fl_chart`, `table_calendar`

### Backend (API Server)
*   **Framework**: Python Flask
*   **Database**: SQLite (Local), SQLAlchemy (ORM)
*   **AI Engine**: Groq API (Llama3-70b / Mixtral)
*   **Integration**: Google Calendar API (OAuth 2.0)

---

## 🚀 安裝與執行指南 (Installation)

### 1. 前置需求
*   [Flutter SDK](https://flutter.dev/docs/get-started/install)
*   Python 3.9+
*   Google Cloud Platform 專案 (啟用 Calendar API 並下載 `credentials.json`)
*   Groq API Key

### 2. 後端設定 (Backend Setup)

1.  進入後端目錄：
    ```bash
    cd backend
    ```
2.  建立並啟動虛擬環境 (建議)：
    ```bash
    python -m venv .venv
    # Windows
    .venv\Scripts\activate
    # Mac/Linux
    source .venv/bin/activate
    ```
3.  安裝依賴套件：
    ```bash
    pip install -r requirements.txt
    ```
4.  **設定 API Keys**:
    *   將您的 **Google Calendar** `credentials.json` 放入 `backend/schedular/` 目錄。
    *   開啟 `backend/schedular/services/scheduler_ai.py`，填入您的 **Groq API Key**：
        ```python
        GROQ_API_KEY = "gsk_your_key_here"
        ```
5.  啟動伺服器：
    ```bash
    python app.py
    ```
    *   伺服器將運行於 `http://0.0.0.0:5000` (或本機 IP)。
    *   首次執行會自動初始化 SQLite 資料庫。

### 3. 前端設定 (Frontend Setup)

1.  回到專案根目錄：
    ```bash
    cd ..
    ```
2.  安裝 Flutter 套件：
    ```bash
    flutter pub get
    ```
3.  **設定 API 連線**:
    *   開啟 `lib/services/api_service.dart`。
    *   修改 `baseUrl` 指向您電腦的 IP 位址 (若在模擬器執行，請勿使用 `localhost`)：
        ```dart
        static const String baseUrl = 'http://192.168.X.X:5000/api';
        ```
4.  啟動 App：
    ```bash
    flutter run
    ```

---

## 📱 使用說明 (Usage)

1.  **新增任務**:
    *   點擊首頁右下角的 **粉紅色 (+)** 按鈕，手動輸入詳細資訊。
    *   點擊 **藍色 (✨)** 按鈕，輸入自然語言（例：「下週五要交期末報告」），讓 AI 自動幫您規劃。
2.  **查看行事曆**:
    *   切換到底部導航欄的 **Calendar** 頁面，檢視每日行程。
    *   點擊任務可查看詳情或刪除。
3.  **兌換獎勵**:
    *   完成任務獲得分數後，前往 **Rewards** 頁面。
    *   新增您喜歡的獎勵，並用積分兌換，享受成就感！

---

## 📂 專案結構 (Structure)

```
plan_d_app/
├── backend/                # Python Flask Backend
│   ├── app.py              # API Entry Point
│   ├── instance/           # SQLite Database
│   └── schedular/          # AI & Scheduler Logic
│       ├── services/       # Core Services (AI, Google, Data)
│       └── dataset/        # JSON Storage (Tasks, Calendar)
├── lib/                    # Flutter Frontend
│   ├── main.dart           # App Entry Point
│   ├── models/             # Data Models
│   ├── screens/            # UI Screens (Dashboard, Calendar, Rewards)
│   ├── services/           # HTTP API Services
│   └── widgets/            # Reusable Widgets (GlassContainer, etc.)
└── pubspec.yaml            # Flutter Dependencies
```

---

## 🤝 貢獻與開發 (Contribution)

歡迎提交 Pull Request 或 Issue！
在開發前，請確保已閱讀 `.gitignore` 避免上傳敏感資料。

---

**Created with ❤️ by Plan D Team**