from difflib import SequenceMatcher
from music_tagger import regexes as Regexes
from ShazamAPI import Shazam
from pathlib import Path
from mutagen.easyid3 import EasyID3
from mutagen.id3 import APIC, ID3, ID3NoHeaderError
from music_tagger.soundcloud import SoundCloudAPI, SoundCloudMetadata
from music_tagger.metadata import MetadataParser, embed_metadata, embed_artwork
import os

class MusicFile:
    def __init__(self, filepath: str):
        self.path = Path(filepath)
        self.ext = self.path.suffix
        self.filename = self.path.with_suffix('').name

        self.metadata = self.__get_embedded_metadata()
        # print(self.__shazam_isrc())

    # def __shazam_isrc(self) -> str:
    #     shazam = Shazam(self.path.open("rb").read()).recognizeSong()
    #     result = next(shazam)[-1].get("track")
    #     wanted_keys = ""

    #     try: return result.get("isrc")
    #     except AttributeError: return result

    def __get_embedded_metadata(self) -> dict:
        try: tags = EasyID3(self.path)
        except ID3NoHeaderError: return {}
        return tags
        
    def match_soundcloud(self) -> dict:
        matches = {}
        results = SoundCloudAPI.search(self.filename, 5) + SoundCloudAPI.search(self.to_string(), 5)
        for result in results:
            ratio = max([
                MusicFile.__compare_strings(self.filename, result.title),
                MusicFile.__compare_strings(self.to_string(), result.title)])
            if ratio > 0.95: return {result: ratio}
            if ratio < 0.4: continue
            matches[result] = ratio
        
        return dict(sorted(matches.items(), key=lambda item: item[1], reverse = True))

    def convert(self, format: str = "mp3", overwrite: bool = True):
        os.system(f"ffmpeg -i \"{self.path}\" -map_metadata 0 -v error -y -vn -ac 2 -id3v2_version 4 -b:a 320k \"{self.path}.{format}\"")
        if overwrite: os.remove(self.path)
        self.path = Path(self.path.with_suffix(format))
        self.filename = self.path.with_suffix('').name
        self.ext = self.path.suffix

    def write_metadata(self, match, overwrite: bool = True):
        if isinstance(match, SoundCloudMetadata):
            meta_dict = MetadataParser(match.title).get_metadata_dict()

            if not meta_dict.get("artist"):
                meta_dict["artist"] = match.user.get_name()
                meta_dict["albumartist"] = match.user.get_name()
            
            if not meta_dict.get("year"): meta_dict["year"] = match.get_year()
            if not meta_dict.get("genre"): meta_dict["genre"] = match.genre

            embed_metadata(self.path.as_posix(), overwrite, **meta_dict)
            embed_artwork(self.path.as_posix(), match.get_artwork_url(), overwrite = overwrite)
            
    # GET PRETTY STRINGS
    # def __pretty_list(self, list: list[str]) -> str:
    #     ret = ""
    #     for i, string in enumerate(list):
    #         ret += string
    #         if i < len(list) - 2:
    #             ret += ", "
    #         elif i < len(list) - 1:
    #             ret += " & "
    #     return ret

    # def get_title(self) -> str:
    #     brackets = "()"
    #     if "(" in self.title or ")" in self.title: brackets = "[]"
    #     ret = self.title

    #     if self.subtitle is not None:
    #         ret += " " + brackets[0] + self.subtitle + brackets[1]
    #         brackets = "[]"

    #     if len(self.remixers.keys()) > 0:
    #         for kind, remixers in self.remixers.items():
    #             ret += " " + brackets[0] + self.__pretty_list(remixers) + " "
    #             if self.is_extended: ret += "Extended "
    #             ret += kind + brackets[1]
    #             brackets = "[]"
    #     elif self.is_extended:
    #         if self.version is not None:
    #             self.version = "Extended " + self.version
    #         else:
    #             self.version = "Extended Mix"

    #     if self.version is not None:
    #         ret += " " + brackets[0] + self.version + brackets[1]

    #     return ret

    # def get_album(self) -> str:
    #     brackets = "()"
    #     if "(" in self.title or ")" in self.title: brackets = "[]"
    #     ret = self.title

    #     if len(self.withs) > 0:
    #         ret += " " + brackets[0] + "with " + self.__pretty_list(self.withs) + brackets[1]
    #         brackets = "[]"

    #     if len(self.features) > 0:
    #         ret += " " + brackets[0] + "feat. " + self.__pretty_list(self.features) + brackets[1]
    #         brackets = "[]"

    #     if len(self.remixers.keys()) > 0:
    #         for kind, remixers in self.remixers.items():
    #             ret += " " + brackets[0] + self.__pretty_list(remixers) + " " + kind + brackets[1]
    #             brackets = "[]"

    #     return ret

    # def get_artists(self) -> str:
    #     all_artists = self.artists + self.withs + self.features
    #     for kind, remixers in self.remixers.items():
    #         if kind != "Mashup": all_artists += remixers
    #     return self.__pretty_list(self.__strip_year_genre(all_artists))

    # def get_album_artist(self) -> str:
    #     if "Mashup" in self.remixers.keys(): return self.remixers["Mashup"][0]
    #     return self.artists[0] if len(self.artists) > 0 else None

    # def __strip_year_genre(self, list: list[str]) -> list[str]:
    #     """Removes year and genre from list and returns a copy"""
    #     l = []
    #     for a in list:
    #         n = Regexes.YEAR_REGEX.sub("", a).strip()
    #         n = Regexes.GENRE_REGEX.sub("", n).strip()
    #         l.append(n)
    #     return l

    # def compare(self, other) -> float:
    #     if self.id and other.id: return Track.__compare_strings(self.id, other.id)
    #     if self.isrc and other.isrc: return Track.__compare_strings(self.isrc, other.isrc)
        
    #     ratios = []
    #     ratios.append(Track.__compare_strings(self.title, other.title))

    #     if self.version and other.version:
    #         ratios.append(Track.__compare_strings(self.version, other.version))

    #     if self.album and other.album:
    #         ratios.append(Track.__compare_strings(self.album, other.album))
        
    #     if self.artists != [] or other.artists != []:
    #         ratios.append(Track.__compare_lists(self.artists, other.artists))
        
    #     if self.features != [] or other.features != []:
    #         ratios.append(Track.__compare_lists(self.features, other.features))

    #     if self.is_extended != other.is_extended: ratios.append(0.2)

    #     if self.remixers != {} or other.remixers != {}:
    #         self_remixers = []
    #         other_remixers = []
    #         for artists in self.remixers.values():
    #             for remixer in artists:
    #                 self_remixers.append(remixer.lower())
                    
    #         for artists in other.remixers.values():
    #             for remixer in artists:
    #                 other_remixers.append(remixer.lower())
    #         vr = Track.__compare_lists(self_remixers, other_remixers)
    #         kr = Track.__compare_lists(self.remixers.keys(), other.remixers.keys())
    #         ratios.append((vr + kr) / 2)

    #     return sum(ratios) / len(ratios)

    @staticmethod
    def __compare_strings(str1: str, str2: str) -> float:
        return SequenceMatcher(None, str1.lower(), str2.lower()).ratio()

    # @staticmethod
    # def __compare_lists(list1: list, list2: list) -> float:
    #     set1 = set(e.lower() for e in list1)
    #     set2 = set(e.lower() for e in list2)
    #     return len(set1.intersection(set2)) / max(len(list1), len(list2))

    def to_string(self) -> str:
        try: return self.metadata["artist"][0] + " - " + self.metadata["title"][0]
        except (IndexError, KeyError): pass
        return self.filename

    def __repr__(self) -> str:
        return self.to_string()

