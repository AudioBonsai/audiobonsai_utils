"""
loadFreshCuts.py

Parse a Fresh Cuts playlist and create the right
"""

__author__ = 'Jesse'

import argparse
import django
import os
import re
import spotipy
import spotipy.util as sputil
import sys

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "audiobonsai.settings")
from django.conf import settings
from rootball.models import FreshCuts, Playlist, Song, Artist, PerformedBy, PlaylistTrack, Release, ReleasedOn
django.setup()

parser = argparse.ArgumentParser(description='load a Fresh Cuts playlist')
parser.add_argument('-pubdate', action='store', dest='pubdate', help='The date of the FreshCuts list publication')
parser.add_argument('-rdiourl', action='store', dest='rdiourl', help='The playlist URL for Rdio (not implemented yet)')
parser.add_argument('-spotifyuri', action='store', dest='spotifyuri', help='The playlist URI from Spotify')

def getSpotifyConn(username='AudioBonsai', scope='user-library-read'):
    '''
    getSpotifyConn -- connect to spotify
    '''
    token = sputil.prompt_for_user_token(username, scope)
    sp = spotipy.Spotify(auth=token)
    return sp

if __name__ == "__main__":
    args = parser.parse_args()
    print args
    fc = FreshCuts()
    sp = getSpotifyConn()
    print sys.argv

    #bits = re.match('spotify:user:([a-z,A-Z,0-9]*):playlist:([a-z,A-Z,0-9]*)', args.spotifyuri)
    bits = re.match('https://open.spotify.com/user/([a-z,A-Z,0-9]*)/playlist/([a-z,A-Z,0-9]*)', args.spotifyuri)
    #print bits.group(1) + ' : ' + bits.group(2)
    splist = sp.user_playlist(user=bits.group(1), playlist_id=bits.group(2))
    fc.get_freshcuts_by_date_spotifyuri(args.pubdate, args.spotifyuri, splist)
