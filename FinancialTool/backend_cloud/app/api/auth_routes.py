from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from backend_cloud.app.database.base import get_db
from backend_cloud.app.database.models import User, VirtualWallet
from backend_cloud.app.schemas.auth import UserCreate, UserLogin, TokenResponse
from backend_cloud.app.core.security import get_password_hash, verify_password, create_access_token
from backend_cloud.app.api.deps import get_current_user

router = APIRouter(prefix="/api/auth", tags=["Authentication"])

@router.post("/register", response_model=TokenResponse)
def register_user(user_in: UserCreate, db: Session = Depends(get_db)):
    """Đăng ký tài khoản mới và cấp ngay 10,000$ tiền ảo"""
    
    # 1. Kiểm tra email đã tồn tại chưa
    user_exists = db.query(User).filter(User.email == user_in.email).first()
    if user_exists:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email đã được sử dụng."
        )

    # 2. Băm mật khẩu và tạo User mới
    hashed_password = get_password_hash(user_in.password)
    new_user = User(
        email=user_in.email,
        password_hash=hashed_password,
        is_active=True
        # role_id = 1 (Bạn có thể set default role ở đây sau này)
    )
    
    db.add(new_user)
    db.commit() # Lưu User để lấy được ID
    db.refresh(new_user)

    # 3. TẠO VÍ TIỀN ẢO TỰ ĐỘNG CHO USER
    new_wallet = VirtualWallet(
        user_id=new_user.id,
        balance=10000.00,
        equity=10000.00
    )
    db.add(new_wallet)
    db.commit()

    # 4. Tự động đăng nhập và trả về Token
    access_token = create_access_token(data={"sub": str(new_user.id)})
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/login", response_model=TokenResponse)
def login_user(user_in: UserLogin, db: Session = Depends(get_db)):
    """Đăng nhập và nhận JWT Token"""
    
    # 1. Tìm User theo email
    user = db.query(User).filter(User.email == user_in.email).first()
    
    # 2. Kiểm tra sự tồn tại và so khớp mật khẩu
    if not user or not verify_password(user_in.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email hoặc mật khẩu không chính xác."
        )

    # 3. Tạo Token
    access_token = create_access_token(data={"sub": str(user.id)})
    return {"access_token": access_token, "token_type": "bearer"}
