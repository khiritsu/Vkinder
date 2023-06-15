# импорты
import vk_api
from vk_api.longpoll import VkLongPoll, VkEventType
from vk_api.utils import get_random_id
import psycopg2

from config import comunity_token, acces_token
from core import VkTools

# отправка сообщений
class BotInterface():
    def __init__(self, comunity_token, acces_token):
        self.vk = vk_api.VkApi(token=comunity_token)
        self.longpoll = VkLongPoll(self.vk)
        self.vk_tools = VkTools(acces_token)
        self.params = {}
        self.worksheets = []
        self.offset = 0

        # Создание подключения к базе данных
        self.conn = psycopg2.connect(database="VKinder", user="postgres", password="your_password", host="localhost", port="5432")

    def __del__(self):
        # Закрытие подключения к базе данных при уничтожении объекта
        self.conn.close()

    def message_send(self, user_id, message, attachment=None):
        self.vk.method('messages.send',
                       {'user_id': user_id,
                        'message': message,
                        'attachment': attachment,
                        'random_id': get_random_id()}
                       )

    def check_profile_in_database(self, user_id):
        cursor = self.conn.cursor()

        cursor.execute("SELECT * FROM matches WHERE profile_id = %s", (user_id,))
        result = cursor.fetchone()

        return result is not None

    def add_profile_to_database(self, user_id):
        cursor = self.conn.cursor()

        cursor.execute("INSERT INTO matches (profile_id) VALUES (%s)", (user_id,))
        self.conn.commit()

    def event_handler(self):
        for event in self.longpoll.listen():
            if event.type == VkEventType.MESSAGE_NEW and event.to_me:
                if event.text.lower() == 'привет':
                    self.params = self.vk_tools.get_profile_info(event.user_id)
                    self.message_send(event.user_id, f'Привет друг, {self.params["name"]}')
                elif event.text.lower() == 'поиск':
                    self.message_send(event.user_id, 'Начинаем поиск')
                    if self.worksheets:
                        worksheet = self.worksheets.pop()
                        photos = self.vk_tools.get_photos(worksheet['id'])
                        photo_string = ''
                        for photo in photos:
                            photo_string += f'photo{photo["owner_id"]}_{photo["id"]},'
                    else:
                        self.worksheets = self.vk_tools.search_worksheet(self.params, self.offset)
                        worksheet = self.worksheets.pop()

                        if not self.check_profile_in_database(event.user_id):
                            self.add_profile_to_database(event.user_id)

                        photos = self.vk_tools.get_photos(worksheet['id'])
                        photo_string = ''
                        for photo in photos:
                            photo_string += f'photo{photo["owner_id"]}_{photo["id"]},'
                        self.offset += 50

                    self.message_send(
                        event.user_id,
                        f'Имя: {worksheet["name"]} Ссылка: vk.com/{worksheet["id"]}',
                        attachment=photo_string
                    )
                elif event.text.lower() == 'пока':
                    self.message_send(event.user_id, 'До новых встреч')
                else:
                    self.message_send(event.user_id, 'Неизвестная команда')

if __name__ == '__main__':
    bot_interface = BotInterface(comunity_token, acces_token)
    bot_interface.event_handler()
