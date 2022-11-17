import re
from os.path import join, expanduser

FOLDER = join(expanduser('~'), ".music-tagger")

AUDIO_FORMATS = [
    ".wav",
    ".flac",
    ".mp3"
]

YEAR_REGEX = re.compile(r"\b(2[01k]\d{2})\b")
BRACKET_REGEX = re.compile(r"[*(\[](.*?)(?:[*)\]]|$)", re.I)

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
GENRE_REGEX = re.compile(r"\b(" + r"|".join(__GENRES) + r")\b", re.I)


__VERSIONS = [
    "Bootleg",
    "Edit",
    "Flip",
    "Mashup",
    "Remaster",
    "Remastered",
    "Remix",
    "Rework"
]
VERSION_REGEX = re.compile(r"\b(" + r"|".join(__VERSIONS) + r")\b", re.I)

__IGNORE = [
    "DL",
    "Download",
    "Free",
    "Giveaway",
    "Support",
    "Supported"
]
IGNORE_REGEX = re.compile(r"\b(" + r"|".join(__IGNORE) + r")\b", re.I)

__FEATURING = [
    "Feat",
    "Featuring",
    "Ft"
]
