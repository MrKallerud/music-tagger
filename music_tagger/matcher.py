from shazam import Shazam
from difflib import SequenceMatcher
from requests import HTTPError

from music_tagger import colors as Color
from music_tagger.music_file import MusicFile
from music_tagger.shazam_track import ShazamTrack
from music_tagger.soundcloud import SoundCloudAPI, SoundCloudTrack
from music_tagger.spotify import SpotifyAPI, SpotifyTrack

class MatchError(Exception):
    def __init__(self, reason: str) -> None:
        super().__init__(reason)

class Matcher:
    __THRESHOLD = 0.8
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
            if music_file.metadata:
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
        matchable_formats = []

        if music_file.metadata and music_file.metadata.get("artist") and music_file.metadata.get("title"):
            if music_file.metadata.get("album"):
                matchable_formats.append(
                    music_file.metadata.get("artist") + " - " + \
                    music_file.metadata.get("title") + " " + \
                    music_file.metadata.get("album"))

            matchable_formats.append(music_file.metadata.get("artist") + " - " + music_file.metadata.get("title"))
            matchable_formats.append(music_file.metadata.get("title") + " - " + music_file.metadata.get("artist"))

        matchable_formats.append(music_file.get_filename())

        if " - " in music_file.get_filename():
            split = music_file.get_filename().split(" - ")
            matchable_formats.append(" - ".join([split[1], split[0]]))

        for format in matchable_formats:
            for result in results:
                matchable_result_formats = [
                    result.get_artist() + " - " + result.get_title() + " " + result.get_album(),
                    result.get_title()
                ]

                for result_format in matchable_result_formats:
                    ratio = Matcher.__compare_strings(format, result_format)
                    if (result in matches.keys() and matches.get(result) > ratio):
                        continue
                    matches[result] = ratio

        if len(matches.keys()) == 0: return None
        return dict(sorted(matches.items(), key=lambda item: item[1], reverse=True))

    @staticmethod
    def __compare_strings(str1: str, str2: str) -> float:
        return SequenceMatcher(None, str1.lower(), str2.lower()).ratio()


if __name__ == "__main__":
    # print(Matcher.identify(MusicFile("/Users/ruud/Desktop/tmp/Artillery (PSY MIX).mp3"), suppress = True))
    # print(Matcher.identify(MusicFile("/Users/ruud/Desktop/tmp/vetikke.mp3")))
    # print(Matcher.identify(MusicFile("/Users/ruud/Desktop/begrn.mp3"), suppress = True))
    print(Matcher.identify(MusicFile("/Users/ruud/Desktop/låter 2/Diplo & SIDEPIECE - On My Mind (Purple Disco Machine Remix).mp3"), suppress = True))