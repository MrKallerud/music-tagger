from argparse import ArgumentParser
from os import mkdir
from os.path import exists
from pathlib import Path

from music_tagger.log import Log, Color
from music_tagger.music_file import MusicFile
from music_tagger.matcher import Matcher
from music_tagger.util import AUDIO_FORMATS, FOLDER

file_count = 0
identified_files = 0

### CONSTANTS
TEXT_INDENT = 9

def main():
    if not exists(FOLDER): mkdir(FOLDER)

    ### ARGUMENTS
    parser = ArgumentParser()

    # Add url
    parser.add_argument("file", type = str, help = "Path to the file to be analyzed.")

    # Add options
    # parser.add_argument("-sc", "--soundcloud", help = "Specify a SoundCloud URL to get metadata from")
    # parser.add_argument("-s", "--spotify", help = "Specify a Spotify URL to get metadata from")
    parser.add_argument("-f", "--format", default = None, help = "Converts audio files to the desired format")
    parser.add_argument("--no_overwrite", action = "store_true", help = "Keeps existing files and metadata")
    parser.add_argument("-sim", "--simulate", action = "store_true", help = "Simulates the matching without writing metadata or converting files")
    parser.add_argument("--suppress", action = "store_true", help = "Will match with the best option without prompting user")

    args = parser.parse_args()
    path = Path(args.file)


    ### LOGGER CONFIG
    Log.config(Log.WARNING)


    ### DO TASKS
    find_and_tag(path, args)

    #print(f"\n{Color.BOLD}{Color.OKGREEN}Finished!{Color.ENDC}", end='')
    #print(f" - Identified {identified_files}/{file_count} files.")

def find_and_tag(path: Path, args):
    if path.is_file(): return tag_music(path, args)
    for file in path.iterdir():
        find_and_tag(file, args)

def tag_music(path: Path, args):
    if path.suffix not in AUDIO_FORMATS:
        Log.warning(f"{path.name} is not a supported filetype"); return

    # Create MusicFile
    file = MusicFile(path)
    Log.info(f"{Color.BOLD}{file}{Color.CLEAR}")

    # TODO: Handle counting better
    global file_count, identified_files
    file_count += 1

    result = Matcher.identify(file)
    if result:
        identity, ratio = result
        Matcher.print_match(identity, ratio)
    else: Log.warning("No match")

    # try:
    #     Matcher.print_match(*file.identify(suppress = args.suppress))
    #     identified_files += 1
    # except Exception as e: logging.error(e.with_traceback())

    # if args.simulate: return

    # if args.format:
    #     format = args.format if args.format.startswith('.') else f".{args.format}"
    #     if file.get_ext() != format:
    #         file.convert(format, args.no_overwrite)

    # file.write_metadata(args.no_overwrite)
