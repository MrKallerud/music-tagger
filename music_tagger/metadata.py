import os
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


class MetadataParser:
    __STRIP_BRACKETS = r"()[]* "
    __ARTIST_SPLIT_REGEX = r"\s*,\s*|\s+(?:,|vs|x|&)\s+"
    __DASH_SPLITTER = " - "

    def __init__(self, title: str):
        self.__filename = title

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
            if self.__DASH_SPLITTER in self.__filename:
                self.title = re.findall(r"-\s+(.*?)\s*(?:[()\[\]]|ft|feat|$)", self.__filename, flags = re.I)[0]
            else:
                self.title = re.findall(r"(.*?)\s*(?:[()\[\]]|ft|feat|$)", self.__filename, flags = re.I)[0].strip(self.__STRIP_BRACKETS)
        except IndexError:
            self.title = self.__filename
            print(f"{Color.WARNING}{Color.BOLD}METADATA PARSING ERROR: {Color.ENDC} Couldn't parse title")
        self.__filename = self.__filename.replace(self.title, "")

    def __parse_artists(self):
        print(self.__filename)
        self.artists = self.__split_artists(self.__filename.split(self.__DASH_SPLITTER)[0].strip())
        for artist in self.artists:
            self.__filename = self.__filename.replace(artist, "")
        self.__filename = re.sub(self.__ARTIST_SPLIT_REGEX, "", self.__filename, re.I) + "".join(self.__filename.split(self.__DASH_SPLITTER)[1:])

    def __split_artists(self, string: str) -> list[str]:
        string = re.sub(self.__ARTIST_SPLIT_REGEX, ",", string, flags = re.I)
        return list(filter(lambda artist: artist != "", string.split(",")))

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
                self.__filename = self.__filename.replace(match, ""); break

            # Remix
            elif Regexes.VERSION_REGEX.search(match):
                remix_type = match.strip(self.__STRIP_BRACKETS).split()[-1].title()
                remixers = self.__split_artists(re.sub(remix_type, "", match, flags = re.I).strip(self.__STRIP_BRACKETS))
                self.remixers[remix_type] = remixers

            # Whatever is left is probably subtitle
            elif "*" not in match:
                self.subtitle = match.strip(self.__STRIP_BRACKETS)

            self.__filename = self.__filename.replace(match, "")
            self.__filename = re.sub(r"[(\[].*?[)\]]", "", self.__filename)

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
            meta_dict["artist"] = self.get_artists()
            meta_dict["albumartist"] = self.get_album_artist()

        if self.genre: meta_dict["genre"] = self.genre
        if self.year: meta_dict["year"] = self.year

        return meta_dict

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

        if self.subtitle is not None:
            ret += " " + brackets[0] + self.subtitle + brackets[1]
            brackets = "[]"

        if len(self.remixers.keys()) > 0:
            for kind, remixers in self.remixers.items():
                ret += " " + brackets[0] + self.pretty_list(remixers) + " "
                if self.is_extended: ret += "Extended "
                ret += kind + brackets[1]
                brackets = "[]"
        elif self.is_extended:
            if self.version is not None:
                self.version = "Extended " + self.version
            else:
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

    def get_artists(self) -> str:
        all_artists = self.artists + self.withs + self.features
        for kind, remixers in self.remixers.items():
            if kind != "Mashup": all_artists += remixers
        return self.pretty_list(self.__strip_year_genre(all_artists))

    def get_album_artist(self) -> str:
        if "Mashup" in self.remixers.keys(): return self.remixers["Mashup"][0]
        return self.artists[0] if len(self.artists) > 0 else None

    def __repr__(self) -> str:
        return f"""Title:          {self.get_title()}
Artists:        {self.get_artists()}
Album:          {self.get_album()}
Album Artist:   {self.get_album_artist()}
Year:           {self.year}
Genre:          {self.genre}"""


# EMBED METADATA TO FILE
def embed_metadata(filepath: Path, overwrite: bool = True, **kwargs):
    try: tags = EasyID3(filepath)
    except ID3NoHeaderError:
        tags = mutagen.File(filepath, easy=True)
        tags.add_tags()
    
    EasyID3.RegisterTextKey('comment', 'COMM')
    EasyID3.RegisterTextKey('year', 'TYER')

    for tag, value in kwargs.items():
        if not overwrite and tag in tags.keys() or value == None: continue
        tags[tag] = value

    tags.save()


def embed_artwork(filepath: Path, url: str, size: int = 800, overwrite: bool = True):
    try: tags = ID3(filepath)
    except ID3NoHeaderError:
        tags = mutagen.File(filepath)
        tags.add_tags()

    if not overwrite and "APIC:" in tags.keys(): return
    tags.delall("APIC")

    r = requests.get(url)
    image = Image.open(BytesIO(r.content))

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
    parse = MetadataParser("Witch Doktor (Illyus & Barrientos Remix) [FREE DOWNLOAD]")
    print(parse)
    print(f"{parse.artists=}")
    print(f"{parse.remixers=}")
    print(f"{parse.title=}")
