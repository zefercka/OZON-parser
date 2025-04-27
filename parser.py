from patchright.sync_api import sync_playwright, Locator, Page
from threading import Event
import re

from database import Item, Seller, Session

from uuid import uuid4
import requests


def parse_item(item: Locator):
    item_data = {}
    
    try:
        url = item.locator("a").first.get_attribute("href").split("?")[0]
        item_data["url"] = url
    except Exception as err:
        print(err)
    
    try:  
        with Session() as session:
            is_item_already_parsed = session.query(Item).where(Item.url == url).count()
        if is_item_already_parsed > 0:
            return
    except Exception as err:
        print(err)
        return
    
    try:
        price = int(
            "".join(
                re.findall(
                    r"\d+",
                    item.locator("xpath=div[1]/div[1]/div[1]/span[1]").text_content()
                )
            )
        )
        item_data["price"] = price
    except Exception as err:
        print(err)

    
    title = item.locator("xpath=div[1]/a[1]").text_content()
    item_data["title"] = title
    
    image_url = item.locator("xpath=a[1]//img").get_attribute("src")
    
    image_name = uuid4()
    item_data["image"] = image_name
    
    # print(item_data)
    
    download_preview(image_url, f"{image_name}_0.jpg")
    
    with Session() as session:
        session.add(Item(
            **item_data
        ))
        session.commit()


def download_preview(url: str, img_name: str):
    r = requests.get(url)
    with open(f"images/{img_name}", 'wb') as file:
        file.write(r.content)
    

def parse_search_page(page: Page):
    # l = page.locator(".aea2_34")   
    # count = int("".join(re.findall('\d+', l.inner_text())))
    
    count = 5000
    parsed = 0
    
    while page.locator(
        "#contentScrollPaginator"
    ).locator(
        "xpath=div[1]"
    ).locator(
        ".tile-root"
    ).count() == 0:
        Event().wait(0.5)

    
    for item in page.locator(
        "#contentScrollPaginator"
    ).locator(
        "xpath=div[1]"
    ).locator(
        ".tile-root"
    ).all():
        parse_item(item)
        parsed += 1
    
    item.scroll_into_view_if_needed()

    parsed_page = 0
    while count > parsed:
        paginator_page_item = page.locator(
            f"""xpath=//*[@id="contentScrollPaginator"]/div[2]/*[./div[@data-index="{parsed_page}"]][1]"""
        )
        
        i = 0
        while paginator_page_item.count() == 0 and i < 100:
            paginator_page_item = page.locator(
                f"""xpath=//*[@id="contentScrollPaginator"]/div[2]/*[./div[@data-index="{parsed_page}"]][1]"""
            )
            i += 1
            Event().wait(0.1)
        
        if i == 100:
            print("Couldn't get page for parsing")
        
        items_page_items = paginator_page_item.locator(
            ".tile-root"
        )
        
        count_items = items_page_items.count()
        
        for i in range(count_items):
            item = items_page_items.nth(i)
            parse_item(item)
            parsed += 1
            
        print("parsed", parsed)
            
        item.scroll_into_view_if_needed()
        
        parsed_page += 1

    
def parser(url: str, user_dir_path: str = "./data_4"):
    with sync_playwright() as p:
        browser = p.chromium.launch_persistent_context(
            headless=False,
            user_data_dir=user_dir_path,
        )
        page = browser.new_page()
        
        page.goto(url)
        
        while "OZON" not in page.title():
            Event().wait(0.5)
        
        parse_search_page(page)

        browser.close()
        

parser(
    url="https://www.ozon.ru/category/knigi-16500/prosveshchenie-85936429/?__rr=3&publisher=856042&sorting=discount"
)