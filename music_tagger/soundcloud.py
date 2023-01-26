import re
from os.path import join
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from music_tagger.util import FOLDER
from music_tagger.metadata_parser import MetadataParser as Parser
from music_tagger.metadata_fields import MetadataFields as Fields
from music_tagger.track import Track, Artist, Album, Artwork

class SoundCloudAPI:
    NAME = "SoundCloud"
    __KEY_FILE = Path(join(FOLDER, "soundcloud.key"))
    WEBURL_BASE = "https://soundcloud.com"
    __API_BASE = "https://api-v2.soundcloud.com"

    __CLIENT_ID_REGEX = re.compile(r'client_id:"(\w{32})"')
    __JS_W_CLIENT_ID = "https://a-v2.sndcdn.com/assets/50-179ff18e.js"
    __JS_URL_REGEX = re.compile(r"https://a-v2\.sndcdn\.com/assets/\d{1,2}-\w{8}\.js")

    __client_id = None

    @staticmethod
    def get_client_id(refresh: bool = False) -> str:
        # Get stored client_id
        if not refresh:
            if SoundCloudAPI.__client_id: return SoundCloudAPI.__client_id
            if SoundCloudAPI.__KEY_FILE.is_file():
                file = SoundCloudAPI.__KEY_FILE.open("r")
                SoundCloudAPI.__client_id = file.read()
                file.close()
                return SoundCloudAPI.__client_id

        # Fetch client_id
        response = requests.get(SoundCloudAPI.__JS_W_CLIENT_ID)
        javascript = str(response.content)
        client_id = SoundCloudAPI.__CLIENT_ID_REGEX.search(javascript)
        if not client_id: raise ValueError("Couldn't get soundcloud client id")
        SoundCloudAPI.__client_id = client_id.group(1)

        # Save to file
        id_file = SoundCloudAPI.__KEY_FILE.open("w")
        id_file.write(SoundCloudAPI.__client_id)
        id_file.close()

        return SoundCloudAPI.__client_id

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
    
        return [SoundCloudAPI.get_track(result) for result in response.json().get("collection")]

    @staticmethod
    def get_track(data: dict[str, any]) -> Track:
        original_title = data.get("title")
        if " - " not in original_title:
            parser = Parser(" - " + original_title, as_strings=False)
        else: parser = Parser(original_title, as_strings=False)

        pub_met: dict = data.get("publisher metadata")
        if pub_met:
            # if parser.metadata.get(Fields.ARTISTS) is None:
            #     parser.metadata[Fields.ARTISTS] = [Artist(artist) for artist in Parser.split_list(pub_met.get("artist"))]
            parser.metadata[Fields.ISRC] = pub_met.get("isrc")
            parser.metadata[Fields.EXPLICIT] = pub_met.get("explicit")

        if parser.metadata.get(Fields.ARTISTS) is None:
            parser.metadata[Fields.ARTISTS] = [SoundCloudAPI.get_artist(data.get("user"))]

        # TODO: Parse key and urls from comment

        parser.metadata[Fields.ORIGINALFILENAME] = original_title
        parser.metadata[Fields.ALBUM] = SoundCloudAPI.get_album(data)
        parser.metadata[Fields.DESCRIPTION] = data.get("description")
        parser.metadata[Fields.DOWNLOAD] = data.get("purchase_url")
        parser.metadata[Fields.DURATION] = data.get("duration")
        parser.metadata[Fields.GENRE] = data.get("genre")
        parser.metadata[Fields.ID] = data.get("id")
        parser.metadata[Fields.LABEL] = data.get("label_name")
        parser.metadata[Fields.PLATFORM] = SoundCloudAPI.NAME
        parser.metadata[Fields.TAGS] = set([tag.strip() for tag in re.split("\s*\\\"\s*(?:\\\")?", data.get("tag_list")) if tag != ''])

        return parser.as_track()

    @staticmethod
    def get_artist(data: dict[str, any]) -> Artist:
        return Artist({
            Fields.NAME: data.get("full_name") if data.get("full_name") else data.get("username"),
            Fields.DESCRIPTION: data.get("description"),
            Fields.IMAGE: Artwork(data.get("avatar_url").replace("large", "t500x500")),
            Fields.ID: data.get("id"),
            Fields.URL: data.get("permalink_url"),
        })

    @staticmethod
    def get_album(data: dict[str, any]) -> Album:
        song_name = Parser.parse_title(data.get("title"))
        album_name = data.get("publisher metadata", {}).get("album_title")

        date = data.get("release_date") if data.get("release_date") else data.get("created_at")
        date = Parser.parse_date(date)

        image = data.get("artwork_url")
        if isinstance(image, str): image = Artwork(image.replace("large", "t500x500"))

        return Album({
            Fields.NAME: album_name,
            Fields.IMAGE: image,
            Fields.DATE: date,
            Fields.ALBUM_TYPE: Parser.parse_album_type(song_name, album_name)
        })

if __name__ == "__main__":
    # Quick tests
    # print("client_id: " + SoundCloudAPI.get_client_id(True))

    results: list[Track] = SoundCloudAPI.search("fat tony unholy remix", limit=20)
    for result in results:
        print(str(result).ljust(100), result.get(Fields.ORIGINALFILENAME))
