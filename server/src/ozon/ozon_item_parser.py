import re
from datetime import datetime, timedelta
from threading import Event
from uuid import uuid4

from patchright._impl._errors import TimeoutError
from patchright.async_api import Page, async_playwright
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

import qwen_integration
from server.src.dependency.exceptions import ItemNotAvailable
from server.src.ozon.dependency import get_id_from_url
from server.src.ozon.model import OzonItem, OzonSeller

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


async def get_seller_info(page: Page, seller_id: int) -> dict:
    try:
        await page.goto(f"{base_seller_url}/{seller_id}/products")
    except TimeoutError:
        return
    
    data = {
        "id": seller_id
    }
    
    try:
        await page\
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
    
    work_time_l_item = cell_list_item\
        .locator("div:has-text('Работает с Ozon')")\
            .first\
        .locator("xpath=div[3]")
            
    work_time_l = (await work_time_l_item.text_content()).lower().split()
                
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
    if await orders_count_div.count() > 0:
        orders_count = (await orders_count_div.first.text_content()).lower().split()
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
    if await avg_rate_div.count() > 0:
        avg_rate = (await avg_rate_div.first.text_content()).split()[0].replace(',', '.')
        data["avg_item_rate"] = float(avg_rate)
    
    
    seller_info_item = modal_layout_item.locator(
        "[data-widget='textBlock']"
    ).last.locator(
        "xpath=div[1]/div[1]/div[1]"
    )
    if await seller_info_item.count() > 0:
        seller_info = await seller_info_item.text_content()
            
        if seller_info.split()[0].lower() == "ип":
            id = re.sub(r"\D", '', seller_info.split()[-1])
            seller_info = qwen_integration.get_ip_info(id)
        
        data["region"] = seller_info
    
    return data


async def get_seller_id(page: Page) -> int | None:
    try:
        is_ozon_1 = await page\
            .locator("[data-widget='webCurrentSeller']")\
            .locator("div:has-text('Продавец')")\
            .last\
            .locator("xpath=..")\
            .locator("div:has-text('Ozon')")\
            .count() > 0

        is_ozon_2 = await page\
            .locator("[data-widget='webCurrentSeller']")\
            .locator("span:has-text('Магазин')")\
            .locator("xpath=../div[1]")\
            .locator("span:has-text('Ozon')")\
            .count() > 0

        if is_ozon_1 or is_ozon_2:
            return None
        
        seller_url = await page\
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
        

async def get_description_text(page: Page) -> str:
    try:
        await page.locator("#section-description").first.scroll_into_view_if_needed()
        
        desc = ""
        for desc_item in await page.locator("#section-description").all():
                desc += (await desc_item.text_content()).lower().strip("описание").strip("автор на обложке") + ' '
        
        return desc
    except TimeoutError:
        await page.locator("footer").scroll_into_view_if_needed()
        return ''


