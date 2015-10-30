import sys
import datetime
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


def parseList(playlist, spots=10, tracks={}, week="MM/DD/YYYY", username='AudioBonsai', scope='user-library-read'):
    '''
    parseList -- read the provided list and score the tracks based on position
    '''
    sp = getSpotifyConn(username, scope)
    bits = re.match('spotify:user:([a-z,A-Z,0-9]*):playlist:([a-z,A-Z,0-9]*)', playlist)
    print bits.group(1)
    user_info = sp.user(bits.group(1))
    username = user_info[u'display_name']
    print(bits.group(2))
    #if re.match(bits.group(2), '3VJeSXOvl8vtleJiLI5AoX'):
    #    username = 'Gary & Ciaran'
    #el
    if re.match(username, 'Justin Tyler'):
        username = 'Moksha'
    elif re.match(username, 'Rodrigo Venegas'):
        username = 'Podrigo'
    elif re.match(username, 'Heidi Wheelock'):
        username = 'Heidi'
    else:
        username = 'Jesse'
    #pprint(user_info)
    print(username)
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
        tracks[uri]['week'] = week
        rank += 1
        if rank > spots:
            break

def scoreVotes(tracks, bonus=49, sotds=[4, 0, 3, 1, 5, 2, 6]):
    '''
    scoreVotes -- combine the scores from the individual lists including adding the two-vote bonus
    '''
    results = {}
    resultsByWeek = {}
    for uri in tracks:
        week = tracks[uri]['week']
        week_str = week.strftime('%m/%d/%Y')
        score = tracks[uri]['score']
        display_str = u'\n\tArtist: {0}\n\tSong:\'{1}\'\n\tAlbum:{2}\n\tFresh Cuts:{3}\n'.format(tracks[uri]['artists'], tracks[uri]['title'], tracks[uri]['album'], week_str)
        display_str = ''.join([u'<div class="artist">{0}</div>\n',
                               u'<div class="song">\'{1}\'</div>\n',
                               u'<div class="album">{2}</div>\n',
                               u'<div class="fresh_cuts">{3}</div>\n']).format(tracks[uri]['artists'], tracks[uri]['title'], tracks[uri]['album'], week_str)

        vote_count = 0
        vote_rank = 25
        vote_string = 'Honorable Mention'
        for key in tracks[uri]:   
            if key not in ['artists', 'album', 'title', 'score', 'week']:
                if tracks[uri][key] < vote_rank:
                    vote_string = key
                    vote_rank = tracks[uri][key]
                #display_str += u'\t{0}\'s #{1}\n'.format(key, unicode(tracks[uri][key]))
                display_str += ''.join(u'<div class="vote">{0}\'s #{1}</div>\n').format(key, unicode(tracks[uri][key]))
                vote_count += 1
        #display_str = u'{0} {1}'.format(vote_string, display_str)
        tracks[uri]['display_str'] = display_str

        if vote_count == 2:
            score += 49
        elif vote_count == 3:
            score += 25
        elif vote_count == 4:
            score += 49
        if score not in results.keys():
            results[score] = []
        results[score].append(uri)
        
        if week_str not in resultsByWeek.keys():
            print 'Creating week_str key: {}'.format(week_str)
            resultsByWeek[week_str] = {}
        if score not in resultsByWeek[week_str].keys():
            resultsByWeek[week_str][score] = []
        resultsByWeek[week_str][score].append(uri)
    for week in resultsByWeek:
        sotd = 0;
        week_datetime = datetime.datetime.strptime(week, '%m/%d/%Y') + datetime.timedelta(days=2)
        for score in sorted(resultsByWeek[week]):
            for uri in resultsByWeek[week][score]:
                print 'week:{}, score:{}, uri:{} sotd:{}'.format(week, score, uri, sotd)
                sotd_datetime = week_datetime + datetime.timedelta(days=sotds[sotd])
                #tracks[uri]['display_str'] += u'\tSOTD:{}\n'.format(sotd_datetime.strftime('%A %m/%d/%Y'))
                #tracks[uri]['display_str'] += u'\tSOTD\n'
                sotd += 1
                if sotd >= len(sotds):
                    break
            if sotd >= len(sotds):
                break
                    
    return results
 
