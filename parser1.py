from patchright.sync_api import sync_playwright, Page
from patchright._impl._errors import TimeoutError
from threading import Event, Thread

from sqlalchemy import create_engine, String, ARRAY
from sqlalchemy.orm import declarative_base, sessionmaker, Mapped, mapped_column

from uuid import uuid4

# DataBase
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
    papper_type: Mapped[str]
    preview_type: Mapped[str]
    book_type: Mapped[str]
    pages_count: Mapped[int]
    circulation: Mapped[int]
    isbn: Mapped[list[str]] = mapped_column(ARRAY(String))
    class_: Mapped[int] = mapped_column(name="class")
    subject: Mapped[str]
    original_name: Mapped[str]
    author: Mapped[list[str]] = mapped_column(ARRAY(String))
    
    def dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "url": self.url,
            "price": self.price,
            "image": self.image,
            "description": self.description,
            "year": self.year,
            "papper_type": self.papper_type,
            "preview_type": self.preview_type,
            "book_type": self.book_type,
            "pages_count": self.pages_count,
            "circulation": self.circulation,
            "isbn": self.isbn,
            "class_": self.class_,
            "subject": self.subject,
            "original_name": self.original_name,
            "author": self.author
        }
    

engine = create_engine('postgresql://postgres:postgres@localhost:5432/OZON_parse')
Session = sessionmaker(engine, expire_on_commit=True)


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
            
        papper_type_item = page.locator(".kr8_28:has-text('Тип бумаги в книге')")
        if papper_type_item.count() > 0:
            data["papper_type"] = papper_type_item.locator("xpath=../../dd").text_content()
            
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
        
        print(data)
        
        with Session() as session:
            session.query(Item).filter(Item.url == url).update(data)
            session.commit()


# Parser       
def parser(items: list[Item], user_dir_path: str = "./data_0",
           count_pages: int = 1):                                      
    with sync_playwright() as p:                   
        browser = p.chromium.launch_persistent_context(
            headless=False,
            user_data_dir=user_dir_path,
        )
        
        page = browser.new_page()
        
        for item in items:
            url = item.url
            # print(url)
            
            try:
                page.goto(f"https://www.ozon.ru{url}")
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
                
            papper_type_item = page.locator(".kr8_28:has-text('Тип бумаги в книге')")
            if papper_type_item.count() > 0:
                data["papper_type"] = papper_type_item.locator("xpath=../../dd").text_content()
                
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
            
            if data != {}:
                with Session() as session:
                    session.query(Item).filter(Item.url == url).update(data)
                    session.commit()
        
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

threads: list[Thread] = []
threads_count = 4
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