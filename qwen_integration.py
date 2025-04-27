from openai import OpenAI
from bs4 import BeautifulSoup
import requests
import random

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
    'Accept-Language': 'en-US,en;q=0.9,ru-RU;q=0.8,ru;q=0.7',
    'Accept-Encoding': 'gzip, deflate, br',
    'Referer': 'https://www.google.com/',  # Имитация перехода с другого сайта
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
    'Sec-Fetch-Dest': 'document',
    'Sec-Fetch-Mode': 'navigate',
    'Sec-Fetch-Site': 'cross-site',
    'Sec-Fetch-User': '?1',
    'Cache-Control': 'max-age=0',
    'DNT': '1',  # Do Not Track
}

proxies=[
    "http://172.67.182.17:80",
    "http://172.67.181.201:80",
    "http://172.67.146.14:80",
    "http://50.175.123.230:80",
    "http://172.67.180.16:80",
]


def get_proxy():  
    # Choose a random proxy from the list  
    proxy = random.choice(proxies)  
    # Return a dictionary with the proxy for both http and https protocols  
    return {'http': proxy}  


def get_ip_info(ip: str) -> str:
    try:
        r = requests.get(
            f"https://www.rusprofile.ru/ip/{ip}",
            headers=headers,
            allow_redirects=True,
            proxies=get_proxy()
        )
        
        print(r.status_code)
        
        soup = BeautifulSoup(r.text, "html.parser")
        e = soup.find("div", {"class": "company-info"}).find("dt", {"class": "company-info__title"}, string="Адрес")
        if e is None:
            e = e = soup.find("div", {"class": "company-info"}).find("dt", {"class": "company-info__title"}, string="Регион")
        
        e = e.parent.find("dd")
                
        return e.text
    except Exception as err:
        print(err)
        return None


# def get_city(info: str) -> str:
#     client = OpenAI(
#         base_url="https://openrouter.ai/api/v1",
#         api_key="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",
#     )
    
#     print(info)

#     try:
#         completion = client.chat.completions.create(
#             model="qwen/qwen2.5-vl-32b-instruct:free",
#             messages=[
#                 {
#                     "role": "user",
#                     "content": [
#                         {
#                             "type": "text",
#                             "text": "В каком городе зарегистрированно предприятие? В ответ отправь одно слово - город \n\n" + info
#                         }
#                     ]
#                 }
#             ]
#         )
#         print(completion)
#     except Exception as err:
#         print(err)
    
#     return completion.choices[0].message.content