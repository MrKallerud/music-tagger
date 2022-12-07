from music_tagger.metadata import MetadataFields as meta
from music_tagger.metadata import MetadataParser as parser
from music_tagger.util import CLEAN_SPACES_REGEX

class Track:
    def __init__(self, data: dict[str, any]):
        self.__metadata = dict(filter(lambda elem: elem[0] is not None, data.items()))

    def get(self, key: str = None):
        if not key: return self.__metadata
        return self.__metadata.get(key)

    def get_name(self) -> str:
        name = self.get(meta.NAME)

        extended = self.get(meta.EXTENDED)
        details = self.get(meta.DETAILS)
        if details:
            for detail in details:
                if extended and extended not in detail and extended not in name:
                    split = detail.split()
                    split.insert(-1, extended)
                    detail = " ".join(split)
                name += f" - {detail}"

        versions = self.get(meta.VERSIONS)
        if versions:
            for version, artists in versions.items():
                artists = parser.pretty_list(artists)
                if extended and extended not in version and extended not in name:
                    name += f" - {artists} {extended} {version}"
                else:
                    name += f" - {artists} {version}"

        return CLEAN_SPACES_REGEX.sub(" ", name).strip()

    def get_artists(self) -> str:
        if self.get(meta.ARTISTS):
            return parser.pretty_list([str(artist) for artist in self.get(meta.ARTISTS)])

    def __repr__(self) -> str:
        return self.get_artists() + " - " + self.get_name()

class Artist:
    def __init__(self, data: dict[str, any]):
        self.__metadata = data

    def get(self, key: str = None):
        if not key: return self.__metadata
        return self.__metadata.get(key)

    def get_name(self) -> str:
        return self.get(meta.NAME)

    def __repr__(self) -> str:
        return self.get_name()

class Album:
    def __init__(self, data: dict[str, any]):
        self.__metadata = data

    def get(self, key: str = None):
        if not key: return self.__metadata
        return self.__metadata.get(key)

    def get_name(self) -> str:
        return self.get(meta.NAME)

    def __repr__(self) -> str:
        return self.get_name()