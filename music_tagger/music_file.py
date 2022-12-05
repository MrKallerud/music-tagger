import os, mutagen
from pathlib import Path

from music_tagger.metadata import embed_artwork, embed_metadata
from mutagen.easyid3 import EasyID3
from mutagen.id3 import ID3NoHeaderError

class MusicFile:
    def __init__(self, filepath: str):
        self.path = Path(filepath)
        
        if not self.path.exists():
            raise FileNotFoundError()

        self.metadata = self.__get_embedded_metadata()
        self.identity = None

    def get_ext(self) -> str:
        return self.path.suffix

    def get_filename(self) -> str:
        return self.path.with_suffix('').name

    def get_duration(self) -> int:
        file = mutagen.File(self.path)
        return round(file.info.length)
    
    def read(self):
        return self.path.read_bytes()

    def identify(self, suppress = False):
        from music_tagger.matcher import Matcher
        return Matcher.identify(self, suppress = suppress)

    def __get_embedded_metadata(self) -> dict | None:
        try: tags = EasyID3(self.path)
        except ID3NoHeaderError: return None
        clean_tags = {}
        for key in tags: clean_tags[key] = tags[key][0]
        return clean_tags

    def convert(self, format: str = ".mp3", no_overwrite: bool = False):
        print("Converting...")
        os.system(f"ffmpeg -i \"{self.path}\" -map_metadata 0 -v error -y -vn -ac 2 -id3v2_version 4 -b:a 320k \"{self.path.with_suffix('')}{format}\"")
        if not no_overwrite: os.remove(self.path)
        self.path = Path(self.path.with_suffix(format))
        return self

    def rename(self, filename: str):
        print("Renaming...")
        self.path = self.path.rename(os.path.join(self.path.parent, filename + self.get_ext()))

    def write_metadata(self, no_overwrite: bool = False):
        from music_tagger.soundcloud import SoundCloudTrack
        from music_tagger.spotify import SpotifyTrack
        from music_tagger.shazam_track import ShazamTrack

        # TODO: Metadata parser if no identity
        if not self.identity: return
        match: SpotifyTrack | SoundCloudTrack | ShazamTrack = self.identity
        if match.get_spotify_metadata():
            match = match.get_spotify_metadata()

        embed_metadata(self.path, no_overwrite, 
            album = match.get_album(),
            albumartist = match.get_album_artist(),
            artist = match.get_artist(),
            bpm = match.get_tempo(),
            comment = match.get_camelot_key(),
            explicit = match.is_explicit(),
            genre = match.get_genre(),
            isrc = match.get_isrc(),
            key = match.get_camelot_key(),
            label = match.get_label(),
            title = match.get_title(),
            year = match.get_year(),
        )
        embed_artwork(self.path, match.get_artwork(), no_overwrite = no_overwrite)
        if no_overwrite: return
        self.rename(f"{match.get_artist()} - {match.get_title()}")

    def to_string(self) -> str:
        ret = ""
        try: ret += self.metadata["artist"] + " - " + self.metadata["title"]
        except (KeyError, TypeError): pass
        try: ret += " - " + self.metadata["album"]
        except (KeyError, TypeError): pass
        if ret != "": return ret
        return self.get_filename()

    def __repr__(self) -> str:
        return self.to_string()

if __name__ == "__main__":
    MusicFile("/Users/ruud/Downloads/Sam Smith (ft. Kim Petras) - UNHOLY [FÄT TONY REMIX].mp3")
    MusicFile("/Users/ruud/Downloads/Artillery (PSY Mix).mp3")