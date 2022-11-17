from http.client import responses
from music_tagger import colors as Color

class HTTPError(Exception):
    """Raised when http request fails"""
    def __init__(self, status_code: int, message: str = "HTTP ERROR"):
        super().__init__(f"{Color.WARNING}{Color.BOLD}{message}: {Color.ENDC}{status_code} {responses.get(status_code)}")
