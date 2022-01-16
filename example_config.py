import os

path_separator = "/"

ROOT_DIR = os.path.abspath(os.curdir)
BUILD_PATH = os.path.join(ROOT_DIR, "data" + path_separator + "db" + path_separator + "build.sql")
token = "" #Nat P
default_prefix = "$"

CLIENT_SECRET_FILE = os.path.join(ROOT_DIR, "client_secret.json")

google_sheets_id = ''
PSQL_PASSWORD = ""
PSQL_UNAME = ""
IMGFLIP_PASSWORD = ""
CATAPI_KEY = ""

if os.name == 'nt': #changes some things if we are on windows instead of linux
    path_separator = "\\"
    PSQL_UNAME = ""
    token = "" #Tom Smith
