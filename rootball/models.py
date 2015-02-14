from django.db import models
from django.core.urlresolvers import reverse
import spotipy
import spotipy.util

class Artist(models.Model):
    name = models.CharField(max_length=255)

    def __unicode__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('artist.views.details', args=[str(self.id)])

class ArtistLink(models.Model):
    SOURCE_CHOICES = (
        ('Website', 'Website'),
        ('Spotify', 'Spotify'),
        ('Rdio', 'Rdio'),
        ('SoundCloud', 'SoundCloud'),
        ('BandCamp', 'BandCamp'),
        ('Twitter', 'Twitter'),
        ('Facebook', 'Facebook'),
        ('YouTube', 'YouTube'),
        ('Instagram', 'Instagram')
    )
    artist = models.ForeignKey(Artist)
    source = models.CharField(max_length=255, choices=SOURCE_CHOICES)
    source_id = models.CharField(max_length=255)
    spotifyuri = models.CharField(max_length=255, unique=True)
    rdiourl = models.CharField(max_length=255, unique=True)

    def __unicode__(self):
        return u'{} ({})'.format(self.artist.__unicode__(), self.source)

    def get_absolute_url(self):
        return reverse('artistlink.views.details', args=[str(self.id)])

class Release(models.Model):
    release_date = models.DateField(null=True, blank=True)
    title = models.CharField(max_length=255)
    spotifyuri = models.CharField(max_length=255, unique=True)
    rdiourl = models.CharField(max_length=255, unique=True)

    def __unicode__(self):
        return u'{} released on {}'.format(self.title, self.release_date)

    def get_absolute_url(self):
        return reverse('album.views.details', args=[str(self.id)])

class ReleaseLink(models.Model):
    SOURCE_CHOICES = (
        ('iTunes', 'iTunes'),
        ('SoundCloud', 'SoundCloud'),
        ('Spotify', 'Spotify'),
        ('Rdio', 'Rdio')
    )
    release = models.ForeignKey(Release)
    source = models.CharField(max_length=255, choices=SOURCE_CHOICES)
    source_id = models.CharField(max_length=255)

    def __unicode__(self):
        return u'{} ({})'.format(self.album.__unicode__(), self.source)

    def get_absolute_url(self):
        return reverse('albumlink.views.details', args=[str(self.id)])


class Song(models.Model):
    title = models.CharField(max_length=255)
    spotifyuri = models.CharField(max_length=255, unique=True)
    rdiourl = models.CharField(max_length=255, unique=True)

    def __unicode__(self):
        return u'{}'.format(self.title)

    def get_absolute_url(self):
        return reverse('song.views.details', args=[str(self.id)])


class SongLink(models.Model):
    SOURCE_CHOICES = (
        ('YouTube', 'YouTube'),
        ('Spotify', 'Spotify'),
        ('Rdio', 'Rdio'),
        ('SoundCloud', 'SoundCloud'),
        ('BandCamp', 'BandCamp')
    )
    song = models.ForeignKey(Song)
    source = models.CharField(max_length=255, choices=SOURCE_CHOICES)
    source_id = models.CharField(max_length=255)
    
    def __unicode__(self):
        return u'{} ({})'.format(self.song.__unicode__(), self.source)

    def get_absolute_url(self):
        return reverse('songlink.views.details', args=[str(self.id)])

class ReleasedOn(models.Model):
    song = models.ForeignKey(Song)
    release = models.ForeignKey(Release)

    def __unicode__(self):
        return u'{} from {}'.format(self.song.__unicode__(), self.release.__unicode__())

    def get_absolute_url(self):
        return reverse('releasedon.views.details', args=[str(self.id)])


class PerformedBy(models.Model):
    song = models.ForeignKey(Song)
    artist = models.ForeignKey(Artist)

    def __unicode__(self):
        return u'{} performed by {}'.format(self.song.__unicode__(), self.artist.__unicode__())

    def get_absolute_url(self):
        return reverse('performedby.views.details', args=[str(self.id)])

class Playlist(models.Model):
    name = models.CharField(max_length=255)
    spotifyuri = models.CharField(max_length=255, unique=True)
    rdiourl = models.CharField(max_length=255, unique=True)

    def __unicode__(self):
        return u'{}'.format(self.name)

    def get_absolute_url(self):
        return reverse('playlist.views.details', args=[str(self.id)])

class PlaylistTrack(models.Model):
    playlist = models.ForeignKey(Playlist)
    position = models.IntegerField()
    song = models.ForeignKey(Song)

    def __unicode__(self):
        return u'{} ({}): {}'.format(self.playlist.__unicode__(), self.position, self.song.__unicode__())

    def get_absolute_url(self):
        return reverse('playlisttrack.views.details', args=[str(self.id)])

class FreshCuts(models.Model):
    date = models.DateField()
    playlist = models.ForeignKey(Playlist)

    def __unicode__(self):
        return u'Fresh Cuts {}'.format(self.date)

    def get_absolute_url(self):
        return reverse('freshcuts.views.details', args=[str(self.id)])

class PodCast(models.Model):
    episode = models.CharField(max_length=255)
    playlist = models.ForeignKey(Playlist)
    
    def __unicode__(self):
        return self.episode

    def get_absolute_url(self):
        return reverse('podcast.views.details', args=[str(self.id)])

class PodCastSource(models.Model):
    podcast = models.ForeignKey(PodCast)
    freshcuts = models.ForeignKey(FreshCuts)

    def __unicode__(self):
        return u'{} source fresh cuts list {}'.format(self.podcast.__unicode__(), self.freshcuts.__unicode__())

    def get_absolute_url(self):
        return reverse('podcastsource.views.details', args=[str(self.id)])

