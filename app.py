import logger
from quart import Quart, jsonify, request
from quart_cors import cors
from api import fetch_hours
from datetime import datetime
from cache import get_cache, set_cache
from logger import logger

app = Quart(__name__)

app = cors(app, allow_origin="*")

@app.get('/timeline')
async def get_statistics():
    user_id = request.args.get('userid')
    fetch_range = request.args.get('range')

    log_message_query = f"查询: user_id={user_id}, range={fetch_range}"
    logger.info(log_message_query)
    print(f"\033[1;34m{datetime.now()} {log_message_query}\033[0m")

    try:
        key = user_id + fetch_range
        result = get_cache(key)
        
        if result is not None:
            log_message_success = f"缓存: user_id={user_id}, range={fetch_range}, hours={result}"
        else:
            result = await fetch_hours(user_id, fetch_range)
            set_cache(key, result)
            
            log_message_success = f"成功: user_id={user_id}, range={fetch_range}, hours={result}"
    
        logger.info(log_message_success)
        print(f"\033[1;32m{datetime.now()} {log_message_success}\033[0m")
        
        return jsonify({'hours': result})
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

        return jsonify({
            'error': f'Internal Server Error: {type(e).__name__}: {str(e) or repr(e)}'
        }), 500

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000)
