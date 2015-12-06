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
import unicodedata
import json

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "audiobonsai.settings")
from django.conf import settings


'''
getSetList --
   Read and score the curators' voting lists, write to PodListen, create a Google Doc and share it
'''

def getSpotifyConn(username='AudioBonsai', scope='user-read-private playlist-modify-private playlist-read-private playlist-modify-public'):
    '''
    getSpotifyConn -- connect to spotify
    '''
    spotify = spotipy.Spotify()
    token = sputil.prompt_for_user_token(username, scope)
    sp = spotipy.Spotify(auth=token)
    return sp


def parseList(playlist, spots=10, tracks={}, week="MM/DD/YYYY", username='AudioBonsai', scope='user-read-private playlist-modify-private playlist-read-private playlist-modify-public'):
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
    votes_list = []
    rank = 1
    playlist = sp.user_playlist(user=bits.group(1), playlist_id=bits.group(2))
    playlist_name = playlist[u'name']
    #pprint(results)

    for track in playlist[u'tracks'][u'items']:
        artists = []
        uri = track[u'track'][u'uri']
        print uri
        #track_match = re.match('spotify:track:([a-z,A-Z,0-9]*)', uri)
        #votes_list.append(track_match.group(1))
        votes_list.append(unicodedata.normalize('NFKD', uri).encode('ascii','ignore'))
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
    #return [username, '<iframe src="https://embed.spotify.com/?uri=spotify:trackset:Top Ten by {0}:{1}" width="480" height="540" frameborder="0" allowtransparency="true"></iframe>'.format(username, ', '.join(votes_list))]
    return [username, username, playlist_embed(username, 'Top Ten by {0}: {1}'.format(username, week.strftime("%B %d, %Y")), track_list=votes_list)]

def playlist_embed(id, name, track_list=None, playlist_uri=None, display=False, curator_refresh=False):
    display_str = ' '
    if not display:
        display_str = 'style="display:none"'
    if track_list is not None:
        sp = getSpotifyConn()
        print(sp._auth_headers())
        print(sp.current_user()[u'id'] + ': ' + name)
        playlist = sp.user_playlist_create(sp.current_user()[u'id'], name)
        playlist_uri = playlist[u'uri']
        print(playlist_uri)
        print([sp._get_uri("track", tid) for tid in track_list])
        print("users/%s/playlists/%s/tracks" % (sp.current_user()[u'id'], sp._get_id('playlist', playlist_uri)))
        sp.user_playlist_add_tracks(sp.current_user()[u'id'], playlist_uri, track_list)
        if curator_refresh:
            sp.user_playlist_replace_tracks(sp.current_user()[u'id'], settings.CURATOR_REFRESH, track_list)
        #return '<div id="{2}" {3}><iframe src="https://embed.spotify.com/?uri=spotify:trackset:{0}:{1}" {2} width="480" height="540" frameborder="0" allowtransparency="true"></iframe></div>'.format(name, ', '.join(track_list), id, display_str)
    return '<div id="{0}" {1}><iframe src="https://embed.spotify.com/?uri={2}" width="480" height="540" frameborder="0" allowtransparency="true"></iframe></div>'.format(id, display_str, playlist_uri)

def append_sotds(track_list):
    sp = getSpotifyConn()
    sp.user_playlist_add_tracks(sp.current_user()[u'id'], settings.SOTD, track_list)
    sp.user_playlist_add_tracks(sp.current_user()[u'id'], settings.SOTD_YEARLY, track_list)

def gen_buttons(playlist_ids, playlist_names):
    buttons = []
    playlist_dict = dict(zip(playlist_ids, playlist_names))
    for playlist_id in playlist_ids:
        buttons.append('<input value="{0}" type="button" id="{1}_btn" alt="{0}" onclick="ab_switcheroo(\'{1}\', [\'{2}\'])" style="width:120px;"/>'.format(playlist_dict[playlist_id], playlist_id, '\', \''.join(playlist_ids)))
    return ''.join(['<div name="buttons" style="width:480px;align:center;float:center">', ''.join(buttons), '</div>'])

