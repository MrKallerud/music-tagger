from mutagen.id3 import APIC, PictureType
from PIL import Image
from PIL.Image import Resampling

from music_tagger.metadata import MetadataFields as meta
from music_tagger.metadata import MetadataParser as parser


class Track:
    def __init__(self, data: dict[str, any]):
        self.__metadata = {k: v for k, v in data.items() if v is not None}

    def get(self, key: str = None, default = None):
        if not key: return self.__metadata
        item = self.__metadata.get(key, default)
        return item if item else default

    def get_name(self) -> str:
        name = self.get(meta.NAME)
        extended = self.get(meta.EXTENDED)
        brackets = "()"

        for detail in self.get(meta.DETAILS, []):
            if extended and extended not in detail and extended not in name:
                split = detail.split()
                split.insert(-1, extended)
                detail = " ".join(split)
            name += " " + brackets[0] + detail + brackets[1]
            brackets = "[]"

        for version, artists in self.get(meta.VERSIONS, {}).items():
            artists = parser.pretty_list(artists)
            if artists: artists += " "
            if extended and extended not in version and extended not in name:
                name += f" {brackets[0]}{artists}{extended} {version}{brackets[1]}"
            else:
                name += f" {brackets[0]}{artists}{version}{brackets[1]}"
            brackets = "[]"

        if extended and extended not in name:
            name += " " + brackets[0] + f"{extended} Mix" + brackets[1]

        return parser.clean_string(name)

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
            data = {meta.NAME: data}
        self.__metadata = {k: v for k, v in data.items() if v is not None}

    def get(self, key: str = None):
        if not key: return self.__metadata
        return self.__metadata.get(key)

    def get_name(self) -> str:
        return self.get(meta.NAME)

    def __repr__(self) -> str:
        return self.get_name()

class Album:
    def __init__(self, data: dict[str, any] | str):
        if isinstance(data, str):
            data = {meta.NAME: data}
        self.__metadata = {k: v for k, v in data.items() if v is not None}

    def get(self, key: str = None):
        if not key: return self.__metadata
        return self.__metadata.get(key)

    def get_name(self) -> str:
        return self.get(meta.NAME)

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
        print("Donwloading artwork...")
        r = requests.get(url)
        r.raise_for_status()
        return Image.open(io.BytesIO(r.content))
        
