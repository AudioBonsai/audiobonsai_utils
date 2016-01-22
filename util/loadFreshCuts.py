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
from rdioapi import Rdio
import sys

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "audiobonsai.settings")
from django.conf import settings
from rootball.models import FreshCuts
django.setup()

parser = argparse.ArgumentParser(description='load a Fresh Cuts playlist')
parser.add_argument('-pubdate', action='store', dest='pubdate', help='The date of the FreshCuts list publication')
parser.add_argument('-rdiourl', action='store', dest='rdiourl', help='The playlist URL for Rdio (not implemented yet)')
parser.add_argument('-spotifyuri', action='store', dest='spotifyuri', help='The playlist URI from Spotify')

def getSpotifyConn(username='AudioBonsai', scope='user-read-private playlist-modify-private playlist-read-private playlist-modify-public'):
    '''
    get_spotify_conn -- connect to spotify
    '''
    token = sputil.prompt_for_user_token(username, scope)
    sp = spotipy.Spotify(auth=token)
    return sp

def getRdioConn():
    rdio_state = {}
    rdio_client = Rdio(settings.RDIO_KEY, settings.RDIO_SECRET, rdio_state)
    return rdio_client

if __name__ == "__main__":
    args = parser.parse_args()
    print args
    fc = FreshCuts()
    sp = getSpotifyConn()
    rdio = getRdioConn()

    print sys.argv

    #bits = re.match('spotify:user:([a-z,A-Z,0-9]*):playlist:([a-z,A-Z,0-9]*)', args.spotifyuri)
    bits = re.match('https://open.spotify.com/user/([a-z,A-Z,0-9]*)/playlist/([a-z,A-Z,0-9]*)', args.spotifyuri)
    #print bits.group(1) + ' : ' + bits.group(2)
    splist = sp.user_playlist(user=bits.group(1), playlist_id=bits.group(2))
    #rdiohash = rdio.call('getObjectFromUrl', url=args.rdiourl, extras = "trackKeys")
    fc.get_freshcuts_by_date_spotifyuri(args.pubdate, args.spotifyuri, splist) #, rdio, args.rdiourl, rdiohash)
