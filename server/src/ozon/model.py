from datetime import datetime

from sqlalchemy import ARRAY, ForeignKey, String, BIGINT
from sqlalchemy.orm import Mapped, mapped_column, relationship

from server.src.database import Base


class OzonItem(Base):
    __tablename__ = "ozon_marked_item"
    
    id: Mapped[int] = mapped_column(BIGINT, primary_key=True, unique=True)
    title: Mapped[str]
    url: Mapped[str]
    price: Mapped[int]
    image: Mapped[str] = mapped_column(String(128))
    description: Mapped[str]
    year: Mapped[int]
    paper_type: Mapped[str]
    preview_type: Mapped[str]
    book_type: Mapped[str]
    pages_count: Mapped[int]
    circulation: Mapped[int]
    isbn: Mapped[list[str]] = mapped_column(ARRAY(String))
    class_: Mapped[int] = mapped_column(name="class")
    subject: Mapped[str]
    original_name: Mapped[str]
    author: Mapped[list[str]] = mapped_column(ARRAY(String))
    seller_id: Mapped[int] = mapped_column(
        ForeignKey("ozon_seller.id")
    )
    days_to_deliver: Mapped[int]
    warehouse_type: Mapped[str] = mapped_column(String(4))
    available: Mapped[bool] = mapped_column(default=True)
    is_fake_model: Mapped[bool] = mapped_column(nullable=False)
    agree: Mapped[int] = mapped_column(default=0)
    disagree: Mapped[int] = mapped_column(default=0)
    
    seller = relationship("OzonSeller", back_populates="items")
    

class OzonSeller(Base):
    __tablename__ = "ozon_seller"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    reg_date: Mapped[datetime]
    orders: Mapped[int]
    avg_item_rate: Mapped[float]
    region: Mapped[str]
    
    items = relationship("OzonItem", back_populates="seller")