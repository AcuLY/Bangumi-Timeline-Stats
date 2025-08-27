FROM python:3.12

COPY . .
RUN pip install -i https://pypi.tuna.tsinghua.edu.cn/simple -r requirements.txt

ENV TZ=Asia/Shanghai
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

CMD [ "python", "app.py" ]