from datetime import datetime, timedelta
from threading import Event, Thread
from uuid import uuid4

import qwen_integration
import re
from database import Item, Seller, Session
from patchright._impl._errors import TimeoutError
from patchright.sync_api import Page, sync_playwright

from sqlalchemy import and_

base_url = "https://www.ozon.ru"
base_seller_url = "https://www.ozon.ru/seller"


months = {
    "января": 1,
    "февраля": 2,
    "марта": 3,
    "апреля": 4,
    "мая": 5,
    "июня": 6,
    "июля": 7,
    "августа": 8,
    "сентября": 9,
    "октября": 10,
    "ноября": 11,
    "декабря": 12
}


def split_list_into_n_parts(lst: list, n: int) -> tuple[list, ...]:
    """
    Разделяет список на n частей. Если длина списка не делится на n нацело,
    первые несколько частей будут немного больше.

    :param lst: Исходный список
    :param n: Количество частей
    :return: Кортеж из n списков
    """
    
    if n <= 0:
        raise ValueError("Количество частей должно быть положительным числом.")
    
    length = len(lst)
    base_size = length // n  # Базовый размер каждой части
    remainder = length % n  # Остаток, который нужно распределить

    parts = []
    start = 0

    for i in range(n):
        # Размер текущей части: базовый размер + 1, если есть остаток
        part_size = base_size + (1 if i < remainder else 0)
        end = start + part_size
        parts.append(lst[start:end])
        start = end

    return tuple(parts)


def get_seller_info(page: Page, seller_id: int) -> dict:
    try:
        page.goto(f"{base_seller_url}/{seller_id}/products")
    except TimeoutError:
        return
    
    data = {
        "id": seller_id
    }
    
    try:
        page\
            .locator("[data-widget='sellerTransparency']")\
            .locator("xpath=div[2]/button[last()]")\
                .click()
    except:
        print("no seller transperecy", page.url)
        return
    
    modal_layout_item = page.locator("[data-widget='modalLayout']")
    cell_list_item = modal_layout_item\
        .locator("[data-widget='cellList']")\
        .locator("xpath=div[1]")
    
    work_time_l = cell_list_item\
        .locator("div:has-text('Работает с Ozon')")\
            .first\
        .locator("xpath=div[3]")\
            .text_content().lower().split()
    
    if "дн" in work_time_l[1]:
        work_time = timedelta(days=int(work_time_l[0]))
    elif "мес" in work_time_l[1]:
        work_time = timedelta(days=30.4 * int(work_time_l[0]))
    else:
        work_time = timedelta(days=365 * int(work_time_l[0]))
    
    data["reg_date"] = datetime.now() - work_time
    
    orders_count_div = cell_list_item\
        .locator("div:has-text('Заказов')")\
            .first\
        .locator("xpath=div[3]")
    if orders_count_div.count() > 0:
        orders_count = orders_count_div.first.text_content().lower().split()
        orders_count[0] = orders_count[0].replace(',', '.')

        if len(orders_count) > 1:
            if orders_count[1].lower() == "m":
                orders_count = float(orders_count[0]) * 1_000_000
            elif orders_count[1].lower() == "k":
                orders_count = float(orders_count[0]) * 1_000
            else:
                orders_count = int(''.join(orders_count))
        else:
            orders_count = float(orders_count[0])
        
        data["orders"] = int(orders_count)
    
    avg_rate_div = cell_list_item\
        .locator("div:has-text('Средняя оценка товаров')")\
            .first\
        .locator("xpath=div[3]")
    if avg_rate_div.count() > 0:
        avg_rate = avg_rate_div.first.text_content().split()[0].replace(',', '.')
        data["avg_item_rate"] = float(avg_rate)
    
    
    seller_info = modal_layout_item.locator(
        "[data-widget='textBlock']"
    ).last.locator(
        "xpath=div[1]/div[1]/div[1]"
    ).text_content()
        
    if seller_info.split()[0].lower() == "ип":
        id = re.sub(r"\D", '', seller_info.split()[-1])
        seller_info = qwen_integration.get_ip_info(id)
    
    data["region"] = seller_info
    
    return data


