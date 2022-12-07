import os, mutagen
from pathlib import Path

from music_tagger.metadata import embed_artwork, embed_metadata
from collections.abc import Sequence
import audio_metadata

class MusicFile:
    def __init__(self, filepath: str):
        self.path = Path(filepath)
        
        if not self.path.exists():
            raise FileNotFoundError()

        metadata = audio_metadata.load(self.path)
        self.__stream = dict(metadata.get("streaminfo"))
        self.__metadata = dict(metadata.get("tags"))
        self.identity = None

    def get_ext(self) -> str:
        return self.path.suffix

    def get_filename(self) -> str:
        return self.path.with_suffix('').name

    def get_metadata(self, key: str = None) -> str | None:
        if not key: return self.__metadata
        value = self.__metadata.get(key)
        if isinstance(value, Sequence) and len(value) != 0:
            return value[0]
        return value

    def get_duration(self) -> float:
        return self.__stream.get("duration") * 1000
    
    def read(self):
        return self.path.read_bytes()

    def identify(self, suppress = False):
        from music_tagger.matcher import Matcher
        self.identity, ratio = Matcher.identify(self, suppress = suppress)
        return self.identity, ratio

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
            key = match.get_musical_key(),
            label = match.get_label(),
            title = match.get_title(),
            year = match.get_year(),
            url = match.get_url(),
        )
        embed_artwork(self.path, match.get_artwork(), no_overwrite = no_overwrite)
        if no_overwrite: return
        self.rename(f"{match.get_artist()} - {match.get_title()}")

    def to_string(self) -> str:
        if self.get_metadata("artist") and self.get_metadata("title"):
            return self.get_metadata("artist") + " - " + self.get_metadata("title")
        return self.get_filename()

    def __repr__(self) -> str:
        return self.to_string()

if __name__ == "__main__":
    file = MusicFile("/Users/ruud/Development/music-tagger/tests/test_files/Lee Cabrera Mike Vale - Shake It (Antho Deck.wav")
    print(file.get_metadata())
    file = MusicFile("/Users/ruud/Development/music-tagger/tests/test_files/Riton _ Kah-Lo - Fake ID.mp3")
    print(file.get_metadata())

    #id, rate = file.identify(True)
    #print(f"{(rate * 100)}% - {id}")