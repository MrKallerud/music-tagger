import re
from os.path import join, expanduser

FOLDER = join(expanduser('~'), ".music-tagger")

AUDIO_FORMATS = [
    ".wav",
    ".flac",
    ".mp3"
]

# REGEXES
def __list_to_regex(list: list) -> re.Pattern:
    return re.compile(r"\b(" + r"|".join(list) + r")\b", re.I)

__GENRES = [
    "Acid Jazz",
    "Acid Punk",
    "Acid",
    "Alternative",
    "AlternRock",
    "Ambient",
    "Bass",
    "Blues",
    "Cabaret",
    "Christian Rap",
    "Classic Rock",
    "Classical",
    "Comedy",
    "Country",
    "Cult",
    "Dance",
    "Darkwave",
    "Death Metal",
    "Deep House",
    "Disco",
    "Dream",
    "EDM",
    "Electronic",
    "Ethnic",
    "Euro-Techno",
    "Eurodance",
    "Funk",
    "Fusion",
    "Game",
    "Gangsta",
    "Gospel",
    "Gothic",
    "Grunge",
    "Hard Rock",
    "Hip-Hop",
    "House",
    "Industrial",
    "Jazz",
    "Jazz+Funk",
    "Jungle",
    "Lo-Fi",
    "Meditative",
    "Metal",
    "Musical",
    "Native American",
    "New Age",
    "New Wave",
    "Noise",
    "Oldies",
    "Other",
    "Polka",
    "Pop-Folk",
    "Pop",
    "Pop/Funk",
    "Pranks",
    "Psychadelic",
    "Psy Trance",
    "Punk",
    "R&B",
    "Rap",
    "Rave",
    "Rave",
    "Reggae",
    "Retro",
    "Rock & Roll",
    "Rock",
    "Showtunes",
    "Ska",
    "Soul",
    "Sound Clip",
    "Soundtrack",
    "Southern Rock",
    "Space",
    "Tech House",
    "Techno-Industrial",
    "Techno",
    "Top 40",
    "Trailer",
    "Trance",
    "Tribal",
    "Trip-Hop",
    "Tropical House",
    "Vocal",
]

__VERSIONS = [
    "Bootleg",
    "Edit",
    "Flip",
    "Mashup",
    "Mix",
    "Remaster",
    "Remastered",
    "Remix",
    "Rework"
]

__IGNORE = [
    "DL",
    "Download",
    "Free",
    "Giveaway",
    "Support",
    "Supported"
]

__FEATURING = [
    "Feat",
    "Featuring",
    "Ft"
]

__EXTENDED = [
    "Extended",
    "Original"
]

ARTIST_SPLIT_REGEX = re.compile(r"\s*,\s*|\s+(?:,|vs|\+|_|x|&)\s+", re.I)
BRACKET_REGEX = re.compile(r"[*(\[].*?(?:[*)\]]|$)", re.I)
DASH_SPLITTER_REGEX = re.compile(r"(?:^|\s+)[-–—](?:\s+|$)")
WITH_REGEX = re.compile(r"\b(with)\b", re.I)
YEAR_REGEX = re.compile(r"\b(2[01k]\d{2})\b")

EXTENDED_REGEX = __list_to_regex(__EXTENDED)
FEAT_REGEX = __list_to_regex(__FEATURING)
GENRE_REGEX = __list_to_regex(__GENRES)
IGNORE_REGEX = __list_to_regex(__IGNORE)
VERSION_REGEX = __list_to_regex(__VERSIONS)