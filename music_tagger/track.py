from mutagen.id3 import APIC, PictureType
from PIL import Image
from PIL.Image import Resampling

from music_tagger.metadata_fields import MetadataFields as Fields
from music_tagger.metadata_parser import MetadataParser as Parser


class Track:
    def __init__(self, data: dict[str, any] = None):
        if data is None: self.__metadata = {}; return None
        if isinstance(data, str): self.__metadata = {Fields.NAME: data}
        else: self.__metadata = {k: v for k, v in data.items() if v is not None}

        # Type tests
        if self.__metadata.get(Fields.ARTISTS):
            assert isinstance(self.__metadata.get(Fields.ARTISTS)[0], Artist)
        if self.__metadata.get(Fields.ALBUM):
            assert isinstance(self.__metadata.get(Fields.ALBUM), Album)
            if self.__metadata.get(Fields.IMAGE):
                assert isinstance(self.__metadata.get(Fields.IMAGE), Artwork)

    def get(self, key: str = None, default = None):
        if not key: return self.__metadata
        item = self.__metadata.get(key, default)
        return item if item else default

    def get_name(self) -> str:
        name = self.get(Fields.NAME, "")
        extended = self.get(Fields.EXTENDED)
        brackets = "()"

        for detail in self.get(Fields.DETAILS, []):
            if extended and extended not in detail and extended not in name:
                split = detail.split()
                split.insert(-1, extended)
                detail = " ".join(split)
            name += " " + brackets[0] + detail + brackets[1]
            brackets = "[]"

        for version, artists in self.get(Fields.VERSIONS, {}).items():
            artists = Parser.format_list([artist.get_name() for artist in artists])
            if artists: artists += " "
            if extended and extended not in version and extended not in name:
                name += f" {brackets[0]}{artists}{extended} {version}{brackets[1]}"
            else:
                name += f" {brackets[0]}{artists}{version}{brackets[1]}"
            brackets = "[]"

        if extended is not None and extended not in name:
            name += " " + brackets[0] + f"{extended} Mix" + brackets[1]

        return Parser.clean_string(name)

    def get_artists(self) -> str:
        all_artists: list[Artist] = []

        all_artists.extend(self.get(Fields.ARTISTS, []))
        all_artists.extend(self.get(Fields.WITH, []))
        all_artists.extend(self.get(Fields.FEATURING, []))
        for _, artists in self.get(Fields.VERSIONS, {}).items():
            all_artists.extend(artists)

        all_artists = [artist.get_name() for artist in all_artists]
        all_artists = list(dict.fromkeys(all_artists))

        return Parser.format_list(all_artists)

    def get_search_strings(self) -> list[str]:
        """Returns a list of strings that can be used to locate the track online."""
        search = []
        if self.get(Fields.ORIGINALFILENAME):
            search.append(self.get(Fields.ORIGINALFILENAME))
        if self.get_artists() and self.get_name():
            search.append(self.get_artists() + " " + self.get_name())
        if len(self.get(Fields.ARTISTS, [])) > 0 and self.get_name():
            search.append(self.get(Fields.ARTISTS)[0].get_name() + " " + self.get_name())
        if self.get_name(): search.append(self.get_name())

        return search

    def compare_to(self, other) -> float:
        from music_tagger.matcher import Matcher
        return Matcher.compare_tracks(self, other)

    def __eq__(self, other: object) -> bool:
        from music_tagger.matcher import Matcher
        return self.compare_to(other) > Matcher.THRESHOLD

    def __hash__(self) -> int:
        if self.get(Fields.ISRC): return hash(self.get(Fields.ISRC))
        if self.get(Fields.ID): return hash(self.get(Fields.ID))
        return hash(str(self))

    def __repr__(self) -> str:
        return "<" + self.get(Fields.PLATFORM, "track").lower() + ":" + Parser.clean_string(
            (self.get_artists() if self.get_artists() else "N/A") + " - " +
            (self.get_name() if self.get_name() else "N/A")) + ">"

class Artist:
    def __init__(self, data: dict[str, any] | str):
        if isinstance(data, str):
            data = {Fields.NAME: data}
        self.__metadata = {k: v for k, v in data.items() if v is not None}

    def get(self, key: str = None, default = None):
        if not key: return self.__metadata
        item = self.__metadata.get(key, default)
        return item if item else default

    def get_name(self) -> str:
        return self.get(Fields.NAME)

    def compare_to(self, other) -> float:
        from music_tagger.matcher import Matcher
        if not isinstance(other, Artist): return 0
        return Matcher._compare_strings(self.get_name(), other.get_name())

    def __eq__(self, other: object) -> bool:
        from music_tagger.matcher import Matcher
        return self.compare_to(other) > Matcher.THRESHOLD

    def __hash__(self) -> int:
        return hash(self.get_name().lower())

    def __repr__(self) -> str:
        return "<artist:" + (self.get_name() if self.get_name() else "N/A") + ">"

class Album:
    def __init__(self, data: dict[str, any] | str):
        if isinstance(data, str): data = {Fields.NAME: data}
        self.__metadata = {k: v for k, v in data.items() if v is not None}

    def get(self, key: str = None, default = None):
        if not key: return self.__metadata
        item = self.__metadata.get(key, default)
        return item if item else default

    def get_name(self) -> str:
        return self.get(Fields.NAME)

    def compare_to(self, other) -> float:
        from music_tagger.matcher import Matcher
        if not isinstance(other, self.__class__): return 0
        # TODO: Compare release dates
        return Matcher._compare_strings(self.get_name(), other.get_name())

    def __eq__(self, other: object) -> bool:
        from music_tagger.matcher import Matcher
        return self.compare_to(other) > Matcher.THRESHOLD

    def __hash__(self) -> int:
        return hash(self.get_name().lower())

    def __repr__(self) -> str:
        return "<album:" + self.get_name() if self.get_name() else "N/A" + ">"

class Artwork:
    def __init__(self, source: str | APIC) -> None:
        self.is_local = isinstance(source, APIC)
        self.__source = source

    def get_apic(self, size: int = 800) -> APIC:
        if self.is_local: return self.__source
        from tempfile import TemporaryFile
        
        image: Image = self.__download_image(self.__source)
        if image.width > size or image.height > size:
            image.thumbnail((size, size), Resampling.LANCZOS)
        tmp = TemporaryFile()
        image.save(tmp, format = "jpeg")
        tmp.seek(0)

        try: return APIC(
                encoding = 3,
                mime = "image/jpeg",
                type = PictureType.COVER_FRONT,
                data = tmp.read())
        finally: tmp.close()

    def __download_image(self, url: str) -> Image:
        import io
        import requests
        print("Downloading artwork...")
        r = requests.get(url)
        r.raise_for_status()
        return Image.open(io.BytesIO(r.content))

    def __repr__(self) -> str:
        return "<artwork:" + self.__source + ">"
        
class Scale:
    def __init__(self, key: str = None, pitch = None, is_major = None) -> None:
        if key is None:
            self.__pitch = pitch
            self.__major = is_major
        else:
            self.__pitch, self.__major = Parser.parse_key(key)
        
        if self.__pitch is None or self.__major is None:
            raise ValueError(f"'{key}' is not a valid scale format.")

    def get_camelot_key(self) -> str:
        return Parser._CAMELOT.get(self.get_musical_key())

    def get_musical_key(self) -> str:
        return Parser._PITCHES[self.__pitch] + ("maj" if self.__major else "min")

    def __repr__(self) -> str:
        return "<scale:" + self.get_musical_key() + ">"

if __name__ == "__main__":
    print(Scale("9b"))