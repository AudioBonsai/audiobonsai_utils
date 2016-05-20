import argparse
import datetime
import django
import os
import re
import spotipy
import spotipy.util as sputil
import traceback
import urllib


__author__ = 'Jesse'

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "audiobonsai.settings")
django.setup()

parser = argparse.ArgumentParser(description='load a Fresh Cuts playlist')
parser.add_argument('-pubdate', action='store', dest='pubdate', help='The date of the FreshCuts list publication')

stats_dict = {}


class AlbumCandidate:
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

    def __init__(self, spotify_uri, sorting_hat_rank=None):
        self.spotifyUri = spotify_uri.__str__()
        self.sortingHatRank = sorting_hat_rank
        self.artistDict = {}
        self.trackDict = {}
        self.albumArtists = []
        self.releaseDate = datetime.datetime.strptime('1970-1-1', '%Y-%m-%d')
        self.mostRecentSingle = None
        self.chosenSingle = None
        self.chosenGuess = None
        self.artistPop = 0
        self.albumTracks = 0

    def set_release_date(self, date_text):
        try:
            self.releaseDate = datetime.datetime.strptime(date_text, '%Y-%m-%d')
        except:
            print('Bad date format: ' + date_text)

    def add_track(self, track_candidate):
        if track_candidate.discNumber not in self.trackDict.keys():
            self.trackDict[track_candidate.discNumber] = {}
        self.trackDict[track_candidate.discNumber][track_candidate.trackNumber] = track_candidate
        self.albumTracks += 1

        for track_artist in track_candidate.artistList:
            if track_artist.spotifyUri not in self.artistDict.keys():
                self.artistDict[track_artist.spotifyUri] = track_artist

    def select_artists(self):
        for uri, album_artist in self.artistDict.items():
            if self.albumTracks == album_artist.get_num_album_tracks(self):
                self.albumArtists.append(album_artist)
                if album_artist.popularity > self.artistPop:
                    self.artistPop = album_artist.popularity

    def get_song_dict(self):
        song_dict = {}
        for disc in self.trackDict.keys():
            for trackNum in self.trackDict[disc].keys():
                song_dict[self.trackDict[disc][trackNum].name] = self.trackDict[disc][trackNum]
        return song_dict

    def pick_single(self, sp_conn, singles_cutoff):
        for album_artist in self.albumArtists:
            try:
                artist_tracks = sp_conn.artist_albums(album_artist.spotifyUri, album_type='single', country='US')
            except:
                print('Error occurred getting artist tracks for {0}'.format(album_artist.name))
                sp_conn = get_spotify_conn()
                artist_tracks = sp_conn.artist_albums(album_artist.spotifyUri, album_type='single', country='US')
            uris = [x[u'uri'] for x in artist_tracks[u'items']]
            if len(uris) == 0:
                break
            singles_dets = sp_conn.albums(uris)
            release_date = singles_cutoff

            album_names = self.get_song_dict()
            match_name = None

            for artist_single in singles_dets[u'albums']:
                singles_names = [x[u'name'] for x in artist_single[u'tracks'][u'items']]
                if artist_single[u'uri'] == self.spotifyUri:
                    continue
                if artist_single[u'name'] in album_names.keys():
                    match_name = artist_single[u'name']
                elif singles_names[0] in album_names.keys():
                    match_name = singles_names[0]
                else:
                    continue
                single_release_date = datetime.datetime.strptime('1970-1-1', '%Y-%m-%d')
                try:
                    single_release_date = datetime.datetime.strptime(artist_single[u'release_date'], '%Y-%m-%d')
                except:
                    print('Bad date format: ' + artist_single[u'release_date'])
                if single_release_date > release_date:
                    release_date = single_release_date
                    self.chosenSingle = album_names[match_name]
                    return

        if self.chosenSingle is None:
            durations = {}
            for trackNum in range(1, 6 if self.albumTracks > 6 else self.albumTracks+1):
                if trackNum not in self.trackDict[1].keys():
                    break
                track = self.trackDict[1][trackNum]
                durations[track.duration] = track
            duration = sorted(durations.keys())[int(len(durations.keys())/2)]
            self.chosenGuess = durations[duration]


