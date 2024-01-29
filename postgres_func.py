import logging
import os

import psycopg2
from dotenv import load_dotenv

import scraper_auto_ria_dictionary

load_dotenv()
logging.basicConfig(level=logging.DEBUG)


class PostgresLogic:
    def __init__(self):
        self.connection = self.__create_new_connection()

    @classmethod
    def __create_new_connection(cls):
        try:
            connection = psycopg2.connect(host='db', database='postgres', user='postgres', password='252525')
            
            try:
                logging.info("Connection to postgres")
    
                logging.info("TRY TO MAKE THE CONNECTION")
                connection.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)
    
                logging.info("Made the connection")
                
                if cls.__check_database_exists(connection, os.getenv("DB_NAME")):
                    cls.__create_database(connection)
               
                return cls.__connect_to_postgres_db()
                    
            except psycopg2.Error as e:
                logging.info("Error: Unable to connect to the db")
                logging.error(e)
                exit(0)
            finally:
                connection.close()
                
        except psycopg2.Error as e:
            logging.info("Error: Unable to connect to the db")
            logging.error(e)
            exit(0)
            
    @classmethod
    def __connect_to_postgres_db(cls):
        """
        Try make to connect with database
        :return: connection
        """
        try:
            logging.info("TRY TO MAKE THE CONNECTION")

            connection = psycopg2.connect(host=os.getenv('DB_HOST'), database=os.getenv('DB_NAME'),
                                    user=os.getenv('DB_USER'), password=os.getenv('DB_PASSWORD'))
            logging.info("Made conn")

            with connection.cursor() as cursor:
                # Создание схемы, если она не существует
                cursor.execute(f'''CREATE SCHEMA IF NOT EXISTS {os.getenv('DB_SCHEMA')}''')

                # Ваш код для создания таблицы или других действий

            # Фиксируем изменения в базе данных
            connection.commit()
            logging.info(f"Created schema {os.getenv('DB_SCHEMA')}")

            return connection
        except psycopg2.Error as e:
            logging.info("Error: Unable to connect to the db")
            logging.error(e)
            exit(0)

    @classmethod
    def __check_database_exists(cls, connection, db_name) -> bool:
        """
        Checking exist database
        :param connection:
        :param db_name:
        :return: bool
        """
        cursor = connection.cursor()
        cursor.execute("SELECT 1 FROM pg_database WHERE datname = %s;", (db_name,))
        return cursor.fetchone() is None

    @classmethod
    def __create_database(cls, connection):
        """
        Create a new database
        :param connection:
        :return:
        """
        cursor = connection.cursor()

        logging.info("Start creating db")

        try:
            cursor.execute(f'''CREATE database {os.getenv('DB_NAME')}''')
            cursor.execute(f'''CREATE USER {os.getenv('DB_USER')} WITH PASSWORD '{os.getenv('DB_PASSWORD')}';''')
            cursor.execute(f'''ALTER ROLE {os.getenv('DB_USER')} SET client_encoding TO 'utf8';''')
            cursor.execute(f'''ALTER ROLE {os.getenv('DB_USER')} SET default_transaction_isolation TO 'read committed';''')
            cursor.execute(f'''ALTER ROLE {os.getenv('DB_USER')} SET timezone TO 'UTC';''')
            cursor.execute(f'''GRANT ALL PRIVILEGES ON DATABASE {os.getenv('DB_NAME')} TO {os.getenv('DB_USER')};''')
            connection.commit()
            logging.info(f"Created the new database with name {os.getenv('DB_NAME')}")
        except psycopg2.Error as e:
            logging.info("Error: Unable to create the new db")
            logging.error(e)
            exit(0)

    def table_exists(self, table_name: str):
        """
            Checking exist table
            :param table_name:
            :return:
            """
        with self.connection.cursor() as cursor:
            cursor.execute(f"SELECT EXISTS(SELECT 1 FROM information_schema.tables WHERE table_schema = %s AND table_name = %s)",
                           (os.getenv('DB_SCHEMA'), table_name,))
            return cursor.fetchone()[0]

    def is_table_empty(self, table_name: str, schema_name: str = os.getenv('DB_SCHEMA')) -> bool:
        """
        Check table is empty or no
        :param table_name:
        :param schema_name:
        :return:
        """
        with self.connection.cursor() as cursor:
            cursor.execute(f'SELECT COUNT(*) FROM {schema_name}.{table_name}')
            row_count = cursor.fetchone()[0]
            return row_count == 0

    def clear_advertisements(self, schema_name: str = os.getenv('DB_SCHEMA')):
        with self.connection.cursor() as cursor:
            cursor.execute(f"DELETE FROM {schema_name}.table_of_cars")

    def create_table_of_cars(self):
        """
        Create table of cars
        :return:
        """
        with self.connection.cursor() as cursor:
            try:
                cursor.execute(f'''
                    CREATE TABLE IF NOT EXISTS {os.getenv('DB_SCHEMA')}.table_of_cars (
                        id SERIAL PRIMARY KEY,
                        user_id INTEGER REFERENCES {os.getenv('DB_SCHEMA')}.users(id),
                        id_car TEXT,
                        url TEXT,
                        title TEXT,
                        price_usd INT,
                        odometer INT,
                        username TEXT,
                        phone_number TEXT,
                        image_url TEXT,
                        images_count INT,
                        car_number TEXT,
                        car_vin TEXT,
                        datetime_found TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                self.connection.commit()
            except psycopg2.Error as e:
                print("Error: Unable to create table_of_cars")
                print(e)

    def create_users_table(self, schema_name: str = os.getenv('DB_SCHEMA')):
        """
        Create users table
        :param schema_name:
        :return:
        """
        with self.connection.cursor() as cursor:
            cursor.execute(f'''
                CREATE TABLE IF NOT EXISTS {schema_name}.users (
                    id SERIAL PRIMARY KEY,
                    user_name TEXT,
                    search_url TEXT
                )
            ''')
            self.connection.commit()

    def insert_to_table_of_cars(self, user_id, id_car, url, title, price_usd, odometer, username, phone_number, image_url,
                                images_count,
                                car_number, car_vin):
        """
        Insert data to table of cars
        :param user_id:
        :param id_car:
        :param url:
        :param title:
        :param price_usd:
        :param odometer:
        :param username:
        :param phone_number:
        :param image_url:
        :param images_count:
        :param car_number:
        :param car_vin:
        :return:
        """
        with self.connection.cursor() as cursor:
            cursor.execute(f'''
                INSERT INTO {os.getenv('DB_SCHEMA')}.table_of_cars (user_id, id_car, url, title, price_usd, odometer, username, phone_number, image_url, images_count, car_number, car_vin, datetime_found)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, DEFAULT)
            ''', (
                user_id, id_car, url, title, price_usd, odometer, username, phone_number, image_url, images_count,
                car_number,
                car_vin))
            self.connection.commit()

    def insert_to_table_of_users(self, username: str, url: str):
        """
         Insert data to table of users
        :param username:
        :param url:
        :return:
        """
        if isinstance(username, str):
            pass
        else:
            username = "username1"

        with self.connection.cursor() as cursor:
            cursor.execute(f'''
                INSERT INTO {os.getenv('DB_SCHEMA')}.users (user_name, search_url)
                VALUES (%s, %s)
            ''', (username, url))
            self.connection.commit()

    def get_list_of_info_from_car_t(self, need_info: str, column: str, data_for_column) -> list:
        """
        Get dict of information of one column from the table of cars by user id
        :param need_info:
        :param column:
        :param data_for_column:
        :return:
        """
        with self.connection.cursor() as cursor:
            cursor.execute(f"SELECT {need_info} FROM {os.getenv('DB_SCHEMA')}.table_of_cars WHERE {column} = {data_for_column}")
            values = cursor.fetchall()
            info_list = [str(value[0]) for value in values]
            return info_list

    def get_info_from_car_t(self, need_info, column, data_for_column):
        with self.connection.cursor() as cursor:
            cursor.execute(f"SELECT {need_info} FROM {os.getenv('DB_SCHEMA')}.table_of_cars WHERE {column} = {data_for_column}")
            result = cursor.fetchone()
            return result[0] if result else None

    def get_search_url_by_user_name(self, user_name):
        """
        Get the search URL for a user by username
        :param user_name: User's name
        :return: Search URL for the user or None if not found
        """
        with self.connection.cursor() as cursor:
            cursor.execute(f"SELECT search_url FROM {os.getenv('DB_SCHEMA')}.users WHERE user_name = %s", (user_name,))
            result = cursor.fetchone()
            return result[0] if result else None

    def get_user_id_by_username(self, username):
        """
        Get user id by username
        :param username:
        :return:
        """
        with self.connection.cursor() as cursor:
            cursor.execute(f"SELECT id FROM {os.getenv('DB_SCHEMA')}.users WHERE user_name = %s", (username,))
            result = cursor.fetchone()
            return result[0] if result else None

    def update_info_in_t_cars(self, need_info, new_info, id_car, user_id):
        """
        Update the amount for a specific item in the db
        :param need_info:
        :param new_info:
        :param id_car:
        :param user_id:
        :return:
        """
        with self.connection.cursor() as cursor:
            cursor.execute(f'''
                UPDATE {os.getenv('DB_SCHEMA')}.table_of_cars
                SET {need_info} = {new_info}
                WHERE id_car = {id_car} and user_id = {user_id}
            ''')
            self.connection.commit()

    def delete_car_from_table(self, user_id, id_car):
        """
        Delete a car from the table based on user_id and id_car
        :param user_id: User's ID
        :param id_car: Car's ID
        :return: None
        """
        with self.connection.cursor() as cursor:
            cursor.execute(f'''
                DELETE FROM {os.getenv('DB_SCHEMA')}.table_of_cars
                WHERE user_id = %s AND id_car = %s
            ''', (user_id, id_car))
            self.connection.commit()

    @classmethod
    def __convert_keys_to_lowercase(cls, data):
        """
        Convert keys to lowercase in dict or list
        :param data:
        :return:
        """
        if isinstance(data, dict):
            return {key.lower(): cls.__convert_keys_to_lowercase(value) for key, value in data.items()}
        elif isinstance(data, list):
            return [cls.__convert_keys_to_lowercase(item) for item in data]
        else:
            return data

    def create_url_for_user(self, brand: str, model: str, id_categories: int = 0):
        logger = logging.getLogger(__name__)

        scraper_audo = scraper_auto_ria_dictionary.AutoRia()
        brands_dictionary = scraper_audo.brands
        models_dictionary = scraper_audo.models
        lowercase_keys_dictionary_of_brand = {key.lower(): value for key, value in brands_dictionary.items()}
        lowercase_keys_dictionary_of_models = self.__convert_keys_to_lowercase(models_dictionary)

        if not isinstance(brand, str) or not isinstance(model, str):
            raise ValueError("Бренд і модель повинні бути строками.")

        if brand.lower() in lowercase_keys_dictionary_of_brand.keys() and brand.lower() in lowercase_keys_dictionary_of_models.keys():
            if model.lower() in lowercase_keys_dictionary_of_models[brand.lower()]:
                model_id = lowercase_keys_dictionary_of_models[brand.lower()][
                    model.lower()]  # отримуємо id за назвою моделі
                url = f"https://auto.ria.com/uk/search/?indexName=auto,order_auto,newauto_search&categories.main.id={id_categories}&brand.id[0]={lowercase_keys_dictionary_of_brand[brand.lower()]}&model.id[0]={model_id}&country.import.usa.not=-1&price.currency=1&abroad.not=-1&custom.not=-1&page=0&size=100"
                logger.debug(f"Создан URL: {url}")
                return url
            else:
                logger.warning("Plz chose the new model for your brand or new brand and model")
                logger.info(f"{models_dictionary}")
                exit(0)
        else:
            logger.warning("Incorrect data. Brand or model not found.")
            logger.warning("Plz chose the new brand and avalible model")
            logger.info(f"{models_dictionary}")
            exit(0)
