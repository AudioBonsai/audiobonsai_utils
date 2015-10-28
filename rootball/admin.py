from django.contrib import admin
from rootball.models import Artist, Release, Song, Playlist, FreshCuts


class ArtistAdmin(admin.ModelAdmin):
    fieldsets = [
        (None, {'fields': ['name']}),
    ]

class ReleaseAdmin(admin.ModelAdmin):
    fieldsets = [
        (None, {'fields': ['artist', 'title']}),
        ('Optional', {'fields': ['release_date']}),
    ]

class SongAdmin(admin.ModelAdmin):
    fieldsets = [
        (None, {'fields': ['title']})
    ]

class PlaylistAdmin(admin.ModelAdmin):
    fieldsets = [
        (None, {'fields': ['name']}),
        ('Optional', {'fields': ['spotifyuri', 'rdiourl']})
    ]

class FreshCutsAdmin(admin.ModelAdmin):
    fieldsets = [
        (None, {'fields': ['date']})
    ]

# Register your models here.
admin.site.register(Artist, ArtistAdmin)
admin.site.register(Release, ReleaseAdmin)
admin.site.register(Song, SongAdmin)
admin.site.register(Playlist, PlaylistAdmin)
admin.site.register(FreshCuts, FreshCutsAdmin)
