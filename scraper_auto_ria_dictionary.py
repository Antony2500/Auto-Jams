import re
import requests
import asyncio
import aiohttp
from bs4 import BeautifulSoup
from transliterate import translit


class AutoRia:
    def __init__(self):
        self.categories = self.__make_dict_of_categories()
        self.brands = self.__make_dict_of_brands()
        self.models = asyncio.run(self.__make_dict_of_models(self.__dict_of_urls_for_find_ids_models(self.brands),
                                                           asyncio.run(self.__make_dict_of_marks_without_id(
                                                               self.__make_dict_of_urls_for_brands(self.brands)))))

    @classmethod
    def __make_dict_of_categories(cls) -> dict:
        """
            Create dict of categories for using
        :return: dict of categories on AutoRia
        """
        url = "https://auto.ria.com/uk/"

        dict_of_categories = {}

        response = requests.get(url)

        if response.status_code == 200:
            soup = BeautifulSoup(response.text, "html.parser")

            tag_select = soup.find("select", {"id": "categories", "name": "category_id",
                                              "data-field": "category",
                                              "aria-label": "Тип транспорту"}) if soup.find("select",
                                                                                            {"id": "categories",
                                                                                             "name": "category_id",
                                                                                             "data-field": "category",
                                                                                             "aria-label": "Тип транспорту"}) else None

            if tag_select:
                for option in tag_select.find_all("option"):
                    dict_of_categories[option.text.lower()] = option["value"]

            else:
                print("Trouble with bot")

        return dict_of_categories

    @classmethod
    def __make_dict_of_brands(cls):
        """
            Create dict of brand for using
        :return: dict of categories on AutoRia
        """
        url = "https://auto.ria.com/uk/search/?indexName=auto,order_auto,newauto_search&country.import.usa.not=-1&price.currency=1&abroad.not=0&custom.not=1&page=0&size=10"
        # Отправляем GET-запрос
        response = requests.get(url)
        dict_of_brands = {}
        # Проверяем успешность запроса
        if response.status_code == 200:
            # Создаем объект BeautifulSoup
            soup = BeautifulSoup(response.text, 'html.parser')
            options_with_attributes = soup.select('option[data-count][value]')
            new_options_with_attributes = set(options_with_attributes)
            russian_pattern = re.compile('[а-яА-Я]')
            count = 0

            for option in new_options_with_attributes:
                count += 1
                if russian_pattern.search(option.text):
                    dict_of_brands[translit(option.text.split("(")[0].strip(), 'ru', reversed=True)] = option["value"]
                else:
                    dict_of_brands[option.text.split("(")[0].strip()] = option["value"]

        else:
            print(f"Ошибка {response.status_code}: Невозможно получить доступ к странице.")

        return dict_of_brands

    @classmethod
    def __make_dict_of_urls_for_brands(cls, dict_of_brands: dict) -> dict:
        if dict_of_brands:
            url = "https://auto.ria.com/uk/hub/"
            dict_of_url_brands = {}

            for brand in dict_of_brands.keys():
                dict_of_url_brands[brand] = url + brand.lower()

            return dict_of_url_brands
        else:
            return {}

    SEMAPHORE_LIMIT = 8

    @classmethod
    async def __make_dict_of_marks_without_id(cls, dict_of_url_brands):
        if dict_of_url_brands:
            async with aiohttp.ClientSession() as session:
                semaphore = asyncio.Semaphore(cls.SEMAPHORE_LIMIT)
                tasks = [cls.__make_list_of_marks_without_id_and_with_semaphore(semaphore, session, ad) for ad in
                         dict_of_url_brands.values()]
                results = await asyncio.gather(*tasks)

                print(len(dict(zip(dict_of_url_brands.keys(), results))))
                return dict(zip(dict_of_url_brands.keys(), results))
        else:
            return {}

    @classmethod
    async def __make_list_of_marks_without_id_and_with_semaphore(cls, semaphore, session, url):
        async with semaphore:
            return await cls.__make_list_of_marks(session, url)

    @classmethod
    async def __make_list_of_marks(cls, session, url):
        try:
            async with session.get(url) as response:
                if response.status == 200:
                    html = await response.text()
                    soup = BeautifulSoup(html, "html.parser")
                    list_of_models = []

                    a_tags = soup.find_all("a", class_="elem")

                    if a_tags:
                        for a in a_tags:
                            list_of_models.append(a.text.split("(")[0].strip())
                        print(list_of_models)
                        return list_of_models
                    else:
                        print(list_of_models)
                        return list_of_models
        except Exception as e:
            print(f"Error: {e}")
            return []

    @classmethod
    def __dict_of_urls_for_find_ids_models(cls, dict_of_brands: dict):
        if dict_of_brands:
            first_part_url = "https://auto.ria.com/uk/search/?indexName=auto,order_auto,newauto_search&brand.id[0]="
            last_part_url = "&country.import.usa.not=-1&price.currency=1&abroad.not=0&custom.not=1&page=0&size=10"
            dict_of_urls_for_find_ids_models = {}

            for brand, id_brand in dict_of_brands.items():
                dict_of_urls_for_find_ids_models[brand] = first_part_url + id_brand + last_part_url

            return dict_of_urls_for_find_ids_models
        else:
            return {}

    @classmethod
    async def __make_dict_of_models(cls, dict_of_urls_for_find_ids_models: dict, dict_of_marks_without_id: dict):
        if dict_of_urls_for_find_ids_models and dict_of_marks_without_id:
            async with aiohttp.ClientSession() as session:
                semaphore = asyncio.Semaphore(cls.SEMAPHORE_LIMIT)
                tasks = [
                    cls.__make_list_of_models_with_semaphore(semaphore, session, url, dict_of_marks_without_id[brand]) for
                    brand, url in dict_of_urls_for_find_ids_models.items()]
                results = await asyncio.gather(*tasks)

                print(len(dict(zip(dict_of_urls_for_find_ids_models.keys(), results))))
                return dict(zip(dict_of_urls_for_find_ids_models.keys(), results))
        else:
            return {}

    @classmethod
    async def __make_list_of_models_with_semaphore(cls, semaphore, session, url, list_of_models):
        async with semaphore:
            return await cls.__make_dict_of_dict_models(session, url, list_of_models)

    @classmethod
    async def __make_dict_of_dict_models(cls, session, url, list_of_models):
        try:
            async with session.get(url) as response:
                if list_of_models != []:
                    html = await response.text()
                    soup = BeautifulSoup(html, "html.parser")
                    dict_of_models_with_id = {}
                    tag_options = set(soup.select("option[data-count][value]"))

                    print(url)

                    for option in tag_options:
                        model = option.text.split("(")[0].strip()
                        if model in list_of_models:
                            dict_of_models_with_id[model] = option["value"]
                    print(dict_of_models_with_id)
                    return dict_of_models_with_id
                else:
                    return []
        except Exception as e:
            print(f"Error: {e}")
            return []


