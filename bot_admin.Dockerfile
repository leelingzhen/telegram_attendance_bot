FROM python:3.8.8-slim-buster
WORKDIR /alliance_bot

ENV VENV=/opt/venv
RUN python3 -m venv $VENV
ENV PATH="VENV/bin:$PATH"

COPY ./requirements.txt ./requirements.txt
RUN pip3 install --upgrade pip
RUN pip3 install -r requirements.txt

COPY ./resources ./resources
COPY ./admin_bot.py ./admin_bot.py
COPY ./helpers.py ./helpers.py
COPY ./config.json ./config.json
CMD ["python", "./admin_bot.py"]
