FROM arm64v8/python:3.9-alpine as target-arm64

FROM arm32v7/python:3.7-alpine as target-armv7

FROM target-$TARGETARCH$TARGETVARIANT

ENV PYTHONUNBUFFERED=1

RUN mkdir -p /usr/app
COPY . /usr/app
WORKDIR /usr/app
RUN pip install -r requirements.txt

CMD ["./entrypoint.sh"]