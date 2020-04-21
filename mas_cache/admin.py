from django.contrib import admin

from mas_cache.models import (
	Application,
	AppStore,
	Chart,
	ChartEntry,
	Genre,
	Metadata,
)


# Inlines


class ChartEntryInline(admin.TabularInline):
	model = ChartEntry
	extra = 0
	ordering = ['position']
	autocomplete_fields = ['application']


# Admin Models


@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
	list_display = [
		'itunes_id',
		'name',
		'bundle_identifier',
		'timestamp',
		'is_bundle',
		'is_known',
	]
	ordering = ['itunes_id']
	search_fields = ['name', 'itunes_id']


@admin.register(AppStore)
class AppStoreAdmin(admin.ModelAdmin):
	list_display = ['country']
	ordering = ['country']


@admin.register(Chart)
class ChartAdmin(admin.ModelAdmin):
	date_hierarchy = 'timestamp'
	inlines = [ChartEntryInline]
	list_display = ['chart_type', 'genre', 'store', 'timestamp']
	list_filter = ['chart_type', 'genre']
	ordering = ['-timestamp']


@admin.register(ChartEntry)
class ChartEntryAdmin(admin.ModelAdmin):
	list_display = ['chart', 'position', 'application']


@admin.register(Genre)
class GenreAdmin(admin.ModelAdmin):
	fields = ['parent', 'name']
	list_display = ['name', 'itunes_id', 'parent']
	list_filter = ['parent']
	ordering = ['name', 'itunes_id']
	search_fields = ['itunes_id', 'name']
	autocomplete_fields = ['parent']


@admin.register(Metadata)
class MetadataAdmin(admin.ModelAdmin):
	date_hierarchy = 'timestamp'
	list_display = ['store', 'application', 'timestamp']
