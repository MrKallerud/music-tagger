from argparse import ArgumentParser
from os import mkdir
from os.path import exists
from pathlib import Path

from music_tagger import colors as Color
from music_tagger.music_file import MusicFile
from music_tagger.matcher import Matcher
from music_tagger.util import AUDIO_FORMATS, FOLDER


def main():
    if not exists(FOLDER): mkdir(FOLDER)

    parser = ArgumentParser()

    # Add url
    parser.add_argument("file", type = str, help = "Path to the file to be analyzed.")

    # Add options
    parser.add_argument("-sc", "--soundcloud", help = "Specify a SoundCloud URL to get metadata from")
    parser.add_argument("-s", "--spotify", help = "Specify a Spotify URL to get metadata from")
    parser.add_argument("-f", "--format", default = None, help = "Converts audio files to the desired format")
    parser.add_argument("--no_overwrite", action = "store_true", help = "Keeps existing files and metadata")
    parser.add_argument("-sim", "--simulate", action = "store_true", help = "Simulates the matching without writing metadata or converting files")
    parser.add_argument("--suppress", action = "store_true", help = "Will match with the best option without prompting user")

    args = parser.parse_args()
    path = Path(args.file)

    if path.is_dir():
        for file in path.iterdir():
            tag_music(file, args)
    else: tag_music(path, args)

def tag_music(path: Path, args):
    if path.suffix not in AUDIO_FORMATS:
        print(path.name, "is not a supported filetype.\n")
        return
    file = MusicFile(path)
    print(f"\n{Color.BOLD}{file}{Color.ENDC}")

    try: Matcher.print_match(*file.identify(suppress = args.suppress))
    except TypeError as e:
        print(f"{Color.WARNING}{Color.BOLD}NO MATCH{Color.ENDC}")
    except Exception as e:
        print(f"{Color.FAIL}{Color.BOLD}ERROR:{Color.ENDC} {e}")
    
    if args.simulate: return

    if args.format:
        format = args.format if args.format.startswith('.') else f".{args.format}"
        if file.get_ext() != format:
            file.convert(format, args.no_overwrite)

    file.write_metadata(args.no_overwrite)
