import json, re
from pathlib import Path
from ssl import SSLContext
from urllib.parse import urljoin
from urllib.request import urlopen
from music_tagger import colors as Color

import requests
from bs4 import BeautifulSoup

from music_tagger.exceptions import HTTPError

ssl_verify=True

def get_ssl_setting():
    if ssl_verify:
        return None
    else:
        return SSLContext()

def get_url(url):
    return urlopen(url,context=get_ssl_setting()).read()

def get_page(url):
    return get_url(url).decode('utf-8')

def get_obj_from(url):
    try:
        return json.loads(get_page(url))
    except Exception:
        return False

class SoundCloudAPI:
    __KEY_FILE = Path(".soundcloud.key")
    WEBURL_BASE = "https://soundcloud.com"
    __API_BASE = "https://api-v2.soundcloud.com"

    __client_id = None

    @staticmethod
    def get_client_id(refresh: bool = False) -> str:
        # Get stored client_id
        if not refresh:
            if SoundCloudAPI.__client_id: return SoundCloudAPI.__client_id
            elif SoundCloudAPI.__KEY_FILE.is_file():
                file = SoundCloudAPI.__KEY_FILE.open("r")
                SoundCloudAPI.__client_id = file.read()
                file.close()
                return SoundCloudAPI.__client_id

        # Fetch client_id
        page_text = get_page(SoundCloudAPI.WEBURL_BASE)
        script_urls = SoundCloudAPI.__find_script_urls(page_text)
        for script in script_urls:
            if not SoundCloudAPI.__client_id and type(script) is str and not "":
                    js_text = f'{get_page(script)}'
                    SoundCloudAPI.__client_id = SoundCloudAPI.__find_client_id(js_text)

        # Save to file
        id_file = SoundCloudAPI.__KEY_FILE.open("w")
        id_file.write(SoundCloudAPI.__client_id)
        id_file.close()

        return SoundCloudAPI.__client_id

    @staticmethod
    def __find_script_urls(html_text):
        dom = BeautifulSoup(html_text, 'html.parser')
        scripts = dom.findAll('script', attrs={'src': True})
        scripts_list = []
        for script in scripts:
            src = script['src']
            if 'cookielaw.org' not in src:  # filter out cookielaw.org
                scripts_list.append(src)
        return scripts_list

    @staticmethod
    def __find_client_id(script_text):
        client_id = re.findall(r'client_id=([a-zA-Z0-9]+)', script_text)
        if len(client_id) > 0:
            return client_id[0]
        else:
            return False

    @staticmethod
    def search(query: str = "", limit: int = 3, offset: int = 0, tries = 10):
        url = "search/tracks"

        params = {
            "q": query,
            "limit": limit,
            "offset": offset,
            "client_id": SoundCloudAPI.get_client_id()
        }

        response = requests.get(urljoin(SoundCloudAPI.__API_BASE, url), params)
        if response.status_code != 200:
            if not tries: raise HTTPError(response.status_code, "SOUNDCLOUD HTTP ERROR")
            return SoundCloudAPI.search(query, limit, offset, tries - 1)
    
        return [SoundCloudMetadata(result) for result in response.json().get("collection")]

class SoundCloudMetadata:
    def __init__(self, data: dict):
        self.__artwork_url = data.get("artwork_url")
        self.__date = data.get("release_date") if data.get("release_date") else data.get("created_at")
        self.description = data.get("description")
        self.genre = data.get("genre")
        self.id = data.get("id")
        self.purchase_url = data.get("purchase_url")
        self.tag_list = re.split("\s*\\\"\s*(?:\\\")?", data.get("tag_list"))
        self.tag_list = set([tag.strip() for tag in self.tag_list if tag != ''])
        self.title = data.get("title")
        self.url = data.get("permalink_url")
        self.user = SoundCloudUser(data.get("user"))

    def get_artwork_url(self) -> str:
        return self.__artwork_url.replace("large", "t500x500")

    def get_year(self) -> str:
        return self.__date[:4]

    def __eq__(self, other: object) -> bool:
        return isinstance(other, self.__class__) and self.id == other.id

    def __hash__(self) -> int:
        return hash(self.id)

    def __repr__(self) -> str:
        return f"{self.title}: {Color.OKBLUE}{Color.UNDERLINE}{self.url}{Color.ENDC}"

class SoundCloudUser:
    def __init__(self, data: dict):
        self.avatar_url = data.get("avatar_url")
        self.description = data.get("description")
        self.first_name = data.get("first_name")
        self.full_name = data.get("full_name")
        self.id = data.get("id")
        self.last_name = data.get("last_name")
        self.url = data.get("permalink_url")
        self.username = data.get("username")

    def get_name(self) -> str:
        return self.full_name if self.full_name else self.username
    
    def __eq__(self, other: object) -> bool:
        return isinstance(other, self.__class__) and self.id == other.id
    
    def __hash__(self) -> int:
        return hash(self.id)

    def __repr__(self) -> str:
        return f"{self.get_name()} ({self.username}): {self.url}"

if __name__ == "__main__":
    # Quick tests
    for result in SoundCloudAPI.search("fat tony unholy remix"):
        print(result)