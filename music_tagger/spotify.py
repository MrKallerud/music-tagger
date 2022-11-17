import requests, json
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from music_tagger.metadata import MetadataParser
from difflib import SequenceMatcher

class SpotifyAPI:
    __WEBURL_BASE = "http://open.spotify.com"
    __API_BASE = "http://api.spotify.com"
    __HTML_PARSER = "html.parser"

    __access_token = None

    @staticmethod
    def get_access_token() -> str:
        if SpotifyAPI.__access_token: return SpotifyAPI.__access_token
        response = requests.get(SpotifyAPI.__WEBURL_BASE)
        if response.status_code != 200:
            raise ValueError(f"get_access_token: {response.status_code}")
        soup = BeautifulSoup(response.content, SpotifyAPI.__HTML_PARSER)
        credentials = json.loads(soup.find(id="session").get_text())
        SpotifyAPI.__access_token = credentials.get("accessToken")
        return SpotifyAPI.__access_token

    @staticmethod
    def identify(filename):
        metadata = MetadataParser(filename)

        print(metadata)
        print()

        try: artists, title, id = SpotifyAPI.search(track = metadata.get_title(), artist = metadata.get_album_artist())
        except TypeError:
            artists, title, id = SpotifyAPI.search(filename)

        # Compare result
        tr = SequenceMatcher(None, metadata.get_title(), title).ratio()
        print(f"{tr=}")
        if tr < 0.6: raise ValueError("Titles don't match")

        ar = 0
        for m_artist in metadata.artists:
            ratio = 0
            for s_artist in artists:
                comp = SequenceMatcher(None, m_artist, s_artist).ratio()
                print(f"{comp=}")
                if ratio < comp: ratio = comp
                print(f"{ratio=}")
            ar += ratio
        print(f"{ar=}")
        ar /= len(metadata.artists)

        print(f"{ar=}")

        return f"Ratio: {(tr * 2 + ar) / 3} - " + ", ".join(artists) + f" - {title} ({id})"

    @staticmethod
    def search(query: str = "", track: str = None, artist: str = None, album: str = None, isrc: str = None, limit: int = 1, offset: int = 0, type: str = "track") -> json:
        url = "/v1/search"
        if track: query += f" track:{track}"
        if artist: query += f" artist:{artist}"
        if album: query += f" album:{album}"
        if isrc: query += f" isrc:{isrc}"

        params = {
            "q": query,
            "limit": limit,
            "offset": offset,
            "type": type
        }

        headers = {
            "authorization": f"Bearer {SpotifyAPI.get_access_token()}"
        }

        response = requests.get(urljoin(SpotifyAPI.__API_BASE, url), params, headers = headers)

        # TODO: Handle status code and other forms of results
        if response.status_code != 200: raise ValueError("search: " + response.status_code)
        
        try:
            result = response.json().get("tracks").get("items")[0]
        except IndexError:
            print("No results!")
            return None

        return [artist.get("name") for artist in result.get("artists")], result.get("name"), result.get("id")

    
    # @staticmethod
    # def __json_to_track(data: json) -> Track:
    #     return Track(
    #         title = data.get("name"),
    #         artists = [artist.get("name") for artist in data.get("artists")],
    #         artwork_url = data.get("album").get("images")[0],

    #     )


if __name__ == "__main__":
    # Quick tests
    print(SpotifyAPI.get_access_token())
    # print(SpotifyAPI.identify("Martin Garrix"))