if __name__ == "__main__":
    MusicFile("/Users/ruud/Downloads/Sam Smith (ft. Kim Petras) - UNHOLY [FÄT TONY REMIX].mp3")
    MusicFile("/Users/ruud/Downloads/Artillery (PSY Mix).mp3")
    # t1 = Track("Loop", artists = ["Martin Garrix", "Vularr"])
    # t2 = Track("loop", artists = ["martin garrix", "vularr"])
    # print(f"{t1} vs {t2} = {t1.compare(t2)}")

    # t1 = Track("Loop", artists = ["Martin Garrix", "Vularr"])
    # t2 = Track("Rebound", artists = ["martin garrix", "vularr"])
    # print(f"{t1} vs {t2} = {t1.compare(t2)}")

    # t1 = Track("I Know You (feat. Bastille)", artists = ["Craid Davis", "Bastille"], album = "I Know You (Remixes) (feat. Bastille)", remixers={"Remix":["Vigiland"]})
    # t2 = Track("I Know You (feat. Bastille)", artists = ["Craig Davis", "Bastille"])
    # print(f"{t1} vs {t2} = {t1.compare(t2)}")

    # t1 = Track("I'm Good (Blue)", artists = ["David Guetta", "Bebe Rexha"], remixers={"Remix":["R3hab"]})
    # t2 = Track("I'm Good (Blue)", artists = ["David Guetta", "Bebe Rexha"], remixers={"Remix":["Broiler"]}, is_extended = True)
    # print(f"{t1} vs {t2} = {t1.compare(t2)}")