import random
from datetime import datetime, timedelta
import pandas as pd
from faker import Faker

fake = Faker('ru_RU')

# Плохие регионы (сомнительные)
bad_regions = ["Сомалиленд", "Зимбабве", "Афганистан", "КНДР", "Венесуэла"]

# Иностранные или фейковые имена продавцов
fake_sellers_names = ["Alibaba Books", "StrangeSeller123", "Edu4U International", "CheapBooks LTD"]

# Небольшие справочники
bad_authors = ["Unknown Author", "Автор неизвестен", "Noname Writer", "Fake Name"]
bad_paper_types = ["Unknown Paper", "Bad Quality Paper"]

# Функция для генерации плохой цены
def generate_bad_price(mean_price=1000, std_dev=200):
    return int(mean_price + random.choice([-1, 1]) * (3 + random.random()) * std_dev)

# Генерация одного продавца
def generate_fake_seller():
    return {
        "seller_id": random.randint(10000, 99999),
        "seller_reg_date": datetime.now() - timedelta(days=random.randint(1, 3000)),
        "seller_orders": random.randint(0, 5),
        "seller_avg_item_rate": round(random.uniform(1.0, 5.0), 2),
        "seller_region": random.choice(bad_regions),
    }

# Генерация одного товара
def generate_fake_item(seller_info):
    return {
        "id": random.randint(100000, 999999),
        "title": fake.sentence(nb_words=4),
        "url": f"https://fakebookstore.com/item/{random.randint(10000,99999)}",
        "price": generate_bad_price(),
        "image": fake.image_url(width=128, height=128),
        "description": fake.text(max_nb_chars=500),
        "year": random.randint(1900, 2025),
        "paper_type": random.choice(bad_paper_types),
        "preview_type": random.choice(["pdf", "jpg"]),
        "book_type": random.choice(["учебник", "тетрадь", "решебник"]),
        "pages_count": random.randint(10, 3000),
        "circulation": random.randint(1, 100),
        "isbn": [fake.isbn13()],
        "class_": random.choice(range(1, 12)),
        "subject": random.choice(["математика", "литература", "история", "география"]),
        "original_name": fake.word(),
        "author": [random.choice(bad_authors)],
        "days_to_deliver": random.randint(20, 90),
        # Данные продавца
        "seller_id": seller_info["seller_id"],
        "seller_reg_date": seller_info["seller_reg_date"],
        "seller_orders": seller_info["seller_orders"],
        "seller_avg_item_rate": seller_info["seller_avg_item_rate"],
        "seller_region": seller_info["seller_region"],
    }

# Главная функция генерации датафрейма
def generate_fake_data_df(n_sellers=5, items_per_seller=3):
    data = []

    for _ in range(n_sellers):
        seller_info = generate_fake_seller()

        for _ in range(items_per_seller):
            item = generate_fake_item(seller_info)
            data.append(item)

    df = pd.DataFrame(data)
    return df

# Генерация примера
if __name__ == "__main__":
    df_fake = generate_fake_data_df(n_sellers=10, items_per_seller=5)
    print(df_fake.head())
