import asyncio
import re
from datetime import datetime

import httpx
from quart import Quart, jsonify, request
from quart_cors import cors

from api import fetch_hours, parse_fetch_range
from cache import get_cache, set_cache
from logger import logger

app = Quart(__name__)
app = cors(app, allow_origin="*")

USER_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{1,64}$")

_inflight_lock = asyncio.Lock()
_inflight_tasks: dict[str, asyncio.Task] = {}


def _validate_request(user_id: str | None, fetch_range: str | None, timestamp: str | None) -> str:
    if not user_id or not USER_ID_PATTERN.fullmatch(user_id):
        raise ValueError("Invalid userid")

    if not fetch_range:
        raise ValueError("Invalid range")
    parse_fetch_range(fetch_range)

    if timestamp is not None and not timestamp.isdecimal():
        raise ValueError("Invalid timestamp")

    return fetch_range


async def _fetch_and_cache(key: str, user_id: str, fetch_range: str) -> dict:
    hours = await fetch_hours(user_id, fetch_range)
    now = int(datetime.now().timestamp())
    result = {"hours": hours, "t": now}
    set_cache(key, result)
    return result


async def _get_or_create_result(key: str, user_id: str, fetch_range: str) -> dict:
    async with _inflight_lock:
        task = _inflight_tasks.get(key)
        if task is None:
            task = asyncio.create_task(_fetch_and_cache(key, user_id, fetch_range))
            _inflight_tasks[key] = task

    try:
        return await task
    finally:
        if task.done():
            async with _inflight_lock:
                if _inflight_tasks.get(key) is task:
                    _inflight_tasks.pop(key, None)


@app.get("/timeline")
async def get_statistics():
    user_id = request.args.get("userid")
    fetch_range = request.args.get("range")
    timestamp = request.args.get("t")

    log_message_query = f"查询: user_id={user_id}, range={fetch_range}, time={timestamp}"
    logger.info(log_message_query)
    print(f"\033[1;34m{datetime.now()} {log_message_query}\033[0m")

    try:
        fetch_range = _validate_request(user_id, fetch_range, timestamp)

        key = f"{user_id}:{fetch_range}"
        result = None

        if timestamp is None:
            result = get_cache(key)

        if result is not None:
            log_message_success = (
                f"缓存: user_id={user_id}, range={fetch_range}, "
                f"hours={result['hours']}, t={result['t']}"
            )
        else:
            result = await _get_or_create_result(key, user_id, fetch_range)
            log_message_success = (
                f"成功: user_id={user_id}, range={fetch_range}, "
                f"hours={result['hours']}, t={result['t']}"
            )

        logger.info(log_message_success)
        print(f"\033[1;32m{datetime.now()} {log_message_success}\033[0m")

        return jsonify({"hours": result["hours"], "t": result["t"]})
    except ValueError as e:
        log_message_error = (
            f"参数错误: user_id={user_id}, range={fetch_range}, "
            f"{type(e).__name__}: {str(e) or repr(e)}"
        )
        logger.warning(log_message_error)
        print(
            f"\033[1;33m{datetime.now()} 参数错误: user_id={user_id}, range={fetch_range}, "
            f"{type(e).__name__}: {e!r}\033[0m"
        )
        return jsonify({"error": str(e)}), 400
    except httpx.HTTPError as e:
        log_message_error = (
            f"上游错误: user_id={user_id}, range={fetch_range}, "
            f"{type(e).__name__}: {str(e) or repr(e)}"
        )
        logger.error(log_message_error)
        print(
            f"\033[1;31m{datetime.now()} 上游错误: user_id={user_id}, range={fetch_range}, "
            f"{type(e).__name__}: {e!r}\033[0m"
        )
        return jsonify(
            {
                "error": (
                    f"Upstream Fetch Failed: {type(e).__name__}: "
                    f"{str(e) or repr(e)}"
                )
            }
        ), 502
    except Exception as e:
        log_message_error = (
            f"错误: user_id={user_id}, range={fetch_range}, "
            f"{type(e).__name__}: {str(e) or repr(e)}"
        )
        logger.error(log_message_error)

        print(
            f"\033[1;31m{datetime.now()} 错误: user_id={user_id}, range={fetch_range}, "
            f"{type(e).__name__}: {e!r}\033[0m"
        )

        return jsonify(
            {
                "error": f"Internal Server Error: {type(e).__name__}: {str(e) or repr(e)}"
            }
        ), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
