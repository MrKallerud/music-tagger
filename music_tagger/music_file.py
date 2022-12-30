import os, audio_metadata, mutagen
from audio_metadata import ID3v2UserText, ID3v2Comment
from mutagen.id3 import ID3NoHeaderError
from pathlib import Path

from music_tagger.metadata import embed_artwork, embed_metadata
from collections.abc import Sequence
from music_tagger.track import Track, Artist, Album, Artwork
from music_tagger.metadata import MetadataParser as Parser
from music_tagger.metadata import MetadataFields as meta
from music_tagger.util import AUDIO_FORMATS

class MusicFile:
    def __init__(self, filepath: str):
        self.path = Path(filepath)
        
        if not self.path.exists():
            raise FileNotFoundError()

        metadata = audio_metadata.load(self.path)
        try: metadata[meta.IMAGE] = mutagen.File(self.path).get("APIC:")
        except ID3NoHeaderError: print("No Artwork")
        
        self.__stream = dict(metadata.get("streaminfo"))
        self.__metadata = dict(metadata.get("tags"))

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
        parsed_filename = Parser(self.get_filename(), as_strings=False)
        try: parsed_title = Parser(self.__first(self.__metadata.get(meta.NAME), ""), as_strings=False)
        except TypeError: parsed_title = Parser("")
        try: parsed_artists = Parser(self.__first(self.__metadata.get(meta.ARTISTS), "") + " - " if self.__metadata.get(meta.ARTISTS) else [], as_strings=False)
        except TypeError: parsed_artists = Parser("")

        metadata = self.__metadata.copy()
        for parser in [parsed_filename, parsed_title, parsed_artists]:
            for key, value in parser.metadata.items():
                if value is None: continue
                if isinstance(value, Sequence) and len(value) == 0: continue
                existing = metadata.get(key)
                if isinstance(existing, (list, dict)) and existing.__class__ == value.__class__:
                    for element in value:
                        if element in existing: continue
                        metadata[key] = existing.append(element)
                else: metadata[key] = value

        metadata[meta.ORIGINALFILENAME] = self.get_filename()

        return Track(self.__filter_dict(metadata))

    def __filter_dict(self, data: dict) -> dict[str, any]:
        for key, value in data.items():
            if not isinstance(value, Sequence) or len(value) != 1 or not isinstance(value[0], str): continue
            if key == meta.ARTISTS and isinstance(value, list) and isinstance(self.__first(value), str):
                data[key] = [Artist(artist) for artist in value]
            else: data[key] = self.__first(value)
        return {k: v for k, v in data.items() if v != [] and v != "" and v is not None}

    def get_track(self) -> Track:
        original_name = self.__first(self.__metadata.get(meta.NAME), self.get_filename())
        name = Parser.clean_string(original_name)
        name, _ = Parser.parse_filetypes(name)
        name, extended = Parser.parse_extended(name)
        name, versions = Parser.parse_versions(name)

        data = self.__metadata.copy()
        data[meta.ORIGINALFILENAME] = self.get_filename()
        
        data[meta.FEATURING] = self.__find_artists(data, Parser.parse_feature)
        data[meta.ARTISTS] = [Parser.parse_feature(self.__first(data.get(meta.ARTISTS)))[0]]

        data[meta.WITH] = self.__find_artists(data, Parser.parse_with)
        data[meta.ARTISTS] = [Parser.parse_with(self.__first(data.get(meta.ARTISTS)))[0]]

        data[meta.ARTISTS] = self.__find_artists(data)
        data[meta.EXTENDED] = extended
        data[meta.NAME] = Parser.parse_title(name)[1]
        data[meta.VERSIONS] = versions
        if data.get(meta.ALBUM): data[meta.ALBUM] = self.__get_album(data)
        if data.get("key"): data[meta.KEY] = data.pop("key")
        if data.get(meta.COMPOSERS): data[meta.COMPOSERS] = Parser.split_list(",".join(data.get(meta.COMPOSERS)))
        if data.get(meta.DESCRIPTION): data[meta.DESCRIPTION] = self.__first(data.pop(meta.DESCRIPTION)).text

        # Handle User Text
        if data.get(meta.TEXT):
            for usertext in data.pop(meta.TEXT):
                data[usertext.description] = usertext.text

        # Convert lists with one item to just the item
        for key, value in data.items():
            if isinstance(value, Sequence) and len(value) == 0: data[key] = None
            if not isinstance(value, Sequence) or len(value) != 1 or not isinstance(value[0], str): continue
            data[key] = self.__first(value)

        return Track(data)

    def __get_album(self, data: dict[str, any]) -> Album:
        name = self.__first(data.pop(meta.ALBUM))
        artists = Parser.split_list(",".join(data.pop(meta.ALBUM_ARTIST, [])))
        date = Parser.parse_date(self.__first(data.pop(meta.DATE)))

        return Album({
            meta.NAME: name,
            meta.ARTISTS: artists,
            meta.IMAGE: Artwork(data.pop(meta.IMAGE, None)),
            meta.DATE: date,
        })

    def __first(self, lst: list, default: any = None) -> any:
        try: return lst[0] if isinstance(lst, list) else default
        except (IndexError, TypeError): return default

    def __find_artists(self, data: dict, method: callable = Parser.parse_artists) -> list[Artist]:
        _, artists = method(data.get(meta.ORIGINALFILENAME))

        title = self.__first(data.get(meta.NAME))
        if title:
            _, from_title = method(title)
            artists.extend(from_title)

        artist = self.__first(data.get(meta.ARTISTS))
        if artist:
            artist += " - "
            _, from_artist = method(artist)
            artists.extend(from_artist)

        artists = [Artist(artist) for artist in artists]
        return list(dict.fromkeys(artists))

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
        #if not '4' in file.name: continue
        file = MusicFile(file)
        track = file.as_track()
        print(f"{track}")
        #print(f"{track.get()}")
