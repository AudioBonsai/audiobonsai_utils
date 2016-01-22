__author__ = 'Jesse'

import argparse
import collections
import datetime
import django
import os
import random
import re
import spotipy
import spotipy.util as sputil
import traceback
import urllib2

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "audiobonsai.settings")
#from django.conf import settings
#from rootball.models import FreshCuts
django.setup()

parser = argparse.ArgumentParser(description='load a Fresh Cuts playlist')
parser.add_argument('-pubdate', action='store', dest='pubdate', help='The date of the FreshCuts list publication')

stats_dict = {}

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
        for uri, artist in self.artistDict.iteritems():
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

    def pickSingle(self, sp, singlesCutoff):
        for artist in self.albumArtists:
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
                    print('Bad date format: ' + album_dets[u'release_date'])
                if singleReleaseDate > releaseDate:
                    releaseDate = singleReleaseDate
                    self.chosenSingle = albumNames[match_name]
                    return

        if self.chosenSingle == None:
            durations = {}
            for trackNum in xrange(1,6 if self.albumTracks > 6 else self.albumTracks+1):
                if trackNum not in self.trackDict[1].keys():
                    break
                track = self.trackDict[1][trackNum]
                durations[track.duration] = track
            duration = sorted(durations.keys())[len(durations.keys())/2]
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

    def __init__(self, album, albumTrack, artistDict, sp):
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
                artistFull = sp.artist(artist[u'uri'])
                artist_candidate = Artist_Candidate(artistFull, album, self)
                artistDict[artist[u'uri']] = artist_candidate
                self.artistList.append(artist_candidate)

        album.addTrack(self)

def getSpotifyConn(username='AudioBonsai', scope='user-read-private playlist-modify-private playlist-read-private playlist-modify-public'):
    '''
    get_spotify_conn -- connect to spotify
    '''
    token = sputil.prompt_for_user_token(username, scope)
    sp = spotipy.Spotify(auth=token)
    return sp

def buildArtistDict(album, album_tracks, artist_dict, ap):
    # Identify all the artists on the album to look for singles and dictify the tracks
    for album_track in album_tracks:
        Track_Candidate(album, album_track, artist_dict, sp)

def processAlbumDets(album, album_dets, sp, album_count, single_cutoff, artist_dict):
    # Get all the tracks on the album
    album_tracks = album_dets[u'tracks'][u'items']
    album_name = album_dets[u'name']
    artist_names = []
    buildArtistDict(album, album_tracks, artist_dict, sp)
    album.selectArtists()
    album.pickSingle(sp, single_cutoff)

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

def getAlbumsFromNewReleases(sp):
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
    response = urllib2.urlopen('http://everynoise.com/spotify_new_releases.html')
    html = response.read()
    #fromfile = open('C:\\Users\\Jesse\\Downloads\\20160101_SortingHat.html')
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

def genPlaylist(sp, fc_tracks, singles_playlist_uri=None, selected_playlist_uri=None):
    if singles_playlist_uri == None:
        playlist = sp.user_playlist_create(sp.current_user()[u'id'], 'Sorting Hat Singles Selection: ' + args.pubdate)
        singles_playlist_uri = playlist[u'uri']

    if selected_playlist_uri == None:
        playlist = sp.user_playlist_create(sp.current_user()[u'id'], 'Sorting Hat Best Guess Selection: ' + args.pubdate)
        selected_playlist_uri = playlist[u'uri']

    track_list = []
    popularities = sorted([x for x in fc_tracks['singles']['tracks'].keys()], reverse=True)
    for popularity in popularities:
        for track in fc_tracks['singles']['tracks'][popularity]:
            if track is None:
                continue
            track_list.append(track.spotifyUri)

    start = 0
    end = 100
    while start <= len(track_list):
        if end > len(track_list):
            end = len(track_list)
        if start == 0:
            sp.user_playlist_replace_tracks(sp.current_user()[u'id'], singles_playlist_uri, track_list[start:end])
        else:
            sp.user_playlist_add_tracks(sp.current_user()[u'id'], singles_playlist_uri, track_list[start:end])
        start += 100
        end += 100

    track_list = []
    popularities = sorted([x for x in fc_tracks['selected']['tracks'].keys()], reverse=True)
    for popularity in popularities:
        for track in fc_tracks['selected']['tracks'][popularity]:
            if track is None:
                continue
            track_list.append(track.spotifyUri)

    start = 0
    end = 100
    while start <= len(track_list):
        if end > len(track_list):
            end = len(track_list)
        if start == 0:
            sp.user_playlist_replace_tracks(sp.current_user()[u'id'], selected_playlist_uri, track_list[start:end])
        else:
            sp.user_playlist_add_tracks(sp.current_user()[u'id'], selected_playlist_uri, track_list[start:end])
        start += 100
        end += 100


if __name__ == "__main__":
    start_time = datetime.datetime.now()
    args = parser.parse_args()
    print args
    sp = getSpotifyConn()

    fc_date = datetime.datetime.strptime('2016-01-15', '%Y-%m-%d')
    single_cutoff = fc_date - datetime.timedelta(days=120)
    print('FC Date: {0} - Singles Cutoff: {1}'.format(fc_date.strftime('%Y-%m-%d'), single_cutoff.strftime('%Y-%m-%d')))

    album_count = 0
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
    #results = getAlbumsFromNewReleases(sp)
    results = getAlbumsFromSortingHat()

    for album in results:
        try:
            album_dets = sp.album(album.spotifyUri)
        except Exception as e:
            try:
                print('Excpetion on ' + album.__str__())
            except Exception as e2:
                print(e2)
            print(e)
            results.append(album)
            sp = getSpotifyConn()
            continue
        if len(album_dets[u'tracks'][u'items']) >= 3:
            album.setReleaseDate(album_dets[u'release_date'])
            if album.releaseDate in release_date_dict.keys():
                release_date_dict[album.releaseDate] += 1
            else:
                release_date_dict[album.releaseDate] = 1

            if album.releaseDate <= fc_date and album.releaseDate - fc_date > datetime.timedelta(days=-7):
                try:
                    album.name = album_dets[u'name']
                    processAlbumDets(album, album_dets, sp, album_count, single_cutoff, artist_dict)
                except Exception as e:
                    print(u'Excpetion on {0}, {1}'.format(album.name, album.spotifyUri))
                    print(e)
                    traceback.print_exc()
                    results.append(album)
                    sp = getSpotifyConn()
                    continue

                album_count += 1
                if album_count % 500 == 0:
                    #break
                    sp = getSpotifyConn()

    for releaseDate in sorted(release_date_dict):
        print('{0}: {1}'.format(releaseDate, release_date_dict[releaseDate]))

    singlesPlaylistURI = 'spotify:user:audiobonsai:playlist:6z8m6hjBXxClAZt3oYONCa'
    selectedPlaylistURI = 'spotify:user:audiobonsai:playlist:626JCrZSTl0AQbO6vqr2MB'

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
    genPlaylist(sp, fc_tracks, singlesPlaylistURI, selectedPlaylistURI)

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




