import bcrypt
import jwt
from datetime import datetime, timedelta

# Cấu hình JWT
SECRET_KEY = "shinsei-super-secret-key-change-it-in-production"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7 # Token sống 7 ngày

def get_password_hash(password: str) -> str:
    """Băm mật khẩu trực tiếp bằng thư viện bcrypt chuẩn"""
    # bcrypt yêu cầu mật khẩu phải là dạng bytes
    pwd_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    hashed_bytes = bcrypt.hashpw(pwd_bytes, salt)
    
    # Trả về dạng string để lưu vào Database dễ dàng
    return hashed_bytes.decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """So khớp mật khẩu nhập vào với mã băm trong DB"""
    return bcrypt.checkpw(
        plain_password.encode('utf-8'),
        hashed_password.encode('utf-8')
    )

def create_access_token(data: dict) -> str:
    """Tạo JWT Token"""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt