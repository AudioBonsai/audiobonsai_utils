import sys
import os
import django
import re
import spotipy
import spotipy.util as sputil
import math
import argparse
from operator import attrgetter
from pprint import pprint

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "audiobonsai.settings")
from django.conf import settings


'''
getSetList --
   Read and score the curators' voting lists, write to PodListen, create a Google Doc and share it
'''

def getSpotifyConn(username='AudioBonsai', scope='user-library-read'): 
    '''
    getSpotifyConn -- connect to spotify
    '''
    spotify = spotipy.Spotify()
    token = sputil.prompt_for_user_token(username, scope)
    sp = spotipy.Spotify(auth=token)
    return sp


def parseList(playlist, spots=10, tracks={}, username='AudioBonsai', scope='user-library-read'):
    '''
    parseList -- read the provided list and score the tracks based on position
    '''
    sp = getSpotifyConn(username, scope)
    bits = re.match('spotify:user:([a-z,A-Z,0-9]*):playlist:([a-z,A-Z,0-9]*)', playlist)
    user_info = sp.user(bits.group(1))
    username = user_info[u'display_name']
    if re.match(username, 'Justin Tyler'):
        username = 'Moksha'
    else:
        username = 'Jesse'
    #pprint(user_info)
    rank = 1
    playlist = sp.user_playlist(user=bits.group(1), playlist_id=bits.group(2))
    playlist_name = playlist[u'name']
    #pprint(results)

    for track in playlist[u'tracks'][u'items']:
        artists = []
        uri = track[u'track'][u'uri']
        for artist in track[u'track'][u'artists']:
            artists.append(artist[u'name'])
        try:
            score = tracks[uri]['score']
        except KeyError:
            tracks[uri] = {}
            tracks[uri]['score'] = 0
        tracks[uri]['artists'] = ', '.join(artists)
        tracks[uri]['album'] = track[u'track'][u'album'][u'name']
        tracks[uri]['title'] = track[u'track'][u'name']
        tracks[uri][username] = rank
        tracks[uri]['score'] += math.pow((spots-rank+1), 2)
        rank += 1
        if rank > spots:
            break

def scoreVotes(tracks, bonus=49):
    '''
    scoreVotes -- combine the scores from the individual lists including adding the two-vote bonus
    '''
    results = {}
    for uri in tracks:
        score = tracks[uri]['score']
        display_str = u'\n\tArtist: {0}\n\tSong:\'{1}\'\n\tAlbum:{2}\n'.format(tracks[uri]['artists'], tracks[uri]['title'], tracks[uri]['album'])
        vote_count = 0
        vote_rank = 25
        vote_string = 'Honorable Mention'
        for key in tracks[uri]:   
            if key not in ['artists', 'album', 'title', 'score']:
                if tracks[uri][key] < vote_rank:
                    vote_string = key
                    vote_rank = tracks[uri][key]
                display_str += u'\t{0}\'s #{1}\n'.format(key, unicode(tracks[uri][key]))
                vote_count += 1
        display_str = u'{0} {1}'.format(vote_string, display_str)

        if vote_count > 1:
            score += bonus
        if score not in results.keys():
            results[score] = []
        results[score].append(display_str)
    return results
 
def printResults(results, spots=10, rank=25):
    '''
    printResults -- write out the results as a playlist and document
    '''
    print "Intro)\n\nAnd now with a little help from our friends the Hit Meters, here are our honorable mentions"
    for score in sorted(results):
        new_rank = rank
        if len(results[score]) > 1:
            rank -= 1
        for entry in results[score]:
            rank_str = str(rank)
            if rank > spots:
                rank_str = "HM"
            print u'{0:2} ({1:3} points): {2}\n'.format(rank_str, str(score), entry)
            new_rank -= 1
            if new_rank == spots:
                print "You put your themes in it\n"
                print "Tracy's Pick of the Week\n"
                print "Now Entering, the top ten\n"
            elif new_rank == 7:
                print "Songs of the Day (plug if available?)\n\nOur top seven songs will also be featured at AudioBonsai.com as songs of the day.  Each day (or as often as our busy lives allow, which means sometimes you'll get five songs for the price of one!) one of these songs will be highlighted on our website.  We also have a Song of the Day playlist on Spotify and Rdio that you can subscribe to for our last eight weeks of songs of the day.\n"

        rank = new_rank
    print "outro)\n\nThanks for listening.  All of the songs we played samples of in this podcast will be embedded in their full glory on this episode's post.  The top seven will be featured as our Songs of the Day for the week.    If you would like to play along, subscribe to the Fresh Cuts: ReFresh list on Spotify and Rdio.  Let us know your favorite before we record Thursday evening via Twitter, Facebook or our website at AudioBonsai.com or leave us a voice mail telling us who you are and what your favorite is at 952-22-AUDIO.  That's 952-222-8346. If you have your pick to us by Thursday night when we record we can work it into the show.  Get it in by Sunday and we can probably duct tape it in awkwardly somewhere.  Monday or later, we can have a nice chat while you listen to what could have been. We hope you found something to love in this episode and we'll see you again next week. "   

if __name__ == "__main__":
    start_path = os.path.realpath(__file__)
    start_array = start_path.split('/')
    sys.path.append('/'.join(start_array[0:len(start_array)-2]))
    
    spots = 10
    bonus = 49
    tracks = {}
    for playlist in [settings.JESSE_TOP_TEN, settings.MOKSHA_TOP_TEN]:
        parseList(playlist, spots, tracks)

    results = scoreVotes(tracks, bonus)

    rank = len(tracks)
    printResults(results, spots, rank)
