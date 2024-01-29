FROM ubuntu:20.04

RUN apt-get update && apt-get install -y python3 python3-pip libpq-dev

RUN apt-get update && \
    apt-get install -y postgresql-client && \
    rm -rf /var/lib/apt/lists/*

ENV PGPASSWORD_PATH /usr/bin/pg_dump

RUN apt-get update && apt-get install -y cron

ENV DEBIAN_FRONTEND=noninteractive

ENV TZ=Europe/Kyiv
RUN apt-get update && apt-get install -y tzdata

RUN apt-get install -y wget xvfb unzip


# -----------------------------------------
RUN echo "deb https://apt.postgresql.org/pub/repos/apt focal-pgdg main" >> /etc/apt/sources.list.d/pgdg.list
RUN wget --quiet -O - https://www.postgresql.org/media/keys/ACCC4CF8.asc | apt-key add -
RUN apt-get update
RUN apt-get -y install postgresql-16
# ----------------------------------------

# Set up the Chrome PPA -> (not sure if needed)
RUN wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add -
RUN echo "deb http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google.list

# Update the package list
RUN apt-get update -y

# Set up Chromedriver Environment variables and install chrome
ENV CHROMEDRIVER_VERSION 114.0.5735.90
ENV CHROME_VERSION 114.0.5735.90-1
RUN wget --no-verbose -O /tmp/chrome.deb https://dl.google.com/linux/chrome/deb/pool/main/g/google-chrome-stable/google-chrome-stable_${CHROME_VERSION}_amd64.deb \
  && apt install -y /tmp/chrome.deb \
  && rm /tmp/chrome.deb

ENV CHROMEDRIVER_DIR /chromedriver
RUN mkdir $CHROMEDRIVER_DIR

# Download and install Chromedriver
RUN wget -q --continue -P $CHROMEDRIVER_DIR "http://chromedriver.storage.googleapis.com/$CHROMEDRIVER_VERSION/chromedriver_linux64.zip"
RUN unzip $CHROMEDRIVER_DIR/chromedriver* -d $CHROMEDRIVER_DIR

# Put Chromedriver into the PATH
ENV PATH $CHROMEDRIVER_DIR:$PATH



# Обновление pip
RUN pip3 install --upgrade pip

COPY main.py /app/
COPY my_cron /etc/cron.d/my_cron

# Устанавливаем разрешения и устанавливаем cron
RUN chmod 0644 /etc/cron.d/my_cron \
    && crontab /etc/cron.d/my_cron \
    && touch /var/log/cron.log

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt


COPY . .

RUN date "+%H:%M:%S   %d/%m/%y"

CMD ["cron", "-f"]