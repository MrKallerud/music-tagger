import json, re, requests
from urllib.parse import urljoin
from bs4 import BeautifulSoup

from music_tagger import colors as Color
from music_tagger import util
from music_tagger.metadata import MetadataParser

class SpotifyAPI:
    NAME = "Spotify"
    WEBURL_BASE = "http://open.spotify.com"
    API_BASE = "http://api.spotify.com"
    __HTML_PARSER = "html.parser"

    __access_token = None

    @staticmethod
    def get_access_token() -> str:
        if SpotifyAPI.__access_token: return SpotifyAPI.__access_token
        response = requests.get(SpotifyAPI.WEBURL_BASE)
        if response.status_code != 200:
            raise ValueError(f"get_access_token: {response.status_code}")
        soup = BeautifulSoup(response.content, SpotifyAPI.__HTML_PARSER)
        credentials = json.loads(soup.find(id="session").get_text())
        SpotifyAPI.__access_token = credentials.get("accessToken")
        return SpotifyAPI.__access_token

    @staticmethod
    def search(query: str = "", track: str = None, artist: str = None, album: str = None, isrc: str = None, limit: int = 5, offset: int = 0, type: str = "track") -> list:
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
        return [SpotifyTrack(result) for result in response.json().get("tracks").get("items")]

    @staticmethod
    def get_audio_features(id: str):
        url = f"/v1/audio-features/{id}"
        headers = {"authorization": f"Bearer {SpotifyAPI.get_access_token()}"}
        response = requests.get(urljoin(SpotifyAPI.API_BASE, url), headers = headers)
        response.raise_for_status()
        return SpotifyAudioFeatures(response.json())

class SpotifyTrack:
    def __init__(self, data: dict):
        self.__album = SpotifyAlbum(data.get("album"))
        self.__artists = [SpotifyArtist(artist) for artist in data.get("artists")]
        self.__explicit = data.get("explicit")
        self.__features = None
        self.__id = data.get("id")
        self.__is_extended = None
        self.__isrc = data.get("external_ids").get("isrc")
        self.__name: str = data.get("name")
        self.__duration = data.get("duration_ms")
        self.__popularity = data.get("popularity")
        self.__remixers = {}
        self.__track_number = data.get("track_number")
        self.__version = None

        self.__parse_extended()
        self.__parse_brackets()
        self.__parse_dash()

    def get_api_url(self) -> str:
        return SpotifyAPI.API_BASE + "/v1/track/" + self.__id

    def get_url(self) -> str:
        return SpotifyAPI.WEBURL_BASE + "/track/" + self.__id

    def get_title(self) -> str:
        brackets = "()"
        ret = self.__name

        if len(self.__remixers.keys()) > 0:
            for kind, remixers in self.__remixers.items():
                ret += " " + brackets[0] + MetadataParser.pretty_list(remixers) + " "
                if self.__is_extended: ret += "Extended "
                ret += kind + brackets[1]
                brackets = "[]"
        elif self.__is_extended:
            if self.__version:
                self.__version = "Extended " + self.__version
            else:
                self.__version = "Extended Mix"

        if self.__version:
            ret += " " + brackets[0] + self.__version + brackets[1]

        return ret

    def get_artist(self) -> str:
        return MetadataParser.pretty_list([artist.name for artist in self.__artists])

    def get_album_artist(self) -> str:
        # TODO: Various Artists
        return self.__album.artists[0]

    def get_album(self) -> str:
        return self.__album.name

    def get_album_type(self) -> str:
        return self.__album.album_type
    
    def get_isrc(self) -> str:
        return self.__isrc

    def get_year(self) -> str:
        return self.__album.get_year()

    def get_artwork(self) -> str:
        return self.__album.artwork_url

    def get_duration(self) -> int:
        return round(self.__duration / 1000)

    def __get_audio_features(self):
        if self.__features: return self.__features
        self.__features = SpotifyAPI.get_audio_features(self.__id)
        return self.__features

    def is_explicit(self) -> bool | None:
        return self.__explicit

    def get_tempo(self) -> str | None:
        return self.__get_audio_features().get_tempo()

    def get_camelot_key(self) -> str | None:
        return self.__get_audio_features().get_camelot_key()

    def get_musical_key(self) -> str | None:
        return self.__get_audio_features().get_musical_key()

    def get_genre(self) -> str | None:
        genres = self.__album.artists[0].genres
        if genres: return genres[0]

    def get_label(self): return None
    def get_spotify_metadata(self): return None

    def __parse_extended(self):
        if util.EXTENDED_REGEX.search(self.__name):
            self.__is_extended = True

    def __parse_brackets(self):
        for match in util.BRACKET_REGEX.findall(self.__name):
            self.__parse_version(match)

            if util.FEAT_REGEX.search(match) or util.WITH_REGEX.search(match):
                self.__name = self.__name.replace(match, "")

            # Clean up string
            self.__name = re.sub(r"[(\[].*?[)\]]", "", self.__name)
            self.__name = re.sub(r"\s+", " ", self.__name).strip()

    def __parse_dash(self):
        if not util.DASH_SPLITTER_REGEX.search(self.__name): return
        split = util.DASH_SPLITTER_REGEX.split(self.__name)
        self.__parse_version(split[-1])

        # Clean up string
        self.__name = split[0]
        self.__name = re.sub(r"\s+", " ", self.__name).strip()

    def __parse_version(self, match: str):
        if not util.VERSION_REGEX.search(match): return
        parts = match.split()
        if util.YEAR_REGEX.search(match) or len(parts) == 1:
            self.__version = match
            return

        remix_type = parts[-1].title()
        remixers = util.ARTIST_SPLIT_REGEX.split(match.replace(remix_type, "").strip())
        self.__remixers[remix_type] = remixers

    def to_string(self) -> str:
        return f"{self.get_artist()} - {self.get_title()} - {self.get_album()}"

    def __eq__(self, other: object) -> bool:
        return isinstance(other, self.__class__) and self.get_isrc() == other.get_isrc()

    def __hash__(self) -> int:
        return hash(self.get_isrc())

    def __repr__(self) -> str:
        return f"{self.to_string()}: {Color.OKBLUE}{Color.UNDERLINE}{self.get_url()}{Color.ENDC}"

