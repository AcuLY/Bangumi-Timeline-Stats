import httpx
import asyncio
from bs4 import BeautifulSoup
from datetime import datetime
from dateutil.relativedelta import relativedelta

semaphore = asyncio.Semaphore(5)

headers = {
    'User-Agent': 'AcuL/Bangumi-Timeline-Stats/1.0 (Web) (https://github.com/AcuLY/Bangumi-Timeline-Stats)'
}


def parse_datetime(response: httpx.Response) -> list[datetime]:
    response.encoding = 'utf-8'
    html_content = response.text
    
    soup = BeautifulSoup(html_content, 'html.parser')
    
    if not soup.find(id="timeline"):
        return []
    
    elements = soup.find_all(class_='titleTip')
    timelines = [element.get('title') for element in elements]
    datetimes = [datetime.strptime(timeline, "%Y-%m-%d %H:%M") for timeline in timelines]

    return datetimes


async def fetch(client: httpx.AsyncClient, url: str, params: dict):
    async with semaphore:
        response = await client.get(url, params=params)
        await asyncio.sleep(0.5)
        return response


async def fetch_timelines_by_pages(client: httpx.AsyncClient, user_id: str, pages: int) -> list[datetime]:
    url = f"https://bgm.tv/user/{user_id}/timeline"
    tasks = [fetch(client, url, {'type': 'progress', 'page': page+1}) for page in range(pages)]
    responses = await asyncio.gather(*tasks)
    datetimes = []
    for response in responses:
        datetimes.extend(parse_datetime(response))
    return datetimes


async def fetch_timelines_by_datetime(client: httpx.AsyncClient, user_id: str, due_date: datetime, step: int) -> list[datetime]:
    datetimes = []
    url = f"https://bgm.tv/user/{user_id}/timeline"
    begin_page = 1
    while True:
        tasks = tasks = [fetch(client, url, {'type': 'progress', 'page': page}) for page in range(begin_page, begin_page + step)]
        responses = await asyncio.gather(*tasks)

        is_end = False
        for response in responses:
            parsed_datetime = parse_datetime(response)
            if not parsed_datetime:
                is_end = True
                break
            for dt in parsed_datetime:
                if dt >= due_date:
                    datetimes.append(dt)
                else:
                    is_end = True
                    break
            if is_end:
                break
        if is_end:
            return datetimes
        
        begin_page += step
        await asyncio.sleep(0.2)


async def fetch_hours(user_id: str, fetch_range: str) -> list[int]:
    async with httpx.AsyncClient(headers=headers, limits=httpx.Limits(max_connections=5)) as client:
        # 数量范围只包含数字
        if fetch_range.isdecimal():
            datetimes = await fetch_timelines_by_pages(client, user_id, int(fetch_range))
        else:
            # time_range 的格式为 %d%c 如 7d, 30d, 6m, 1y
            value = int(fetch_range[:-1])
            time_type = fetch_range[-1]
            now = datetime.now()
            if time_type == 'd':
                due_date = now - relativedelta(days=value)
                step = 1
            elif time_type == 'm':
                due_date = now - relativedelta(months=value)
                step = 2
            else:
                due_date = now - relativedelta(years=value)
                step = 5

            datetimes = await fetch_timelines_by_datetime(client, user_id, due_date, step)

        hours = [0] * 24
        for dt in datetimes:
            hours[dt.hour] += 1

        return hours

