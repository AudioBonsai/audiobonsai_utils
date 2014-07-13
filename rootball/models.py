from django.db import models
from django.core.urlresolvers import reverse

class Artist(models.Model):
    name = models.CharField(max_length=255)

    def __unicode__(self):
        return self.name

    def get_absoulte_url(self):
        return reverse('artist.views.details', args=[str(self.id)])

class ArtistLink(models.Model):
    SOURCE_CHOICES = (
        ('Website', 'Website'),
        ('Spotify', 'Spotify'),
        ('Rdio', 'Rdio'),
        ('ScoundCloud', 'SoundCloud'),
        ('BandCamp', 'BandCamp'),
        ('Twitter', 'Twitter'),
        ('YouTube', 'YouTube'),
        ('Instagram', 'Instagram')
    )
    artist = models.ForeignKey(Artist)
    source = models.CharField(max_length=255, choices=SOURCE_CHOICES)
    source_id = models.CharField(max_length=255)

    def __unicode__(self):
        return u'{} ({})'.format(self.artist.__unicode__(), self.source)

    def get_absoulte_url(self):
        return reverse('artistlink.views.details', args=[str(self.id)])

class Album(models.Model):
    artist = models.ForeignKey(Artist)
    release_date = models.DateField(null=True, blank=True)
    title = models.CharField(max_length=255)

    def __unicode__(self):
        return u'{} by {}'.format(self.title, self.artist.__unicode__())

    def get_absoulte_url(self):
        return reverse('album.views.details', args=[str(self.id)])

class AlbumLink(models.Model):
    SOURCE_CHOICES = (
        ('iTunes', 'iTunes'),
        ('SoundCloud', 'SoundCloud'),
        ('Spotify', 'Spotify'),
        ('Rdio', 'Rdio')
    )
    album = models.ForeignKey(Album)
    source = models.CharField(max_length=255, choices=SOURCE_CHOICES)
    source_id = models.CharField(max_length=255)

    def __unicode__(self):
        return u'{} ({})'.format(self.album.__unicode__(), self.source)

    def get_absoulte_url(self):
        return reverse('albumlink.views.details', args=[str(self.id)])


class Song(models.Model):
    album = models.ForeignKey(Album, null=True, blank=True)
    artist = models.ForeignKey(Artist)
    title = models.CharField(max_length=255)
    sotd = models.DateField(null=True, blank=True, verbose_name="Song of the Day")
    sotw = models.DateField(null=True, blank=True, verbose_name="Song of the Week")

    def __unicode__(self):
        return u'{} by {}'.format(self.title, self.artist.__unicode__())

    def get_absoulte_url(self):
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

    def get_absoulte_url(self):
        return reverse('songlink.views.details', args=[str(self.id)])

