from quart import Quart, jsonify, request
from quart_cors import cors
from api import fetch_hours

app = Quart(__name__)

app = cors(app, allow_origin="*")

@app.get('/timeline')
async def get_statistics():
    user_id = request.args.get('userid')
    fetch_range = request.args.get('range')

    hours = await fetch_hours(user_id, fetch_range)

    return jsonify({'hours': hours})

if __name__ == '__main__':
    app.run()