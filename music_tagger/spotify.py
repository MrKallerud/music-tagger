import json, re, requests
from urllib.parse import urljoin
from bs4 import BeautifulSoup

from music_tagger import colors as Color
from music_tagger import util
from music_tagger.metadata_parser import MetadataParser as Parser
from music_tagger.metadata_fields import MetadataFields as Fields
from music_tagger.track import Track, Artist, Album, Artwork

class SpotifyAPI:
    NAME = "Spotify"
    WEBURL_BASE = "https://open.spotify.com"
    API_BASE = "https://api.spotify.com"
    __HTML_PARSER = "html.parser"

    __access_token = None

    @staticmethod
    def get_access_token() -> str:
        if SpotifyAPI.__access_token: return SpotifyAPI.__access_token
        response = requests.get(SpotifyAPI.WEBURL_BASE)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, SpotifyAPI.__HTML_PARSER)
        credentials = json.loads(soup.find(id="session").get_text())
        SpotifyAPI.__access_token = credentials.get("accessToken")
        return SpotifyAPI.__access_token

    @staticmethod
    def search(query: str = "", track: str = None, artist: str = None, album: str = None, isrc: str = None, limit: int = 5, offset: int = 0, type: str = "track") -> list[Track]:
        url = "/v1/search"
        if track: query += f" track:{track}"
        if artist: query += f" artist:{artist}"
        if album: query += f" album:{album}"
        if isrc: query += f" isrc:{isrc}"

        params = {
            "q": query.strip(),
            "limit": limit,
            "offset": offset,
            "type": type
        }

        headers = {"authorization": f"Bearer {SpotifyAPI.get_access_token()}"}
        
        response = requests.get(urljoin(SpotifyAPI.API_BASE, url), params, headers = headers)
        response.raise_for_status()
        return [SpotifyAPI.get_track(result) for result in response.json().get("tracks").get("items")]

    @staticmethod
    def get_track(data: dict[str, any]) -> Track:
        parser = Parser(" - " + data.get("name"), as_strings = False)

        parser.metadata[Fields.ALBUM] = SpotifyAPI.get_album(data.get("album"))
        parser.metadata[Fields.ARTISTS] = [SpotifyAPI.get_artist(artist) for artist in data.get("artists")]
        parser.metadata[Fields.DURATION] = data.get("duration_ms")
        parser.metadata[Fields.EXPLICIT] = data.get("explicit")
        parser.metadata[Fields.ORIGINALFILENAME] = data.get("name")
        parser.metadata[Fields.ID] = data.get("id")
        parser.metadata[Fields.ISRC] = data.get("external_ids").get("isrc")
        parser.metadata[Fields.PLATFORM] = SpotifyAPI.NAME
        parser.metadata[Fields.POPULARITY] = data.get("popularity")
        parser.metadata[Fields.TRACK_NUMBER] = data.get("track_number")
        parser.metadata[Fields.URL] = SpotifyAPI.WEBURL_BASE + "/track/" + data.get("id")

        return parser.as_track()

    @staticmethod
    def get_artist(data: dict[str, any]) -> Artist:
        return Artist({
            Fields.GENRE: data.get("genres"),
            Fields.ID: data.get("id"),
            Fields.NAME: data.get("name"),
            Fields.URL: SpotifyAPI.WEBURL_BASE + "/artist/" + data.get("id"),
        })

    @staticmethod
    def get_album(data: dict[str, any]) -> Album:
        return Album({
            Fields.ALBUM_TYPE: data.get("album_type"),
            Fields.ARTISTS: [SpotifyAPI.get_artist(artist) for artist in data.get("artists")],
            Fields.DATE: Parser.parse_date(data.get("release_date")),
            Fields.ID: data.get("id"),
            Fields.IMAGE: Artwork(data.get("images")[0].get("url")),
            Fields.NAME: data.get("name"),
            Fields.TRACK_COUNT: data.get("total_tracks"),
            Fields.URL: SpotifyAPI.WEBURL_BASE + "/album/" + data.get("id"),
        })

    @staticmethod
    def get_audio_features(id: str):
        url = f"/v1/audio-features/{id}"
        headers = {"authorization": f"Bearer {SpotifyAPI.get_access_token()}"}
        response = requests.get(urljoin(SpotifyAPI.API_BASE, url), headers = headers)
        response.raise_for_status()
        return SpotifyAudioFeatures(response.json())

class SpotifyAudioFeatures:
    __PITCH_CLASS = [
        "C",  # 0
        "C#", # 1
        "D",  # 2
        "D#", # 3
        "E",  # 4
        "F",  # 5
        "F#", # 6
        "G",  # 7
        "G#", # 8
        "A",  # 9
        "A#", # 10
        "B",  # 11
    ]

    __PITCH_CAMELOT = {
        "G#min": "1A",
        "D#min": "2A",
        "A#min": "3A",
        "Fmin":  "4A",
        "Cmin":  "5A",
        "Gmin":  "6A",
        "Dmin":  "7A",
        "Amin":  "8A",
        "Emin":  "9A",
        "Bmin":  "10A",
        "F#min": "11A",
        "C#min": "12A",
        "Bmaj":  "1B",
        "F#maj": "2B",
        "C#maj": "3B",
        "G#maj": "4B",
        "D#maj": "5B",
        "A#maj": "6B",
        "Fmaj":  "7B",
        "Cmaj":  "8B",
        "Gmaj":  "9B",
        "Dmaj":  "10B",
        "Amaj":  "11B",
        "Emaj":  "12B",
    }

    def __init__(self, data: dict) -> None:
        self.energy: float = data.get("energy")
        self.key: int = data.get("key")
        self.loudness: float = data.get("loudness")
        self.mode = bool(data.get("mode"))
        self.tempo: float = data.get("tempo")

    def get_camelot_key(self) -> str:
        return self.__PITCH_CAMELOT.get(self.get_musical_key())

    def get_musical_key(self) -> str:
        scale = "maj" if self.mode else "min"
        return self.__PITCH_CLASS[self.key] + scale

    def get_tempo(self) -> int:
        return round(self.tempo)

if __name__ == "__main__":
    # Quick tests
    print(SpotifyAPI.get_access_token(), end='\n\n')

    for result in SpotifyAPI.search("Cold Heart Claptone Remix", limit=10):
        print(result)
        print(result.get())
        break
