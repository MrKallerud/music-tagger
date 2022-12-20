import re
from io import BytesIO

import mutagen
import requests
from tempfile import TemporaryFile
from mutagen.easyid3 import EasyID3
from mutagen.id3 import APIC, ID3, ID3NoHeaderError
from PIL import Image
from PIL.Image import Resampling
from pathlib import Path
from datetime import datetime

from music_tagger import util as Regexes

class MetadataFields:
    ALBUM = "album"
    ALBUM_ARTIST = "albumartist"
    ALBUM_TYPE = "albumtype"
    ARTISTS = "artist"
    COMPOSERS = "composer"
    DATE = "date"
    DESCRIPTION = "comment"
    DETAILS = "version"
    DOWNLOAD = "buy_url"
    DURATION = "length"
    EXPLICIT = "itunesadvisory"
    EXTENDED = "extended"
    FEATURING = "featuring"
    GENRE = "genre"
    ID = "id"
    IMAGE = "artwork"
    ISRC = "isrc"
    KEY = "initialkey"
    LABEL = "organization"
    NAME = "title"
    ORIGINALFILENAME = "originalfilename"
    PLATFORM = "platform"
    POPULARITY = "popularimeter"
    TAGS = "tags"
    TEMPO = "bpm"
    TEXT = "usertext"
    TRACK_COUNT = "trackcount"
    TRACK_NUMBER = "tracknumber"
    URL = "website"
    VERSIONS = "remixers"
    WITH = "with"

    # "albumartistsort"
    # "album"
    # "albumsort"
    # "arranger"
    # "artistsort"
    # "asin"
    # "author"
    # "barcode"
    # "catalognumber"
    # "compilation"
    # "composersort"
    # "conductor"
    # "copyright"
    # "discnumber"
    # "discsubtitle"
    # "encodedby"
    # "language"
    # "lyricist"
    # "media"
    # "mood"
    # "originaldate"
    # "performer"
    # "releasecountry"
    # "replaygain_*_gain"
    # "replaygain_*_peak"
    # "titlesort"

    @staticmethod
    def valid_fields() -> list[str]:
        fields = MetadataFields.__dict__
        fields = dict(filter(lambda item: item[0].isupper(), fields.items()))
        return list(fields.values())
        

