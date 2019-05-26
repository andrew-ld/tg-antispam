import gevent.monkey
import gevent.pool
import gevent.lock
gevent.monkey.patch_all()  # noqa

import io
import config
import telegram
import dhash
import os.path
import PIL.Image
import functools
import typing


def safe_api_call(fnc: typing.Callable):
    def safe_fnc(*args, **kwargs):
        try:
            fnc(*args, **kwargs)
        except telegram.TelegramError:
            pass

    return safe_fnc


class Fucker(config.Config):
    bot: telegram.Bot

    def __init__(self):
        self.dataset = []   # type: typing.List[int]
        self.bad = []       # type: typing.List[int]

        self.banned = {}    # type: typing.Dict[int, typing.List[int]]
        self.j_time = {}    # type: typing.Dict[int, typing.Dict[int, float]]

        self.gban_lock = gevent.lock.Semaphore()
        self.exec_pool = gevent.pool.Pool()
        self.bot = telegram.Bot(self.TOKEN)

        self.reload_dataset()

    #
    # REQUESTS ABSTRACTION
    #

    def log(
        self,
        user: telegram.User,
        chat: telegram.Chat,
        text: str = ""
    ):
        text += self.LOG_MESSAGE.format(user.id, abs(chat.id))
        self.bot.send_message(self.LOG_CHAT_ID, text, "html")

    @safe_api_call
    def del_ban(
        self,
        chat: telegram.Chat,
        mess: telegram.Message,
        user: telegram.User
    ):
        name = user.mention_html()
        text = self.BAN_MESSAGE.format(name)

        mess.delete()

        if not self.is_banned(user, chat):
            chat.kick_member(user.id)
            self.add_to_banned(user, chat)

            chat.send_message(text, "html")
            self.log(user, chat, text)

    def safe_del_ban(
        self,
        chat: telegram.Chat,
        mess: telegram.Message,
        user: telegram.User
    ):
        self.gban_lock.acquire(True)
        self.del_ban(chat, mess, user)
        self.gban_lock.release()

    #
    # MESSAGE HANDLERS
    #

    def file_add_handler(
        self,
        chat: telegram.Chat,
        mess: telegram.Message
    ):
        file_id = mess.photo[-1].file_id
        self.add_to_dataset(file_id)
        chat.send_message(self.ADD_END_MSG, "html")

    def stats_handler(
        self,
        chat: telegram.Chat
    ):
        text = self.STATS_MSG.format(
            len(self.bad),
            len(self.dataset),
        )

        chat.send_message(text, "html")

    def private_handler(
        self,
        chat: telegram.Chat,
        mess: telegram.Message
    ):
        if self.is_admin(chat):
            if mess.photo:
                self.file_add_handler(chat, mess)

            else:
                self.stats_handler(chat)

        else:
            chat.send_message(self.WELCOME_MSG, "html")

    def group_handler(
        self,
        chat: telegram.chat,
        mess: telegram.Message,
        user: telegram.User
    ):
        if self.is_blacklisted(user):
            self.safe_del_ban(chat, mess, user)
            return

        self.add_to_jtime(chat, mess)

        if (
            self.low_join_time(chat, mess, user)
            and self.check_bad_words(mess)
        ):
            self.add_to_blacklist(user)
            self.safe_del_ban(chat, mess, user)
            return

        if self.check_user_propic(user):
            self.add_to_blacklist(user)
            self.safe_del_ban(chat, mess, user)

    #
    # DATA ABSTRACTION
    #

    @staticmethod
    def photos_to_file_id(photos: telegram.UserProfilePhotos) -> str:
        return photos.photos[0][-1].file_id

    def file_id_to_pil(self, file_id: str) -> PIL.Image:
        photo = self.bot.get_file(file_id)
        photo = photo.download_as_bytearray()
        photo = io.BytesIO(photo)
        photo = PIL.Image.open(photo)

        return photo

    @functools.lru_cache()
    def check_dataset(self, user_hash: int) -> bool:
        return any(
            dhash.diff(user_hash, mf_hash)
            < self.ACCEPTABLE_DIFFERENCE
            for mf_hash in self.dataset
        )

    def add_to_dataset(self, file_id: str):
        photo = self.bot.get_file(file_id)
        photo.download(self.DATASET_DIR + file_id)
        self.reload_dataset()

    def reload_dataset(self):
        self.dataset.clear()

        for name in os.listdir(self.DATASET_DIR):
            path = self.DATASET_DIR + name

            if os.path.isfile(path):
                image = PIL.Image.open(path)
                ihash = dhash.dhash_int(image)

                self.dataset.append(ihash)

    def is_admin(self, chat: telegram.Chat):
        return chat.id == self.ADMIN_ID

    #
    # JOIN TIME CONTROLLER
    #

    def get_jtime(self, chat: telegram.Chat) -> typing.Dict[int, float]:
        return self.j_time.setdefault(chat.id, {})

    def add_to_jtime(
        self,
        chat: telegram.Chat,
        mess: telegram.Message
    ):
        self.get_jtime(chat).update(
            (user.id, mess.date.timestamp())
            for user in mess.new_chat_members
        )

    def low_join_time(
        self, chat: telegram.Chat,
        mess: telegram.Message,
        user: telegram.User,
    ) -> bool:
        j_obj = self.get_jtime(chat)

        if user.id not in j_obj:
            return False

        j_time = j_obj[user.id]
        c_time = mess.date.timestamp()

        return c_time - j_time < self.ALLOWED_TIME

    #
    # BLACKLIST
    #

    def is_blacklisted(self, user: telegram.User) -> bool:
        return user.id in self.bad

    def add_to_blacklist(self, user: telegram.User):
        self.bad.append(user.id)

    def get_banned(self, chat: telegram.Chat) -> typing.List[int]:
        return self.banned.setdefault(chat.id, [])

    def is_banned(
        self,
        user: telegram.User,
        chat: telegram.Chat
    ) -> bool:
        return user.id in self.get_banned(chat)

    def add_to_banned(
        self,
        user: telegram.User,
        chat: telegram.Chat
    ):
        self.get_banned(chat).append(user.id)

    #
    # ANTI SPAM CHECKS
    #

    @functools.lru_cache()
    def check_user_propic(self, user: telegram.User) -> bool:
        photos = user.get_profile_photos()

        if not photos.photos:
            return False

        file_id = self.photos_to_file_id(photos)
        photo = self.file_id_to_pil(file_id)
        user_hash = dhash.dhash_int(photo)

        return self.check_dataset(user_hash)

    def check_bad_words(self, mess: telegram.Message) -> bool:
        if mess.text is None:
            return False

        have_links = any(
            entity.type == "url"
            for entity in mess.entities
        )

        if not (have_links or mess.forward_from):
            return False

        s_text = mess.text.lower()

        return all(
            any(
                word in s_text
                for word in words
            )

            for words in self.ILLEGAL_WORDS
        )

    #
    # UPDATES HANDLING
    #

    @safe_api_call
    def process_update(self, update: telegram.Update):
        user = update.effective_user
        chat = update.effective_chat
        mess = update.effective_message

        if None in (user, chat, mess):
            return

        if chat.type in ("group", "supergroup"):
            self.group_handler(chat, mess, user)

        if chat.type in ("private",):
            self.private_handler(user, mess)

    def raw_polling(self, offset: int) -> int:
        updates = self.bot.get_updates(offset)
        self.exec_pool.map(self.process_update, updates)

        if updates:
            return updates[-1].update_id + 1

        return offset

    def start(self, offset: int = 0):
        while True:
            offset = self.raw_polling(offset)


if __name__ == "__main__":
    bot = Fucker()
    bot.start()
