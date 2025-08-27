FROM python:3.12

COPY . .
RUN pip install -i https://pypi.tuna.tsinghua.edu.cn/simple -r requirements.txt

CMD [ "python", "app.py" ]