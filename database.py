from sqlalchemy import create_engine, String, ARRAY, ForeignKey
from sqlalchemy.orm import (declarative_base, sessionmaker, Mapped, 
                            mapped_column, relationship)

from datetime import datetime

Base = declarative_base()


class Item(Base):
    __tablename__ = "education_seller"
    
    id: Mapped[int] = mapped_column(primary_key=True)
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
        ForeignKey("seller.id")
    )
    
    seller = relationship("Seller", back_populates="items")
    
    def dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "url": self.url,
            "price": self.price,
            "image": self.image,
            "description": self.description,
            "year": self.year,
            "paper_type": self.paper_type,
            "preview_type": self.preview_type,
            "book_type": self.book_type,
            "pages_count": self.pages_count,
            "circulation": self.circulation,
            "isbn": self.isbn,
            "class_": self.class_,
            "subject": self.subject,
            "original_name": self.original_name,
            "author": self.author,
            "seller_id": self.seller_id
        }
    

class Seller(Base):
    __tablename__ = "seller"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    reg_date: Mapped[datetime]
    orders: Mapped[int]
    avg_item_rate: Mapped[float]
    region: Mapped[str]
    
    items = relationship("Item", back_populates="seller")


engine = create_engine('postgresql://postgres:postgres@localhost:5432/OZON_parse')
Session = sessionmaker(engine, expire_on_commit=True)