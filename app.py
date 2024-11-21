import logging
from quart import Quart, jsonify, request
from quart_cors import cors
from api import fetch_hours
from datetime import datetime

# 设置日志
logging.basicConfig(
    filename='app.log', 
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

app = Quart(__name__)

app = cors(app, allow_origin="*")

@app.get('/timeline')
async def get_statistics():
    user_id = request.args.get('userid')
    fetch_range = request.args.get('range')

    log_message_query = f"查询: user_id={user_id}, range={fetch_range}"
    logging.info(log_message_query)
    print(f"\033[1;34m{datetime.now()} {log_message_query}\033[0m")

    try:
        hours = await fetch_hours(user_id, fetch_range)
        log_message_success = f"成功: user_id={user_id}, range={fetch_range}, hours={hours}"
        logging.info(log_message_success)
        print(f"\033[1;32m{datetime.now()} {log_message_success}\033[0m")
        return jsonify({'hours': hours})
    except Exception as e:
        log_message_error = f"错误: user_id={user_id}, range={fetch_range}, error={str(e)}"
        logging.error(log_message_error)
        print(f"\033[1;31m{datetime.now()} {log_message_error}\033[0m")
        return jsonify({'error': 'Internal Server Error'}), 500

if __name__ == '__main__':
    app.run()
