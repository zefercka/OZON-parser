from datetime import datetime, timedelta
from threading import Event, Thread
from uuid import uuid4

import qwen_integration
import re
from database import Item, Seller, Session
from patchright._impl._errors import TimeoutError
from patchright.sync_api import Page, sync_playwright
# from patchright.async_api import async_playwright, Page

base_url = "https://www.ozon.ru"
base_seller_url = "https://www.ozon.ru/seller"

def parse_seller(page: Page, seller_id: int) -> dict:
    try:
        page.goto(f"{base_seller_url}/{seller_id}/products")
    except TimeoutError:
        return
    
    Event().wait(1)
    
    data = {
        "id": seller_id
    }
    
    page.locator(".y9h_20 button.ag90-a0").last.click()
    
    seller_info = page.locator(".bq020-a:has-text('Работает согласно графику Ozon')").locator("xpath=..").locator(".bq020-a").first.text_content()
    seller_info = seller_info.split()
    
    org_type = seller_info[0]
    
    if org_type.lower() == "ип":
        id = re.sub(r"\D", '', seller_info[-1])
        print(id)
        seller_info = qwen_integration.get_ip_info(id)
    else:
        seller_info = " ".join(seller_info)
    
    data["region"] = seller_info
    
    with Session() as session:
        session.query(Seller).filter(Seller.id == seller_id).update(data)
        session.commit()
        
        
with Session() as session:
    sellers = session.query(Seller).filter(Seller.region == "Адрес").all()
    
    
with sync_playwright() as p:
    browser = p.chromium.launch_persistent_context(
        headless=False,
        user_data_dir="data_4",
        no_viewport=True,
    )
    
    page = browser.new_page()
    
    for seller in sellers:
        seller_id = seller.id
        
        parse_seller(page, seller_id)
        
    browser.close()