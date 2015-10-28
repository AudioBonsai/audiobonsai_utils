from django.db import models
from django.core.urlresolvers import reverse

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


