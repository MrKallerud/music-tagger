from shazam import Shazam
from difflib import SequenceMatcher

from music_tagger.music_file import MusicFile
from music_tagger.soundcloud import SoundCloudAPI
from music_tagger.spotify import SpotifyAPI
from music_tagger.track import Track, Artist, Album
from music_tagger.metadata_fields import MetadataFields as Fields

class MatchError(Exception):
    def __init__(self, reason: str) -> None:
        super().__init__(reason)

class Matcher:
    THRESHOLD = 0.9
    __MIN_THRESHOLD = 0.6
    __MS_THRESHOLD = 2000

    api = SpotifyAPI | SoundCloudAPI

    @staticmethod
    def identify(music_file: MusicFile, apis: list[api] = [SpotifyAPI, SoundCloudAPI]) -> tuple[Track, float]:
        """Searches through the APIs to find the best match."""

        track = music_file.as_track()

        # Iterate through all the apis and collect the best matches
        all_results = {}
        for api in apis:
            print(f"[search] {api.NAME}...")
            results = api.search(track = track.get_name(), artist = track.get_artists())

    @staticmethod
    def compare_tracks(this: Track, other: Track) -> float:
        # ISRC
        isrc_rate = None
        if this.get(Fields.ISRC) is not None and other.get(Fields.ISRC) is not None:
            if this.get(Fields.ISRC).lower() == other.get(Fields.ISRC).lower(): isrc_rate = 1
            else: isrc_rate = -10

        # Duration
        time_rate = None
        if Fields.DURATION in this.get() and Fields.DURATION in other.get():
            time_diff = abs(this.get(Fields.DURATION) - other.get(Fields.DURATION))
            time_rate = min((Matcher.__MS_THRESHOLD - time_diff) / Matcher.__MS_THRESHOLD, 1)

        # Title
        title_rate = Matcher._compare_strings(this.get(Fields.NAME), other.get(Fields.NAME))
        if title_rate is not None and title_rate < Matcher.__MIN_THRESHOLD: title_rate = 0

        # Artists (Incl. with and feature)
        artist_rate = Matcher.__compare_lists(
            this.get(Fields.ARTISTS, []) + this.get(Fields.FEATURING, []) + this.get(Fields.WITH, []),
            other.get(Fields.ARTISTS, []) + other.get(Fields.FEATURING, []) + other.get(Fields.WITH, [])
        )

        # Album
        album_rate = None
        if this.get(Fields.ALBUM) is not None and other.get(Fields.ALBUM) is not None:
            album_rate = this.get(Fields.ALBUM).compare_to(other.get(Fields.ALBUM))

        # Extended
        extended_rate = None
        if this.get(Fields.EXTENDED) is not None or other.get(Fields.EXTENDED) is not None:
            extended_rate = Matcher._compare_strings(this.get(Fields.EXTENDED, ""), other.get(Fields.EXTENDED, ""))
            if extended_rate is not None and extended_rate < Matcher.THRESHOLD: extended_rate = -1
        
        # Versions
        version_rates = []
        for version, artists in other.get(Fields.VERSIONS, {}).items():
            other_artists = this.get(Fields.VERSIONS, {}).get(version)
            diff = Matcher.__compare_lists(artists, other_artists)
            if diff is None: version_rates.append(0)
            else: version_rates.append(diff)
        if len(version_rates) != 0:
            version_rate = sum(version_rates) / len(version_rates)
        else: version_rate = None

        # Result
        rates = {
            Fields.ALBUM: album_rate,
            Fields.ARTISTS: artist_rate,
            Fields.DURATION: time_rate,
            Fields.EXTENDED: extended_rate,
            Fields.ISRC: isrc_rate,
            Fields.NAME: title_rate,
            Fields.VERSIONS: version_rate,
        }

        for key, value in rates.items():
            print(f"{key.capitalize()}:".ljust(20), end='')
            if value is None: print("N/A")
            else: print(f"{int(value*100)}%")

        rates = list(filter(lambda x: x is not None, rates.values()))
        print("Total:".ljust(20), end=f"{int(sum(rates) / len(rates) * 100)}%\n")
        return min(1, max(0, sum(rates) / len(rates)))

    # @staticmethod
    # def identify2(music_file: MusicFile, apis: list[api] = [SpotifyAPI, SoundCloudAPI], album_types = ["Single"], suppress: bool = False) -> tuple[track, float]:
    #     all_results = {}
        
    #     for api in apis:
    #         print(f"Matching with {api.NAME}...")
    #         results = Matcher.__match(music_file, api)
    #         if not results: continue
    #         for track, ratio in results.items():
    #             if ratio >= Matcher.__THRESHOLD and suppress: return track, ratio
    #         all_results.update(results)

    #     print(f"Matching with Shazam...")
    #     shazam = Matcher.__shazam(music_file)
    #     if shazam:
    #         shazam_result = Matcher.__check_results(music_file, [shazam])
    #         shazam.get_spotify_metadata(all_results)
    #         if shazam_result: all_results.update(shazam_result)

    #     # Filtering
    #     # TODO: Accept Album, but pri Single
    #     if len(all_results.keys()) == 0: raise MatchError("No matches")
    #     all_results = dict(filter(lambda item: abs(item[0].get_duration() - music_file.get_duration()) <= 1, all_results.items()))
    #     if len(all_results.keys()) == 0: raise MatchError("No matching durations")
    #     all_results = dict(filter(lambda item: item[0].get_album_type() in album_types, all_results.items()))
    #     if len(all_results.keys()) == 0: raise MatchError("No matching album types")

    #     print(music_file.get_filename())
    #     print(music_file.to_string())
    #     print(all_results)

    #     all_results = dict(sorted(all_results.items(), key=lambda item: item[1], reverse=True))
    #     if suppress: return list(all_results.items())[0]

    #     i = 0
    #     for result, ratio in all_results.items():
    #         print(f"{i + 1}. ", end='')
    #         Matcher.print_match(result, ratio)
    #         i += 1

    #     choice = input("Select best match (or nothing): ")
    #     if choice.strip().isdigit():
    #         return list(all_results.items())[int(choice.strip()) - 1]

    # @staticmethod
    # def print_match(match: track, ratio: float):
    #     if ratio > 0.8: print(Color.OKGREEN, end='')
    #     elif ratio > Matcher.__MIN_THRESHOLD: print(Color.WARNING, end='')
    #     else: print(Color.FAIL, end='')
    #     print(f"{ratio:.1%}:{Color.ENDC} {match}")

    # @staticmethod
    # def __shazam(music_file: MusicFile) -> track:
    #     with Shazam(music_file.read()) as shazam:
    #         for _, result in shazam.results:
    #             if not result.get("track"): return None
    #             return ShazamTrack(result)

    # @staticmethod
    # def __match(music_file: MusicFile, api: api) -> dict[Track, float] | None:
    #     try:
    #         results = api.search(music_file.get_filename())
    #         if music_file.get_filename() != music_file.to_string():
    #             results.extend(api.search(music_file.to_string()))
    #         results = list(dict.fromkeys(results))
    #         return Matcher.__check_results(music_file, results)
    #     except HTTPError as e:
    #         print(e.request.url)
    
    # @staticmethod
    # def __check_results(music_file: MusicFile, results: list[track]) -> dict[track, float] | None:
    #     if len(results) == 0: return None
    #     matches = {}

    #     for result in results:
    #         print(f"[comparing] {music_file} // {result}")
    #         ratio = Matcher.__compare_result(music_file, result)
    #         matches[result] = ratio

    #     if len(matches.keys()) == 0: return None
    #     return dict(sorted(matches.items(), key=lambda item: item[1], reverse=True))

    # @staticmethod
    # def __compare_result(music_file: MusicFile, result: track):
    #     # Compare filename
    #     filename_match = max(
    #         Matcher.__compare_strings(music_file.get_filename(), result.get_filename()),
    #         Matcher.__compare_strings(music_file.to_string(), result.to_string()),
    #         Matcher.__compare_strings(music_file.get_filename(), result.to_string()),
    #         Matcher.__compare_strings(music_file.to_string(), result.get_filename())
    #     )

    #     # Compare duration
    #     duration_match = min(1 - abs(music_file.get_duration() - result.get_duration()), 0)

    #     # Compare metadata
    #     parsed_metadata = MetadataParser(music_file.get_filename())
    #     title_match = Matcher.__compare_metadata("title", music_file, parsed_metadata, result)
    #     artist_match = Matcher.__compare_metadata("artist", music_file, parsed_metadata, result)
    #     album_match = Matcher.__compare_metadata("album", music_file, parsed_metadata, result)

    #     return sum([filename_match, duration_match, title_match]) / 3

    # @staticmethod
    # def __compare_metadata(key: str, file: MusicFile, parsed_file: MetadataParser, result: track) -> float:
    #     file_value = file.get_metadata(key)
    #     try: file_parsed_value = getattr(parsed_file, key)
    #     except AttributeError: file_parsed_value = None
    #     try: result_value = getattr(result, key)
    #     except AttributeError: result_value = None
    #     try: result_parsed_value = getattr(result.metadata_parser, key)
    #     except AttributeError: result_parsed_value = None

    #     print(f"{file_value=}")
    #     print(f"{file_parsed_value=}")
    #     print(f"{result_value=}")
    #     print(f"{result_parsed_value=}")

    #     comparisons = [0]
    #     comparisons.append(Matcher.__compare_strings(file_value, result_value))
    #     comparisons.append(Matcher.__compare_strings(file_parsed_value, result_value))
    #     comparisons.append(Matcher.__compare_strings(file_parsed_value, result_parsed_value))
    #     comparisons.append(Matcher.__compare_strings(file_value, result_parsed_value))

    #     return max(filter(None, comparisons))

    # @staticmethod
    # def __compare_version(parsed_file: MetadataParser, result: track) -> float:
    #     file_versions = [parsed_file.version]
    #     file_versions.extend(parsed_file.remixers)

    @staticmethod
    def __compare_lists(lst1: list, lst2: list) -> float | None:
        if not isinstance(lst1, list) or not isinstance(lst2, list): return None
        longest = lst1 if len(lst1) >= len(lst2) else lst2
        shortest = lst1 if longest is lst2 else lst2
        assert longest is not shortest
        if len(longest) == 0: return None

        similar = 0
        for x in shortest:
            for y in longest:
                if x == y:
                    similar += 1
                    break
                elif isinstance(x, str) and isinstance(y, str):
                    diff = Matcher._compare_strings(x, y)
                    if diff > Matcher.__MIN_THRESHOLD: similar += diff; break
                elif isinstance(x, (Artist, Album)) and isinstance(y, (Artist, Album)):
                    diff = x.compare_to(y)
                    if diff > Matcher.__MIN_THRESHOLD: similar += diff; break
        
        return similar / len(shortest)

    @staticmethod
    def _compare_strings(str1: str, str2: str) -> float | None:
        if not isinstance(str1, str) or not isinstance(str2, str): return None
        return SequenceMatcher(None, str1.lower(), str2.lower()).ratio()


if __name__ == "__main__":
    #print(Matcher.identify(MusicFile("/Users/ruud/Development/music-tagger/tests/test_files/Elton John, Dua Lipa - Cold Heart (Claptone .mp3"), suppress=True))

    track1 = Track({
        Fields.NAME: "Loop",
        Fields.DURATION: 200_323,
        Fields.ARTISTS: [Artist("Martin Garrix"), Artist("Dallas K")],
        Fields.FEATURING: [Artist("Sasha Alex Sloan")],
        Fields.ISRC: "USUG12204822",
        Fields.VERSIONS: {"Remix": [Artist("Brooks")]},
        Fields.EXTENDED: "Extended",
        Fields.ALBUM: Album("Loop - Single")
    })

    track2 = Track({
        Fields.NAME: "Loop",
        Fields.DURATION: 200_000,
        Fields.FEATURING: [Artist("sasha sloan")],
        Fields.ISRC: "usug12204822",
        Fields.VERSIONS: {"Remix": [Artist("brooks")]},
        Fields.EXTENDED: "Extended",
        Fields.ALBUM: Album("Revive - EP")
    })

    Matcher.compare_tracks(track1, track2)
