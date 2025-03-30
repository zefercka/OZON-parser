from patchright.sync_api import sync_playwright, Locator
from threading import Event
import re

from sqlalchemy import create_engine, String, ARRAY, Integer
from sqlalchemy.orm import declarative_base, sessionmaker, Mapped, mapped_column

from typing import List

from uuid import uuid4
import requests

# DataBase
Base = declarative_base()
class Item(Base):
    __tablename__ = "education_seller"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str]
    url: Mapped[str]
    price: Mapped[int]
    image: Mapped[str] = mapped_column(String(128))
    desciption: Mapped[str]
    year: Mapped[int]
    papper_type: Mapped[str]
    preview_type: Mapped[str]
    book_type: Mapped[str]
    pages_count: Mapped[int]
    circulation: Mapped[int]
    isbn: Mapped[list[int]] = mapped_column(ARRAY(Integer))
    class_: Mapped[int] = mapped_column(name="class")
    subject: Mapped[str]
    original_name: Mapped[str]
    author: Mapped[list[str]] = mapped_column(ARRAY(String))
    

engine = create_engine('postgresql://postgres:postgres@localhost:5432/OZON_parse')
Session = sessionmaker(engine, expire_on_commit=True)


def parse_item(item: Locator):
    url = item.locator(".oj3_25").get_attribute("href")
    price = int(
        "".join(re.findall("\d+", item.locator(".c3025-a0").inner_text().split('\n')[0]))
    )
    title = item.locator(".mj9_25").first.locator(".bq017-a.bq017-a4.bq017-a6.nj2_25").first.text_content()
    
    image_url = item.locator(".o0j_25 img").get_attribute("src")
    print(image_url)
    
    image_name = uuid4()
    
    download_preview(image_url, f"{image_name}_0.jpg")
    
    with Session() as session:
        session.add(Item(
            title=title, url=url, price=price, image=image_name
        ))
        session.commit()


def download_preview(url: str, img_name: str):
    r = requests.get(url)
    with open(f"images/{img_name}", 'wb') as file:
        file.write(r.content)


# Parser       
def parser(urls: list[str]):                                        
    with sync_playwright() as p:                   
        browser = p.chromium.launch_persistent_context(
            headless=False,
            user_data_dir="./data",
        )
        page = browser.new_page()
        
        for url in urls:
            page.goto(f"https://www.ozon.ru{url}")
        
            page.screenshot(path="screenshot.png")
        
            print(page.title())
            while "OZON" not in page.title():
                Event().wait(2)
            
            desc = ""
            for desc_item in page.locator("#section-description").all():
                desc += desc_item.locator(".RA-a1").text_content() + "\n"
                
            year = \
                page.locator('//*[@id="section-characteristics"]/div[2]/div/div[1]/dl[3]/dd').first.inner_text()
            
            
            print(desc)
            print(year)

        Event().wait(5)
        browser.close()
        
parser([
    # "/product/matematika-proverochnye-raboty-2-klass-fgos-shkola-rossii-volkova-svetlana-ivanovna-1218537971/?_bctx=CAQQkdMM&at=Rlty4gOJWcOPO02EcDNNrANh1j11vDcBOj9ZkulvzyAM&hs=1"
    "/product/russkiy-yazyk-7-klass-uchebnik-chast-2-baranov-m-ladyzhenskaya-taisa-alekseevna-584734710/?_bctx=CAQQ"
])