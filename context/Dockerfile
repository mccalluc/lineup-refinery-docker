FROM python:3.6.5-alpine3.7

WORKDIR /var

ENV V=0.0.1
ENV REPO=lineup-taggle-prebuilt

COPY . .
RUN pip install -r requirements.txt

RUN python -m wget https://github.com/mccalluc/$REPO/archive/v$V.zip
RUN unzip $REPO-$V.zip
WORKDIR $REPO-$V

CMD "../on_startup.sh"