def printResults(results, tracks, spots=10, rank=25):
    '''
    printResults -- write out the results as a playlist and document
    '''
    #print "Intro)\n\nAnd now with a little help from our friends the Hit Meters, here are our honorable mentions"
    dir1 = 'left'
    dir2 = 'right'
    print '<div style="sotd">Songs of the Day</div><hr width="100%"</div>'
    for score in reversed(sorted(results)):
        new_rank = rank
        for entry in results[score]:
            rank_str = str(rank)
            if rank == spots+1:
                #rank_str = "Honorable Mention"
                print '<div style="sotd">Honorable Mentions</div><hr width="100%"</div>'
            #print u'{0:2} ({1:3} points): {2}\n'.format(rank_str, str(score), tracks[entry]['display_str'])

            print ''.join([u'<div width="100%"><div style=\'float:{0}\'>\n',
                           u'<div class="rank">#{1}:</div>{2}\n'
                           u'</div>\n',
                           u'<div style=\'float:{3}\'>\n',
                           u'<iframe src="https://embed.spotify.com/?uri={4}" width="300" height="380" frameborder="0" allowtransparency="true"></iframe>\n'
                           u'</div>\n',
                           u'<hr width="100%"/></div>\n']).format(dir1, rank_str, tracks[entry]['display_str'], dir2, entry)
            if dir1 == 'right':
                dir1 = 'left'
                dir2 = 'right'
            else:
                dir1 = 'right'
                dir2 = 'left'

            new_rank += 1
            #if new_rank == spots:
                #print "You put your themes in it\n"
                #print "Tracy's Expansion of Presence Spotlight\n"
                #print "Now Entering, the top ten\n"
            #elif new_rank == 7:
                #print "Songs of the Day (plug if available?)\n\nOur top seven songs will also be featured at AudioBonsai.com as songs of the day.  Each day (or as often as our busy lives allow, which means sometimes you'll get five songs for the price of one!) one of these songs will be highlighted on our website.  We also have a Song of the Day playlist on Spotify and Rdio that you can subscribe to for our last eight weeks of songs of the day.\n"

        if len(results[score]) > 1:
            rank += len(results[score])
        rank = new_rank
    #print "outro)\n\nThanks for listening.  All of the songs we played samples of in this podcast will be embedded in their full glory on this episode's post.  The top seven will be featured as our Songs of the Day for the week.    If you would like to play along, subscribe to the Fresh Cuts: ReFresh list on Spotify and Rdio.  Let us know your favorite before we record Thursday evening via Twitter, Facebook or our website at AudioBonsai.com or leave us a voice mail telling us who you are and what your favorite is at 952-22-AUDIO.  That's 952-222-8346. If you have your pick to us by Thursday night when we record we can work it into the show.  Get it in by Sunday and we can probably duct tape it in awkwardly somewhere.  Monday or later, we can have a nice chat while you listen to what could have been. We hope you found something to love in this episode and we'll see you again next week. "

if __name__ == "__main__":
    start_path = os.path.realpath(__file__)
    start_array = start_path.split('/')
    sys.path.append('/'.join(start_array[0:len(start_array)-2]))
    
    spots = 10
    bonus = 49
    tracks = {}
    for playlist, week in zip([settings.JESSE_TOP_TEN, settings.MOKSHA_TOP_TEN],#, settings.JESSE_TOP_TEN_2, settings.MOKSHA_TOP_TEN_2],
                              [datetime.datetime.strptime("10/23/2015", "%m/%d/%Y"), datetime.datetime.strptime("10/23/2015", "%m/%d/%Y")]): #,
                               #datetime.datetime.strptime("10/16/2015", "%m/%d/%Y"), datetime.datetime.strptime("10/02/2015", "%m/%d/%Y")]):
    #for playlist, week in zip([settings.JESSE_TOP_TEN, settings.MOKSHA_TOP_TEN, settings.HEIDI_TOP_TEN, settings.MEG_TOP_TEN],
    #                          [datetime.datetime.strptime("08/07/2015", "%m/%d/%Y"), datetime.datetime.strptime("08/07/2015", "%m/%d/%Y"),
    #                           datetime.datetime.strptime("08/07/2015", "%m/%d/%Y"), datetime.datetime.strptime("08/07/2015", "%m/%d/%Y")]):
        print "{}: {}".format(week.strftime("%A, %m/%d/%Y"), playlist)
        parseList(playlist, spots, tracks, week)

    results = scoreVotes(tracks, bonus)

    rank = len(tracks)
    printResults(results, tracks, 7, 1)
