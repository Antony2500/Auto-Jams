import asyncio
import aiohttp
import logging
import os
import subprocess
import psycopg2
import requests
import re

import schedule
from bs4 import BeautifulSoup
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.chrome.service import Service

import postgres_func
import time

time.sleep(5)

load_dotenv()

logging.basicConfig(filename='app.log', level=logging.INFO)


class Scraper:
    def __init__(self):
        self.postgres_db = self.__get_or_create_connection()

    @classmethod
    def __get_or_create_connection(cls):
        try:
            postgres_db = postgres_func.PostgresLogic()
            return postgres_db
        except Exception as e:
            logging.info("Error: Unable to connect to the db")
            logging.error(e)
            exit(0)

    @classmethod
    def __get_all_advertisements(cls, first_part_url, last_part_url):
        """
           Getting href from every ad
           :param first_part_url:
           :param last_part_url:
           :return:
           """

        link_list = []

        page_number = 0
        while True:
            url = f"{first_part_url}{page_number}{last_part_url}"
            logging.debug('Fetching data from URL: %s', url)  # Log the URL being fetched
            response = requests.get(url)

            if response.status_code == 200:
                html = response.text
                soup = BeautifulSoup(html, 'html.parser')

                link = soup.find_all('a', class_='address')

                if not link:
                    logging.debug('There are no advertisements on page %d. End data collection.', page_number)
                    break

                link_list.extend(link)
                page_number += 1
            else:
                logging.error('Error %d: Unable to access page.', response.status_code)
                break

        return link_list

    async def __start_scraping(self, id_user: int, url: str, list_of_ids: list):
        first_part_url = url[:url.find("page")] + "page="
        last_part_url = '&size=100'
        list_of_checked_car_id = []

        all_ads = self.__get_all_advertisements(first_part_url, last_part_url)
        async with aiohttp.ClientSession() as session:
            tasks = [self.__fetch_ad(session, ad['href'], id_user, list_of_ids, list_of_checked_car_id) for ad in
                     all_ads]
            await asyncio.gather(*tasks)

        return list_of_checked_car_id

    async def __fetch_ad(self, session, ad_url, id_user, list_of_ids: dict, list_of_checked_car_id):
        """
        Parsing url's car
        :param session:
        :param ad_url:
        :param id_user:
        :param list_of_ids:
        :param list_of_checked_car_id:
        :return:
        """
        try:
            async with session.get(ad_url, timeout=50) as response:
                if response.status == 200:
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    # id_car
                    id_car = ''.join(re.findall(r'\d+', ad_url))
                    if id_car not in list_of_ids:

                        # title (строка)
                        title = soup.find('h1', class_='head').text if soup.find('h1', class_='head') else None
                        print("Title", title)

                        # price_usd (число)
                        price_usd = soup.find('strong', class_='').text
                        amount = 0
                        if price_usd:
                            amount = int(''.join(re.findall(r'\d+', price_usd)))
                            print(amount, " в долларах $")

                        # odometer (число, нужно перевести 95 тыс. в 95000 и записать как число)
                        tag_odometer = soup.find('dd', class_='mhide')
                        odometer = 0
                        if tag_odometer:
                            span_odometer = tag_odometer.find('span', class_='argument')
                            if span_odometer:
                                if span_odometer.text.split()[0] != 'без':
                                    odometer = int(span_odometer.text.split()[0]) * 1000
                        print("Odometer", odometer)

                        # username (строка)
                        tag_username = soup.find('div', class_='seller_info_name bold')
                        username = "Ім'я Не Вказано"
                        if tag_username:
                            username = tag_username.text
                        else:
                            tag_username = soup.find('h4', class_='seller_info_name')
                            if tag_username:
                                username = tag_username.find('a').text if not None else "Ім'я Не Вказано"
                        print("Username", username)

                        # image_url (строка)
                        image_url = ""
                        tag_div_img = soup.find('div', class_='carousel-inner')
                        if tag_div_img:
                            tag_picture_img = tag_div_img.find('picture')
                            if tag_picture_img:
                                tag_source_img = tag_picture_img.find(['source'])
                                if tag_source_img:
                                    image_url = tag_source_img.get('srcset')
                        print("Image_url - ", image_url)

                        # images_count (число)
                        tag_count = soup.find('span', class_='count')
                        img_count = 0
                        if tag_count:
                            tag_span_count = tag_count.find('span', class_='mhide')
                            if tag_span_count:
                                img_count = int(''.join(re.findall(r'\d+', tag_span_count.text)))

                        print('Count - ', img_count)

                        # car_number (строка)
                        tag_span_car_number = soup.find('span', class_='state-num ua')
                        car_number = 'Без номерів'
                        if tag_span_car_number:
                            car_number = tag_span_car_number.text[0:10]

                        print('Car number - ', car_number)

                        # car_vin (строка)
                        tag_span_vin_code = soup.find('span', 'label-vin')
                        tag_span_vin_code2 = soup.find('span', 'vin-code')
                        car_vin = "Немає"
                        if tag_span_vin_code:
                            car_vin = tag_span_vin_code.text
                        elif tag_span_vin_code2:
                            car_vin = tag_span_vin_code2.text
                        print("Car vin - ", car_vin)

                        # phone_number (текст, пример структуры: +38063……..)

                        options = webdriver.chrome.options.Options()
                        options.add_argument("--headless")
                        options.add_argument('--no-sandbox')
                        options.add_argument('--disable-dev-shm-usage')

                        with webdriver.Chrome(options=options) as driver:
                            driver.get(ad_url)

                            try:
                                show_button = WebDriverWait(driver, 20).until(
                                    EC.element_to_be_clickable((By.LINK_TEXT, 'показати'))
                                )

                                driver.execute_script("arguments[0].click();", show_button)

                                modal_window = WebDriverWait(driver, 20).until(
                                    EC.presence_of_element_located(
                                        (By.XPATH, '//div[@class="popup-show-phone modal fade in"]'))
                                )

                                nested_div = modal_window.find_element(By.XPATH,
                                                                       '//div[@class="popup-successful-call-desk size24 bold green mhide green"]')

                                if nested_div:
                                    phone_number = nested_div.text

                            except TimeoutException:
                                print(
                                    "TimeoutException: Element 'показати' not found within 20 seconds. Setting phone_number to '-'.")
                            finally:
                                print("Phone number:", phone_number)

                        self.postgres_db.insert_to_table_of_cars(id_user, id_car, ad_url, title, amount, odometer,
                                                                 username, phone_number, image_url, img_count,
                                                                 car_number, car_vin)

                        logging.info(f"New car with id {id_car} in base")

                    else:
                        list_of_checked_car_id.append(id_car)
                        logging.info(f"Car with id {id_car} in base")
                else:
                    logging.error('Error %d: Unable to access page.', response.status)
        except Exception as e:
            logging.exception('An error occurred while processing ad: %s', str(e))
        finally:
            logging.info("End scraping")

    dump_folder_path = Path(__file__).parent / 'dumps'

    dump_folder_path.mkdir(parents=True, exist_ok=True)

    dump_path = '/app/dumps/dump_{}.sql'.format(datetime.now().strftime("%Y%m%d%H%M%S"))


    @classmethod
    def __create_database_dump(cls):
        """
        Create a dump of the PostgreSQL db

        """
        try:

            db_name = os.getenv('DB_NAME')
            db_user = os.getenv('DB_USER')

            dump_folder_path = Path(__file__).parent / 'dumps'

            dump_folder_path.mkdir(parents=True, exist_ok=True)

            dump_filename = f'dump_{datetime.now().strftime("%Y%m%d%H%M%S")}.sql'
            dump_path = '/app/dumps/dump_{}.sql'.format(datetime.now().strftime("%Y%m%d%H%M%S"))

            os.environ['PGPASSWORD'] = os.getenv('DB_PASSWORD')

            dump_command = [
                'pg_dump',
                '-h', os.getenv('DB_HOST'),
                '-U', db_user,
                '-d', db_name,
                '-f', str(dump_path)
            ]

            subprocess.run(dump_command)

            print(f"Database dump created successfully at: {dump_path}")

        except Exception as e:
            print(f"Error: Unable to create db dump")
            print(e)

        finally:
            os.environ.pop('PGPASSWORD', None)

    def start_scraping(self):
        logging.info("Start scraping")

        try:
            logging.info("Checking table users")
            if not self.postgres_db.table_exists('users'):
                logging.info("Start to create table of users")
                self.postgres_db.create_users_table()
                logging.info("Created 'users' table")

            if self.postgres_db.is_table_empty('users'):
                url = self.postgres_db.create_url_for_user(os.getenv('BRAND_FOR_SCRAPER'),
                                                           os.getenv('MODEL_FOR_SCRAPER'))
                self.postgres_db.insert_to_table_of_users(os.getenv('USERNAME_FOR_TABLE'), url)
                logging.info("Inserted user data into 'users' table")

            if not self.postgres_db.table_exists('table_of_cars'):
                self.postgres_db.create_table_of_cars()
                logging.info("Created 'table_of_cars' table")

            username = os.getenv('USERNAME_FOR_TABLE')
            url = self.postgres_db.get_search_url_by_user_name(username)
            user_id = self.postgres_db.get_user_id_by_username(username)
            list_of_car_ids = self.postgres_db.get_list_of_info_from_car_t("id_car", "user_id", user_id)
            got_list_of_id_cars = asyncio.run(self.__start_scraping(user_id, url, list_of_car_ids))

            for i in list_of_car_ids:
                if i not in got_list_of_id_cars:
                    self.postgres_db.delete_car_from_table(user_id, i)
                    logging.info(f"Deleted car with id {i} for user {user_id}")

        except psycopg2.Error as e:
            logging.error(f"Error: Unable to perform db operations - {e}")
        finally:
            self.__create_database_dump()
            self.postgres_db.connection.close()


