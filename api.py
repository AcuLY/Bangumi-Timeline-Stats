import asyncio
import os
import time
from datetime import datetime

import httpx
from bs4 import BeautifulSoup
from dateutil.relativedelta import relativedelta

headers = {
    "User-Agent": "AcuL/Bangumi-Timeline-Stats/1.0 (Web) (https://github.com/AcuLY/Bangumi-Timeline-Stats)"
}


def _read_env_int(name: str, default: int, minimum: int = 1) -> int:
    try:
        value = int(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default
    return max(minimum, value)


def _read_env_float(name: str, default: float, minimum: float = 0.0) -> float:
    try:
        value = float(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default
    return max(minimum, value)


def _read_base_urls() -> list[str]:
    raw_multi = os.getenv("BANGUMI_BASE_URLS", "")
    if raw_multi.strip():
        urls = [u.strip().rstrip("/") for u in raw_multi.split(",") if u.strip()]
        if urls:
            return urls

    raw_single = os.getenv("BANGUMI_BASE_URL", "").strip().rstrip("/")
    if raw_single:
        return [raw_single]

    return ["https://bangumi.tv", "https://chii.in"]


BANGUMI_BASE_URLS = _read_base_urls()
HTTPX_CONNECT_TIMEOUT_SECONDS = _read_env_float(
    "HTTPX_CONNECT_TIMEOUT_SECONDS", 10.0
)
HTTPX_READ_TIMEOUT_SECONDS = _read_env_float("HTTPX_READ_TIMEOUT_SECONDS", 45.0)
HTTPX_WRITE_TIMEOUT_SECONDS = _read_env_float("HTTPX_WRITE_TIMEOUT_SECONDS", 10.0)
HTTPX_POOL_TIMEOUT_SECONDS = _read_env_float("HTTPX_POOL_TIMEOUT_SECONDS", 30.0)
OUTBOUND_MAX_CONCURRENCY = _read_env_int("OUTBOUND_MAX_CONCURRENCY", 2)
REQUEST_INTERVAL_SECONDS = _read_env_float("REQUEST_INTERVAL_SECONDS", 1.0)
REQUEST_RETRY_ATTEMPTS = _read_env_int("REQUEST_RETRY_ATTEMPTS", 3)
REQUEST_RETRY_BACKOFF_SECONDS = _read_env_float(
    "REQUEST_RETRY_BACKOFF_SECONDS", 1.5
)

timeout = httpx.Timeout(
    connect=HTTPX_CONNECT_TIMEOUT_SECONDS,
    read=HTTPX_READ_TIMEOUT_SECONDS,
    write=HTTPX_WRITE_TIMEOUT_SECONDS,
    pool=HTTPX_POOL_TIMEOUT_SECONDS,
)

MAX_PAGE_RANGE = 10
MAX_DAY_RANGE = 7
MAX_MONTH_RANGE = 6
MAX_YEAR_RANGE = 1

_outbound_semaphore = asyncio.Semaphore(OUTBOUND_MAX_CONCURRENCY)
_request_interval_lock = asyncio.Lock()
_next_request_time = 0.0


def user_urls(user_id: str) -> list[str]:
    return [f"{base_url}/user/{user_id}/timeline" for base_url in BANGUMI_BASE_URLS]


def parse_fetch_range(fetch_range: str) -> tuple[str, int, str]:
    if fetch_range.isdecimal():
        pages = int(fetch_range)
        if pages < 1 or pages > MAX_PAGE_RANGE:
            raise ValueError(f"page range must be between 1 and {MAX_PAGE_RANGE}")
        return ("pages", pages, "")

    if len(fetch_range) < 2 or (not fetch_range[:-1].isdecimal()):
        raise ValueError("range format is invalid")

    value = int(fetch_range[:-1])
    time_type = fetch_range[-1]

    if time_type == "d":
        if value < 1 or value > MAX_DAY_RANGE:
            raise ValueError(f"day range must be between 1 and {MAX_DAY_RANGE}")
    elif time_type == "m":
        if value < 1 or value > MAX_MONTH_RANGE:
            raise ValueError(f"month range must be between 1 and {MAX_MONTH_RANGE}")
    elif time_type == "y":
        if value < 1 or value > MAX_YEAR_RANGE:
            raise ValueError(f"year range must be between 1 and {MAX_YEAR_RANGE}")
    else:
        raise ValueError("range unit must be one of d/m/y")

    return ("time", value, time_type)


def parse_datetime(response: httpx.Response) -> list[datetime]:
    response.encoding = "utf-8"
    html_content = response.text

    soup = BeautifulSoup(html_content, "html.parser")

    if not soup.find(id="timeline"):
        return []

    elements = soup.find_all(class_="titleTip")
    timelines = [element.get("title") for element in elements]
    datetimes = [
        datetime.strptime(timeline, "%Y-%m-%d %H:%M") for timeline in timelines
    ]

    return datetimes


async def fetch(client: httpx.AsyncClient, url: str, params: dict):
    global _next_request_time

    async with _outbound_semaphore:
        last_error = None
        for attempt in range(1, REQUEST_RETRY_ATTEMPTS + 1):
            async with _request_interval_lock:
                now = time.monotonic()
                if now < _next_request_time:
                    await asyncio.sleep(_next_request_time - now)
                    now = time.monotonic()
                _next_request_time = now + REQUEST_INTERVAL_SECONDS

            try:
                response = await client.get(url, params=params)
                response.raise_for_status()
                return response
            except httpx.HTTPStatusError as exc:
                last_error = exc
                if attempt >= REQUEST_RETRY_ATTEMPTS:
                    raise
                if exc.response.status_code not in (429, 500, 502, 503, 504):
                    raise
                await asyncio.sleep(REQUEST_RETRY_BACKOFF_SECONDS * attempt)
            except (httpx.TimeoutException, httpx.TransportError) as exc:
                last_error = exc
                if attempt >= REQUEST_RETRY_ATTEMPTS:
                    raise
                await asyncio.sleep(REQUEST_RETRY_BACKOFF_SECONDS * attempt)

        raise last_error


async def fetch_timelines_by_pages(
    client: httpx.AsyncClient, user_id: str, pages: int
) -> list[datetime]:
    last_error = None
    for url in user_urls(user_id):
        try:
            tasks = [
                fetch(client, url, {"type": "progress", "page": page + 1})
                for page in range(pages)
            ]
            responses = await asyncio.gather(*tasks)
            datetimes = []
            for response in responses:
                datetimes.extend(parse_datetime(response))
            return datetimes
        except (httpx.TimeoutException, httpx.TransportError, httpx.HTTPStatusError) as exc:
            last_error = exc

    if last_error is not None:
        raise last_error
    return []


async def fetch_timelines_by_datetime(
    client: httpx.AsyncClient, user_id: str, due_date: datetime, step: int
) -> list[datetime]:
    last_error = None
    for url in user_urls(user_id):
        try:
            datetimes = []
            begin_page = 1
            while True:
                tasks = [
                    fetch(client, url, {"type": "progress", "page": page})
                    for page in range(begin_page, begin_page + step)
                ]
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
        except (httpx.TimeoutException, httpx.TransportError, httpx.HTTPStatusError) as exc:
            last_error = exc

    if last_error is not None:
        raise last_error
    return []


async def fetch_hours(user_id: str, fetch_range: str) -> list[int]:
    range_type, value, time_type = parse_fetch_range(fetch_range)

    async with httpx.AsyncClient(
        headers=headers,
        limits=httpx.Limits(max_connections=OUTBOUND_MAX_CONCURRENCY),
        timeout=timeout,
    ) as client:
        if range_type == "pages":
            datetimes = await fetch_timelines_by_pages(client, user_id, value)
        else:
            now = datetime.now()
            if time_type == "d":
                due_date = now - relativedelta(days=value)
                step = 1
            elif time_type == "m":
                due_date = now - relativedelta(months=value)
                step = 2
            else:
                due_date = now - relativedelta(years=value)
                step = 5

            datetimes = await fetch_timelines_by_datetime(
                client, user_id, due_date, step
            )

        hours = [0] * 24
        for dt in datetimes:
            hours[dt.hour] += 1

        return hours
