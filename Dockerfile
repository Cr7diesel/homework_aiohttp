FROM python:3.10
COPY . ./src

WORKDIR /src

RUN pip install --no-cache-dir -r /src/requirements.txt

ADD https://github.com/ufoscout/docker-compose-wait/releases/download/2.7.3/wait /wait
RUN chmod +x /wait

ENTRYPOINT /wait && bash ./entrypoint.sh