class ArtistCandidate:
    spotifyUri = ''
    name = ''
    popularity = ''
    albumDict = dict()
    genres = list()

    def __init__(self, artist_dets, artist_album, track):
        self.name = artist_dets[u'name']
        self.spotifyUri = artist_dets[u'uri']
        self.genres = artist_dets[u'genres']
        if artist_dets[u'popularity'] != '-':
            self.popularity = int(artist_dets[u'popularity'])
        else:
            self.popularity = 0
        self.albumDict = dict()
        self.albumDict[artist_album.spotifyUri] = {}
        self.albumDict[artist_album.spotifyUri]['album'] = artist_album
        self.albumDict[artist_album.spotifyUri]['tracks'] = [track]

    def add_track(self, source_album, track):
        if source_album.spotifyUri not in self.albumDict.keys():
            self.albumDict[source_album.spotifyUri] = {}
            self.albumDict[source_album.spotifyUri]['album'] = source_album
            self.albumDict[source_album.spotifyUri]['tracks'] = [track]
        else:
            self.albumDict[source_album.spotifyUri]['tracks'].append(track)

    def get_num_album_tracks(self, album_dict):
        return len(self.albumDict[album_dict.spotifyUri]['tracks'])


class TrackCandidate:
    duration = ''
    discNumber = ''
    trackNumber = ''
    name = ''
    spotifyUri = ''
    artistList = []

    def __init__(self, source_album, album_track, track_artist_dict, passed_sp):
        self.duration = int(album_track[u'duration_ms'])
        self.name = album_track[u'name']
        self.spotifyUri = album_track[u'uri']
        self.discNumber = int(album_track[u'disc_number'])
        self.trackNumber = int(album_track[u'track_number'])
        self.artistList = []

        for track_artist in album_track[u'artists']:
            if track_artist[u'uri'] in track_artist_dict.keys():
                track_artist_dict[track_artist[u'uri']].add_track(source_album, self)
            else:
                try:
                    artist_full = passed_sp.artist(track_artist[u'uri'])
                except:
                    print('Problem resolving artist {0}'.format(track_artist[u'uri']))
                    passed_sp = get_spotify_conn()
                    artist_full = passed_sp.artist(track_artist[u'uri'])
                artist_candidate = ArtistCandidate(artist_full, source_album, self)
                track_artist_dict[track_artist[u'uri']] = artist_candidate
                self.artistList.append(artist_candidate)

        source_album.add_track(self)


def get_spotify_conn(username='audiobonsai',
                     scope='user-read-private playlist-modify-private playlist-read-private playlist-modify-public'):
    """
    get_spotify_conn -- connect to spotify
    """
    token = sputil.prompt_for_user_token(username, scope)
    return_sp = spotipy.Spotify(auth=token)
    return return_sp


def build_artist_dict(album, album_tracks, artist_dict, ap):
    # Identify all the artists on the album to look for singles and dictify the tracks
    for album_track in album_tracks:
        TrackCandidate(album, album_track, artist_dict, sp)


