from music_tagger.metadata import MetadataFields as meta
from music_tagger.metadata import MetadataParser as parser

class Track:
    def __init__(self, data: dict[str, any]):
        self.__metadata = dict(filter(lambda elem: elem[0] is not None, data.items()))

    def get(self, key: str = None, default = None):
        if not key: return self.__metadata
        item = self.__metadata.get(key, default)
        return item if item else default

    def get_name(self) -> str:
        name = self.get(meta.NAME)
        brackets = "()"

        extended = self.get(meta.EXTENDED)
        details = self.get(meta.DETAILS)
        if details:
            for detail in details:
                if extended and extended not in detail and extended not in name:
                    split = detail.split()
                    split.insert(-1, extended)
                    detail = " ".join(split)
                name += " " + brackets[0] + detail + brackets[1]
                brackets = "[]"

        versions = self.get(meta.VERSIONS)
        if versions:
            for version, artists in versions.items():
                artists = parser.pretty_list(artists)
                if artists: artists += " "
                if extended and extended not in version and extended not in name:
                    name += f" {brackets[0]}{artists}{extended} {version}{brackets[1]}"
                else:
                    name += f" {brackets[0]}{artists}{version}{brackets[1]}"
                brackets = "[]"

        return parser.clean_title(name)

    def get_artists(self) -> str:
        all_artists = []

        all_artists.extend(self.get(meta.ARTISTS, []))
        all_artists.extend(self.get(meta.WITH, []))
        all_artists.extend(self.get(meta.FEATURING, []))
        for _, artists in self.get(meta.VERSIONS, {}).items():
            all_artists.extend(artists)

        all_artists = [str(artist) for artist in all_artists]
        all_artists = list(dict.fromkeys(all_artists))

        return parser.pretty_list(all_artists)

    def __repr__(self) -> str:
        return self.get_artists() + " - " + self.get_name()

class Artist:
    def __init__(self, data: dict[str, any] | str):
        if isinstance(data, str):
            self.__metadata = {meta.NAME: data}
        else:
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