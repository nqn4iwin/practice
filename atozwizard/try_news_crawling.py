def extract_text(soup, selectors):
    for selector in selectors:
        tag = soup.select_one(selector)
        if tag:
            return tag.text.strip()
    return None




import requests
import datetime
from bs4 import BeautifulSoup

date = datetime.datetime.strptime('20251228','%Y%m%d')
date = date - datetime.timedelta(days=1)
print(date.strftime('%Y%m%d'))

TITLE_SELECTORS = [
    '#title_area',
    'h2.media_end_head_headline'
]

CONTENT_SELECTORS = [
    '#dic_area',
    '#newsct_article'
]
date = datetime.datetime.strptime('20251228','%Y%m%d')
page = 1

for i in range(20):

    while True:

        date_str = date.strftime('%Y%m%d')
        url = f'https://news.naver.com/main/list.naver?mode=LPOD&mid=sec&oid=003&date={date_str}&page={page}'

        response = requests.get(url)
        soup = BeautifulSoup(response.text,'html.parser')
        for news_item in soup.select('div.list_body ul li dl dt:not(.photo) a'):
            article_url = news_item['href']
            
            try:
                
                article_res = requests.get(article_url)
                article_soup = BeautifulSoup(article_res.text,'html.parser')
                
                title = extract_text(article_soup, TITLE_SELECTORS)
                content = extract_text(article_soup,CONTENT_SELECTORS)
                
                if not title or not content:
                    print('[skip] 구조 불일치',article_url)
                    print("==================날짜 :",date.strftime('%Y%m%d'),"=====================")
                    print("=========================현재페이지 : ", page,"==========================")
                    print("=======================================================================")
                    continue
                
                print(title)
                print()
                print(content)
                print("==================날짜 :",date.strftime('%Y%m%d'),"=====================")
                print("=========================현재페이지 : ", page,"==========================")
                print("=======================================================================")
            except Exception as e:
                print('[error]',article_url,e)
        
            #print(news_item.text.strip())
        page += 1
        
        if page == 2:
            print("================크롤링 종료================")
            break
        
    
    date = date - datetime.timedelta(days=1)
    
