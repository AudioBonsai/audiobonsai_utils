import argparse
import collections
import datetime
import django
import os
import random
import re
import spotipy
import spotipy.util as sputil
from spotipy import oauth2
import traceback
import urllib

#from ipyparallel import Client

__author__ = 'Jesse'

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "audiobonsai.settings")
django.setup()
from django.conf import settings

parser = argparse.ArgumentParser(description='load a Fresh Cuts playlist')
parser.add_argument('-pubdate', action='store', dest='pubdate', help='The date of the FreshCuts list publication')

stats_dict = {}

def getSpotifyConn(username=settings.SP_USERNAME, scope='user-read-private playlist-modify-private playlist-read-private playlist-modify-public'):
    '''
    get_spotify_conn -- connect to spotify
    '''
    global sp
    token = sputil.prompt_for_user_token(username, scope)
    sp = spotipy.Spotify(auth=token)
    print('Spotify user id: {0}'.format(sp.current_user()[u'id']))
    return sp

sp = getSpotifyConn(username=settings.SP_USERNAME)

#rc = Client()
#lview = rc.load_balanced_view()

class Album_Candidate:
    spotifyUri = ''
    sortingHatRank = ''
    releaseDate = datetime.datetime.strptime('1970-1-1', '%Y-%m-%d')
    artistDict = {}
    trackDict = {}
    mostRecentSingle = None
    artistPop = 0
    albumTracks = 0
    albumArtists = []
    chosenSingle = None
    chosenGuess = None

    def __init__(self, spotifyUri, sortingHatRank=None):
        self.spotifyUri = spotifyUri.__str__()
        self.sortingHatRank = sortingHatRank
        self.artistDict = {}
        self.trackDict = {}
        self.albumArtists = []
        self.releaseDate = datetime.datetime.strptime('1970-1-1', '%Y-%m-%d')
        self.mostRecentSingle = None
        self.chosenSingle = None
        self.chosenGuess = None
        self.artistPop = 0
        self.albumTracks = 0


    def setReleaseDate(self, dateText):
        try:
            self.releaseDate = datetime.datetime.strptime(dateText, '%Y-%m-%d')
        except:
            print('Bad date format: ' + dateText)

    def addTrack(self, trackCandidate):
        if trackCandidate.discNumber not in self.trackDict.keys():
            self.trackDict[trackCandidate.discNumber] = {}
        self.trackDict[trackCandidate.discNumber][trackCandidate.trackNumber] = trackCandidate
        self.albumTracks += 1

        for artist in trackCandidate.artistList:
            if artist.spotifyUri not in self.artistDict.keys():
                self.artistDict[artist.spotifyUri] = artist

    def selectArtists(self):
        for uri, artist in self.artistDict.items():
            if self.albumTracks == artist.getNumAlbumTracks(self):
                self.albumArtists.append(artist)
                if artist.popularity > self.artistPop:
                    self.artistPop = artist.popularity

    def getSongDict(self):
        songDict = {}
        for disc in self.trackDict.keys():
            for trackNum in self.trackDict[disc].keys():
                songDict[self.trackDict[disc][trackNum].name] = self.trackDict[disc][trackNum]
        return songDict

    def pickSingle(self, singlesCutoff):
        global sp
        for artist in self.albumArtists:
            try:
                artist_tracks = sp.artist_albums(artist.spotifyUri, album_type='single', country='US')
            except:
                print('Error occurred getting artist tracks for {0}'.format(artist.name))
                #sp = getSpotifyConn(username=settings.SP_USERNAME)
                sp = refreshToken()
                artist_tracks = sp.artist_albums(artist.spotifyUri, album_type='single', country='US')
            uris = [x[u'uri'] for x in artist_tracks[u'items']]
            if len(uris) == 0:
                break
            singles_dets = sp.albums(uris)
            releaseDate = singlesCutoff

            albumNames = self.getSongDict()
            match_name = None

            for artist_single in singles_dets[u'albums']:
                singlesNames = [x[u'name'] for x in artist_single[u'tracks'][u'items']]
                if artist_single[u'uri'] == self.spotifyUri:
                    continue
                if artist_single[u'name'] in albumNames.keys():
                    match_name = artist_single[u'name']
                elif singlesNames[0] in albumNames.keys():
                    match_name = singlesNames[0]
                else:
                    continue
                singleReleaseDate = datetime.datetime.strptime('1970-1-1', '%Y-%m-%d')
                try:
                    singleReleaseDate = datetime.datetime.strptime(artist_single[u'release_date'], '%Y-%m-%d')
                except:
                    print('Bad date format: ' + artist_single[u'release_date'])
                if singleReleaseDate > releaseDate:
                    releaseDate = singleReleaseDate
                    self.chosenSingle = albumNames[match_name]
                    return

        if self.chosenSingle == None:
            durations = {}
            for trackNum in range(1,6 if self.albumTracks > 6 else self.albumTracks+1):
                if trackNum not in self.trackDict[1].keys():
                    break
                track = self.trackDict[1][trackNum]
                durations[track.duration] = track
            duration = sorted(durations.keys())[int(len(durations.keys())/2)]
            self.chosenGuess = durations[duration]


