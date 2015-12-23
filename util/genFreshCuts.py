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
                return
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

        if self.chosenSingle == None:
            durations = {}
            for trackNum in xrange(1,6):
                track = self.trackDict[1][trackNum]
                durations[track.duration] = track
            duration = sorted(durations.keys())[2]
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
            self.popularity = artistDets[u'popularity']
        self.albumDict[album.spotifyUri] = {}
        self.albumDict[album.spotifyUri]['album'] = album
        self.albumDict[album.spotifyUri]['tracks'] = [track]

    def addTrack(self, album, track):
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

        for artist in albumTrack[u'artists']:
            if artist[u'uri'] in artistDict.keys():
                artistDict[artist[u'uri']].addTrack(album, self)
            else:
                artistFull = sp.artist(artist[u'uri'])
                artist_candidate =  Artist_Candidate(artistFull, album, self)
                artistDict[artist[u'uri']] = artist_candidate
                self.artistList.append(artist_candidate)

        album.addTrack(self)

def getSpotifyConn(username='AudioBonsai', scope='user-read-private playlist-modify-private playlist-read-private playlist-modify-public'):
    '''
    getSpotifyConn -- connect to spotify
    '''
    token = sputil.prompt_for_user_token(username, scope)
    sp = spotipy.Spotify(auth=token)
    return sp

def buildArtistDict(album, album_tracks, artist_dict, ap):
    #print(u'{0}: buildArtistDict({1})'.format(datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'), album.name))
    #artist_dict = {}
    #track_dict = {}
    #return_dict = {}
    #duration_list = []

    # Identify all the artists on the album to look for singles and dictify the tracks
    for album_track in album_tracks:
        Track_Candidate(album, album_track, artist_dict, sp)
        #duration = int(album_track[u'duration_ms'])
        #disc_number = int(album_track[u'disc_number'])
        #track_number = int(album_track[u'track_number'])

        #return_dict[album_track[u'name']] = {}
        #return_dict[album_track[u'name']]['uri'] = album_track[u'uri']
        #return_dict[album_track[u'name']]['disc_number'] = disc_number
        #return_dict[album_track[u'name']]['track_number'] = track_number
        #if disc_number == 1 and track_number <= 4:
        #    if duration not in track_dict.keys():
        #        track_dict[duration] = {}
        #    track_dict[duration][album_track[u'name']] = album_track[u'uri']

        #for artist in album_track[u'artists']:
            #artist_dict[artist[u'name']] = artist[u'uri']
        #    if artist[u'uri'] in artist_dict.keys():
        #        artist_dict[artist[u'uri']]['tracks'] += 1
        #    else:
        #        artist_full = sp.artist(artist[u'uri'])
        #        artist_dict[artist[u'uri']] = {}
        #        artist_dict[artist[u'uri']]['tracks'] = 1
        #        artist_dict[artist[u'uri']]['name'] = artist[u'name']
        #        artist_dict[artist[u'uri']]['popularity'] = '-'
        #        if artist_full[u'popularity'] != '-':
        #            artist_dict[artist[u'uri']]['popularity'] = int(artist_full[u'popularity'])
    #durations = sorted(track_dict.keys())
    #if len(durations) == 0:
    #    return [None, None, None, None, None, None]
    #duration = durations[len(durations)/2]
    #song_names = track_dict[duration].keys()
    #song_name = random.sample(song_names, 1)
    #selected_track = track_dict[duration][song_name[0]]
    #return [selected_track, return_dict, artist_dict,
    #        return_dict[song_name[0]]['disc_number'],
    #        return_dict[song_name[0]]['track_number'], song_name[0]]