class SpotifyAlbum:
    def __init__(self, data: dict):
        self.id = data.get("id")
        self.album_type = data.get("album_type")
        self.total_tracks = data.get("total_tracks")
        self.artwork_url = data.get("images")[0].get("url")
        self.name = data.get("name")
        self.release_date = data.get("release_date")
        self.artists = [SpotifyArtist(artist) for artist in data.get("artists")]

    def get_api_url(self) -> str:
        return SpotifyAPI.API_BASE + "/v1/album/" + self.__id

    def get_url(self) -> str:
        return SpotifyAPI.WEBURL_BASE + "/album/" + self.__id

    def get_year(self) -> str:
        return self.release_date[:4]

    def __eq__(self, other: object) -> bool:
        return isinstance(other, self.__class__) and self.id == other.id

    def __hash__(self) -> int:
        return hash(self.id)

    def __repr__(self) -> str:
        return self.name

class SpotifyArtist:
    def __init__(self, data: dict):
        self.id = data.get("id")
        self.genres = data.get("genres")
        self.name = data.get("name")

    def get_api_url(self) -> str:
        return SpotifyAPI.API_BASE + "/v1/artist/" + self.id

    def get_url(self) -> str:
        return SpotifyAPI.WEBURL_BASE + "/artist/" + self.id

    def __eq__(self, other: object) -> bool:
        return isinstance(other, self.__class__) and self.id == other.id

    def __hash__(self) -> int:
        return hash(self.id)

    def __repr__(self) -> str:
        return self.name

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
    print(SpotifyAPI.get_access_token())
    for result in SpotifyAPI.search("Cold H)eart Claptone Extended remix"):
        print(result)
