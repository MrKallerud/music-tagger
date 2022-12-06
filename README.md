
# Music Tagger
An automatic tool for tagging your music library with metadata from online music libraries.

## Features
- Automatically identifies track identity based on
    - Filename
    - Embedded metadata
    - Audio recognition with Shazam
- Fetches metadata and artwork from
    - Spotify
    - SoundCloud
    - Shazam
- Embeds metadata to file
- Encodes audio files to `.mp3`

## Planned features
- [ ] Implement lyric fetching from Genius.
- [ ] Implement metadata fetching from MusicBrainz.
- [ ] Make it possible to specify a url to get metadata from.
- [ ] Make it possible to parse metadata without fetching online.
- [ ] Make it easier to import this package in other Python projects.
- [ ] Add package to pypi

## Installation

<!-- > ℹ️ Just copy-paste the quick install command below into terminal -->

1. Install [Homebrew](https://brew.sh/)
    ```bash
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    ```

2. Install Python and ffmpeg
    ```bash
    brew install python ffmpeg
    ```

3. Clone this repository
    ```bash
    clone https://github.com/MrKallerud/music-tagger
    ```
4. Go into the folder and install the package
    ```bash
    pip3 install .
    ```

<!-- ### Quick Install
Just paste this into the termial to easily install everything
```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)" && brew install python ffmpeg && curl https://cloud.kallerud.no/s/imPxzGJAHootemr/download -o .ez-hype.zip && unzip .ez-hype.zip && rm .ez-hype.zip && cd .ez-hype && pip3 install .
```
### Quick Update
Just paste this into the termial to easily update the program
```bash
rm -r .ez-hype && curl https://cloud.kallerud.no/s/imPxzGJAHootemr/download -o .ez-hype.zip && unzip .ez-hype.zip && rm .ez-hype.zip && cd .ez-hype && pip3 install .
``` -->

## Usage

```bash
music-tagger [File or folder] [Options]
```

### Options
| Command                        | Description
| ------------------------------ | ---
| `-h`, `--help`                 | Show this help message and exit
| `-o PATH`, `--output PATH`     | The output filename with extension
| `-f FORMAT`, `--format FORMAT` | Converts audio files to the desired format
| `--no_overwrite`               | Keeps existing files and metadata
| `-sim`, `--simulate`           | Simulates the matching without writing metadata or converting files
| `--suppress`                   | Will match with the best option without prompting user
<!-- | `-sc URL`, `--soundcloud URL`  | Specify a SoundCloud URL to get metadata from
| `-s URL`, `--spotify URL`      | Specify a Spotify URL to get metadata from -->

### Examples

- Print out the best match to the chosen track without doing anything to the file.
    ```bash
    music-tagger "~/Downloads/Martin Garrix - Scared to be Lonely (feat. Dua Lipa).mp3" --suppress -sim
    ```