def buildSinglesList(track_dict, artist_dict, max_tracks, sp, album_uri, single_cutoff=None):
    selected_single = None
    selected_single_disc_number = None
    selected_single_track_number = None
    selected_single_track_name = None
    top_pop = -1
    if single_cutoff == None:
        release_date = datetime.datetime.strptime('2015-1-1', '%Y-%m-%d')
    else:
        release_date = single_cutoff

    # See if any of the artists singles are on the album
    for artist_uri in artist_dict.keys():
        if artist_dict[artist_uri]['tracks'] < max_tracks:
            continue

        artist_tracks = sp.artist_albums(artist_uri, album_type='single', country='US')
        uris = [x[u'uri'] for x in artist_tracks[u'items']]
        if len(uris) == 0:
            return [selected_single, selected_single_disc_number, selected_single_track_number, selected_single_track_name]
        singles_dets = sp.albums(uris)
        for artist_single in singles_dets[u'albums']:
            if artist_single[u'uri'] == album_uri:
                continue
            song_names = [x[u'name'] for x in artist_single[u'tracks'][u'items']]
            match_name = ''
            if artist_single[u'name'] in track_dict.keys():
                match_name = artist_single[u'name']
            elif song_names[0] in track_dict.keys():
                match_name = song_names[0]
            else:
                continue
            single_release_date = datetime.datetime.strptime('1970-1-1', '%Y-%m-%d')
            try:
                single_release_date = datetime.datetime.strptime(artist_single[u'release_date'], '%Y-%m-%d')
            except:
                print('Bad date format: ' + album_dets[u'release_date'])
            if single_release_date > release_date:
                selected_single = track_dict[match_name]['uri']
                selected_single_disc_number = track_dict[match_name]['disc_number']
                selected_single_track_number = track_dict[match_name]['track_number']
                selected_single_track_name = match_name
                release_date = single_release_date
    return [selected_single, selected_single_disc_number, selected_single_track_number, selected_single_track_name]

def processAlbumDets(album, album_dets, sp, album_count, single_cutoff, artist_dict):
    #print(u'{0}: processAlbumDets({1})'.format(datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'), album.name))
    #print(album_dets)
    # Get all the tracks on the album
    album_tracks = album_dets[u'tracks'][u'items']
    album_name = album_dets[u'name']
    artist_names = []
    #[selected_track, track_dict, artist_dict, disc_number, track_number, track_name] = buildArtistDict(album, album_tracks, artist_dict, sp)
    buildArtistDict(album, album_tracks, artist_dict, sp)
    #if selected_track == None:
        #return [False, None, None, None, None, None]
    #max_tracks = -1
    #max_pop = -1
    #for artist in artist_dict.keys():
    #    if artist_dict[artist]['tracks'] > max_tracks:
    #        max_tracks = artist_dict[artist]['tracks']
    #for artist in artist_dict.keys():
    #    if artist_dict[artist]['tracks'] < max_tracks:
    #        continue
    #    if artist_dict[artist]['popularity'] > max_pop:
    #        max_pop = artist_dict[artist]['popularity']
    #for artist in artist_dict.keys():
    #    if artist_dict[artist]['tracks'] == max_tracks:
    #        artist_names.append(artist_dict[artist]['name'])

    album.selectArtists()

    #[selected_single, single_disc_number, single_track_number, single_name] = buildSinglesList(track_dict, artist_dict, max_tracks, sp, album_dets[u'uri'], single_cutoff)
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
    # Keep the most recent single on the album, or all tracks if no single found
    #if selected_single is not None:
    #    print(u'{6}: {0} from {1} by {2}({5}) on disc {3} as track {4}, most recent single'.format(single_name, album_name,
    #                                                                                    u', '.join(artist_names),
    #                                                                                    single_disc_number,
    #                                                                                    single_track_number, max_pop, album_count))
    #    return [True, selected_single, disc_number, track_number, max_pop, single_name]
    #else:
    #    print(u'{6}: {0} from {1} by {2}({5}) on disc {3} as track {4}'.format(track_name, album_name, u', '.join(artist_names),
    #                                                                disc_number, track_number, max_pop, album_count))
    #    return [False, selected_track, disc_number, track_number, max_pop, track_name]

def getAlbumsFromNewReleases(sp):
    #print(u'{0}: getAlbumsFromNewReleases'.format(datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
    uris = []
    rescount = 500
    limit = 50
    offset = 0
    # Get all new releases
    while(rescount > offset):
        #print('{0}: {1} processed'.format(datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'), offset))
        results = sp.new_releases(country='US', limit=limit, offset=offset)
        if results == None:
            break
        rescount = results[u'albums'][u'total']
        #uris += [x[u'uri'] for x in results[u'albums'][u'items']]
        for x in results[u'albums'][u'items']:
            uris.append(Album_Candidate(x[u'uri']))
        offset = len(uris)

    return uris

