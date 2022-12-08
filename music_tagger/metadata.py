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

from music_tagger import colors as Color
from music_tagger import util as Regexes

class MetadataFields:
    NAME = "title"
    ARTISTS = "artists"
    ALBUM = "album"
    ALBUM_ARTIST = "albumartist"

    ALBUM_TYPE = "albumtype"
    DATE = "date"
    DESCRIPTION = "comment"
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
    PLATFORM = "platform"
    POPULARITY = "popularimeter"
    VERSIONS = "remixers"
    TAGS = "tags"
    TEMPO = "bpm"
    TRACK_COUNT = "trackcount"
    TRACK_NUMBER = "tracknumber"
    URL = "website"
    DETAILS = "version"
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
    # "composer"
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
    __STRIP_BRACKETS = r"()[]* "

    def __init__(self, title: str):
        self.__filename = re.sub(r"\s{2,}", " ", title.strip())

        self.artists = []
        self.features = []
        self.is_extended = False
        self.remixers = {}
        self.subtitle = None
        self.title = None
        self.version = None
        self.withs = []

        self.genre = None
        self.year = None

        try:
            self.__parse_genre()
            self.__parse_year()
            self.__parse_title()
            self.__parse_feature()
            self.__parse_with()
            self.__parse_brackets()
            self.__parse_artists()
        except Exception as e:
            print(f"{Color.WARNING}{Color.BOLD}METADATA PARSING ERROR: {Color.ENDC}{e}")
            raise e

    def __parse_title(self):
        try:
            if Regexes.DASH_SPLITTER_REGEX.search(self.__filename):
                self.title = re.findall(r"-\s+(.*?)\s*(?:[()\[\]]|ft|feat|$)", self.__filename, flags = re.I)[0]
            else:
                self.title = re.findall(r"(.*?)\s*(?:[()\[\]]|ft|feat|$)", self.__filename, flags = re.I)[0].strip(self.__STRIP_BRACKETS)
        except IndexError:
            self.title = self.__filename
            print(f"{Color.WARNING}{Color.BOLD}METADATA PARSING ERROR:{Color.ENDC} Couldn't parse title")
        self.__filename = self.__filename.replace(self.title, "")
        self.__filename = re.sub(r"\s{2,}", " ", self.__filename)

    def __parse_artists(self):
        artists = Regexes.DASH_SPLITTER_REGEX.split(self.__filename)[0]
        self.artists = self.split_list(artists)
        for artist in self.artists:
            self.__filename = self.__filename.replace(artist, "")
        self.__filename = Regexes.ARTIST_SPLIT_REGEX.sub("", self.__filename)
        self.__filename = Regexes.DASH_SPLITTER_REGEX.sub("", self.__filename)

    def __parse_feature(self):
        matches = re.findall("\\b(?:ft|feat)\.?\s*[^()\[\]-]*", self.__filename, re.I)
        if len(matches) == 0: return []
        for match in matches:
            self.features.append(re.sub("\\b(ft|feat)\.?\s*", "", match, flags = re.I).strip())
            self.__filename = self.__filename.replace(match, "")
        self.__filename = re.sub("\(\s*\)", "", self.__filename)

    def __parse_with(self):
        matches = re.findall("\\bwith\.?\s*[^()\[\]]*", self.__filename, re.I)
        if len(matches) == 0: return []
        for match in matches:
            self.withs.append(re.sub("\\bwith\.?\s*", "", match, flags = re.I).strip())
            self.__filename = self.__filename.replace(match, "")
        self.__filename = re.sub("\(\s*\)", "", self.__filename)
    
    def __parse_brackets(self):
        for match in Regexes.BRACKET_REGEX.findall(self.__filename):
            # Extended
            if re.search("extended", match, flags = re.I) is not None:
                self.is_extended = True
                self.__filename = re.sub("\\bextended\s?", "", self.__filename, flags = re.I)
                match = re.sub("\\bextended\s?", "", match, flags = re.I)

            # Discard
            if Regexes.IGNORE_REGEX.search(match):
                self.__filename = self.__filename.replace(match, "")
                continue

            # Remix
            elif Regexes.VERSION_REGEX.search(match):
                remix_type = match.strip(self.__STRIP_BRACKETS).split()[-1].title()
                remixers = self.split_list(re.sub(remix_type, "", match, flags = re.I).strip(self.__STRIP_BRACKETS))
                if len(remixers) != 0:
                    self.remixers[remix_type] = remixers

            # Whatever is left is probably subtitle
            elif "*" not in match and match.strip() != "":
                self.subtitle = match.strip(self.__STRIP_BRACKETS)

            self.__filename = self.__filename.replace(match, "")
            self.__filename = re.sub(r"[(\[].*?[)\]]", "", self.__filename)

        self.__filename = self.__filename.strip()

    def __parse_year(self):
        try:
            self.year = Regexes.YEAR_REGEX.search(self.__filename)[0]
            self.year = re.sub("k", "0", self.year, flags = re.I)
        except (IndexError, TypeError): pass

    def __parse_genre(self):
        try: Regexes.GENRE_REGEX.search(self.__filename)[0]
        except (IndexError, TypeError): pass

    def __strip_year_genre(self, list: list[str]) -> list[str]:
        """Removes year and genre from list and returns a copy"""
        l = []
        for a in list:
            n = Regexes.YEAR_REGEX.sub("", a).strip()
            n = Regexes.GENRE_REGEX.sub("", n).strip()
            l.append(n)
        return l

    def get_metadata_dict(self) -> dict:
        meta_dict =  {
            "title": self.get_title(),
            "album": self.get_album(),
        }

        if len(self.artists) > 0:
            meta_dict["artist"] = self.get_artist()
            meta_dict["albumartist"] = self.get_album_artist()

        if self.genre: meta_dict["genre"] = self.genre
        elif "Mashup" in self.remixers.keys():
            meta_dict["genre"] = "Mashup"
        if self.year: meta_dict["year"] = self.year

        return meta_dict

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
        if re.search(r"- ep?\s*$", album_name, re.I): return "EP"
        if song_name.lower() not in album_name.lower(): return "Album"
        return "Single"

    @staticmethod
    def parse_title(string: str) -> tuple[str, str]:
        if Regexes.DASH_SPLITTER_REGEX.search(string):
            string = Regexes.AFTER_DASH_REGEX.search(string).group(1)
        title = Regexes.BEFORE_BRACK_DASH_REGEX.search(string).group(1)
        return string.replace(title, ""), title

    @staticmethod
    def parse_genre(string: str) -> tuple[str, str | None]:
        genres = []
        for genre in Regexes.GENRE_REGEX.finditer(string):
            genres.append(genre)
            string = string.replace(genre, "")
        return string, genres if len(genres) != 0 else None

    @staticmethod
    def parse_year(string: str) -> tuple[str, str | None]:
        year = Regexes.YEAR_REGEX.search(string)
        if not year: return string, None
        string = string.replace(year, "")
        year = re.sub("k", "0", string, flags=re.I)
        return string, year

    @staticmethod
    def clean_title(string: str) -> str:
        string = string.replace("–—", "-")
        for match in Regexes.BRACKET_REGEX.findall(string):
            if not Regexes.IGNORE_REGEX.search(match): continue
            string = string.replace(match, "")
        string = Regexes.EMPTY_BRACKETS_REGEX.sub(" ", string)
        string = Regexes.MULTIPLE_SPACES_REGEX.sub(" ", string)
        return string.strip(" -+.,&#")

    @staticmethod
    def parse_artists(string: str) -> tuple[str, list[str] | None]:
        if not Regexes.DASH_SPLITTER_REGEX.search(string): return string, None
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
            split = group.split()
            version = split.pop(-1).capitalize()
            versions[version] = MetadataParser.split_list(" ".join(split).strip())
            title = title.replace(match.group(0), "").strip()
        if versions == {}: return string, None
        return title, versions

    @staticmethod
    def parse_feature(string: str) -> tuple[str, list[str] | None]:
        match = Regexes.FEAT_REGEX.search(string)
        if not match: return string, None
        string = string.replace(match.group(0).strip(r"-()[]* "), "")
        return MetadataParser.clean_title(string), MetadataParser.split_list(match.group(1))

    @staticmethod
    def parse_with(string: str) -> tuple[str, list[str] | None]:
        title = Regexes.WITH_REGEX.sub("", string)
        artists = Regexes.WITH_REGEX_GROUPED.search(string)
        if not artists: return string, None
        return title, MetadataParser.split_list(artists.group(1))

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
        return list(filter(lambda artist: artist != "", string.split(",")))

    # GET PRETTY STRINGS
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

    def get_title(self) -> str:
        brackets = "()"
        ret = self.title

        if self.subtitle:
            ret += " " + brackets[0] + self.subtitle + brackets[1]
            brackets = "[]"

        if len(self.remixers.keys()) > 0:
            for kind, remixers in self.remixers.items():
                ret += " " + brackets[0] + self.pretty_list(remixers) + " "
                if self.is_extended: ret += "Extended "
                ret += kind + brackets[1]
                brackets = "[]"
        elif self.is_extended:
            if self.version and "Extended" not in self.version:
                self.version = "Extended " + self.version
            elif not self.version:
                self.version = "Extended Mix"

        if self.version is not None:
            ret += " " + brackets[0] + self.version + brackets[1]

        return ret

    def get_album(self) -> str:
        brackets = "()"
        ret = self.title

        if len(self.withs) > 0:
            ret += " " + brackets[0] + "with " + self.pretty_list(self.withs) + brackets[1]
            brackets = "[]"

        if len(self.features) > 0:
            ret += " " + brackets[0] + "feat. " + self.pretty_list(self.features) + brackets[1]
            brackets = "[]"

        if len(self.remixers.keys()) > 0:
            for kind, remixers in self.remixers.items():
                ret += " " + brackets[0] + self.pretty_list(remixers) + " " + kind + brackets[1]
                brackets = "[]"

        return ret

    def get_artist(self) -> str | None:
        all_artists = self.artists + self.withs + self.features
        for kind, remixers in self.remixers.items():
            if kind != "Mashup": all_artists += remixers
        artist_string = self.pretty_list(self.__strip_year_genre(all_artists))
        if artist_string != "": return artist_string

    def get_album_artist(self) -> str | None:
        if "Mashup" in self.remixers.keys(): return self.remixers["Mashup"][0]
        return self.artists[0] if len(self.artists) > 0 else None

    def __repr__(self) -> str:
        return f"""Title:          {self.get_title()}
Artists:        {self.get_artist()}
Album:          {self.get_album()}
Album Artist:   {self.get_album_artist()}
Year:           {self.year}
Genre:          {self.genre}"""

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
    # parse = MetadataParser(
    #     "[FREE DL] Riton & Kah-Lo - Fake ID (ÅMRTÜM Edit)")
    # print(parse)
    # print(f"{parse.artists=}")
    # print(f"{parse.remixers=}")
    # print(f"{parse.version=}")

    string = " Hei [FREE DOWNLOAD] () "
    print(f"'{MetadataParser.clean_title(string)}'")
