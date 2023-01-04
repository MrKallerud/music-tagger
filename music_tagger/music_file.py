import os, audio_metadata, mutagen
from audio_metadata import ID3v2UserText, ID3v2Comment
from mutagen.id3 import ID3NoHeaderError
from pathlib import Path

from music_tagger.metadata_parser import embed_artwork, embed_metadata
from collections.abc import Sequence
from music_tagger.track import Track, Artist, Album, Artwork
from music_tagger.metadata_parser import MetadataParser as Parser
from music_tagger.metadata_fields import MetadataFields as Fields
from music_tagger.util import AUDIO_FORMATS

class MusicFile:
    def __init__(self, filepath: str):
        self.path = Path(filepath)
        
        if not self.path.exists():
            raise FileNotFoundError()

        metadata = audio_metadata.load(self.path)
        try: metadata[Fields.IMAGE] = mutagen.File(self.path).get("APIC:")
        except ID3NoHeaderError: print("No Artwork")
        
        self.__metadata = self.__clean_metadata(dict(metadata.get("tags")))
        stream = dict(metadata.get("streaminfo"))
        self.size = stream.get("_size")                 # bytes
        self.duration = stream.get("duration") * 1000   # ms
        self.bitrate = stream.get("bitrate") / 1000     # kbps
        self.sample_rate = stream.get("sample_rate")    # hz
        self.channels = stream.get("channels")

    def get_ext(self) -> str:
        return self.path.suffix

    def get_filename(self) -> str:
        return self.path.with_suffix('').name

    def get_metadata(self, key: str = None, default = None):
        if not key: return self.__metadata
        return  self.__metadata.get(key, default)

    def __clean_metadata(self, data: dict[str, any]) -> dict[str, any]:
        for key, value in data.items():
            # Convert lists
            if not isinstance(value, str) and isinstance(value, Sequence) and len(value) == 1:
                value = self.__first(value, value)
                data[key] = value
            if isinstance(value, Sequence) and len(value) == 0:
                value = None
                data[key] = value
                continue
            # Convert comments
            if isinstance(value, ID3v2Comment):
                data[Fields.DESCRIPTION] = value.text
                continue
            # Convert User fields
            if isinstance(value, ID3v2UserText):
                data[key] = None
                data[value.description] = value.text
                continue
            # Convert dates
            if isinstance(value, str) and Parser.is_date(value):
                value = Parser.parse_date(value)
                data[key] = value
                continue
            # Convert numbers
            if isinstance(value, str) and value.isdigit():
                value = int(value)
                data[key] = value

        return {k: v for k, v in data.items() if v is not None}
    
    def read(self):
        return self.path.read_bytes()

    def convert(self, format: str = ".mp3", keep_original: bool = False):
        print("Converting...")
        os.system(f"ffmpeg -i \"{self.path}\" -map_metadata 0 -v error -y -vn -ac 2 -id3v2_version 4 -b:a 320k \"{self.path.with_suffix('')}{format}\"")
        if not keep_original: os.remove(self.path)
        self.path = Path(self.path.with_suffix(format))
        return self

    def rename(self, filename: str):
        print("Renaming...")
        self.path = self.path.rename(os.path.join(self.path.parent, filename + self.get_ext()))

    def as_track(self) -> Track:
        metadata: dict[str, any] = self.get_metadata()

        parsed_filename = Parser(self.get_filename(), as_strings=False)
        try: parsed_title = Parser(metadata.get(Fields.NAME), as_strings=False)
        except TypeError: parsed_title = Parser()
        try: parsed_artists = Parser(metadata.get(Fields.ARTISTS) + " - " if metadata.get(Fields.ARTISTS) else [], as_strings=False)
        except TypeError: parsed_artists = Parser()

        metadata, metadata[Fields.ALBUM] = self.__get_album(metadata.copy())

        for parser in [parsed_filename, parsed_title, parsed_artists]:
            for key, value in parser.metadata.items():
                if value is None: continue
                if isinstance(value, Sequence) and len(value) == 0: continue
                # TODO: Merge lists
                #existing = metadata.get(key)
                # if isinstance(existing, (list, dict)) and existing.__class__ == value.__class__:
                #     for element in value:
                #         if metadata[key] is None: metadata[key] = []
                #         if element in existing: continue
                #         metadata[key] = metadata[key].append(element)

                metadata[key] = value

        metadata[Fields.ORIGINALFILENAME] = self.get_filename()

        return Track(metadata)

    def __get_album(self, data: dict[str, any]) -> tuple[dict, Album]:
        name = self.__first(data.pop(Fields.ALBUM))
        artists = Parser.split_list(",".join(data.pop(Fields.ALBUM_ARTIST, [])))
        date = Parser.parse_date(self.__first(data.pop(Fields.DATE)))

        return data, Album({
            Fields.NAME: name,
            Fields.ARTISTS: artists,
            Fields.IMAGE: Artwork(data.pop(Fields.IMAGE, None)),
            Fields.DATE: date
        })

    def __first(self, lst: list, default: any = None) -> any:
        try: return lst[0] if isinstance(lst, list) else default if default else lst
        except (IndexError, TypeError): return default if default else lst

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
    for file in Path("/Users/ruud/Desktop/låter").iterdir():
        if file.suffix not in AUDIO_FORMATS: continue
        if not '4' in file.name: continue
        file = MusicFile(file)
        track = file.as_track()
        print(f"{track}")
        #print(f"{track.get()}")