def create_playlist_switcher(playlists):
    playlist_ids = []
    playlist_names = []
    playlist_divs = []
    for playlist in playlists:
        playlist_ids.append(playlist[0])
        playlist_names.append(playlist[1])
        playlist_divs.append(playlist[2])
    button_text = gen_buttons(playlist_ids, playlist_names)
    return ''.join(['<div style="float:right;padding-left:15px;align:center">', ''.join(playlist_divs), button_text, '</div>'])

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
 
def printResults(results, tracks, week, freshcuts, playlists, spots=10, rank=25):
    '''
    printResults -- write out the results as a playlist and document
    '''
    #print "Intro)\n\nAnd now with a little help from our friends the Hit Meters, here are our honorable mentions"
    dir1 = 'left'
    dir2 = 'right'

    hm_print = False
    votes_list = []
    sotd_list = []
    display_list = ['<div class="sotd">Songs of the Day</div><hr width="100%"</div>']
    for score in reversed(sorted(results)):
        new_rank = rank
        for entry in results[score]:
            rank_str = str(rank)
            if rank >= spots+1:
                if not hm_print:
                    #rank_str = "Honorable Mention"
                    display_list.append('<div style="sotd">Honorable Mentions</div><hr width="100%"</div>')
                    hm_print = True
            else:
                sotd_list.append(entry)
            #print u'{0:2} ({1:3} points): {2}\n'.format(rank_str, str(score), tracks[entry]['display_str'])
            #track_match = re.match('spotify:track:([a-z,A-Z,0-9]*)', entry)
            #votes_list.append(track_match.group(1))
            votes_list.append(unicodedata.normalize('NFKD', entry).encode('ascii','ignore'))
            display_list.append(''.join([u'<div width="100%">\n'
                           u'<div style=\'float:{3};padding-{2}:15px;\'>\n',
                           u'<iframe src="https://embed.spotify.com/?uri={4}" width="300" height="380" frameborder="0" allowtransparency="true"></iframe>\n'
                           u'</div>\n',
                           u'<p>\n',
                           u'<div class="rank">#{0}:</div>{1}\n'
                           u'</p>\n',
                           u'<hr width="100%"/></div>\n']).format(rank_str, tracks[entry]['display_str'], dir1, dir2, entry))
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

