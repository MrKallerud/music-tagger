import requests, json, re
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from music_tagger.metadata import MetadataParser
from difflib import SequenceMatcher
from music_tagger.exceptions import HTTPError
from music_tagger import util
from music_tagger import colors as Color

class SpotifyAPI:
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
    def identify(filename):
        metadata = MetadataParser(filename)

        print(metadata)
        print()

        try: artists, title, id = SpotifyAPI.search(track = metadata.get_title(), artist = metadata.get_album_artist())
        except TypeError:
            artists, title, id = SpotifyAPI.search(filename)

        # Compare result
        tr = SequenceMatcher(None, metadata.get_title(), title).ratio()
        print(f"{tr=}")
        if tr < 0.6: raise ValueError("Titles don't match")

        ar = 0
        for m_artist in metadata.artists:
            ratio = 0
            for s_artist in artists:
                comp = SequenceMatcher(None, m_artist, s_artist).ratio()
                print(f"{comp=}")
                if ratio < comp: ratio = comp
                print(f"{ratio=}")
            ar += ratio
        print(f"{ar=}")
        ar /= len(metadata.artists)

        print(f"{ar=}")

        return f"Ratio: {(tr * 2 + ar) / 3} - " + ", ".join(artists) + f" - {title} ({id})"

    @staticmethod
    def search(query: str = "", track: str = None, artist: str = None, album: str = None, isrc: str = None, limit: int = 10, offset: int = 0, type: str = "track") -> list:
        url = "/v1/search"
        if track: query += f" track:{track}"
        if artist: query += f" artist:{artist}"
        if album: query += f" album:{album}"
        if isrc: query += f" isrc:{isrc}"

        params = {
            "q": query,
            "limit": limit,
            "offset": offset,
            "type": type
        }

        headers = {
            "authorization": f"Bearer {SpotifyAPI.get_access_token()}"
        }

        response = requests.get(urljoin(SpotifyAPI.API_BASE, url), params, headers = headers)

        # TODO: Handle status code and other forms of results
        if response.status_code != 200: raise HTTPError(response.status_code, "SPOTIFY HTTP ERROR")

        return [SpotifyTrack(result) for result in response.json().get("tracks").get("items")]

    @staticmethod
    def get_audio_features(id: str):
        url = f"/v1/audio-features/{id}"
        headers = {"authorization": f"Bearer {SpotifyAPI.get_access_token()}"}
        response = requests.get(urljoin(SpotifyAPI.API_BASE, url), headers = headers)
        if response.status_code != 200: raise HTTPError(response.status_code, "SPOTIFY HTTP ERROR")
        return SpotifyAudioFeatures(response.json())

class SpotifyTrack:
    def __init__(self, data: dict):
        self.explicit = data.get("explicit")
        self.id = data.get("id")
        self.isrc = data.get("external_ids").get("isrc")
        self.__name: str = data.get("name")
        self.popularity = data.get("popularity")
        self.track_number = data.get("track_number")
        self.__artists = [SpotifyArtist(artist) for artist in data.get("artists")]
        self.album = SpotifyAlbum(data.get("album"))
        self.__features = None
        self.is_extended = None
        self.version = None
        self.remixers = {}

        self.__parse_extended()
        self.__parse_brackets()
        self.__parse_dash()

    def get_api_url(self) -> str:
        return urljoin(SpotifyAPI.API_BASE + "/v1/track", self.id)

    def get_web_url(self) -> str:
        return SpotifyAPI.WEBURL_BASE + "/track/" + self.id

    def get_title(self) -> str:
        brackets = "()"
        ret = self.__name

        if len(self.remixers.keys()) > 0:
            for kind, remixers in self.remixers.items():
                ret += " " + brackets[0] + MetadataParser.pretty_list(remixers) + " "
                if self.is_extended: ret += "Extended "
                ret += kind + brackets[1]
                brackets = "[]"
        elif self.is_extended:
            if self.version:
                self.version = "Extended " + self.version
            else:
                self.version = "Extended Mix"

        if self.version:
            ret += " " + brackets[0] + self.version + brackets[1]

        return ret

    def get_artists(self) -> str:
        return MetadataParser.pretty_list([artist.name for artist in self.__artists])

    def get_audio_features(self) -> str:
        if self.__features: return self.__features
        self.__features = SpotifyAPI.get_audio_features(self.id)
        return self.__features

    def __parse_extended(self):
        if util.EXTENDED_REGEX.search(self.__name):
            self.is_extended = True

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
            self.version = match
            return

        remix_type = parts[-1].title()
        remixers = util.ARTIST_SPLIT_REGEX.split(re.sub(remix_type, "", match, flags = re.I).strip())
        self.remixers[remix_type] = remixers

    def to_string(self) -> str:
        return f"{self.get_artists()} - {self.get_title()} ({self.album.name})"

    def __eq__(self, other: object) -> bool:
        return isinstance(other, self.__class__) and self.id == other.id

    def __hash__(self) -> int:
        return hash(self.id)

    def __repr__(self) -> str:
        return f"{self.to_string()}: {Color.OKBLUE}{Color.UNDERLINE}{self.get_web_url()}{Color.ENDC}"

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
        return urljoin(urljoin(SpotifyAPI.API_BASE, "v1/album"), self.id)

    def get_web_url(self) -> str:
        return urljoin(urljoin(SpotifyAPI.WEBURL_BASE, "album"), self.id)

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
        self.name = data.get("name")

    def get_api_url(self) -> str:
        return urljoin(urljoin(SpotifyAPI.API_BASE, "v1/artist"), self.id)

    def get_web_url(self) -> str:
        return urljoin(urljoin(SpotifyAPI.WEBURL_BASE, "artist"), self.id)

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
    for result in SpotifyAPI.search("skazi Artillery psy mix"):
        print(result.version)
        print(result)
        exit(0)
