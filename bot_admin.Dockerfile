FROM python:3.8.8-slim-buster
WORKDIR /attendance_bot

ENV VENV=/opt/venv
RUN python3 -m venv $VENV
ENV PATH="VENV/bin:$PATH"

COPY ./requirements.txt ./requirements.txt
COPY ./src ./src
COPY ./setup.py ./setup.py
RUN pip3 install --upgrade pip
RUN pip3 install .

COPY ./resources ./resources
COPY ./admin_bot.py ./admin_bot.py
COPY ./config.json ./config.json
CMD ["python", "./admin_bot.py"]