class MetadataParser:
    def __init__(self, string: str):
        if not isinstance(string, str): raise TypeError(f"MetadataParser can only parse from string, not {string.__class__.__name__}")
        self.__metadata = {MetadataFields.ORIGINALFILENAME: string}

        self.__metadata[MetadataFields.DATE] = self.parse_date(self.parse_year(string)[1])
        _     , self.__metadata[MetadataFields.GENRE] = self.parse_genre(string)
        string, self.__metadata[MetadataFields.FEATURING] = self.parse_feature(string)
        string, self.__metadata[MetadataFields.WITH] = self.parse_with(string)
        string, self.__metadata[MetadataFields.VERSIONS] = self.parse_versions(string)
        string, self.__metadata[MetadataFields.ARTISTS] = self.parse_artists(string)
        string, self.__metadata[MetadataFields.NAME] = self.parse_title(string)

        self.__metadata = {k: v for k, v in self.__metadata.items() if v != [] and v is not None}

    def as_track(self):
        from music_tagger.track import Track
        return Track(self.__metadata)

    @staticmethod
    def parse_date(string: str) -> datetime | None:
        if not string: return None
        sep = "-"
        if " " in string: sep = " "
        if "." in string: sep = "."
        format = r"%Y-%m-%dT%H:%M:%SZ"
        if re.fullmatch(r"\d{4}", string): format = r"%Y"
        if re.fullmatch(r"\d{4}\W\d{2}", string): format = f"%Y{sep}%m"
        if re.fullmatch(r"\d{4}\W\d{2}\W\d{2}", string): format = f"%Y{sep}%m{sep}%d"

        return datetime.strptime(string, format)

    @staticmethod
    def parse_filetypes(string: str) -> tuple[str, str | None]:
        filetype = None
        for filetype in Regexes.FILETYPE_REGEX.finditer(string):
            string = string.replace(filetype.group(0), "")
        return string, filetype

    @staticmethod
    def parse_album_type(song_name: str, album_name: str) -> str:
        if not album_name: return "Single"
        if re.search(r"- single\s*$", album_name, re.I): return "Single"
        if re.search(r"- ep\s*$", album_name, re.I): return "EP"
        if song_name.lower() not in album_name.lower(): return "Album"
        return "Single"

    @staticmethod
    def parse_title(string: str) -> tuple[str, str | None]:
        if not isinstance(string, str): return string, None
        if Regexes.DASH_SPLITTER_REGEX.search(string):
            string = Regexes.AFTER_DASH_REGEX.search(string).group(1)
        title = Regexes.BEFORE_BRACK_DASH_REGEX.search(string).group(1)
        return string.replace(title, ""), title

    @staticmethod
    def parse_genre(string: str) -> tuple[str, str | None]:
        genres = []
        for genre in Regexes.GENRE_REGEX.findall(string):
            print(genre)
            genres.append(genre.title())
            string = string.replace(genre, "")
        return string, genres if len(genres) != 0 else None

    @staticmethod
    def parse_year(string: str) -> tuple[str, str | None]:
        year = Regexes.YEAR_REGEX.search(string)
        if not year: return string, None
        year = year.group(0)
        string = string.replace(year, "")
        year = re.sub("k", "0", year, flags=re.I)
        return string, year

    @staticmethod
    def clean_string(string: str) -> str:
        if not isinstance(string, str): return None
        string = string.replace("-–—", "-")
        for match in Regexes.BRACKET_REGEX.findall(string):
            if not Regexes.IGNORE_REGEX.search(match): continue
            string = string.replace(match, "")
        string = Regexes.EMPTY_BRACKETS_REGEX.sub(" ", string)
        string = Regexes.MULTIPLE_SPACES_REGEX.sub(" ", string)
        return string.strip(" -+.,&#")

    @staticmethod
    def parse_artists(string: str) -> tuple[str, list[str]]:
        if not isinstance(string, str): return string, []
        if not Regexes.DASH_SPLITTER_REGEX.search(string): return string, []
        split = Regexes.DASH_SPLITTER_REGEX.split(string)
        artists = MetadataParser.split_list(split.pop(0))
        return " ".join(split), artists

    @staticmethod
    def parse_versions(string: str) -> tuple[str, dict[str, list[str]] | None]:
        title = string
        versions = {}
        for match in Regexes.REMIX_REGEX.finditer(string):
            group = match.group(1)
            if re.search(r"[()\[\]-]", group): continue
            version = [str(word).capitalize() for word in Regexes.VERSION_REGEX.findall(group)]
            split = re.sub(" ".join(version), "", group, flags = re.I)
            unnessecary = ["Edit", "Version", "Mix"]
            if len(version) > 1 and version[-1] in unnessecary: version.pop(-1)
            versions[" ".join(version)] = MetadataParser.split_list(split.strip())
            title = title.replace(match.group(0), "").strip()

        if versions.get("Mix") == []: del versions["Mix"]
        if versions == {}: return string, None
        return title, versions

    @staticmethod
    def parse_feature(string: str) -> tuple[str, list[str]]:
        if not isinstance(string, str): return string, []
        match = Regexes.FEAT_REGEX.search(string)
        if not match: return string, []
        string = string.replace(match.group(0).strip(r"-()[]* "), "")
        return string, MetadataParser.split_list(match.group(1))

    @staticmethod
    def parse_with(string: str) -> tuple[str, list[str]]:
        if not isinstance(string, str): return string, []
        match = Regexes.WITH_REGEX.search(string)
        if not match: return string, []
        string = string.replace(match.group(0).strip(r"-()[]* "), "")
        return string, MetadataParser.split_list(match.group(1))

    @staticmethod
    def parse_extended(string: str) -> tuple[str, str | None]:
        title = string
        version = None
        for match in Regexes.EXTENDED_REGEX.finditer(string):
            version = match.group(0)
            title = title.replace(version, "")
        return title, version

    @staticmethod
    def parse_dash_version(string: str) -> tuple[str, dict[str, str] | None]:
        """Parses a title with dashes instead of brackets

        Returns
            `song_title`: str
            `list_of_versions`: [str]
        Example
            Cold Heart - PNAU & PS1 Remix - Acoustic
            -> ("Cold Heart", ["PNAU & PS1 Remix", "Acoustic"])
        """
        if not Regexes.DASH_SPLITTER_REGEX.search(string):
            return string, None

        parts = Regexes.DASH_SPLITTER_REGEX.split(string)
        title = parts.pop(0)

        return title, parts

    @staticmethod
    def split_list(string: str) -> list[str]:
        string = Regexes.ARTIST_SPLIT_REGEX.sub(",", string)
        l = [MetadataParser.clean_string(word) for word in string.split(",")]
        return list(filter(lambda artist: artist != "", l))

    @staticmethod
    def pretty_list(list: list[str]) -> str:
        ret = ""
        for i, string in enumerate(list):
            ret += string
            if i < len(list) - 2:
                ret += ", "
            elif i < len(list) - 1:
                ret += " & "
        return ret

    def __repr__(self) -> str:
        return str(self.as_track())

# EMBED METADATA TO FILE
def embed_metadata(filepath: Path, no_overwrite: bool = False, **kwargs):
    try:
        tags = EasyID3(filepath)
    except ID3NoHeaderError:
        tags = mutagen.File(filepath, easy=True)
        tags.add_tags()
    
    EasyID3.RegisterTextKey('comment', 'COMM')
    EasyID3.RegisterTextKey('year', 'TYER')
    EasyID3.RegisterTextKey('key', 'TKEY')
    EasyID3.RegisterTextKey('label', 'TPUB')
    EasyID3.RegisterTXXXKey("explicit", "itunesadvisory")
    EasyID3.RegisterTXXXKey("url", "url")

    print("Embedding metadata...")
    for tag, value in kwargs.items():
        if no_overwrite and tag in tags.keys() or not value: continue
        if tag in tags.keys(): tags.pop(tag)
        if value is bool: value = 1 if value else 0
        tags[tag] = str(value)

    tags.save()

def embed_artwork(filepath: Path, url: str, size: int = 800, no_overwrite: bool = False):
    try: tags = ID3(filepath)
    except ID3NoHeaderError:
        tags = mutagen.File(filepath)
        tags.add_tags()

    if no_overwrite and "APIC:" in tags.keys(): return
    print("Embedding artwork...")
    tags.delall("APIC")

    r = requests.get(url)
    image = Image.open(BytesIO(r.content))

    if image.width > size or image.height > size:
        image.thumbnail((size, size), Resampling.LANCZOS)
    tmp = TemporaryFile()
    image.save(tmp, format = "jpeg")
    tmp.seek(0)

    tags["APIC"] = APIC(
        encoding = 3,
        mime = "image/jpeg",
        type = 3,
        data = tmp.read())

    tmp.close()
    tags.save()

if __name__ == "__main__":
    parser = MetadataParser("Yolo (Mick 2k22 Deep House Remix)")
    print(parser)
    print(parser.as_track().get())
