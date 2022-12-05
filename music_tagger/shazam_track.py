from music_tagger import colors as Color
from music_tagger.spotify import SpotifyAPI, SpotifyTrack
from requests import HTTPError

class ShazamTrack:
    def __init__(self, data: dict) -> None:
        if not data.get("isrc"): data = data.get("track")

        self.__isrc = data.get("isrc")
        self.__artwork = data.get("images").get("coverarthq").replace("400x400", "800x800")
        self.__genre = data.get("genres").get("primary")
        self.__title = data.get("title")
        self.__url = data.get("url")
        self.__artist = data.get("subtitle")
        self.__metadata = {}

        self.__spotify = None

        for json in data.get("sections")[0].get("metadata"):
            self.__metadata[json.get("title").lower()] = json.get("text")

    def get_artwork(self) -> str:
        return self.__artwork

    def get_title(self) -> str:
        return self.__title

    def get_artist(self) -> str:
        return self.__artist
    
    def get_album(self) -> str:
        return self.__metadata.get("album")
    
    def get_genre(self) -> str:
        return self.__genre
    
    def get_year(self) -> int:
        return int(self.__metadata.get("released"))
    
    def get_label(self) -> int:
        return self.__metadata.get("label")
    
    def get_isrc(self) -> int:
        return self.__isrc

    def get_duration(self) -> int:
        if self.get_spotify_metadata():
            return self.get_spotify_metadata().get_duration()
        return 0

    def get_spotify_metadata(self, matches: list[SpotifyTrack] = []) -> SpotifyTrack | None:
        if self.__spotify: return self.__spotify
        if not self.__isrc: return
        if not matches: matches = SpotifyAPI.search(isrc=self.__isrc, limit = 10)

        for match in filter(lambda match: match.get_isrc() == self.__isrc, matches):
            return match

    def to_string(self) -> str:
        return f"{self.get_artist()} - {self.get_title()} - {self.get_album()}"

    def __eq__(self, other: object) -> bool:
        return isinstance(other, self.__class__) and self.__isrc == other.__isrc

    def __hash__(self) -> int:
        return hash(self.__isrc)

    def __repr__(self) -> str:
        return f"{self.to_string()}: {Color.OKBLUE}{Color.UNDERLINE}{self.__url}{Color.ENDC}"