class Artist_Candidate:
    spotifyUri = ''
    name = ''
    popularity = ''
    albumDict = {}

    def __init__(self, artistDets, album, track):
        self.name = artistDets[u'name']
        self.spotifyUri = artistDets[u'uri']
        if artistDets[u'popularity'] != '-':
            self.popularity = int(artistDets[u'popularity'])
        else:
            self.popularity = 0
        self.albumDict = {}
        self.albumDict[album.spotifyUri] = {}
        self.albumDict[album.spotifyUri]['album'] = album
        self.albumDict[album.spotifyUri]['tracks'] = [track]

    def addTrack(self, album, track):
        if album.spotifyUri not in self.albumDict.keys():
            self.albumDict[album.spotifyUri] = {}
            self.albumDict[album.spotifyUri]['album'] = album
            self.albumDict[album.spotifyUri]['tracks'] = [track]
        else:
            self.albumDict[album.spotifyUri]['tracks'].append(track)

    def getNumAlbumTracks(self, album):
        return len(self.albumDict[album.spotifyUri]['tracks'])

class Track_Candidate:
    duration = ''
    discNumber = ''
    trackNumber = ''
    name = ''
    spotifyUri = ''
    artistList = []

    def __init__(self, album, albumTrack, artistDict):
        global sp
        self.duration = int(albumTrack[u'duration_ms'])
        self.name = albumTrack[u'name']
        self.spotifyUri = albumTrack[u'uri']
        self.discNumber = int(albumTrack[u'disc_number'])
        self.trackNumber = int(albumTrack[u'track_number'])
        self.artistList = []

        for artist in albumTrack[u'artists']:
            if artist[u'uri'] in artistDict.keys():
                artistDict[artist[u'uri']].addTrack(album, self)
            else:
                try:
                    artistFull = sp.artist(artist[u'uri'])
                except:
                    print('Problem resolving artist {0}'.format(artist[u'uri']))
                    #sp = getSpotifyConn(username=settings.SP_USERNAME)
                    sp = refreshToken()
                    artistFull = sp.artist(artist[u'uri'])
                artist_candidate = Artist_Candidate(artistFull, album, self)
                artistDict[artist[u'uri']] = artist_candidate
                self.artistList.append(artist_candidate)

        album.addTrack(self)


def refreshToken(scope='user-read-private playlist-modify-private playlist-read-private playlist-modify-public'):
    global sp
    sp_oauth = oauth2.SpotifyOAuth(os.environ['SPOTIPY_CLIENT_ID'],
                                   os.environ['SPOTIPY_CLIENT_SECRET'],
                                   'http://localhost:8888/callback',
                                   scope=scope, cache_path='c:/Users/Jesse/PyCharmProjects/audiobonsai.com/util/.cache-audiobonsai')
    token_info = sp_oauth.get_cached_token()
    print(token_info)
    token_info = sp_oauth.refresh_access_token(token_info['refresh_token'])
    sp = spotipy.Spotify(auth=token_info['access_token'])
    return sp


