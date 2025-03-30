from patchright.sync_api import sync_playwright, Locator
from threading import Event
import re

from sqlalchemy import create_engine, String
from sqlalchemy.orm import declarative_base, sessionmaker, Mapped, mapped_column

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
with sync_playwright() as p:                   
    browser = p.chromium.launch_persistent_context(
        headless=False,
        user_data_dir="./data",
    )
    page = browser.new_page()
    
    page.goto(
        # "https://www.ozon.ru/search/?deny_category_prediction=true&from_global=true&publisher=856042"
        "https://www.ozon.ru/seller/izdatelstvo-prosveshchenie-207249/brand/prosveshchenie-85936429/?miniapp=seller_207249"
    )
    
    page.screenshot(path="screenshot.png")
    
    print(page.title())
    while "OZON" not in page.title():
        Event().wait(2)

    # l = page.locator(".aea2_34")   
    # count = int("".join(re.findall('\d+', l.inner_text())))
    # print(count)
    
    count = 5000
    parsed = 0

    for item in page.locator(".mj8_25").all():
        parse_item(item)
        parsed += 1
    
    item.scroll_into_view_if_needed()

    parsed_page = 0
    while count > parsed:
        print("while")
        items_page_item = page.locator(f".a4ea_34 > div[data-index='{parsed_page}']")
        if items_page_item.count() > 0:
            items = items_page_item.locator(".mj8_25").all()
            
            items[-1].scroll_into_view_if_needed()
            for item in items:
                parse_item(item)
                    
                parsed += 1
                print(parsed)
            
            parsed_page += 1

    Event().wait(5)
    browser.close()