def getAlbumsFromSortingHat():
    print('{0}: getAlbumsFromSortingHat'.format(datetime.datetime.strptime(datetime.datetime.now(), '%Y-%m-%d')))
    response = urllib2.urlopen('http://everynoise.com/spotify_new_releases.html')
    html = response.read()
    track_dict = {}
    artist_ranks = {}
    track_items = html.split('</div><div class=')
    print(len(track_items))
    match_string = re.compile(' title="artist rank:.*')
    group_string = re.compile(' title="artist rank: ([0-9,-]+)"><a onclick=".*" href="(spotify:album:.*)"><span class=.*>.*</span> <span class=.*><i>.*</i></span></a> <span class="play trackcount" albumid=spotify:album:.* nolink=true onclick=".*">([0-9]+)</span>')

    for track in track_items:
        for match in match_string.findall(track):
            bits = group_string.match(match)
            if bits == None:
                continue
            if int(bits.group(3)) > 2:
                album_candidate = Album_Candidate(bits.group(2), bits.group(1))
                #track_dict[bits.group(2)] = bits.group(1)
                track_dict[bits.group(2)] = album_candidate
                if bits.group(1) == '-':
                    if '-' in artist_ranks.keys():
                        artist_ranks['-'] += 1
                    else:
                        artist_ranks['-'] = 1
                elif int(bits.group(1))/1000 in artist_ranks.keys():
                    artist_ranks[int(bits.group(1))/1000] += 1
                else:
                    artist_ranks[int(bits.group(1))/1000] = 1

    print(len(track_dict.keys()))
    for rank in sorted(artist_ranks.keys()):
        print('{0} : {1}'.format(rank*1000, artist_ranks[rank]))
    return track_dict.keys()