def buildArtistDict(album, album_tracks, artist_dict):
    # Identify all the artists on the album to look for singles and dictify the tracks
    for album_track in album_tracks:
        Track_Candidate(album, album_track, artist_dict)

def processAlbumDets(album, album_dets, album_count, single_cutoff, artist_dict):
    # Get all the tracks on the album
    album_tracks = album_dets[u'tracks'][u'items']
    album_name = album_dets[u'name']
    artist_names = []
    buildArtistDict(album, album_tracks, artist_dict)
    album.selectArtists()
    album.pickSingle(single_cutoff)

    if album.chosenSingle != None:
        print(u'{6}: {0}: {1} from {2} by {3}({4}), {5}'.format(album_count, album.chosenSingle.name, album.name,
                                                           ', '.join([artist.name for artist in album.albumArtists]),
                                                           album.artistPop, 'Single', datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
    elif album.chosenGuess != None:
        print(u'{6}: {0}: {1} from {2} by {3}({4}), {5}'.format(album_count, album.chosenGuess.name, album.name,
                                                           ', '.join([artist.name for artist in album.albumArtists]),
                                                           album.artistPop, 'Guess', datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
    else:
        print(u'{2}: No track chosen for {0}, {1}'.format(album.name, album.spotifyUri, datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')))

def getAlbumsFromNewReleases():
    global sp
    uris = []
    rescount = 500
    limit = 50
    offset = 0
    # Get all new releases
    while(rescount > offset):
        results = sp.new_releases(country='US', limit=limit, offset=offset)
        if results == None:
            break
        rescount = results[u'albums'][u'total']
        for x in results[u'albums'][u'items']:
            uris.append(Album_Candidate(x[u'uri']))
        offset = len(uris)

    return uris

def getAlbumsFromSortingHat():
    response = urllib.request.urlopen('http://everynoise.com/spotify_new_releases.html')
    html = response.read().decode("utf-8")
    #print(type(html))
    #fromfile = open('/Users/jerdmann/Downloads/20160520_SortingHat.html')
    #html = fromfile.read()
    track_list = []
    artist_ranks = {}
    track_items = html.split('</div><div class=')
    print(len(track_items))
    match_string = re.compile(' title="artist rank:.*')
    group_string = re.compile(' title="artist rank: ([0-9,-]+)"><a onclick=".*" href="(spotify:album:.*)"><span class=.*>.*</span> <span class=.*>.*</span></a> <span class="play trackcount" albumid=spotify:album:.* nolink=true onclick=".*">([0-9]+)</span>')

    for track in track_items:
        for match in match_string.findall(track):
            bits = group_string.match(match)
            if bits == None:
                continue
            if int(bits.group(3)) > 2:
                track_list.append(Album_Candidate(bits.group(2), bits.group(1)))
                if bits.group(1) == '-':
                    if '-' in artist_ranks.keys():
                        artist_ranks['-'] += 1
                    else:
                        artist_ranks['-'] = 1
                elif int(bits.group(1))/1000 in artist_ranks.keys():
                    artist_ranks[int(bits.group(1))/1000] += 1
                else:
                    artist_ranks[int(bits.group(1))/1000] = 1

    print(len(track_list))
    #for rank in sorted(artist_ranks.keys()):
    #    print('{0} : {1}'.format(rank*1000, artist_ranks[rank]))
    return track_list

def updatePlaylist(uri, track_list):
    global sp
    start = 0
    end = 100
    while start <= len(track_list):
        if end > len(track_list):
            end = len(track_list)
        if start == 0:
            try:
                sp.user_playlist_replace_tracks(sp.current_user()[u'id'], uri, track_list[start:end])
            except:
                #sp = getSpotifyConn(username=settings.SP_USERNAME)
                sp = refreshToken()
                sp.user_playlist_replace_tracks(sp.current_user()[u'id'], uri, track_list[start:end])
            #sp.user_playlist_replace_tracks(sp.current_user()[u'id'], uri, track_list[start:end])
        else:
            try:
                sp.user_playlist_add_tracks(sp.current_user()[u'id'], uri, track_list[start:end])
            except:
                #sp = getSpotifyConn(username=settings.SP_USERNAME)
                sp = refreshToken()
                try:
                    sp.user_playlist_add_tracks(sp.current_user()[u'id'], uri, track_list[start:end])
                except:
                    #sp = getSpotifyConn(username=settings.SP_USERNAME)
                    sp = refreshToken()
                    sp.user_playlist_add_tracks(sp.current_user()[u'id'], uri, track_list[start:end])
            #sp.user_playlist_add_tracks(sp.current_user()[u'id'], uri, track_list[start:end])
        start += 100
        end += 100

def genPlaylist(fc_tracks, singles_playlist_uri=None, selected_playlist_uri=None, jje_playlist_uris=None):
    global sp
    if singles_playlist_uri == None:
        playlist = sp.user_playlist_create(sp.current_user()[u'id'], 'Sorting Hat Singles Selection: ' + args.pubdate)
        singles_playlist_uri = playlist[u'uri']

    if selected_playlist_uri == None:
        playlist = sp.user_playlist_create(sp.current_user()[u'id'], 'Sorting Hat Best Guess Selection: ' + args.pubdate)
        selected_playlist_uri = playlist[u'uri']

    for [type, playlist_uri] in list(zip(['singles', 'selected'], [singles_playlist_uri, selected_playlist_uri])):
        track_list = []
        popularities = sorted([x for x in fc_tracks[type]['tracks'].keys()], reverse=True)
        for popularity in popularities:
            for track in fc_tracks[type]['tracks'][popularity]:
                if track is None:
                    continue
                track_list.append(track.spotifyUri)
                if popularity >= 51:
                    jje_playlist_uris[type]['top50']['tracks'].append(track.spotifyUri)
                elif popularity >= 26:
                    jje_playlist_uris[type]['verge']['tracks'].append(track.spotifyUri)
                elif popularity >= 11:
                    jje_playlist_uris[type]['unheralded']['tracks'].append(track.spotifyUri)
                elif popularity >= 1:
                    jje_playlist_uris[type]['underground']['tracks'].append(track.spotifyUri)
                elif popularity == 0:
                    jje_playlist_uris[type]['unknown']['tracks'].append(track.spotifyUri)

        updatePlaylist(playlist_uri, track_list)
        updatePlaylist(jje_playlist_uris[type]['top50']['uri'], jje_playlist_uris[type]['top50']['tracks'])
        updatePlaylist(jje_playlist_uris[type]['verge']['uri'], jje_playlist_uris[type]['verge']['tracks'])
        updatePlaylist(jje_playlist_uris[type]['unheralded']['uri'], jje_playlist_uris[type]['unheralded']['tracks'])
        updatePlaylist(jje_playlist_uris[type]['underground']['uri'], jje_playlist_uris[type]['underground']['tracks'])
        updatePlaylist(jje_playlist_uris[type]['unknown']['uri'], jje_playlist_uris[type]['unknown']['tracks'])

    '''
    track_list = []
    popularities = sorted([x for x in fc_tracks['selected']['tracks'].keys()], reverse=True)
    for popularity in popularities:
        for track in fc_tracks['selected']['tracks'][popularity]:
            if track is None:
                continue
            track_list.append(track.spotifyUri)

    updatePlaylist(selected_playlist_uri, track_list)
    '''


#@lview.parallel()
def processList(albums):
    #print('Hello')
    #sp = getSpotifyConn(username=settings.SP_USERNAME)
    #sp = refreshToken()
    album_count = 0
    for album in albums:
        try:
            success = processAlbum(album, album_count)
        except Exception as e:
            if re.match('.*non existing id.*', e.__repr__()):
                print('{0} does not exist, skipping'.format(album))
                continue
            else:
                #print('WTF is this?  ' + e)
                #sp = getSpotifyConn(username=settings.SP_USERNAME)
                sp = refreshToken()
                success = False
                #continue
        if success:
           album_count += 1
        else:
            albums.append(album)
            #sp = getSpotifyConn(username=settings.SP_USERNAME)
            #sp = refreshToken()
        #if album_count % 100 == 0:
            #sp = getSpotifyConn(username=settings.SP_USERNAME)
            #sp = refreshToken()


def processAlbum(album, album_count):
    global sp
    #sp = getSpotifyConn(username=settings.SP_USERNAME)
    try:
        album_dets = sp.album(album.spotifyUri)
    except Exception as e:
        try:
            print('Exception on ' + album.spotifyUri)
            album_dets = sp.album(album.spotifyUri)
        except Exception as e2:
            print(e2)
            raise e2
        print(e)
        return False
    if len(album_dets[u'tracks'][u'items']) >= 3:
        album.setReleaseDate(album_dets[u'release_date'])
        if album.releaseDate in release_date_dict.keys():
            release_date_dict[album.releaseDate] += 1
        else:
            release_date_dict[album.releaseDate] = 1

        if album.releaseDate <= fc_date and album.releaseDate - fc_date > datetime.timedelta(days=-7):
            try:
                album.name = album_dets[u'name']
                processAlbumDets(album, album_dets, album_count, single_cutoff, artist_dict)
                #processAlbumDets(album, album_dets, 0, single_cutoff, artist_dict)
            except Exception as e:
                print(u'Excpetion on {0}, {1}'.format(album.name, album.spotifyUri))
                print(e)
                traceback.print_exc()
                return False
    return True

if __name__ == "__main__":
    start_time = datetime.datetime.now()
    args = parser.parse_args()
    print(args)
    sp = refreshToken()
    #sp = getSpotifyConn(username=settings.SP_USERNAME)

    fc_date = datetime.datetime.strptime('2017-09-08', '%Y-%m-%d')
    single_cutoff = fc_date - datetime.timedelta(days=120)
    print('FC Date: {0} - Singles Cutoff: {1}'.format(fc_date.strftime('%Y-%m-%d'), single_cutoff.strftime('%Y-%m-%d')))

    fc_tracks = {}
    fc_tracks['singles'] = {}
    fc_tracks['singles']['tracks'] = {}
    fc_tracks['singles']['stats'] = {}
    fc_tracks['selected'] = {}
    fc_tracks['selected']['tracks'] = {}
    fc_tracks['selected']['stats'] = {}
    release_date_dict = {}
    artist_dict = {}
    # Get all new releases
    #results = get_albums_from_new_releases(sp)
    results = getAlbumsFromSortingHat()

    processList(results)
    print('List Processed')
    #results_range = []
    #for i in range(0, len(results), int(len(results)/len(rc.ids))):
    #    results_range.append(results[i:i+int(len(results)/len(rc.ids))])
    #    print('{0:d}:{1:d}'.format(i, i+int(len(results)/len(rc.ids))))

    #lview.map(processList, results)

    for releaseDate in sorted(release_date_dict):
        print('{0}: {1}'.format(releaseDate, release_date_dict[releaseDate]))

    singlesPlaylistURI = 'spotify:user:audiobonsai:playlist:6z8m6hjBXxClAZt3oYONCa'
    selectedPlaylistURI = 'spotify:user:audiobonsai:playlist:626JCrZSTl0AQbO6vqr2MB'

    jje_playlist_uris = {
        'singles': {
            'top50': {
                'uri': 'spotify:user:audiobonsai:playlist:78A4Pum3nlLnU5mb6zyZuU',
                'tracks': []
            },
            'verge': {
                'uri': 'spotify:user:audiobonsai:playlist:0Nm2KEg2IbNzUEjQmSrK8r',
                'tracks': []
            },
            'unheralded': {
                'uri': 'spotify:user:audiobonsai:playlist:7ASt2ojJPVew8WlU4QNGbu',
                'tracks': []
            },
            'underground': {
                'uri': 'spotify:user:audiobonsai:playlist:08LxlbYEBw5UWNiB4ofNWq',
                'tracks': []
            },
            'unknown': {
                'uri': 'spotify:user:audiobonsai:playlist:6jyIbFQdwm6Uyh5BsGia1m',
                'tracks': []
            },
        },
        'selected': {
            'top50': {
                'uri': 'spotify:user:audiobonsai:playlist:5Gd2uZYUAf7XSusTHgtlSK',
                'tracks': []
            },
            'verge': {
                'uri': 'spotify:user:audiobonsai:playlist:7C6iGQ24yabUiKqfqBmTRJ',
                'tracks': []
            },
            'unheralded': {
                'uri': 'spotify:user:audiobonsai:playlist:0EYAZXqRgSRw1hP4YWPP3T',
                'tracks': []
            },
            'underground': {
                'uri': 'spotify:user:audiobonsai:playlist:2gemnklb54ZvHy7zWZIm2e',
                'tracks': []
            },
            'unknown': {
                'uri': 'spotify:user:audiobonsai:playlist:7fGLJYj11ecJFTX37pYjt8',
                'tracks': []
            },
        }
    }

    removed_count = 0
    remix_count = 0
    remaster_count = 0
    reissue_count = 0
    compilation_count = 0
    remix_regex = re.compile('.*remix.*', re.IGNORECASE)
    remaster_regex = re.compile('.*remaster.*', re.IGNORECASE)
    reissue_regex = re.compile('.*reissue.*', re.IGNORECASE)
    for album in results:
        if album.chosenSingle != None:
            if album.artistPop not in fc_tracks['singles']['tracks'].keys():
                fc_tracks['singles']['tracks'][album.artistPop] = []
            fc_tracks['singles']['tracks'][album.artistPop].append(album.chosenSingle)
        elif album.chosenGuess != None:
            skip = False
            for artist in album.artistDict.keys():
                if len(album.artistDict[artist].albumDict.keys()) > 1:
                    skip = True
                    #albumNames = [albumDict['album'].name for uri, albumDict in album.artistDict[artist].albumDict.iteritems()]
                    #print(u'{0} has {1} albums: {2}'.format(album.artistDict[artist].name, len(album.artistDict[artist].albumDict.keys()), ', '.join(albumNames)))
            if skip:
                removed_count += 1
                continue
            elif len(album.artistDict.keys()) == 0:
                compilation_count += 1
                continue
            elif remix_regex.match(album.name) or remix_regex.match(album.chosenGuess.name):
                remix_count += 1
                continue
            elif remaster_regex.match(album.name) or remaster_regex.match(album.chosenGuess.name):
                remaster_count += 1
                continue
            elif reissue_regex.match(album.name) or reissue_regex.match(album.chosenGuess.name):
                reissue_count += 1
                continue


            if album.artistPop not in fc_tracks['selected']['tracks'].keys():
                fc_tracks['selected']['tracks'][album.artistPop] = []
            fc_tracks['selected']['tracks'][album.artistPop].append(album.chosenGuess)

    print('Removed {0} albums for duplicate artist appearences in best guess list'.format(removed_count))
    print('Removed {0} albums for matching \'Remix\' in best guess list'.format(remix_count))
    print('Removed {0} albums for matching \'Remaster\' in best guess list'.format(remaster_count))
    print('Removed {0} albums for matching \'Reissue\' in best guess list'.format(reissue_count))
    print('Removed {0} compilation albums from best guess list'.format(compilation_count))
    genPlaylist(fc_tracks, singlesPlaylistURI, selectedPlaylistURI, jje_playlist_uris)

    pops = {}
    for type in sorted(fc_tracks.keys()):
        for pop in fc_tracks[type]['tracks'].keys():
            if pop not in pops.keys():
                pops[pop] = {}
                pops[pop]['selected'] = 0
                pops[pop]['singles'] = 0
            pops[pop][type] =  len(fc_tracks[type]['tracks'][pop])
        #pops = sorted([x for x in fc_tracks[type]['tracks'].keys()], reverse=True)
        #for popularity in pops:
        #    print('{0}: Artist Popularity({1}): {2}'.format(type, popularity, len(fc_tracks[type]['tracks'][popularity])))

    print(','.join(['Popularity','Selected','Singles']))
    for pop in sorted(pops.keys(), reverse=True):
        print(','.join([str(pop), str(pops[pop]['selected']), str(pops[pop]['singles'])]))

    end_time = datetime.datetime.now()
    total_time = end_time - start_time
    hours, remainder = divmod(total_time.seconds.__int__(), 3600)
    minutes, seconds = divmod(remainder, 60)
    print('Execution time: ' + '%s:%s:%s' % (hours, minutes, seconds))




