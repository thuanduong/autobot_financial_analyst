from fastapi import APIRouter, Depends
from backend_cloud.app.database.models import User
from backend_cloud.app.api.deps import get_current_user

router = APIRouter(prefix="/api/user", tags=["User Info"])

# 🔒 ĐÂY LÀ ROUTE ĐƯỢC BẢO VỆ
@router.get("/me")
def get_my_profile(current_user: User = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "email": current_user.email,
        "created_at": current_user.created_at,
        "wallet": {
            "balance": float(current_user.wallet.balance) if current_user.wallet else 0.0,
            "equity": float(current_user.wallet.equity) if current_user.wallet else 0.0
        }
    }