def genPlaylist(sp, fc_tracks, singles_playlist_uri=None, selected_playlist_uri=None):
    #print(u'{0}: genPlaylist'.format(datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
    #singles_in = open('c:\\Users\\Jesse\\singles.txt', mode='r')
    #stats_dict['singles'] = {}
    #stats_dict['selected'] = {}
    #for single in singles_in:
    #    single = single.strip()
    #    if len(single) == 0:
    #        continue
    #    vals = single.split(',')
    #    track_uri = vals[0]
    #    artist_pop = vals[1]
    #    disc_track_pos = vals[2]
    #    if artist_pop not in fc_tracks['singles']['tracks'].keys():
    #        fc_tracks['singles']['tracks'][artist_pop] = []
    #    if track_uri in fc_tracks['singles']['tracks'][artist_pop]:
    #        continue
    #    fc_tracks['singles']['tracks'][artist_pop].append(track_uri)
    #    if disc_track_pos in fc_tracks['singles']['stats'].keys():
    #        fc_tracks['singles']['stats'][disc_track_pos] += 1
    #    else:
    #        fc_tracks['singles']['stats'][disc_track_pos] = 1
    #    if artist_pop not in stats_dict['singles'].keys():
    #        stats_dict['singles'][artist_pop] = 1
    #    else:
    #        stats_dict['singles'][artist_pop] += 1
    #singles_in.close()
    #best_guess_in = open('c:\\Users\\Jesse\\best_guess.txt', mode='r')
    #for best_guess in best_guess_in:
    #    best_guess = best_guess.strip()
    #    if len(best_guess) == 0:
    #        continue
    #    vals = best_guess.split(',')
    #    track_uri = vals[0]
    #    artist_pop = vals[1]
    #    disc_track_pos = vals[2]
    #    if artist_pop not in fc_tracks['selected']['tracks'].keys():
    #        fc_tracks['selected']['tracks'][artist_pop] = []
    #    if track_uri in fc_tracks['selected']['tracks'][artist_pop]:
    #        continue
    #    fc_tracks['selected']['tracks'][artist_pop].append(track_uri)
    #    if disc_track_pos in fc_tracks['selected']['stats'].keys():
    #        fc_tracks['selected']['stats'][disc_track_pos] += 1
    #    else:
    #        fc_tracks['selected']['stats'][disc_track_pos] = 1
    #    if artist_pop not in stats_dict['selected'].keys():
    #        stats_dict['selected'][artist_pop] = 1
    #    else:
    #        stats_dict['selected'][artist_pop] += 1
    #best_guess_in.close()

    if singles_playlist_uri == None:
        playlist = sp.user_playlist_create(sp.current_user()[u'id'], 'Sorting Hat Singles Selection: ' + args.pubdate)
        singles_playlist_uri = playlist[u'uri']

    if selected_playlist_uri == None:
        playlist = sp.user_playlist_create(sp.current_user()[u'id'], 'Sorting Hat Best Guess Selection: ' + args.pubdate)
        selected_playlist_uri = playlist[u'uri']

    track_list = []
    popularities = sorted([int(x) for x in fc_tracks['singles']['tracks'].keys()], reverse=True)
    for popularity in popularities:
        for track in fc_tracks['singles']['tracks'][str(popularity)]:
            track_list.append(track)

    start = 0
    end = 99
    while start <= len(track_list):
        if end > len(track_list):
            end = len(track_list)
        if start == 0:
            sp.user_playlist_replace_tracks(sp.current_user()[u'id'], singles_playlist_uri, track_list[start:end])
        else:
            sp.user_playlist_add_tracks(sp.current_user()[u'id'], singles_playlist_uri, track_list[start:end])
        #print('Here we would normally be adding tracks {} to {} to singles'.format(start, end))
        start += 100
        end += 100

    track_list = []
    popularities = sorted([int(x) for x in fc_tracks['selected']['tracks'].keys()], reverse=True)
    for popularity in popularities:
        for track in fc_tracks['selected']['tracks'][str(popularity)]:
            track_list.append(track)

    start = 0
    end = 99
    while start <= len(track_list):
        if end > len(track_list):
            end = len(track_list)
        if start == 0:
            sp.user_playlist_replace_tracks(sp.current_user()[u'id'], selected_playlist_uri, track_list[start:end])
        else:
            sp.user_playlist_add_tracks(sp.current_user()[u'id'], selected_playlist_uri, track_list[start:end])
        #print('Here we would normally be adding tracks {} to {} to best guess'.format(start, end))
        start += 100
        end += 100

    #print('Singles')
    #for position in fc_tracks['singles']['stats'].keys():
    #    print('{0}: {1}'.format(position, fc_tracks['singles']['stats'][position]))
    #print('Selections')
    #for position in fc_tracks['selected']['stats'].keys():
    #    print('{0}: {1}'.format(position, fc_tracks['selected']['stats'][position]))

