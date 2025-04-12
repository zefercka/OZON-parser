from patchright.sync_api import sync_playwright, Page
from patchright._impl._errors import TimeoutError
from threading import Event, Thread

from datetime import datetime

from database import Item, Seller, Session

from uuid import uuid4

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


def parse_page(url: list[Item], page: Page):
    for item in items:
        url = item.url
        # print(url)
        page.goto(f"https://www.ozon.ru{url}")
    
        page.screenshot(path="screenshot.png")
    
        # print(page.title())
        while "OZON" not in page.title():
            Event().wait(0.5)
            
        data = {}
        
        desc = ""
        for desc_item in page.locator("#section-description").all():
            if desc_item.locator(".RA-a1").count() > 0:
                desc += desc_item.locator(".RA-a1").text_content() + ' '
        
        data["description"] = desc
        
        page.locator("#section-description").first.scroll_into_view_if_needed()
        
        year_item = page.locator(".kr8_28:has-text('Год выпуска')")
        if year_item.count() > 0:
            data["year"] = year_item.locator("xpath=../../dd").text_content()
            
        paper_type_item = page.locator(".kr8_28:has-text('Тип бумаги в книге')")
        if paper_type_item.count() > 0:
            data["paper_type"] = paper_type_item.locator("xpath=../../dd").text_content()
            
        preview_type_item = page.locator(".kr8_28:has-text('Тип обложки')")
        if preview_type_item.count() > 0:
            data["preview_type"] = preview_type_item.locator("xpath=../../dd").text_content()
            
        book_type_item = page.locator(".kr8_28:has-text('Тип книги')")
        if book_type_item.count() > 0:
            data["book_type"] = book_type_item.locator("xpath=../../dd").text_content()
            
        pages_count_item = page.locator(".kr8_28:has-text('Количество страниц')")
        if pages_count_item.count() > 0:
            data["pages_count"] = int(pages_count_item.locator("xpath=../../dd").text_content())
            
        isbn_item = page.locator(".kr8_28:has-text('ISBN')")
        if isbn_item.count() > 0:
            isbns = isbn_item.locator("xpath=../../dd").text_content().split(", ")
            isbns = [i.replace('-', '') for i in isbns]
            data["isbn"] = isbns
            
        class_item = page.locator(".kr8_28:has-text('Класс')")
        if class_item.count() > 0:
            data["class_"] = int(class_item.locator("xpath=../../dd").text_content().split()[0])
        
        subject_item = page.locator(".kr8_28:has-text('Предмет обучения')")
        if subject_item.count() > 0:
            data["subject"] = subject_item.locator("xpath=../../dd").text_content()
            
        original_name_item = page.locator(".kr8_28:has-text('Оригинальное название')")
        if original_name_item.count() > 0:
            data["original_name"] = original_name_item.locator("xpath=../../dd").text_content()
            
        author_item = page.locator(".kr8_28:has-text('Автор')")
        if author_item.count() > 0:
            authors = author_item.locator("xpath=../../dd").text_content().split(",")
            data["author"] = authors
        
        print(data)
        
        with Session() as session:
            session.query(Item).filter(Item.url == url).update(data)
            session.commit()


def parse_seller(page: Page, seller_id: int):
    try:
        page.goto(f"{base_seller_url}/{seller_id}")
    except TimeoutError:
        return
    
    page.locator(".y9h_20 button.ag90-a0").last.click()
    
    wor = page.locator(".b390-a9:has-text('Работает с Ozon')").locator("xpath=../../../..").locator(".b390-a5").text_content()
    print(wor)
    
    Event().wait(5)
    