def get_seller_id(page: Page) -> int | None:
    try:
        is_ozon_1 = page\
            .locator("[data-widget='webCurrentSeller']")\
            .locator("div:has-text('Продавец')")\
            .last\
            .locator("xpath=..")\
            .locator("div:has-text('Ozon')")\
            .count() > 0

        is_ozon_2 = page\
            .locator("[data-widget='webCurrentSeller']")\
            .locator("span:has-text('Магазин')")\
            .locator("xpath=../div[1]")\
            .locator("span:has-text('Ozon')")\
            .count() > 0

        if is_ozon_1 or is_ozon_2:
            return None
        
        seller_url = page\
            .locator("[data-widget='webStickyProducts']")\
                .first\
            .locator("a[href*='seller']")\
                .first.get_attribute("href")
        
        if seller_url:
            seller_id = seller_url.split('/')[2]
            
        return int(seller_id)
    except Exception as err:
        print("no shop item", page.url)
        print(err)
        

def get_description_text(page: Page) -> str:
    try:
        page.locator("#section-description").first.scroll_into_view_if_needed()
        
        desc = ""
        for desc_item in page.locator("#section-description").all():
                desc += desc_item.text_content().lower().strip("описание").strip("автор на обложке") + ' '
        
        return desc
    except TimeoutError:
        page.locator("footer").scroll_into_view_if_needed()
        return ''


def get_product_information(page: Page) -> dict:
    data = {}
    
    year_item = page.locator("dt:has-text('Год выпуска')")
    if year_item.count() > 0:
        data["year"] = int(year_item.locator("xpath=../dd").text_content())
        
    paper_type_item = page.locator("dt:has-text('Тип бумаги в книге')")
    if paper_type_item.count() > 0:
        data["paper_type"] = paper_type_item.first.locator("xpath=../dd").text_content()
        
    preview_type_item = page.locator("dt:has-text('Тип обложки')")
    if preview_type_item.count() > 0:
        data["preview_type"] = preview_type_item.first.locator("xpath=../dd").text_content()
        
    book_type_item = page.locator("dt:has-text('Тип книги')")
    if book_type_item.count() > 0:
        data["book_type"] = book_type_item.first.locator("xpath=../dd").text_content()
        
    pages_count_item = page.locator("dt:has-text('Количество страниц')")
    if pages_count_item.count() > 0:
        data["pages_count"] = int(
            pages_count_item.first.locator("xpath=../dd").text_content()
        )
        
    isbn_item = page.locator("dt:has-text('ISBN')")
    if isbn_item.count() > 0:
        isbns = isbn_item.first.locator("xpath=../dd").text_content().split(",")
        isbns = [i.replace('-', '').strip() for i in isbns]
        data["isbn"] = isbns
        
    class_item = page.locator("dt:has-text('Класс')")
    if class_item.count() > 0:
        data["class_"] = int(
            re.sub(
                r"\D", '', class_item.first.locator("xpath=../dd").text_content()
            )
        )
    
    subject_item = page.locator("dt:has-text('Предмет обучения')")
    if subject_item.count() > 0:
        data["subject"] = subject_item.locator("xpath=../dd").text_content()
        
    original_name_item = page.locator("dt:has-text('Оригинальное название')")
    if original_name_item.count() > 0:
        data["original_name"] = original_name_item.locator("xpath=../dd").text_content()
        
    author_item = page.locator("dt:has-text('Автор')")
    if author_item.count() > 0:
        authors = author_item.locator("xpath=../dd").text_content().split(",")
        authors = [i.strip() for i in authors]
        data["author"] = authors
    
    return data


def get_days_to_deliver(page: Page) -> int:
    try:
        Event().wait(0.5)
        
        deliver_date_text = page.locator(
            "[data-widget='webAddToCart']"
        ).first.locator(
            "xpath=div[1]/div[1]/div[1]"
        ).locator("span").first.text_content().lower()
        
        date = re.sub(r"(доставим|после|доставка|с)\s*|[.,!?;]", '', deliver_date_text)
        
        if "личный кабинет" in date:
            days_to_deliver = -1
        elif date == "завтра":
            days_to_deliver = 1
        elif date == "послезавтра":
            days_to_deliver = 2
        else:
            date = date.split()
            
            month = months.get(date[1])
            day = int(date[0])
            year = datetime.now().year
            date_obj = datetime(year=year, month=month, day=day)
            
            days_to_deliver = (date_obj - datetime.now()).days + 1
        
        return days_to_deliver
    except Exception as err:
        print("No deliver date", page.url)
        print(err)


