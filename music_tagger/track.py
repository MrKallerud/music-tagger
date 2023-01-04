from mutagen.id3 import APIC, PictureType
from PIL import Image
from PIL.Image import Resampling

from music_tagger.metadata_fields import MetadataFields as Fields
from music_tagger.metadata_parser import MetadataParser as Parser


class Track:
    def __init__(self, data: dict[str, any]):
        self.__metadata = {k: v for k, v in data.items() if v is not None}

    def get(self, key: str = None, default = None):
        if not key: return self.__metadata
        item = self.__metadata.get(key, default)
        return item if item else default

    def get_name(self) -> str:
        name = self.get(Fields.NAME)
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
            artists = Parser.format_list(artists)
            if artists: artists += " "
            if extended and extended not in version and extended not in name:
                name += f" {brackets[0]}{artists}{extended} {version}{brackets[1]}"
            else:
                name += f" {brackets[0]}{artists}{version}{brackets[1]}"
            brackets = "[]"

        if extended and extended not in name:
            name += " " + brackets[0] + f"{extended} Mix" + brackets[1]

        return Parser.clean_string(name)

    def get_artists(self) -> str:
        all_artists = []

        all_artists.extend(self.get(Fields.ARTISTS, []))
        all_artists.extend(self.get(Fields.WITH, []))
        all_artists.extend(self.get(Fields.FEATURING, []))
        for _, artists in self.get(Fields.VERSIONS, {}).items():
            all_artists.extend(artists)

        all_artists = [str(artist) for artist in all_artists]
        all_artists = list(dict.fromkeys(all_artists))

        return Parser.format_list(all_artists)

    def __eq__(self, other: object) -> bool:
        return not (not isinstance(other, self.__class__) or \
            self.get(Fields.ISRC) != other.get(Fields.ISRC) or \
            self.get(Fields.ID) != other.get(Fields.ID) or \
            self.get(Fields.NAME) != other.get(Fields.NAME) or \
            self.get(Fields.ARTISTS) != other.get(Fields.ARTISTS) or \
            self.get(Fields.VERSIONS) != other.get(Fields.VERSIONS))

    def __hash__(self) -> int:
        if self.get(Fields.ISRC): return hash(self.get(Fields.ISRC))
        if self.get(Fields.ID): return hash(self.get(Fields.ID))
        return hash(str(self))

    def __repr__(self) -> str:
        return Parser.clean_string(
            (self.get_artists() if self.get_artists() else "") + " - " +
            (self.get_name() if self.get_name() else ""))

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

    def __eq__(self, other: object) -> bool:
        return isinstance(other, self.__class__) and self.get_name().lower() == self.get_name().lower()

    def __hash__(self) -> int:
        return hash(self.get_name().lower())

    def __repr__(self) -> str:
        return self.get_name()

class Album:
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

    def __eq__(self, other: object) -> bool:
        return isinstance(other, self.__class__) and self.get_name().lower() == self.get_name().lower()

    def __hash__(self) -> int:
        return hash(self.get_name().lower())

    def __repr__(self) -> str:
        return self.get_name()


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
        
class Key:
    def __init__(self, key: str) -> None:
        # TODO: Convert between camelot and musical key
        self.musical = key
        #self.camelot = key
