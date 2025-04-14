from datetime import datetime, timedelta
from threading import Event, Thread
from uuid import uuid4

import qwen_integration
import re
from database import Item, Seller, Session
from patchright._impl._errors import TimeoutError
from patchright.sync_api import Page, sync_playwright

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


def parse_seller(page: Page, seller_id: int) -> dict:
    try:
        page.goto(f"{base_seller_url}/{seller_id}/products")
    except TimeoutError:
        return
    
    data = {
        "id": seller_id
    }
    
    page.locator(".y9h_20 button.ag90-a0").last.click()
    
    work_time_l = page.locator(".b390-a:has-text('Работает с Ozon')").locator(".b390-a5").text_content().lower().split()
    
    if "дн" in work_time_l[1]:
        work_time = timedelta(days=int(work_time_l[0]))
    elif "мес" in work_time_l[1]:
        work_time = timedelta(days=30.4 * int(work_time_l[0]))
    else:
        work_time = timedelta(days=365 * int(work_time_l[0]))
    
    data["reg_date"] = datetime.now() - work_time
    
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
        
    
    orders_count_div = page.locator(".b390-a:has-text('Заказов')").locator(".b390-a5")
    if orders_count_div.count() > 0:
        orders_count = orders_count_div.first.text_content().split()
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
        
        print(seller_id)
        print(orders_count)
        data["orders"] = int(orders_count)
    
    avg_rate_div = page.locator(".b390-a:has-text('Средняя оценка товаров')").locator(".b390-a5")
    if avg_rate_div.count() > 0:
        avg_rate = avg_rate_div.first.text_content().split()[0].replace(',', '.')
        data["avg_item_rate"] = float(avg_rate)
    
    return data
     

# Parser       
def parser(items: list[Item], user_dir_path: str = "./data_0"):                                      
    with sync_playwright() as p:
        browser = p.chromium.launch_persistent_context(
            headless=False,
            user_data_dir=user_dir_path,
            no_viewport=True,
        )
        
        page = browser.new_page()
        
        for item in items:
            url = item.url
            # print(url)
            
            try:
                page.goto(f"{base_url}{url}")
            except TimeoutError:
                continue
        
            while "OZON" not in page.title():
                Event().wait(0.5)
                
            
            product_is_over = page.locator("h2:has-text('Этот товар закончился')").count()
            if product_is_over != 0:
                continue
        
            product_is_deleted = page.locator("h2:has-text('Такой страницы не существует')").count()
            if product_is_deleted != 0:
                continue
            
            product_is_unavailable = page.locator("h2:has-text('Товар не доставляется в ваш регион')").count()
            if product_is_unavailable != 0:
                continue
            
            data = {}
            data = {
                "url": url
            }
            
            # try:
            #     page.locator("#section-description").first.scroll_into_view_if_needed()
                
            #     desc = ""
            #     for desc_item in page.locator("#section-description").all():
            #         if desc_item.locator(".RA-a1").count() > 0:
            #             desc += desc_item.locator(".RA-a1").text_content() + ' '
                
            #     data["description"] = desc
            # except TimeoutError:
            #     page.locator("footer").scroll_into_view_if_needed()
                
            # year_item = page.locator("dt:has-text('Год выпуска')")
            # if year_item.count() > 0:
            #     data["year"] = int(year_item.locator("xpath=../dd").text_content())
                
            # paper_type_item = page.locator("dt:has-text('Тип бумаги в книге')")
            # if paper_type_item.count() > 0:
            #     data["paper_type"] = paper_type_item.locator("xpath=../dd").text_content()
                
            # preview_type_item = page.locator("dt:has-text('Тип обложки')")
            # if preview_type_item.count() > 0:
            #     data["preview_type"] = preview_type_item.locator("xpath=../dd").text_content()
                
            # book_type_item = page.locator("dt:has-text('Тип книги')")
            # if book_type_item.count() > 0:
            #     data["book_type"] = book_type_item.locator("xpath=../dd").text_content()
                
            # pages_count_item = page.locator("dt:has-text('Количество страниц')")
            # if pages_count_item.count() > 0:
            #     data["pages_count"] = int(pages_count_item.locator("xpath=../dd").text_content())
                
            # isbn_item = page.locator("dt:has-text('ISBN')")
            # if isbn_item.count() > 0:
            #     isbns = isbn_item.locator("xpath=../dd").text_content().split(", ")
            #     isbns = [i.replace('-', '') for i in isbns]
            #     data["isbn"] = isbns
                
            # class_item = page.locator("dt:has-text('Класс')")
            # if class_item.count() > 0:
            #     data["class_"] = int(class_item.locator("xpath=../dd").text_content().split()[0])
            
            # subject_item = page.locator("dt:has-text('Предмет обучения')")
            # if subject_item.count() > 0:
            #     data["subject"] = subject_item.locator("xpath=../dd").text_content()
                
            # original_name_item = page.locator("dt:has-text('Оригинальное название')")
            # if original_name_item.count() > 0:
            #     data["original_name"] = original_name_item.locator("xpath=../dd").text_content()
                
            # author_item = page.locator("dt:has-text('Автор')")
            # if author_item.count() > 0:
            #     authors = author_item.locator("xpath=../dd").text_content().split(", ")
            #     data["author"] = authors
            
            try:
                Event().wait(0.5)
                
                deliver_date_text = page.locator("span:has-text('Завтра')")
                if page.locator("span:has-text('Завтра')").count() > 0:
                    deliver_date_text = deliver_date_text.first.text_content().lower()          
                else:
                    deliver_date_text = page.locator("span:has-text('Доставим')").first.text_content().lower()
                
                date = deliver_date_text.replace("доставим", '').replace('с', '').replace("завтра,", '').replace("поле", '').strip()
                
                print("---------")
                print(date)
                print("---------")
                if date in ["завтра", "завтра,"]:
                    days_to_deliver = 1
                elif date in ["послезавтра", "послезавтра,"]:
                    days_to_deliver = 2
                else:
                    date = date.split()
                    
                    month = months.get(date[1])
                    day = int(date[0])
                    year = datetime.now().year
                    date_obj = datetime(year=year, month=month, day=day)
                    
                    days_to_deliver = (date_obj - datetime.now()).days + 1
                
                data["days_to_deliver"] = days_to_deliver
            except Exception as err:
                print(err)
                print("No deliver date")
                
            try:
                seller_url = page.locator(".k0p_28").first.get_attribute("href")
                seller_id = seller_url.split('/')[2]
                
                data["seller_id"] = int(seller_id)
                
            except Exception as err:
                print("no shop item")
                print(err)
                
            print(data)
            
            if "seller_id" in data:
                with Session() as session:
                    seller = session.query(Seller).filter(Seller.id == data["seller_id"]).first()
                    
                if seller is None:
                    seller_info = parse_seller(page, seller_id)
                    with Session() as session:
                        session.add(Seller(
                            **seller_info
                        ))
                        session.commit()
                        
                if "url" in data:
                    # print(data)
                    with Session() as session:
                        session.query(Item).filter(Item.url == url).update(data)
                        session.commit()
            else:
                print(f"no seller info for url {url}")
            
        browser.close()
      
      
