import json
import re
from os.path import join
from pathlib import Path
from ssl import SSLContext
from urllib.parse import urljoin
from urllib.request import urlopen

import requests
from bs4 import BeautifulSoup

from music_tagger import colors as Color
from music_tagger.util import FOLDER
from music_tagger.metadata import MetadataParser
from music_tagger.spotify import SpotifyAPI, SpotifyTrack

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
    NAME = "SoundCloud"
    __KEY_FILE = Path(join(FOLDER, "soundcloud.key"))
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
    def search(query: str = "", limit: int = 5, offset: int = 0, tries = 10) -> list:
        url = "search/tracks"

        params = {
            "q": query,
            "limit": limit,
            "offset": offset,
            "client_id": SoundCloudAPI.get_client_id()
        }

        response = requests.get(urljoin(SoundCloudAPI.__API_BASE, url), params)
        if response.status_code != 200:
            if not tries: response.raise_for_status()
            return SoundCloudAPI.search(query, limit, offset, tries - 1)
    
        return [SoundCloudTrack(result) for result in response.json().get("collection")]

class SoundCloudTrack:
    def __init__(self, data: dict):
        self.__artwork_url = data.get("artwork_url")
        self.__date = data.get("release_date") if data.get("release_date") else data.get("created_at")
        self.__description = data.get("description")
        self.__duration = data.get("duration")
        self.__genre = data.get("genre")
        self.__id = data.get("id")
        self.__label = data.get("label_name")
        self.__purchase_url = data.get("purchase_url")
        self.__tags = set([tag.strip() for tag in re.split("\s*\\\"\s*(?:\\\")?", data.get("tag_list")) if tag != ''])
        self.__title = data.get("title")
        self.__url = data.get("permalink_url")
        self.__user = SoundCloudUser(data.get("user"))

        self.__publisher_metadata = data.get("publisher_metadata")
        self.__metadata_parser = MetadataParser(self.__title)

    def get_title(self) -> str:
        # if self.__publisher_metadata:
        #     title = self.__publisher_metadata.get("release_title")
        #     if title: return title
        return self.__metadata_parser.get_title()

    def get_artist(self) -> str:
        if self.__metadata_parser.get_artist():
            return self.__metadata_parser.get_artist()

        if self.__publisher_metadata:
            artist = self.__publisher_metadata.get("artist")
            if artist: return artist
        return self.__user.get_name()

    def get_album_artist(self) -> str:
        if self.__metadata_parser.get_album_artist():
            return self.__metadata_parser.get_album_artist()
        return self.__user.get_name()

    def is_explicit(self) -> bool | None:
        if self.__publisher_metadata:
            return self.__publisher_metadata.get("explicit")

    def get_duration(self) -> int:
        return round(self.__duration / 1000)

    def get_isrc(self) -> str:
        if self.__publisher_metadata:
            return self.__publisher_metadata.get("isrc")
    
    def get_album(self) -> str:
        if self.__publisher_metadata:
            album_title = self.__publisher_metadata.get("album_title")
            if album_title: return album_title
        return self.__metadata_parser.get_album()

    def get_genre(self) -> str:
        return self.__genre
    
    def get_label(self) -> str:
        return self.__label

    def get_album_type(self) -> str:
        return "Single"

    def get_artwork(self) -> str | None:
        if self.__artwork_url:
            return self.__artwork_url.replace("large", "t500x500")
        if self.__user.avatar_url:
            return self.__user.avatar_url.replace("large", "t500x500")

    def get_year(self) -> int:
        return int(self.__date[:4])

    def get_tempo(self) -> str | None:
        return None

    def get_camelot_key(self) -> str | None:
        return None

    def get_musical_key(self) -> str | None:
        return None

    def get_spotify_metadata(self) -> SpotifyTrack | None:
        if self.__publisher_metadata and self.__publisher_metadata.get("isrc"):
            try: return SpotifyAPI.search(isrc = self.__publisher_metadata.get("isrc"))[0]
            except IndexError: return None

    def to_string(self) -> str:
        return f"{self.get_artist()} - {self.get_title()}"

    def __eq__(self, other: object) -> bool:
        if self.get_isrc() and other.get_isrc():
            return self.get_isrc() == other.get_isrc()
        return isinstance(other, self.__class__) and self.__id == other.__id

    def __hash__(self) -> int:
        if self.get_isrc(): return hash(self.get_isrc())
        return hash(self.__id)

    def __repr__(self) -> str:
        return f"{self.to_string()}: {Color.OKBLUE}{Color.UNDERLINE}{self.__url}{Color.ENDC}"

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
    results = SoundCloudAPI.search(
        "HUGEL Feat. Lorna & Jenn Morel - Tamo Loco (Extended) Available everywhere !")
    for result in results:
        print(result)
