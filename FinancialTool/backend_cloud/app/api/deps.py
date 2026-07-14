from fastapi import Depends, HTTPException, status, Query, WebSocketException
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
import jwt

from backend_cloud.app.database.base import get_db
from backend_cloud.app.database.models import User
from backend_cloud.app.core.security import SECRET_KEY, ALGORITHM

# Chốt chặn này sẽ tự động tìm Header "Authorization: Bearer <token>"
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    """Chốt chặn cho các API HTTP (GET, POST, PUT, DELETE)"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token không hợp lệ hoặc đã hết hạn",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        # Giải mã token
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except jwt.PyJWTError: # Bắt mọi lỗi liên quan đến JWT (hết hạn, sai chữ ký...)
        raise credentials_exception
        
    # Truy vấn DB xem user còn tồn tại không
    user = db.query(User).filter(User.id == int(user_id)).first()
    if user is None:
        raise credentials_exception
        
    return user


async def get_current_user_ws(token: str = Query(...), db: Session = Depends(get_db)) -> User:
    """Chốt chặn cho kết nối WebSocket (Lấy token từ Query Parameter)"""
    try:
        if not token or token == "null" or token == "undefined":
            print("⚠️ WebSocket Auth: Token is null or undefined string")
            raise WebSocketException(code=status.WS_1008_POLICY_VIOLATION)
            
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            # WebSocket dùng status code đặc thù (1008 Policy Violation)
            raise WebSocketException(code=status.WS_1008_POLICY_VIOLATION)
            
        user = db.query(User).filter(User.id == int(user_id)).first()
        if user is None:
            raise WebSocketException(code=status.WS_1008_POLICY_VIOLATION)
            
        return user
    except jwt.PyJWTError:
        raise WebSocketException(code=status.WS_1008_POLICY_VIOLATION)