from django.db import models
from django.core.urlresolvers import reverse
import datetime

class Artist(models.Model):
    name = models.CharField(max_length=255)
    spotifyuri = models.CharField(max_length=255)
    rdiourl = models.URLField(max_length=255)
    website = models.URLField(max_length=255)
    twitter = models.CharField(max_length=255)
    facebook = models.URLField(max_length=255)
    soundcloud = models.URLField(max_length=255)
    bandcamp = models.URLField(max_length=255)
    youtube = models.URLField(max_length=255)

    def get_artist_by_spotify_uri(self, artist_uri, artist_name):
        match_list = Artist.objects.filter(spotifyuri=artist_uri)
        if len(match_list) == 0:
            artist_obj = Artist()
            artist_obj.name = artist_name
            artist_obj.spotifyuri = artist_uri
            artist_obj.save()
        else:
            artist_obj = match_list[0]
        return artist_obj

    def __unicode__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('artist.views.details', args=[str(self.id)])

class Release(models.Model):
    release_date = models.DateField(null=True, blank=True)
    title = models.CharField(max_length=255)
    spotifyuri = models.CharField(max_length=255, unique=True)
    rdiourl = models.URLField(max_length=255)
    itunes = models.URLField(max_length=255)
    soundcloud = models.URLField(max_length=255)
    bandcamp = models.URLField(max_length=255)

    RELEASE_TYPE_CHOICES = (
        ('Single', 'Single'),
        ('EP', 'EP'),
        ('LP', 'LP')
    )

    def get_release_by_spotify_uri(self, album_uri, album_name):
        match_list = Release.objects.filter(spotifyuri=album_uri)
        if len(match_list) == 0:
            release_obj = Release()
            release_obj.spotifyuri = album_uri
            release_obj.title = album_name
            release_obj.save()
        else:
            release_obj = match_list[0]
        return release_obj

    def __unicode__(self):
        return u'{}'.format(self.title)

    def get_absolute_url(self):
        return reverse('album.views.details', args=[str(self.id)])

class Song(models.Model):
    title = models.CharField(max_length=255)
    spotifyuri = models.CharField(max_length=255, unique=True)
    rdiourl = models.URLField(max_length=255)
    itunes = models.URLField(max_length=255)
    soundcloud = models.URLField(max_length=255)
    bandcamp = models.URLField(max_length=255)
    youtube = models.URLField(max_length=255)

    def get_song_by_spotify_uri(self, song_uri, song_title):
        match_list = Song.objects.filter(spotifyuri=song_uri)
        if len(match_list) == 0:
            song_obj = Song()
            song_obj.spotifyuri = song_uri
            song_obj.title = song_title
            song_obj.save()
        else:
            song_obj = match_list[0]
        return song_obj

    def __unicode__(self):
        return u'{}'.format(self.title)

    def get_absolute_url(self):
        return reverse('song.views.details', args=[str(self.id)])

class PerformedBy(models.Model):
    song = models.ForeignKey(Song)
    artist = models.ForeignKey(Artist)

    def set_link(self, artist_obj, song_obj):
        self.song = song_obj
        self.artist = artist_obj
        self.save()

    def __unicode__(self):
        return u'{} performed by {}'.format(self.song.__unicode__(), self.artist.__unicode__())

    def get_absolute_url(self):
        return reverse('performedby.views.details', args=[str(self.id)])

class Playlist(models.Model):
    name = models.CharField(max_length=255)
    spotifyuri = models.CharField(max_length=255, unique=True)
    rdiourl = models.CharField(max_length=255)

    def parse_spotify_list(self, splist):
        position = 0
        self.name = splist[u'name']
        for track in splist[u'tracks'][u'items']:
            song_obj = Song()
            song_obj = song_obj.get_song_by_spotify_uri(track[u'track'][u'uri'], track[u'track'][u'name'])
            playlist_pos = PlaylistTrack()
            playlist_pos.set_link(self, song_obj, position)
            position += 1
            for artist in track[u'track'][u'artists']:
                artist_obj = Artist()
                artist_obj = artist_obj.get_artist_by_spotify_uri(artist[u'uri'], artist[u'name'])
                performance = PerformedBy()
                performance.set_link(artist_obj, song_obj)
            release_obj = Release()
            release_obj = release_obj.get_release_by_spotify_uri(track[u'track'][u'album'][u'uri'],
                                                                 track[u'track'][u'album'][u'name'])
        self.save()

    def parse_rdio_list(self, rdioclient, rdiohash):
        for trackKey in rdiohash[u'trackKeys']:
            track = rdioclient.call('get', keys=trackKey)
            print('\'{}\' by {} from {}'.format(track[trackKey][u'name'], track[trackKey][u'artist'], track[trackKey][u'album']))

    def get_playlist_by_uri(self, playlist_uri):
        match_list = Playlist.objects.filter(spotifyuri=playlist_uri)
        if len(match_list) == 0:
            match_list = Playlist.objects.filter(rdiourl=playlist_uri)
            if len(match_list) == 0:
                playlist_obj = Playlist()
                playlist_obj.spotifyuri = playlist_uri
                playlist_obj.save()
            else:
                playlist_obj = match_list[0]
        return playlist_obj

    def __unicode__(self):
        return u'{}'.format(self.name)

    def get_absolute_url(self):
        return reverse('playlist.views.details', args=[str(self.id)])

class PlaylistTrack(models.Model):
    playlist = models.ForeignKey(Playlist)
    position = models.IntegerField()
    song = models.ForeignKey(Song)

    def set_link(self, playlist_obj, song_obj, position):
        self.playlist = playlist_obj
        self.song = song_obj
        self.position = position
        self.save()

    def __unicode__(self):
        return u'{} ({}): {}'.format(self.playlist.__unicode__(), self.position, self.song.__unicode__())

    def get_absolute_url(self):
        return reverse('playlisttrack.views.details', args=[str(self.id)])

class FreshCuts(models.Model):
    date = models.DateField()
    playlist = models.ForeignKey(Playlist)

    def get_freshcuts_by_date_spotifyuri(self, pubdate, spotifyuri, splist): #, rdioclient, rdiourl, rdiohash):
        match_list = FreshCuts.objects.filter(date=pubdate)
        if len(match_list) == 0:
            freshcuts_obj = FreshCuts()
            freshcuts_obj.date = pubdate
            pl = Playlist()
            pl = pl.get_playlist_by_uri(spotifyuri)
            #pl.rdiourl = rdiourl
            pl.parse_spotify_list(splist)
            #pl.parse_rdio_list(rdioclient, rdiohash)
            freshcuts_obj.playlist = pl
            freshcuts_obj.save()
        else:
            freshcuts_obj = match_list[0]
        return freshcuts_obj

    def __unicode__(self):
        return u'Fresh Cuts {}'.format(self.date)

    def get_absolute_url(self):
        return reverse('freshcuts.views.details', args=[str(self.id)])


class AlbumCandidate(models.Model):
    spotifyUri = models.CharField(max_length=255)
    sortingHatRank = models.IntegerField()
    releaseDate = models.DateField()
    artistDict = {}
    trackDict = {}
    mostRecentSingle = None
    artistPop = 0
    albumTracks = 0
    albumArtists = []
    chosenSingle = None
    chosenGuess = None

    def __init__(self, spotify_uri, sorting_hat_rank=None):
        self.releaseDate = datetime.datetime.strptime('1970-1-1', '%Y-%m-%d')
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


class ArtistCandidate(models.Model):
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


class TrackCandidate(models.Model):
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