class Config:
    DATASET_DIR = "dataset/"

    TOKEN = ...

    LOG_CHAT_ID = ...

    ADMIN_ID = ...

    ACCEPTABLE_DIFFERENCE = 10

    ALLOWED_TIME = 10

    WELCOME_MSG = "this bot works <b>only in groups</> with <b>delete</> and <b>ban</> permissions, " \
                  "automatically ban all <code>dex testnet spammer/scammer</>"

    STATS_MSG = "<b>Cache details</b>\n\n" \
                "Banned users: <code>{}</>\n" \
                "Dataset size: <code>{}</>"

    ADD_END_MSG = "<b>done!</b>"

    BAN_MESSAGE = "I have banned {}"

    LOG_MESSAGE = "\n#user_id{}\n#chat_id{}"

    ILLEGAL_WORDS = (
        ("btc", "eth", "bitcoin", "ethereum", "blockchain", "giveway", "hello!", "binance"),
        ("exchange", "prize", "address", "day", "confirm", "wallet", "participate", "good news")
    )