if __name__ == "__main__":
    start_time = datetime.datetime.now()
    args = parser.parse_args()
    print args
    sp = getSpotifyConn()

    fc_date = datetime.datetime.strptime('2015-12-18', '%Y-%m-%d')
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
    results = getAlbumsFromNewReleases(sp)
    #results = getAlbumsFromSortingHat()

    #results = [x.__str__() for x in results]

    #processed_in = open('c:\\Users\\Jesse\\tracks.txt')
    #for album in processed_in:
    #    album = album.strip()
    #    if album in results:
    #        results.remove(album)
    #        album_count += 1
    #processed_in.close()
    #processed_out = open('c:\\Users\\Jesse\\tracks.txt', mode='a')
    #singles_out = open('c:\\Users\\Jesse\\singles.txt', mode='a')
    #best_guess_out = open('c:\\Users\\Jesse\\best_guess.txt', mode='a')
    for album in results:
        try:
            album_dets = sp.album(album.spotifyUri)
        except Exception as e:
            print('Excpetion on ' + album.__str__())
            print(e)
            results.append(album)
            sp = getSpotifyConn()
            continue
        if len(album_dets[u'tracks'][u'items']) >= 3:
            #releaseDate = datetime.datetime.strptime('1970-1-1', '%Y-%m-%d')
            #try:
                #releaseDate = datetime.datetime.strptime(album_dets[u'release_date'], '%Y-%m-%d')
            #except:
                #print('Bad date format: ' + album_dets[u'release_date'])
            album.setReleaseDate(album_dets[u'release_date'])
            if album.releaseDate in release_date_dict.keys():
                release_date_dict[album.releaseDate] += 1
            else:
                release_date_dict[album.releaseDate] = 1
            #print('{0} - {1} = {2}'.format(release_date, fc_date, release_date - fc_date))
            # Make sure the album released the week in question, not after, not before
            if album.releaseDate <= fc_date and album.releaseDate - fc_date > datetime.timedelta(days=-7):
                try:
                    #[single, track, disc, track_num, artist_pop, track_name] = processAlbumDets(album, album_dets, sp, album_count, single_cutoff, artist_dict)
                    #print('{0} pop {1}'.format(track_name, artist_pop))
                    album.name = album_dets[u'name']
                    processAlbumDets(album, album_dets, sp, album_count, single_cutoff, artist_dict)
                except Exception as e:
                    print(u'Excpetion on {0}, {1}'.format(album.name, album.spotifyUri))
                    print(e)
                    traceback.print_exc()
                    results.append(album)
                    sp = getSpotifyConn()
                    continue
                #if track == None:
                #    continue
                #track_list = None
                #if single:
                #    track_list = fc_tracks['singles']
                #else:
                #    track_list = fc_tracks['selected']
                #if artist_pop not in track_list['tracks'].keys():
                #    track_list['tracks'][artist_pop] = []
                #track_list['tracks'][artist_pop].append(track)
                #position = '_'.join([str(disc), str(track_num)])
                #if position not in track_list['stats'].keys():
                #    track_list['stats'][position] = 1
                #else:
                #    track_list['stats'][position] += 1
                #if single:
                #    singles_out.write(u','.join([track,str(artist_pop),position]) + '\n')
                #    singles_out.flush()
                #else:
                #    best_guess_out.write(u','.join([track,str(artist_pop),position]) + '\n')
                #    best_guess_out.flush()
                album_count += 1
                if album_count % 500 == 0:
                    sp = getSpotifyConn()
        #processed_out.write(album + '\n')
        #processed_out.flush()
    #processed_out.close()
    #singles_out.close()
    #best_guess_out.close()

    for releaseDate in sorted(release_date_dict):
        print('{0}: {1}'.format(releaseDate, release_date_dict[releaseDate]))

    singlesPlaylistURI = 'spotify:user:audiobonsai:playlist:6z8m6hjBXxClAZt3oYONCa'
    selectedPlaylistURI = 'spotify:user:audiobonsai:playlist:626JCrZSTl0AQbO6vqr2MB'

    for album in results:
        if album.chosenSingle != None:
            if album.artistPop not in fc_tracks['singles']['tracks'].keys():
                fc_tracks['singles']['tracks'][album.artistPop] = []
                fc_tracks['singles']['tracks'][album.artistPop].append(album.chosenSingle)
        elif album.chosenGuess != None:
            skip = False
            for artist in album.artistDict.keys():
                if len(artist.albumDict.keys()) > 1:
                    skip = True
                    albumNames = [album.name for uri, album in artist.albumDict.iteritems()]
                    print(u'{0} has {1} albums: {2}'.format(artist.name, len(artist.albumDict.keys()), ', '.join(albumNames)))
            if skip:
                continue

            fc_tracks['selected']['tracks'][album.artistPop] = []
            fc_tracks['selected']['tracks'][album.artistPop].append(album.chosenSingle)

    genPlaylist(sp, fc_tracks, singlesPlaylistURI, selectedPlaylistURI)

    for type in sorted(stats_dict.keys()):
        pops = sorted([int(x) for x in stats_dict[type].keys()], reverse=True)
        for popularity in pops:
            print('{0}: Artist Popularity({1}): {2}'.format(type, popularity, stats_dict[type][str(popularity)]))

    end_time = datetime.datetime.now()
    total_time = end_time - start_time
    hours, remainder = divmod(total_time.seconds.__int__(), 3600)
    minutes, seconds = divmod(remainder, 60)
    print('Execution time: ' + '%s:%s:%s' % (hours, minutes, seconds))




