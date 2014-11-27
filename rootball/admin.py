from django.contrib import admin
from rootball.models import Artist, ArtistLink, Album, AlbumLink, Song, SongLink, Playlist, FreshCuts, PodCast

class ArtistLinkInline(admin.StackedInline):
    model = ArtistLink
    extra = 1

class ArtistAdmin(admin.ModelAdmin):
    fieldsets = [
        (None, {'fields': ['name']}),
    ]
    inlines = [ArtistLinkInline]

class AlbumLinkInline(admin.StackedInline):
    model = AlbumLink
    extra = 1

class AlbumAdmin(admin.ModelAdmin):
    fieldsets = [
        (None, {'fields': ['artist', 'title']}),
        ('Optional', {'fields': ['release_date']}),
    ]
    inlines = [AlbumLinkInline]

class SongLinkInline(admin.StackedInline):
    model = SongLink
    extra = 1

class SongAdmin(admin.ModelAdmin):
    fieldsets = [
        (None, {'fields': ['title', 'artist']}),
        ('Optional', {'fields': ['album']}),
        ('Honors', {'fields': ['sotd', 'sotw']})
    ]
    inlines = [SongLinkInline]


class PlaylistAdmin(admin.ModelAdmin):
    fieldsets = [
        (None, {'fields': ['name']}),
        ('Optional', {'fields': ['spotifyuri', 'rdiourl']})
    ]

class FreshCutsAdmin(admin.ModelAdmin):
    fieldsets = [
        (None, {'fields': ['date', 'playlist']}),
    ]

class PodCastAdmin(admin.ModelAdmin):
    fieldsets = [
        (None, {'fields': ['episode', 'freshcuts', 'playlist']}),
    ]

# Register your models here.
admin.site.register(Artist, ArtistAdmin)
admin.site.register(Album, AlbumAdmin)
admin.site.register(Song, SongAdmin)
admin.site.register(Playlist, PlaylistAdmin)
admin.site.register(FreshCuts, FreshCutsAdmin)
admin.site.register(PodCast, PodCastAdmin)
