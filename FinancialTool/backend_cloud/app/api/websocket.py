from typing import List, Dict
from fastapi import WebSocket, WebSocketDisconnect
import asyncio
import json

class ConnectionManager:
    def __init__(self):
        # Danh sách kết nối đang hoạt động
        self.active_connections: Dict[str, List[WebSocket]] = {}
        self._lock = None

    def get_lock(self):
        if self._lock is None:
            self._lock = asyncio.Lock()
        return self._lock
        
    async def connect(self, websocket: WebSocket, user_id: int | str):
        await websocket.accept()
        uid = str(user_id)
        async with self.get_lock():
            if uid not in self.active_connections:
                self.active_connections[uid] = []
            self.active_connections[uid].append(websocket)
            print(f"✅ WebSocket Connected: {uid}")

    async def disconnect(self, websocket: WebSocket, user_id: str):
        uid = str(user_id)
        async with self.get_lock():
            #print(f"⚠️ CẢNH BÁO: Đang xóa user_id {user_id} khỏi danh sách!")
            if uid in self.active_connections:
                if websocket in self.active_connections[uid]:
                    self.active_connections[uid].remove(websocket)
                if len(self.active_connections[uid]) == 0:
                    del self.active_connections[uid]

    async def broadcast(self, message: dict):
        async with self.get_lock():
            current_connections = dict(self.active_connections)
                    
        for user_id, connections in current_connections.items():
            for connection in connections:
                try:
                    await connection.send_json(message)
                except Exception as e:
                    print(f"⚠️ Lỗi gửi tin cho {user_id}: {e}")
                    await self.disconnect(connection, user_id)

    async def send_personal_message(self, user_id: int, message: dict):
        uid = str(user_id)
        async with self.get_lock():
            if uid in self.active_connections:
                current_connections = self.active_connections[uid]
                for connection in current_connections:
                    try:
                        await connection.send_json(message)
                    except Exception as e:
                        await self.disconnect(connection, user_id)

# Singleton Instance
ws_manager = ConnectionManager()