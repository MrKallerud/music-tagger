import logging
from shazam import Shazam
from difflib import SequenceMatcher

from music_tagger.music_file import MusicFile
from music_tagger.soundcloud import SoundCloudAPI
from music_tagger.spotify import SpotifyAPI
from music_tagger.track import Track, Artist, Album
from music_tagger.metadata_fields import MetadataFields as Fields
from music_tagger import Log, Color


class Matcher:
    THRESHOLD = 0.9
    __MIN_THRESHOLD = 0.6
    __MS_THRESHOLD = 5000

    api = SpotifyAPI | SoundCloudAPI

    @staticmethod
    def identify(music_file: MusicFile, apis: list[api] = [SpotifyAPI, SoundCloudAPI]) -> tuple[Track, float] | None:
        """Searches through the APIs to find the best match."""
        track = music_file.as_track()

        # Iterate through all the apis and collect the best matches
        matches = {}
        for api in apis:
            logging.info(f"Searching {api.NAME}...")
            for search in track.get_search_strings():
                results = api.search(search, limit = 10)

                # Collect matches and potential matches
                for result in results:
                    logging.debug(result)
                    ratio = track.compare_to(result)
                    if ratio > Matcher.THRESHOLD: return result, ratio
                    if ratio < Matcher.__MIN_THRESHOLD: continue
                    matches[result] = ratio


        for track, ratio in sorted(matches.items(), key=lambda x: x[1], reverse=True):
            logging.info(f"{int(ratio * 100)}%".rjust(3) + f" - {track}")

        # Return best match
        if matches != {}: return list(matches.items())[0]

        # TODO: Let user select from potential match
        # Log results
        matches_info = "Matches:"
        for match, ratio in matches.items():
            matches_info += f"\n\t{int(ratio * 100)}% - " + str(match)
        logging.debug(matches_info)

    @staticmethod
    def compare_tracks(this: Track, other: Track) -> float:
        # Metadata
        metadata_rate = Matcher.__compare_metadata(this, other)
        
        # ISRC
        isrc_rate = None
        if this.get(Fields.ISRC) is not None and other.get(Fields.ISRC) is not None:
            isrc_rate = 1 if Matcher._compare_strings(this.get(Fields.ISRC), other.get(Fields.ISRC)) > Matcher.THRESHOLD else 0
        if isrc_rate is None:
            logging.debug(f"{Fields.ISRC}:".upper().ljust(12) + f"N/A".rjust(4))
        else: logging.debug(f"{Fields.ISRC}:".upper().ljust(12) + f"{int(isrc_rate * 100)}%".rjust(4))

        # Duration
        time_rate = None
        if Fields.DURATION in this.get() and Fields.DURATION in other.get():
            time_diff = abs(this.get(Fields.DURATION) - other.get(Fields.DURATION))
            time_rate = max(min((Matcher.__MS_THRESHOLD - time_diff) / Matcher.__MS_THRESHOLD, 1), 0)
        if time_rate is None:
            logging.debug(f"{Fields.DURATION}:".capitalize().ljust(12) + f"N/A".rjust(4))
        else: logging.debug(f"{Fields.DURATION}:".capitalize().ljust(12) + f"{int(time_rate * 100)}%".rjust(4))

        rates = list(filter(lambda x: x is not None, metadata_rate + [isrc_rate, time_rate]))
        total_rate = sum(rates) / len(rates)
        logging.debug("Total:".ljust(12) + f"{int(total_rate * 100)}%".rjust(4) + "\n")
        return total_rate

    @staticmethod
    def __compare_metadata(this: Track, other: Track) -> list[float]:
        from itertools import chain

        # Title
        title_rate = Matcher._compare_strings(this.get(Fields.NAME), other.get(Fields.NAME))
        if title_rate is not None and title_rate < Matcher.__MIN_THRESHOLD: title_rate = 0

        # Artists (Incl. with, feature and remix)
        this_artists = set(this.get(Fields.ARTISTS, []) +\
            this.get(Fields.FEATURING, []) +\
            this.get(Fields.WITH, []))

        other_artists = set(other.get(Fields.ARTISTS, []) +\
            other.get(Fields.FEATURING, []) +\
            other.get(Fields.WITH, []))
        artist_rate = Matcher.__compare_lists(list(this_artists), list(other_artists))

        # Album
        album_rate = None
        if this.get(Fields.ALBUM) is not None and other.get(Fields.ALBUM) is not None:
            album_rate = this.get(Fields.ALBUM).compare_to(other.get(Fields.ALBUM))
        if album_rate is not None and album_rate < Matcher.__MIN_THRESHOLD: album_rate = 0

        # Extended
        extended_rate = None
        if this.get(Fields.EXTENDED) is not None or other.get(Fields.EXTENDED) is not None:
            extended_rate = Matcher._compare_strings(this.get(Fields.EXTENDED, ""), other.get(Fields.EXTENDED, ""))
            if extended_rate is not None and extended_rate < Matcher.THRESHOLD: extended_rate = 0
        
        # Version
        version_rate = None
        if this.get(Fields.VERSIONS) and other.get(Fields.VERSIONS):
            # Version
            this_version = this.get(Fields.VERSIONS)
            other_version = other.get(Fields.VERSIONS)
            type_rate = Matcher.__compare_lists(list(this_version.keys()), list(other_version.keys()))
            if type_rate < Matcher.__MIN_THRESHOLD: type_rate = 0

            # Artists
            this_artists = list(chain.from_iterable(this.get(Fields.VERSIONS, {}).values()))
            other_artists = list(chain.from_iterable(other.get(Fields.VERSIONS, {}).values()))
            artist_rate = Matcher.__compare_lists(this_artists, other_artists)

            # Total
            if artist_rate is None: version_rate = type_rate
            else: version_rate = (type_rate + artist_rate) / 2

        # esult
        rates = {
            Fields.ALBUM: album_rate,
            Fields.ARTISTS: artist_rate,
            Fields.EXTENDED: extended_rate,
            Fields.NAME: title_rate,
            Fields.VERSIONS: version_rate
        }

        # Info
        info = "Metadata:"
        for key, value in rates.items():
            info += "\n\t" + f"{key.capitalize()}:".ljust(12)
            if value is None: info += "N/A".rjust(4).ljust(12)
            else:
                info += f"{int(value*100)}%".rjust(4).ljust(12)
                info += f"{this.get(key)} // {other.get(key)}"

        rates = list(filter(lambda x: x is not None, rates.values()))
        logging.debug(info)
        return rates

    @staticmethod
    def __compare_lists(lst1: list, lst2: list) -> float | None:
        if not isinstance(lst1, list) or not isinstance(lst2, list): return None
        if len(lst1) == len(lst2) == 0: return 1

        longest = lst1 if len(lst1) >= len(lst2) else lst2
        shortest = lst1 if longest is lst2 else lst2
        assert longest is not shortest
        if len(longest) == 0 or len(shortest) == 0: return None

        checked = []
        similar = 0
        for x in shortest:
            for y in longest:
                if {x, y} in checked: continue
                if isinstance(x, str) and isinstance(y, str):
                    diff = Matcher._compare_strings(x, y)
                    if diff > Matcher.__MIN_THRESHOLD: similar += diff
                elif isinstance(x, (Artist, Album)) and isinstance(y, (Artist, Album)) and isinstance(x, y.__class__):
                    diff = x.compare_to(y)
                    if diff > Matcher.__MIN_THRESHOLD: similar += diff
                elif x == y: similar += 1
                checked.append({x, y})
        
        return max(0, similar / len(longest) - 0.1 * (len(longest) - len(shortest)))

    @staticmethod
    def _compare_strings(str1: str, str2: str) -> float | None:
        if not isinstance(str1, str) or not isinstance(str2, str): return None
        return SequenceMatcher(None, str1.lower(), str2.lower()).ratio()

    @staticmethod
    def print_match(match: Track, ratio: float):
        color = Color.YELLOW if ratio > Matcher.__MIN_THRESHOLD else Color.RED
        if ratio > 0.8: color = Color.GREEN
        Log.info(f"{ratio:.1%}: {match.get_artists()} - {match.get_name()}", "match", color)

if __name__ == "__main__":
    import sys
    sys.path.append('./')
    import tests.test_files_index as Test
    logging.basicConfig(level=logging.DEBUG)

    for file in Test.all_test_files():
        #if file != Test.FAKE_ID: continue
        music_file = MusicFile(file)
        result = Matcher.identify(music_file)
        logging.info(result)
