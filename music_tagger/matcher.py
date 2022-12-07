from shazam import Shazam
from difflib import SequenceMatcher
from requests import HTTPError

from music_tagger import colors as Color
from music_tagger.music_file import MusicFile
from music_tagger.shazam_track import ShazamTrack
from music_tagger.soundcloud import SoundCloudAPI, SoundCloudTrack
from music_tagger.spotify import SpotifyAPI, SpotifyTrack
from music_tagger.metadata import MetadataParser

class MatchError(Exception):
    def __init__(self, reason: str) -> None:
        super().__init__(reason)

class Matcher:
    __THRESHOLD = 0.9
    __MIN_THRESHOLD = 0.6

    track = SpotifyTrack | SoundCloudTrack | ShazamTrack
    api = SpotifyAPI | SoundCloudAPI

    @staticmethod
    def identify(music_file: MusicFile, apis: list[api] = [SpotifyAPI, SoundCloudAPI], album_types = ["Single"], suppress: bool = False) -> tuple[track, float]:
        all_results = {}
        
        for api in apis:
            print(f"Matching with {api.NAME}...")
            results = Matcher.__match(music_file, api)
            if not results: continue
            for track, ratio in results.items():
                if ratio >= Matcher.__THRESHOLD and suppress: return track, ratio
            all_results.update(results)

        print(f"Matching with Shazam...")
        shazam = Matcher.__shazam(music_file)
        if shazam:
            shazam_result = Matcher.__check_results(music_file, [shazam])
            shazam.get_spotify_metadata(all_results)
            if shazam_result: all_results.update(shazam_result)

        # Filtering
        # TODO: Accept Album, but pri Single
        if len(all_results.keys()) == 0: raise MatchError("No matches")
        all_results = dict(filter(lambda item: abs(item[0].get_duration() - music_file.get_duration()) <= 1, all_results.items()))
        if len(all_results.keys()) == 0: raise MatchError("No matching durations")
        all_results = dict(filter(lambda item: item[0].get_album_type() in album_types, all_results.items()))
        if len(all_results.keys()) == 0: raise MatchError("No matching album types")

        print(music_file.get_filename())
        print(music_file.to_string())
        print(all_results)

        all_results = dict(sorted(all_results.items(), key=lambda item: item[1], reverse=True))
        if suppress: return list(all_results.items())[0]

        i = 0
        for result, ratio in all_results.items():
            print(f"{i + 1}. ", end='')
            Matcher.print_match(result, ratio)
            i += 1

        choice = input("Select best match (or nothing): ")
        if choice.strip().isdigit():
            return list(all_results.items())[int(choice.strip()) - 1]

    @staticmethod
    def print_match(match: track, ratio: float):
        if ratio > 0.8: print(Color.OKGREEN, end='')
        elif ratio > Matcher.__MIN_THRESHOLD: print(Color.WARNING, end='')
        else: print(Color.FAIL, end='')
        print(f"{ratio:.1%}:{Color.ENDC} {match}")

    @staticmethod
    def __shazam(music_file: MusicFile) -> track:
        with Shazam(music_file.read()) as shazam:
            for _, result in shazam.results:
                if not result.get("track"): return None
                return ShazamTrack(result)

    @staticmethod
    def __match(music_file: MusicFile, api: api) -> dict[track, float] | None:
        try:
            results = api.search(music_file.get_filename())
            if music_file.get_filename() != music_file.to_string():
                results.extend(api.search(music_file.to_string()))
            results = list(dict.fromkeys(results))
            return Matcher.__check_results(music_file, results)
        except HTTPError as e:
            print(e.request.url)
            return None
    
    @staticmethod
    def __check_results(music_file: MusicFile, results: list[track]) -> dict[track, float] | None:
        if len(results) == 0: return None
        matches = {}

        for result in results:
            print(f"Comparing {music_file} // {result}")
            ratio = Matcher.__compare_result(music_file, result)
            matches[result] = ratio

        if len(matches.keys()) == 0: return None
        return dict(sorted(matches.items(), key=lambda item: item[1], reverse=True))

    @staticmethod
    def __compare_result(music_file: MusicFile, result: track):
        # Compare filename
        filename_match = max(
            Matcher.__compare_strings(music_file.get_filename(), result.get_filename()),
            Matcher.__compare_strings(music_file.to_string(), result.to_string()),
            Matcher.__compare_strings(music_file.get_filename(), result.to_string()),
            Matcher.__compare_strings(music_file.to_string(), result.get_filename())
        )

        # Compare duration
        duration_match = min(1 - abs(music_file.get_duration() - result.get_duration()), 0)

        # Compare metadata
        parsed_metadata = MetadataParser(music_file.get_filename())
        title_match = Matcher.__compare_metadata("title", music_file, parsed_metadata, result)
        artist_match = Matcher.__compare_metadata("artist", music_file, parsed_metadata, result)
        album_match = Matcher.__compare_metadata("album", music_file, parsed_metadata, result)

        return sum([filename_match, duration_match, title_match]) / 3

    @staticmethod
    def __compare_metadata(key: str, file: MusicFile, parsed_file: MetadataParser, result: track) -> float:
        file_value = file.get_metadata(key)
        try: file_parsed_value = getattr(parsed_file, key)
        except AttributeError: file_parsed_value = None
        try: result_value = getattr(result, key)
        except AttributeError: result_value = None
        try: result_parsed_value = getattr(result.metadata_parser, key)
        except AttributeError: result_parsed_value = None

        print(f"{file_value=}")
        print(f"{file_parsed_value=}")
        print(f"{result_value=}")
        print(f"{result_parsed_value=}")

        comparisons = [0]
        comparisons.append(Matcher.__compare_strings(file_value, result_value))
        comparisons.append(Matcher.__compare_strings(file_parsed_value, result_value))
        comparisons.append(Matcher.__compare_strings(file_parsed_value, result_parsed_value))
        comparisons.append(Matcher.__compare_strings(file_value, result_parsed_value))

        return max(filter(None, comparisons))

    @staticmethod
    def __compare_version(parsed_file: MetadataParser, result: track) -> float:
        file_versions = [parsed_file.version]
        file_versions.extend(parsed_file.remixers)

    @staticmethod
    def __compare_strings(str1: str, str2: str) -> float | None:
        if not str1 or not str2: return None
        return SequenceMatcher(None, str1.lower(), str2.lower()).ratio()


if __name__ == "__main__":
    print(Matcher.identify(MusicFile("/Users/ruud/Development/music-tagger/tests/test_files/Elton John, Dua Lipa - Cold Heart (Claptone .mp3"), suppress=True))
