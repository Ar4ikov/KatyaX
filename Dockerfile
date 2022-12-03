FROM python:3.9-slim-buster

WORKDIR /katyax

# copy all to workdir
COPY . .

RUN apt update && apt-get install libpq-dev build-essential -y

# install requirements
RUN pip install -r requirements.txt

# run the bot
CMD ["python", "bot.py"]