import os.path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

SCOPES = ["https://www.googleapis.com/auth/calendar"]
TOKEN_FILE = "./backend/dataset/token.json"
CREDS_FILE = "./backend/dataset/credentials.json"

class GoogleCalendarService:
    def __init__(self):
        self.creds = None
        self.service = None
        self._authenticate()

    def _authenticate(self):
        """處理 Google OAuth 認證"""
        if os.path.exists(TOKEN_FILE):
            self.creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
        
        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                try:
                    self.creds.refresh(Request())
                except Exception as e:
                    print(f"Token refresh failed: {e}, please delete token.json and login again.")
                    return
            else:
                if not os.path.exists(CREDS_FILE):
                    print(f"錯誤: 找不到 {CREDS_FILE}，無法進行登入。")
                    return
                flow = InstalledAppFlow.from_client_secrets_file(CREDS_FILE, SCOPES)
                self.creds = flow.run_local_server(port=0)
            
            with open(TOKEN_FILE, "w") as token:
                token.write(self.creds.to_json())
        
        try:
            self.service = build("calendar", "v3", credentials=self.creds)
        except HttpError as error:
            print(f"Google Service 初始化失敗: {error}")

    def add_event(self, summary, start_dt, end_dt, event_id, description=None, recurrence_rule=None):
        """新增事件到 Google Calendar"""
        if not self.service: 
            print("⚠️ Google Service 未連接，跳過雲端同步。")
            return False

        event_body = {
            'summary': summary,
            'description': description,
            'start': {
                'dateTime': start_dt, # 預期格式: '2025-12-13T04:00:00+08:00'
                'timeZone': 'Asia/Taipei',
            },
            'end': {
                'dateTime': end_dt,
                'timeZone': 'Asia/Taipei',
            },
            'id': event_id, # 指定 ID 方便之後刪除
        }
        
        if recurrence_rule:
             event_body['recurrence'] = [recurrence_rule]

        try:
            self.service.events().insert(calendarId='primary', body=event_body).execute()
            print(f"☁️ [Google Calendar] 已新增: {summary}")
            return True
        except HttpError as error:
            print(f"❌ [Google Calendar] 新增失敗: {error}")
            return False

    def delete_event(self, event_id):
        """從 Google Calendar 刪除指定 ID 的事件"""
        if not self.service: return False
        
        try:
            self.service.events().delete(calendarId='primary', eventId=event_id).execute()
            print(f"🗑️ [Google Calendar] 已刪除 ID: {event_id}")
            return True
        except HttpError as error:
            # 404/410 代表事件已經不存在，視為刪除成功
            if error.resp.status in [404, 410]:
                print(f"ℹ️ [Google Calendar] 事件 {event_id} 已不在雲端。")
                return True
            print(f"❌ [Google Calendar] 刪除失敗: {error}")
            return False