# Parser       
def parser(items: list[Item], user_dir_path: str = "./data_0",
           count_pages: int = 1):                                      
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
        
            # page.screenshot(path="screenshot.png")
        
            # print(page.title())
            while "OZON" not in page.title():
                Event().wait(0.5)
                
            
            product_is_over = page.locator("h2.vl1_28:has-text('Этот товар закончился')").count()
            if product_is_over != 0:
                continue
            
            data = {}
            
            try:
                desc = ""
                for desc_item in page.locator("#section-description").all():
                    if desc_item.locator(".RA-a1").count() > 0:
                        desc += desc_item.locator(".RA-a1").text_content() + ' '
                
                data["description"] = desc
                
                page.locator("#section-description").first.scroll_into_view_if_needed()
            except TimeoutError:
                page.locator("footer").scroll_into_view_if_needed()
                
            year_item = page.locator(".kr8_28:has-text('Год выпуска')")
            if year_item.count() > 0:
                data["year"] = year_item.locator("xpath=../../dd").text_content()
                
            paper_type_item = page.locator(".kr8_28:has-text('Тип бумаги в книге')")
            if paper_type_item.count() > 0:
                data["paper_type"] = paper_type_item.locator("xpath=../../dd").text_content()
                
            preview_type_item = page.locator(".kr8_28:has-text('Тип обложки')")
            if preview_type_item.count() > 0:
                data["preview_type"] = preview_type_item.locator("xpath=../../dd").text_content()
                
            book_type_item = page.locator(".kr8_28:has-text('Тип книги')")
            if book_type_item.count() > 0:
                data["book_type"] = book_type_item.locator("xpath=../../dd").text_content()
                
            pages_count_item = page.locator(".kr8_28:has-text('Количество страниц')")
            if pages_count_item.count() > 0:
                data["pages_count"] = int(pages_count_item.locator("xpath=../../dd").text_content())
                
            isbn_item = page.locator(".kr8_28:has-text('ISBN')")
            if isbn_item.count() > 0:
                isbns = isbn_item.locator("xpath=../../dd").text_content().split(", ")
                isbns = [i.replace('-', '') for i in isbns]
                data["isbn"] = isbns
                
            class_item = page.locator(".kr8_28:has-text('Класс')")
            if class_item.count() > 0:
                data["class_"] = int(class_item.locator("xpath=../../dd").text_content().split()[0])
            
            subject_item = page.locator(".kr8_28:has-text('Предмет обучения')")
            if subject_item.count() > 0:
                data["subject"] = subject_item.locator("xpath=../../dd").text_content()
                
            original_name_item = page.locator(".kr8_28:has-text('Оригинальное название')")
            if original_name_item.count() > 0:
                data["original_name"] = original_name_item.locator("xpath=../../dd").text_content()
                
            author_item = page.locator(".kr8_28:has-text('Автор')")
            if author_item.count() > 0:
                authors = author_item.locator("xpath=../../dd").text_content().split(", ")
                data["author"] = authors
            
            try:
                deliver_date_text = page.locator(".pm_28 .p8k_28").text_content().lower()
                date = deliver_date_text.replace("доставим", '').strip()
                
                if date == "завтра":
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
            
            if "seller_id" in data:
                with Session() as session:
                    seller = session.query(Seller).filter(Seller.id == data["seller_id"]).first()
                    
                    if seller is None:
                        parse_seller(page, seller_id)
                    else:
                        pass
                        # if "url" in data:
                        #     with Session() as session:
                        #         session.query(Item).filter(Item.url == url).update(data)
                        #         session.commit()
        
        # pages: list[Page] = []
        # for i in range(count_pages):
        #     pages.append(browser.new_page())
        
        # threads: list[Thread] = []
        # split_threads = split_list_into_n_parts(items, count_pages)
        # for i in range(count_pages):
        #     t = Thread(target=parse_page, args=(split_threads[i], pages[i], ))
        #     threads.append(t)
        #     t.start()
            
        # for t in threads:
        #     t.join()
            
        browser.close()
      
with Session() as session:
    items = session.query(Item).filter(Item.description == None).all()

count = len(items)     

# parser(urls, "data_0")

items = [session.query(Item).first()]
items[0].url = "/product/angliyskiy-yazyk-uchebnoe-posobie-dlya-nachinayushchih-2014437467/?at=ywtAO9jp0hgzongVHVOqnv5IRwpArgcXlVAWEcyAMrq"

threads: list[Thread] = []
threads_count = 1
split_threads = split_list_into_n_parts(items, threads_count)
for i, items_to_thread in enumerate(split_threads):
    print(len(items_to_thread))
    
    user_dir_path = f"./data_{i}"
    t = Thread(target=parser, args=(items_to_thread, user_dir_path, 4))
    threads.append(t)
    t.start()

for i in threads:
    i.join()

    
# parser([
#     "/product/matematika-proverochnye-raboty-2-klass-fgos-shkola-rossii-volkova-svetlana-ivanovna-1218537971/?_bctx=CAQQkdMM&at=Rlty4gOJWcOPO02EcDNNrANh1j11vDcBOj9ZkulvzyAM&hs=1"
#     # "/product/russkiy-yazyk-7-klass-uchebnik-chast-2-baranov-m-ladyzhenskaya-taisa-alekseevna-584734710/?_bctx=CAQQ"
# ])