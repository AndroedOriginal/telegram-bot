import os

# Единая папка для всех файлов состояния бота (events.json, warnings.json,
# user_directory.json), отдельно от кода. Это позволяет примонтировать сюда
# один persistent volume на хостинге, не затрагивая .py файлы, которые
# лежат рядом в handlers/ и utils/.
DATA_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data"
)

os.makedirs(DATA_DIR, exist_ok=True)


def data_path(filename):
    return os.path.join(DATA_DIR, filename)