def get_warehouse_type(page: Page) -> str:
    try:
        warehouse_type_item = page.locator(
            "h2:has-text('Информация о доставке')"
        ).locator(
            "xpath=../div[1]/div[1]/button[1]/span[1]/div[1]/span[1]/span[2]"
        )
        
        if warehouse_type_item.count() > 0:
            warehouse_type_text = warehouse_type_item.text_content().lower()
        else:
            warehouse_type_text = "fbs"
        
        if "ozon" in warehouse_type_text:
            return "ozon"
        else:
            return "fbs"

    except Exception as err:
        print("can't get warehouse type", page.url)
        print(err)


# Parser       
def parser(items: list[Item], user_dir_path: str = "./data_0"):                                      
    with sync_playwright() as p:
        browser = p.chromium.launch_persistent_context(
            headless=False,
            user_data_dir=user_dir_path,
            no_viewport=True,
        )
        
        page = browser.new_page()
        
        # seller_id = 52057
        # print(get_seller_info(page, seller_id))
        
        # browser.close()
        
        # return

        for item in items:
            url = item.url
            
            try:
                page.goto(f"{base_url}{url}")
            except TimeoutError:
                continue
        
            while "OZON" not in page.title():
                Event().wait(0.5)
                
            product_is_over = page.locator("h2:has-text('Этот товар закончился')").count()
            product_is_deleted = page.locator("h2:has-text('Такой страницы не существует')").count()
            product_is_unavailable = page.locator("h2:has-text('Товар не доставляется в ваш регион')").count()
            
            if product_is_deleted or product_is_over or product_is_unavailable:
                with Session() as session:
                    session.query(Item).filter(Item.url == url).update({"available": False})
                    session.commit()
                
                continue
            
            data = {}
            data = {
                "url": url
            }
            
            data["description"] = get_description_text(page)
            
            data.update(get_product_information(page))
            
            seller_id = get_seller_id(page)
            if seller_id:
                data["seller_id"] = seller_id

            data["days_to_deliver"] = get_days_to_deliver(page)
            
            data["warehouse_type"] = get_warehouse_type(page)
            
            
            if "seller_id" in data:
                with Session() as session:
                    seller = session.query(Seller).filter(Seller.id == data["seller_id"]).first()
                    
                if seller is None:
                    seller_info = get_seller_info(page, data["seller_id"])
                    with Session() as session:
                        session.add(Seller(
                            **seller_info
                        ))
                        session.commit()
            else:
                print(f"no seller info for url {url}")
            
            if "url" in data:
                with Session() as session:
                    session.query(Item).filter(Item.url == url).update(data)
                    session.commit()
            
        browser.close()
      
      
with Session() as session:
    # items = session.query(Item).filter(Item.description == None).all()
    items = session.query(Item).filter(and_(Item.warehouse_type == None, Item.available == True)).all()

count = len(items)

# items = [session.query(Item).fi
# items[0].url = "/product/angliyskiy-yazyk-uchebnoe-posobie-dlya-nachinayushchih-2014437467/?at=ywtAO9jp0hgzongVHVOqnv5IRwpArgcXlVAWEcyAMrq"
# items[0].url = "/product/okruzhayushchiy-mir-2-klass-rabochie-tetradi-k-novomu-fp-komplekt-iz-2-h-chastey-fgos-pleshakov-922338721/"

# 3e3caeca-ea35-4615-a6c6-d7cad48d663b
# 8aab1a1a-ef05-4392-968d-1e2d29e7bb07 
# b76ed641-c5f5-4fc7-bdb8-d17e5091f789
# 162c2378-6bb9-4df3-a188-c126f8a9218d
# f66be52c-615f-4b60-9291-383dafa6ecb1

threads: list[Thread] = []
threads_count = 1
split_threads = split_list_into_n_parts(items, threads_count)
for i, items_to_thread in enumerate(split_threads):
    print(len(items_to_thread))
    
    # user_dir_path = f"./data_{i}"
    user_dir_path = "data_4"
    t = Thread(target=parser, args=(items_to_thread, user_dir_path))
    threads.append(t)
    t.start()

for i in threads:
    i.join()