async def get_product_information(page: Page) -> dict:
    data = {}
    
    title_item = page.locator("h1")
    if await title_item.count() > 0:
        data["title"] = await title_item.text_content()
        data["title"] = data["title"].lower().replace('\n', '').strip()
        
    price_item = page.locator("[data-widget='webPrice']").locator(
        "xpath=div[1]/div[1]"
    )
    if await price_item.count() > 0:
        data["price"] = int(re.sub(r"\D", '', await price_item.text_content()))
    
    year_item = page.locator("dt:has-text('Год выпуска')")
    if await year_item.count() > 0:
        data["year"] = int(await year_item.locator("xpath=../dd").text_content())
        
    paper_type_item = page.locator("dt:has-text('Тип бумаги в книге')")
    if await paper_type_item.count() > 0:
        data["paper_type"] = await paper_type_item.first.locator("xpath=../dd").text_content()
        
    preview_type_item = page.locator("dt:has-text('Тип обложки')")
    if await preview_type_item.count() > 0:
        data["preview_type"] = await preview_type_item.first.locator("xpath=../dd").text_content()
        
    book_type_item = page.locator("dt:has-text('Тип книги')")
    if await book_type_item.count() > 0:
        data["book_type"] = await book_type_item.first.locator("xpath=../dd").text_content()
        
    pages_count_item = page.locator("dt:has-text('Количество страниц')")
    if await pages_count_item.count() > 0:
        data["pages_count"] = int(
            await pages_count_item.first.locator("xpath=../dd").text_content()
        )
        
    isbn_item = page.locator("dt:has-text('ISBN')")
    if await isbn_item.count() > 0:
        isbns = (await isbn_item.first.locator("xpath=../dd").text_content()).split(",")
        isbns = [i.replace('-', '').strip() for i in isbns]
        data["isbn"] = isbns
        
    class_item = page.locator("dt:has-text('Класс')")
    if await class_item.count() > 0:
        data["class_"] = int(
            re.sub(
                r"\D", '', await class_item.first.locator("xpath=../dd").text_content()
            )
        )
        
        if data["class_"] == 1234567891011:
            data["class_"] = None
    
    subject_item = page.locator("dt:has-text('Предмет обучения')")
    if await subject_item.count() > 0:
        data["subject"] = await subject_item.locator("xpath=../dd").text_content()
        
    original_name_item = page.locator("dt:has-text('Оригинальное название')")
    if await original_name_item.count() > 0:
        data["original_name"] = await original_name_item.locator("xpath=../dd").text_content()
        
    author_item = page.locator("dt:has-text('Автор')")
    if await author_item.count() > 0:
        authors = (await author_item.locator("xpath=../dd").text_content()).split(",")
        authors = [i.strip() for i in authors]
        data["author"] = authors
    
    image_item = page.locator("div[data-widget='webGallery']").locator("img").last
    if await image_item.count() > 0:
        data["image"] = await image_item.get_attribute("src")
    
    data["description"] = await get_description_text(page)
    
    return data


async def get_days_to_deliver(page: Page) -> int:
    try:
        Event().wait(0.5)
        
        deliver_date_text = await page.locator(
            "[data-widget='webAddToCart']"
        ).first.locator(
            "xpath=div[1]/div[1]/div[1]"
        ).locator("span").first.text_content()
        deliver_date_text = deliver_date_text.lower()
        
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


async def get_warehouse_type(page: Page) -> str:
    try:
        warehouse_type_item = page.locator(
            "h2:has-text('Информация о доставке')"
        ).locator(
            "xpath=../div[1]/div[1]/button[1]/span[1]/div[1]/span[1]/span[2]"
        )
        
        if await warehouse_type_item.count() > 0:
            warehouse_type_text = await warehouse_type_item.text_content()
            warehouse_type_text = warehouse_type_text.lower()
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
async def parser(session: AsyncSession, url: str, user_dir_path: str = "./data_0") -> OzonItem:
    id_ = get_id_from_url(url)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch_persistent_context(
            headless=False,
            user_data_dir=user_dir_path,
            no_viewport=True,
        )
        
        page = await browser.new_page()
            
        try:
            await page.goto(f"{base_url}{url}")
        except TimeoutError:
            return 
    
        while "OZON" not in await page.title():
            Event().wait(0.5)
            
        product_is_over = await page.locator("h2:has-text('Этот товар закончился')").count()
        product_is_deleted = await page.locator("h2:has-text('Такой страницы не существует')").count()
        product_is_unavailable = await page.locator("h2:has-text('Товар не доставляется в ваш регион')").count()
        
        if product_is_deleted or product_is_over or product_is_unavailable:
            raise ItemNotAvailable
        
        data = {
            "id": id_,
            "url": url,
        }
        
        data["description"] = await get_description_text(page)
        
        data.update(await get_product_information(page))
        
        seller_id = await get_seller_id(page)
        if seller_id:
            data["seller_id"] = seller_id

        data["days_to_deliver"] = await get_days_to_deliver(page)
        data["warehouse_type"] = await get_warehouse_type(page)
        
        
        if "seller_id" in data:
            query = select(OzonSeller).filter(OzonSeller.id == data["seller_id"])
            result = await session.execute(query)
            seller = result.fetchone()
                
            if seller is None:
                seller_info = await get_seller_info(page, data["seller_id"])
                seller = OzonSeller(**seller_info)
                session.add(seller)
        else:
            print(f"no seller info for url {url}")
        
        await browser.close()
        
        print(data)
        
        return data