#    freshcuts_playlist = '<iframe src="https://embed.spotify.com/?uri=' + freshcuts + '" width="480" height="540" frameborder="0" allowtransparency="true"></iframe>'
    freshcuts_playlist = playlist_embed('fresh_cuts', 'Fresh_cuts', playlist_uri=freshcuts)
    combined_playlist = playlist_embed('combined_list', 'Curators Picks: {0}'.format(week.strftime("%B %d, %Y")), track_list=votes_list, display=True, curator_refresh=True) #'<iframe src="https://embed.spotify.com/?uri=spotify:trackset:Combined Scoring List:{0}" width="480" height="540" frameborder="0" allowtransparency="true"></iframe>'.format(', '.join(votes_list))
    playlists.insert(0, ['combined_list', 'Combined', combined_playlist])
    playlists.insert(0, ['fresh_cuts', 'Fresh Cuts', freshcuts_playlist])
    append_sotds(sotd_list)

    print '<div class="preamble">' \
          '{0}' \
          '<p style="padding-right: 50px;">Every week the curators of AudioBonsai.com create a playlist called the ' \
          'Fresh Cuts with sample tracks from 60+ EPs and LPs released on Spotify and Rdio that week. However, if you ' \
          'don\'t feel up to the challenge of such a large amount of new music we compile our individual top ten lists. ' \
          'These are scored and the results below. The Songs of the Day are our top seven in the combined scoring and ' \
          'also get included in our <a href="https://open.spotify.com/user/audiobonsai/playlist/5w8fgbOIgwzNwG9pQ1csd4">' \
          'Songs of the Day</a> playlist on Spotify. Honorable Mentions are songs that also get votes, but don\'t quite ' \
          'make the songs of the day.</p>' \
          '<p style="padding-right: 50px;">The Fresh Cuts, Combined list, Moksha\'s votes and Jesse\'s votes are embedded ' \
          'here. The default list is the combined list, but clicking on the buttons will show you the other lists as ' \
          'well. Heck you can even copy them to your Spotify account and taunt your friends with your impeccable new ' \
          'music playlists! Enjoy!</p>' \
          '</div>'.format(create_playlist_switcher(playlists))
    print('\n'.join(display_list))
    #print "outro)\n\nThanks for listening.  All of the songs we played samples of in this podcast will be embedded in their full glory on this episode's post.  The top seven will be featured as our Songs of the Day for the week.    If you would like to play along, subscribe to the Fresh Cuts: ReFresh list on Spotify and Rdio.  Let us know your favorite before we record Thursday evening via Twitter, Facebook or our website at AudioBonsai.com or leave us a voice mail telling us who you are and what your favorite is at 952-22-AUDIO.  That's 952-222-8346. If you have your pick to us by Thursday night when we record we can work it into the show.  Get it in by Sunday and we can probably duct tape it in awkwardly somewhere.  Monday or later, we can have a nice chat while you listen to what could have been. We hope you found something to love in this episode and we'll see you again next week. "

def genTagList(playlist_uri):
    sp = getSpotifyConn()
    bits = re.match('spotify:user:([a-z,A-Z,0-9]*):playlist:([a-z,A-Z,0-9]*)', playlist_uri)
    playlist = sp.user_playlist(user=bits.group(1), playlist_id=bits.group(2))
    artists = []
    for track in playlist[u'tracks'][u'items']:
        for artist in track[u'track'][u'artists']:
            artists.append(artist[u'name'])
    return ','.join(artists)

if __name__ == "__main__":
    start_path = os.path.realpath(__file__)
    start_array = start_path.split('/')
    sys.path.append('/'.join(start_array[0:len(start_array)-2]))
    
    spots = 10
    bonus = 49
    tracks = {}
    playlists = []
    fresh_cuts_uri = 'spotify:user:audiobonsai:playlist:5tPUfLgzfhJwFhuANwUPpm'
    for playlist, week in zip([settings.JESSE_TOP_TEN, settings.MOKSHA_TOP_TEN_3],#, settings.JESSE_TOP_TEN_2, settings.MOKSHA_TOP_TEN_2],
                              [datetime.datetime.strptime("11/20/2015", "%m/%d/%Y"), datetime.datetime.strptime("11/20/2015", "%m/%d/%Y")]): #,
                               #datetime.datetime.strptime("10/16/2015", "%m/%d/%Y"), datetime.datetime.strptime("10/02/2015", "%m/%d/%Y")]):
    #for playlist, week in zip([settings.JESSE_TOP_TEN, settings.MOKSHA_TOP_TEN, settings.HEIDI_TOP_TEN, settings.MEG_TOP_TEN],
    #                          [datetime.datetime.strptime("08/07/2015", "%m/%d/%Y"), datetime.datetime.strptime("08/07/2015", "%m/%d/%Y"),
    #                           datetime.datetime.strptime("08/07/2015", "%m/%d/%Y"), datetime.datetime.strptime("08/07/2015", "%m/%d/%Y")]):
        print "{}: {}".format(week.strftime("%A, %m/%d/%Y"), playlist)
        playlists.append(parseList(playlist, spots, tracks, week))

    results = scoreVotes(tracks, bonus)

    rank = len(tracks)
    printResults(results, tracks, week, fresh_cuts_uri, playlists, 7, 1)
    print(genTagList(fresh_cuts_uri))
