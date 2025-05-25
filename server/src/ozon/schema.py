from pydantic import BaseModel
from typing import Optional


class CheckUrl(BaseModel):
    url: str
    

class Feedback(BaseModel):
    agree: bool
    
    
class OzonItem(BaseModel):
    id: int
    title: str
    url: str
    price: int
    image: str
    authors: Optional[list[str]]
    is_fake: bool