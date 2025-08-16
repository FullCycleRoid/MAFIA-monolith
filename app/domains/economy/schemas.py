from pydantic import BaseModel


class PurchaseRequest(BaseModel):
    item_type: str  # skin, language
    item_id: str
    price: int
