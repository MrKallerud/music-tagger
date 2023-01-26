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
from music_tagger.metadata_fields import MetadataFields as fields


class MetadataParser:
    _PITCHES = [
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

    _CAMELOT = {
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

    def __init__(self, string: str = None, as_strings: bool = True):
        if string == "" or string is None: self.metadata = {}; return
        if not isinstance(string, str): raise TypeError(f"MetadataParser can only parse from string, not {string.__class__.__name__}.")
        self.metadata = {fields.ORIGINALFILENAME: string}

        _, year = self.parse_year(string)
        _, self.metadata[fields.GENRE] = self.parse_genre(string)
        self.metadata[fields.DATE] = self.parse_date(year)

        string, self.metadata[fields.EXTENDED] = self.parse_extended(string)
        string, self.metadata[fields.FEATURING] = self.parse_feature(string, as_strings)
        string, self.metadata[fields.WITH] = self.parse_with(string, as_strings)
        string = self.__clean_ignore(string)
        string, self.metadata[fields.VERSIONS] = self.parse_versions(string, as_strings)
        string, self.metadata[fields.ARTISTS] = self.parse_artists(string, as_strings)
        string, self.metadata[fields.NAME] = self.parse_title(string)

        self.metadata = {k: v for k, v in self.metadata.items() if v != [] and v is not None}

    def as_track(self):
        from music_tagger.track import Track
        return Track(self.metadata)

    def __add__(self, other: object):
        if not isinstance(other, MetadataParser): raise TypeError(f"Can only add MetadataParser with MetadataParser, not {other.__class__.__name__}")
        self.metadata.update(other.metadata)
        return self

    @staticmethod
    def parse_date(string: str, format: str = None) -> datetime | None:
        if not isinstance(string, str): return None
        if format is not None: return datetime.strptime(string, format)
        
        sep = "-"
        if " " in string: sep = " "
        if "." in string: sep = "."

        format = r"%Y-%m-%dT%H:%M:%SZ"
        if re.fullmatch(r"\d{4}", string): format = r"%Y"
        if re.fullmatch(r"\d{4}\W\d{2}", string): format = f"%Y{sep}%m"
        if re.fullmatch(r"\d{4}\W\d{2}\W\d{2}", string): format = f"%Y{sep}%m{sep}%d"

        return datetime.strptime(string, format)

    @staticmethod
    def is_date(string: str) -> bool:
        return re.fullmatch(r"\d{4}", string) is not None or \
            re.fullmatch(r"\d{4}\W\d{2}", string) is not None or \
            re.fullmatch(r"\d{4}\W\d{2}\W\d{2}", string) is not None or \
            re.fullmatch(r"\d{4}\W\d{2}\W\d{2}T\d{2}\W\d{2}\W\d{2}Z?", string) is not None

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
        # Check that the argument is a not-empty string
        if not isinstance(string, str) or string == '': return string, None

        # If the string includes a dash, only use whats after the dash
        # 'Artist - Title' -> 'Title'
        # 'Artist - ' -> ''
        if Regexes.DASH_SPLITTER_REGEX.search(string):
            string = Regexes.AFTER_DASH_REGEX.search(string).group(1).strip()
            if string == '': return string, None
        title = Regexes.BEFORE_BRACK_DASH_REGEX.search(string).group(1)
        return string.replace(title, ""), title

    @staticmethod
    def parse_genre(string: str) -> tuple[str, str | None]:
        genres = []
        for genre in Regexes.GENRE_REGEX.findall(string):
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
        if not isinstance(string, str): return string
        string = string.replace("-–—", "-")
        for match in Regexes.BRACKET_REGEX.findall(string):
            if not Regexes.IGNORE_REGEX.search(match): continue
            string = string.replace(match, "")
        string = Regexes.EMPTY_BRACKETS_REGEX.sub(" ", string)
        string = Regexes.MULTIPLE_SPACES_REGEX.sub(" ", string)
        return string.strip(" -+.,&#")

    @staticmethod
    def parse_artists(string: str, as_strings: bool = True) -> tuple[str, list[str]]:
        from music_tagger.track import Artist

        if not isinstance(string, str): return string, []
        if not Regexes.DASH_SPLITTER_REGEX.search(string): return string, []
        split = Regexes.DASH_SPLITTER_REGEX.split(string)
        artists = MetadataParser.split_list(split.pop(0))
        if not as_strings: artists = [Artist(artist) for artist in artists]
        return " ".join(split), artists

    @staticmethod
    def parse_versions(string: str, as_strings: bool = True) -> tuple[str, dict[str, list[str]] | None]:
        from music_tagger.track import Artist

        title = string
        # Remove artists
        if Regexes.DASH_SPLITTER_REGEX.search(string): title = Regexes.AFTER_DASH_REGEX.search(string).group(1)

        versions = {}
        for match in Regexes.REMIX_REGEX.finditer(title):
            line = match.group(1)
            if re.search(r"[()\[\]-]", line): continue
            year = [str(y) for y in Regexes.YEAR_REGEX.findall(line)]
            for y in year: line = re.sub(y, "", line, flags=re.I)

            quote = [str(q) for q in Regexes.ANY_QUOTE_REGEX.findall(line)]
            for q in quote: line = re.sub(q, "", line, flags=re.I)

            version = [str(word).title() for word in Regexes.VERSION_REGEX.findall(line)]
            for v in version: line = re.sub(v, "", line, flags=re.I)
            for unnessecary in ["Edit", "Version", "Mix"]:
                if len(version) == 1: break
                if unnessecary in version: version.remove(unnessecary)
            
            version = " ".join((year if len(year) > 0 else []) + (quote if len(quote) > 0 else []) + (version if len(version) > 0 else []))
            artists = MetadataParser.split_list(MetadataParser.clean_string(line))

            if as_strings: versions[version] = artists
            else: versions[version] = [Artist(artist) for artist in artists]

            string = string.replace(match.group(0), "").strip()

        if versions.get("Mix") == []: del versions["Mix"]
        if versions == {}: return string, None
        return string, versions

    @staticmethod
    def __clean_ignore(string: str) -> str:
        # Search after brackets
        suffix = re.search(r"[^\])]+$", string)
        if suffix and Regexes.IGNORE_REGEX.search(suffix.group(0)):
            string = string.replace(suffix.group(0), "")

        # Search brackets
        for match in Regexes.BRACKET_REGEX.finditer(string):
            if not Regexes.IGNORE_REGEX.search(match.group(0)): continue
            string = string.replace(str(match.group(0)), "")

        return string

    @staticmethod
    def parse_feature(string: str, as_strings: bool = True) -> tuple[str, list[str]]:
        from music_tagger.track import Artist

        if not isinstance(string, str): return string, []
        match = Regexes.FEAT_REGEX.search(string)
        if not match: return string, []
        string = string.replace(match.group(0).strip(r"-()[]* "), "")

        artists = MetadataParser.split_list(match.group(1))
        if not as_strings: artists = [Artist(artist) for artist in artists]
        return string, artists

    @staticmethod
    def parse_with(string: str, as_strings: bool = True) -> tuple[str, list[str]]:
        from music_tagger.track import Artist

        if not isinstance(string, str): return string, []
        match = Regexes.WITH_REGEX.search(string)
        if not match: return string, []
        string = string.replace(match.group(0).strip(r"-()[]* "), "")

        artists = MetadataParser.split_list(match.group(1))
        if not as_strings: artists = [Artist(artist) for artist in artists]
        return string, artists

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
    def is_scale(string: str) -> bool:
        return Regexes.KEY_REGEX.search(string) is not None or \
            Regexes.CAMELOT_KEY_REGEX.search(string) is not None

    @staticmethod
    def parse_key(string: str, as_string: bool = True):
        """Parses a string representation of a musical key.

        Args:
            string (str): The string representation of the key.
            as_string (bool): If True, returns the pitch and mode as strings. If False, returns a Scale object.

        Returns:
            If as_string is True:
                (str, bool): A tuple containing the pitch and mode.
            If as_string is False:
                Scale: A Scale object representing the parsed key.
        """
        from music_tagger.track import Scale
        if not isinstance(string, str): return None, None
        string = MetadataParser.clean_string(string)

        match = Regexes.KEY_REGEX.fullmatch(string)
        if match:
            pitch, is_major = MetadataParser.__parse_musical_key(match.group(0))
        else:
            match = Regexes.CAMELOT_KEY_REGEX.fullmatch(string)
            if match:
                pitch, is_major = MetadataParser.__parse_camelot_key(match.group(0))

        if match is None: return None, None
        if as_string: return pitch, is_major
        return Scale(pitch, is_major)

    @staticmethod
    def __parse_musical_key(string: str) -> tuple[str, bool]:
        for i, note in enumerate(MetadataParser._PITCHES):
            if note == string[0].upper():
                pitch = i
                if '#' in string or '♯' in string: pitch += 1
                elif 'b' in string or '♭' in string: pitch -= 1
                pitch = pitch % 12
                if re.search(r"(m|min|minor)\b", string, re.I):
                    is_major = False
                else: is_major = True
                return pitch, is_major

    @staticmethod
    def __parse_camelot_key(string: str) -> tuple[str, bool] | None:
        for key, value in MetadataParser._CAMELOT.items():
            if string.upper() == value:
                return MetadataParser.__parse_musical_key(key)

    @staticmethod
    def split_list(string: str) -> list[str]:
        string = Regexes.ARTIST_SPLIT_REGEX.sub(",", string)
        l = [MetadataParser.clean_string(word) for word in string.split(",")]
        return list(filter(lambda artist: artist != "", l))

    @staticmethod
    def format_list(list: list) -> str:
        ret = ""
        for i, string in enumerate(list):
            ret += str(string)
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
    parser = MetadataParser(" - Cold Heart - Claptone Remix", as_strings=False)
    #print(parser)
    print(parser.as_track().get())