from music_tagger.music_file import MusicFile
from music_tagger import colors as Color
from argparse import ArgumentParser
from pathlib import Path
from os import listdir
from os.path import join

def main():
    parser = ArgumentParser()

    # Add url
    parser.add_argument("file", type = str, help = "Path to the file to be analyzed.")

    # Add options
    services = parser.add_mutually_exclusive_group()
    services.add_argument("-sc", "--soundcloud", help = "Specify a SoundCloud URL to get metadata from")
    services.add_argument("-s", "--spotify", help = "Specify a Spotify URL to get metadata from")

    parser.add_argument("-o", "--overwrite", help = "Overwrites existing metadata without asking")

    args = parser.parse_args()

    path = Path(args.file)

    if path.is_dir():
        for file in path.iterdir():
            # TODO: Convert wav to mp3
            if file.suffix != ".mp3": continue
            file = MusicFile(file)
            match = identify(file)
            #file.write_metadata(match)
    else:
        file = MusicFile(path)
        match = identify(file)

def identify(file: MusicFile):
    print(f"\n{Color.BOLD}{file.to_string()}{Color.ENDC}")
    # TODO: Shazam
    # TODO: Spotify

    # Soundcloud
    sc_matches: dict = file.match_soundcloud()

    for sc_match, sc_matchrate in sc_matches.items():
        if sc_matchrate > 0.8: print(Color.OKGREEN, end='')
        elif sc_matchrate < 0.5: print(Color.FAIL, end='')
        else: print(Color.WARNING, end='')
        print(f"{sc_matchrate:.1%}:{Color.ENDC} {sc_match.title}")
        if sc_matchrate > 0.85: return sc_match
        choice = input("y/n: ")
        if 'y' in choice.lower(): return sc_match

    return None

if __name__ == "__main__":
    file = MusicFile("/Users/ruud/Downloads/ABBA - GIMME GIMME GIMME [FÄT TONY _ MEDUN R.mp3")
    match = identify(file)
    file.write_metadata(match)
