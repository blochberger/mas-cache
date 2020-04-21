from mas_cache.models import AppStore, Genre


def AppStoreType(value: str) -> AppStore:
	try:
		return AppStore.objects.get(country=value)
	except AppStore.DoesNotExist:
		raise ValueError


def GenreType(value: str) -> Genre:
	try:
		return Genre.objects.get(itunes_id=int(value))
	except Genre.DoesNotExist:
		raise ValueError
