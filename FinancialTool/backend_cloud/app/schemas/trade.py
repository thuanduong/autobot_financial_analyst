from pydantic import BaseModel
from typing import Optional

class OrderCreate(BaseModel):
    symbol: str
    order_type: str # "BUY" hoặc "SELL"
    volume: float   # Khối lượng Lot (VD: 0.1)

class OrderClose(BaseModel):
    order_id: int

class SymbolConfigBase(BaseModel):
    symbol: str
    contract_size: float
    base_leverage: int
    is_active: bool = True

class SymbolConfigCreate(SymbolConfigBase):
    pass

class SymbolConfigUpdate(BaseModel):
    contract_size: Optional[float] = None
    base_leverage: Optional[int] = None
    is_active: Optional[bool] = None