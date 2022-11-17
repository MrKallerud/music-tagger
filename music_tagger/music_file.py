import os
from difflib import SequenceMatcher
from pathlib import Path

import mutagen
from mutagen.easyid3 import EasyID3
from mutagen.id3 import ID3NoHeaderError

from music_tagger.metadata import MetadataParser, embed_artwork, embed_metadata
from music_tagger.soundcloud import SoundCloudAPI, SoundCloudTrack
from music_tagger.spotify import SpotifyAPI, SpotifyTrack


class MusicFile:
    def __init__(self, filepath: str):
        self.path = Path(filepath)

        self.metadata = self.__get_embedded_metadata()
        # print(self.__shazam_isrc())

    # def __shazam_isrc(self) -> str:
    #     shazam = Shazam(self.path.open("rb").read()).recognizeSong()
    #     result = next(shazam)[-1].get("track")
    #     wanted_keys = ""

    #     try: return result.get("isrc")
    #     except AttributeError: return result

    def get_ext(self) -> str:
        return self.path.suffix

    def get_filename(self) -> str:
        return self.path.with_suffix('').name

    def __get_embedded_metadata(self) -> dict:
        try: tags = EasyID3(self.path)
        except ID3NoHeaderError: return {}
        return tags
        
    def match_soundcloud(self) -> dict:
        matches = {}
        results = SoundCloudAPI.search(self.get_filename(), 5) + SoundCloudAPI.search(self.to_string(), 5)
        for result in results:
            ratio = max([
                MusicFile.__compare_strings(self.get_filename(), result.title),
                MusicFile.__compare_strings(self.to_string(), result.title)])
            if ratio > 0.95: return {result: ratio}
            if ratio < 0.5: continue
            matches[result] = ratio
        
        return dict(sorted(matches.items(), key=lambda item: item[1], reverse = True))

    def match_spotify(self) -> dict:
        matches = {}

        results = SpotifyAPI.search(self.to_string())
        for result in results:
            ratio = max([
                MusicFile.__compare_strings(self.get_filename(), result.to_string()),
                MusicFile.__compare_strings(self.to_string(), result.to_string())])
            if ratio < 0.6: continue
            matches[result] = ratio
        
        return dict(sorted(matches.items(), key=lambda item: item[1], reverse = True))

    def convert(self, format: str = "mp3", overwrite: bool = True):
        os.system(f"ffmpeg -i \"{self.path}\" -map_metadata 0 -v error -y -vn -ac 2 -id3v2_version 4 -b:a 320k \"{self.path.with_suffix('')}.{format}\"")
        if overwrite: os.remove(self.path)
        self.path = Path(self.path.with_suffix(f".{format}"))
        return self

    def rename(self, filename: str):
        self.path = self.path.rename(os.path.join(self.path.parent, filename))

    def write_metadata(self, match, overwrite: bool = True):
        if isinstance(match, SoundCloudTrack):
            parser = MetadataParser(match.title)

            if len(parser.artists) == 0:
                parser.artists.append(match.user.get_name())
            
            if not parser.year: parser.year = match.get_year()
            if not parser.genre: parser.genre = match.genre

            meta_dict = parser.get_metadata_dict()
            embed_metadata(self.path, overwrite, **meta_dict)
            embed_artwork(self.path, match.get_artwork_url(), overwrite = overwrite)

            bitrate = mutagen.File(self.path).info.bitrate / 1000
            if match.purchase_url and "hypeddit" in match.purchase_url and bitrate < 320:
                print(f"File is low quality ({bitrate} kbps)")
                print(f"Consider running the following command to download higher quality:")
                print(f"ez-hype {match.url}")

            self.rename(parser.get_artists() + " - " + parser.get_title() + self.get_ext())

        if isinstance(match, SpotifyTrack):
            embed_artwork(self.path, match.album.artwork_url)
            embed_metadata(self.path, overwrite, 
                title = match.get_title(),
                album = match.album.name,
                artist = match.get_artists(),
                albumartist = match.album.artists[0].name,
                year = match.album.get_year(),
                explicit = match.explicit,
                isrc = match.isrc,
                tempo = match.get_audio_features().get_tempo(),
                key = match.get_audio_features().get_musical_key(),
                comment = match.get_audio_features().get_camelot_key(),
                popularity = match.popularity
            )
            self.rename(f"{match.get_artists()} - {match.get_title()}{self.get_ext()}")

    @staticmethod
    def __compare_strings(str1: str, str2: str) -> float:
        return SequenceMatcher(None, str1.lower(), str2.lower()).ratio()

    # @staticmethod
    # def __compare_lists(list1: list, list2: list) -> float:
    #     set1 = set(e.lower() for e in list1)
    #     set2 = set(e.lower() for e in list2)
    #     return len(set1.intersection(set2)) / max(len(list1), len(list2))

    def to_string(self) -> str:
        ret = ""
        try: ret += self.metadata["artist"][0] + " - " + self.metadata["title"][0]
        except (IndexError, KeyError): pass
        try: ret += " (" + self.metadata["album"][0] + ")"
        except (IndexError, KeyError): pass
        if ret != "": return ret
        return self.get_filename()

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