def process_album_dets(album_obj, album_dets, sp, album_count, single_cutoff, artist_dict):
    # Get all the tracks on the album
    album_tracks = album_dets[u'tracks'][u'items']
    build_artist_dict(album_obj, album_tracks, artist_dict, sp)
    album_obj.select_artists()
    album_obj.pick_single(sp, single_cutoff)

    if album_obj.chosenSingle is not None:
        print(u'{6}: {0}: {1} from {2} by {3}({4}), {5}'.format(album_count, album_obj.chosenSingle.name,
                                                                album_obj.name,
                                                                ', '.join(
                                                                    [artist.name for artist in album_obj.albumArtists]),
                                                                album_obj.artistPop,
                                                                'Single',
                                                                datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
    elif album_obj.chosenGuess is not None:
        print(u'{6}: {0}: {1} from {2} by {3}({4}), {5}'.format(album_count, album_obj.chosenGuess.name, album_obj.name,
                                                                ', '.join(
                                                                    [artist.name for artist in album_obj.albumArtists]),
                                                                album_obj.artistPop, 'Guess',
                                                                datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
    else:
        print(u'{2}: No track chosen for {0}, {1}'.format(album_obj.name, album_obj.spotifyUri,
                                                          datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')))


def get_albums_from_new_releases(sp):
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
            uris.append(AlbumCandidate(x[u'uri']))
        offset = len(uris)

    return uris


def get_albums_from_sorting_hat():
    response = urllib.request.urlopen('http://everynoise.com/spotify_new_releases.html')
    html = response.read().decode("utf-8")
    print(type(html))
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
                track_list.append(AlbumCandidate(bits.group(2), bits.group(1)))
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


def update_playlist(upd_sp, uri, track_list):
    start = 0
    end = 100
    while start <= len(track_list):
        if end > len(track_list):
            end = len(track_list)
        if start == 0:
            try:
                upd_sp.user_playlist_replace_tracks(upd_sp.current_user()[u'id'], uri, track_list[start:end])
            except:
                upd_sp = get_spotify_conn()
                upd_sp.user_playlist_replace_tracks(upd_sp.current_user()[u'id'], uri, track_list[start:end])
            #sp.user_playlist_replace_tracks(sp.current_user()[u'id'], uri, track_list[start:end])
        else:
            try:
                upd_sp.user_playlist_add_tracks(upd_sp.current_user()[u'id'], uri, track_list[start:end])
            except:
                upd_sp = get_spotify_conn()
                upd_sp.user_playlist_add_tracks(upd_sp.current_user()[u'id'], uri, track_list[start:end])
            #sp.user_playlist_add_tracks(sp.current_user()[u'id'], uri, track_list[start:end])
        start += 100
        end += 100


def gen_playlist(sp, fc_tracks, singles_playlist_uri=None, selected_playlist_uri=None, jje_playlist_uris=None):
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

        update_playlist(sp, playlist_uri, track_list)
        update_playlist(sp, jje_playlist_uris[type]['top50']['uri'], jje_playlist_uris[type]['top50']['tracks'])
        update_playlist(sp, jje_playlist_uris[type]['verge']['uri'], jje_playlist_uris[type]['verge']['tracks'])
        update_playlist(sp, jje_playlist_uris[type]['unheralded']['uri'],
                        jje_playlist_uris[type]['unheralded']['tracks'])
        update_playlist(sp, jje_playlist_uris[type]['underground']['uri'],
                        jje_playlist_uris[type]['underground']['tracks'])
        update_playlist(sp, jje_playlist_uris[type]['unknown']['uri'], jje_playlist_uris[type]['unknown']['tracks'])

    '''
    track_list = []
    popularities = sorted([x for x in fc_tracks['selected']['tracks'].keys()], reverse=True)
    for popularity in popularities:
        for track in fc_tracks['selected']['tracks'][popularity]:
            if track is None:
                continue
            track_list.append(track.spotifyUri)

    update_playlist(sp, selected_playlist_uri, track_list)
    '''


def process_list(albums):
    sp = get_spotify_conn()
    album_count = 0
    for album in albums:
        success = process_album(album, sp, album_count)
        if success:
           album_count += 1
        else:
            albums.append(album)
            sp = get_spotify_conn()
        if album_count % 100 == 0:
            sp = get_spotify_conn()


def process_album(album, sp, album_count):
    #sp = get_spotify_conn()
    try:
        album_dets = sp.album(album.spotifyUri)
    except Exception as e:
        try:
            print('Excpetion on ' + album.__str__())
        except Exception as e2:
            print(e2)
        print(e)
        return False
    if len(album_dets[u'tracks'][u'items']) >= 3:
        album.set_release_date(album_dets[u'release_date'])
        if album.releaseDate in release_date_dict.keys():
            release_date_dict[album.releaseDate] += 1
        else:
            release_date_dict[album.releaseDate] = 1

        if album.releaseDate <= fc_date and album.releaseDate - fc_date > datetime.timedelta(days=-7):
            try:
                album.name = album_dets[u'name']
                process_album_dets(album, album_dets, sp, album_count, single_cutoff, artist_dict)
                #process_album_dets(album, album_dets, sp, 0, single_cutoff, artist_dict)
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
    sp = get_spotify_conn()

    fc_date = datetime.datetime.strptime('2016-05-06', '%Y-%m-%d')
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
    results = get_albums_from_sorting_hat()
    process_list(results)
    #results_range = []
    #for i in range(0, len(results), int(len(results)/len(rc.ids))):
    #    results_range.append(results[i:i+int(len(results)/len(rc.ids))])
    #    print('{0:d}:{1:d}'.format(i, i+int(len(results)/len(rc.ids))))

    #lview.map(process_list, results)

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
    gen_playlist(sp, fc_tracks, singlesPlaylistURI, selectedPlaylistURI, jje_playlist_uris)

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