with Session() as session:
    # items = session.query(Item).filter(Item.description == None).all()
    items = session.query(Item).filter(Item.days_to_deliver == None).all()

count = len(items)

# parser(urls, "data_0")

# items = [session.query(Item).fi
# items[0].url = "/product/angliyskiy-yazyk-uchebnoe-posobie-dlya-nachinayushchih-2014437467/?at=ywtAO9jp0hgzongVHVOqnv5IRwpArgcXlVAWEcyAMrq"
# items[0].url = "/product/okruzhayushchiy-mir-2-klass-rabochie-tetradi-k-novomu-fp-komplekt-iz-2-h-chastey-fgos-pleshakov-922338721/"

# 3e3caeca-ea35-4615-a6c6-d7cad48d663b
# 8aab1a1a-ef05-4392-968d-1e2d29e7bb07 
# b76ed641-c5f5-4fc7-bdb8-d17e5091f789
# 162c2378-6bb9-4df3-a188-c126f8a9218d

threads: list[Thread] = []
threads_count = 4
split_threads = split_list_into_n_parts(items, threads_count)
for i, items_to_thread in enumerate(split_threads):
    print(len(items_to_thread))
    
    user_dir_path = f"./data_{i}"
    t = Thread(target=parser, args=(items_to_thread, user_dir_path))
    threads.append(t)
    t.start()

for i in threads:
    i.join()

    
# parser([
#     "/product/matematika-proverochnye-raboty-2-klass-fgos-shkola-rossii-volkova-svetlana-ivanovna-1218537971/?_bctx=CAQQkdMM&at=Rlty4gOJWcOPO02EcDNNrANh1j11vDcBOj9ZkulvzyAM&hs=1"
#     # "/product/russkiy-yazyk-7-klass-uchebnik-chast-2-baranov-m-ladyzhenskaya-taisa-alekseevna-584734710/?_bctx=CAQQ"
# ])