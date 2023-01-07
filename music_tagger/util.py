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
    "Psy Trance",
    "Psychadelic",
    "Punk",
    "R&B",
    "Rap",
    "Rave",
    "Reggae",
    "Retro",
    "Rock & Roll",
    "Rock",
    "Showtunes",
    "Ska",
    "Slap House",
    "Slap",
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
]

__VERSIONS = [
    "Acoustic",
    "Bootleg",
    "Edit",
    "Edition",
    "Flip",
    "Mashup",
    "Mix",
    "Radio Edit",
    "Remaster",
    "Remastered",
    "Remix",
    "Rework",
    "Version",
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
    "ft"
]

__EXTENDED = [
    "Extended",
    "Original"
]

ARTIST_SPLIT_REGEX = re.compile(r"\s*,\s*|\s+(?:,|vs|\+|_|·|//|x|&)\s+", re.I)
BRACKET_REGEX = re.compile(r"[*(\[].*?(?:[*)\]]|$)", re.I)
DASH_SPLITTER_REGEX = re.compile(r"(?:^|\s+)[-–—](?:\s+|$)")
YEAR_REGEX = re.compile(r"\b(2[01k]\d{2})\b", re.I)
FEAT_REGEX = re.compile(r"(?:^|\(|\[)?\s*(?:" + r"|".join(__FEATURING) + r")(?:\.\s*|\s+)(.+?)\s*(?:\(|\)|\[|\]|\s-|$)", re.I)
WITH_REGEX = re.compile(r"(?:^|\(|\[)?\s*with(?:\.\s*|\s+)(.+?)\s*(?:\(|\)|\[|\]|\s-|$)", re.I)

# QUOTE_REGEX = re.compile(r"'(.*?)'")
# DOUBLE_QUOTE_REGEX = re.compile(r'"(.*?)"')
ANY_QUOTE_REGEX = re.compile(r"['\"].*?['\"]")

REMIX_REGEX = re.compile(r"(?:[\[\]()-]|-\s*)(.*?(?:" + "|".join(__VERSIONS) + ")\s*)(?:\)|\])?", re.I)

CAMELOT_KEY_REGEX = re.compile(r"\b([1-9]|1[0-2])([ab])\b", re.I)
KEY_REGEX = re.compile(r"\b([cdefgba][#♯b♭]?)\s*(minor|min|major|maj|m)?\b", re.I)

MULTIPLE_SPACES_REGEX = re.compile(r"\s{2,}")
EMPTY_BRACKETS_REGEX = re.compile(r"[*(\[)]\s*[\])*]")
AFTER_DASH_REGEX = re.compile(r"[-–—]\s*(.+)")
BEFORE_BRACK_DASH_REGEX = re.compile(r"^(.+?)\s*(?:\(|\[|\s[-–—]|$)")

EXTENDED_REGEX = __list_to_regex(__EXTENDED)
GENRE_REGEX = __list_to_regex(__GENRES)
IGNORE_REGEX = __list_to_regex(__IGNORE)
VERSION_REGEX = __list_to_regex(__VERSIONS)
FILETYPE_REGEX = re.compile(r"(?:" + r"|".join(AUDIO_FORMATS) + r")\b")