FROM python:3.9-slim-buster

WORKDIR /katyax

# copy all to workdir
COPY . .

RUN sudo apt-get install build-dep python-psycopg2

# install requirements
RUN pip install -r requirements.txt

# run the bot
CMD ["python", "bot.py"]