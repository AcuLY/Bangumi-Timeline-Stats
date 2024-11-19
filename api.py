import httpx
import asyncio
from bs4 import BeautifulSoup
from datetime import datetime


headers = {
    'User-Agent': 'AcuL/BangumiStaffStatistics/1.0 (Web) (https://github.com/AcuLY/BangumiStaffStats)'
}


def parse_datetime(response: httpx.Response) -> list[datetime]:
    if response.status_code != 200:
        return []
    
    response.encoding = 'utf-8'
    html_content = response.text
    
    soup = BeautifulSoup(html_content, 'html.parser')
    
    elements = soup.find_all(class_='titleTip')
    timelines = [element.get('title') for element in elements]
    datetimes = [datetime.strptime(timeline, "%Y-%m-%d %H:%M") for timeline in timelines]
    
    return datetimes


async def fetch_timelines_by_pages(user_id: str, pages: int) -> list[datetime]:
    async with httpx.AsyncClient(headers=headers, limits=httpx.Limits(max_connections=10)) as client:
        url = f"https://bgm.tv/user/{user_id}/timeline"
        tasks = [client.get(url, params={'type': 'progress', 'page': page+1}) for page in range(pages)]
        responses = await asyncio.gather(*tasks)
        datetimes = []
        for response in responses:
            datetimes.extend(parse_datetime(response))
        return datetimes


async def fetch_timelines_by_datetime(user_id: str, due_date: datetime) -> list[datetime]:
    datetimes = []
    async with httpx.AsyncClient(headers=headers, limits=httpx.Limits(max_connections=10)) as client:
        url = f"https://bgm.tv/user/{user_id}/timeline"
        begin_page = 1
        while True:
            tasks = [client.get(url, params={'type': 'progress', 'page': page+1}) for page in range(begin_page, begin_page + 10)]
            responses = await asyncio.gather(*tasks)
            
            for response in responses:
                current_datetimes = parse_datetime(response)
                if not current_datetimes:
                    return datetimes

                for dt in current_datetimes:
                    if dt >= due_date:
                        datetimes.append(dt)
                    else:
                        return datetimes
            
            begin_page += 10


async def fetch_hours(user_id: str, range_type: str, due_date: datetime=None) -> list[int]:
    if range_type == 'default':
        datetimes = await fetch_timelines_by_pages(user_id, 5)
    else:
        datetimes = await fetch_timelines_by_datetime(user_id, due_date)

    hours = [0] * 24
    for dt in datetimes:
        hours[dt.hour] += 1

    return hours

