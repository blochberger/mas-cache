import json

from typing import Any, Dict, Optional

from django.core.management import CommandError, CommandParser

from core.management import CoreCommand
from mas_cache.management import AppStoreType
from mas_cache.models import Application, AppStore, Metadata


class Command(CoreCommand):

	help = """
		Return metadata for a given application. The latest metadata found in
		the Mac App Store (MAS) cache is returned. Note that the data is
		formatted the same way as the MAS uses it internally. This might be
		subject to change. Metadata can be retrieved officially via the iTunes
		Search API: https://itunes.apple.com/lookup?id=<app_id>. Note that the
		formats are different.
	"""

	def add_arguments(self, parser: CommandParser):
		parser.add_argument(
			'-s', '--store',
			type=AppStoreType,
			default=AppStore.objects.first(),
			help="""
				Output charts for a specific store. Since in most cases only a
				single store is present, the first one found in the database is
				used by default. The store is specified by the country code,
				e. g., us or de.
			""",
		)
		parser.add_argument(
			'app',
			type=int,
			help="""
				The ID of the application, for which metadata should be returned.
			""",
		)

	def handle(self, *args, **options):
		store: AppStore = options['store']
		app_id: int = options['app']
		app = Application.objects.get(itunes_id=app_id)

		metadatas = Metadata.objects.filter(
			application=app,
			store=store,
			data__isnull=False,
		).order_by('-timestamp')

		metadata: Optional[Metadata] = None
		for current in metadatas:
			data: Dict[str, Any] = current.data

			# Sometimes applications are fetched lazily by the MAS, meaning that
			# there is only a placeholder, but no actual data.
			if 'attributes' not in data:
				continue

			if data.get('type', None) == 'app-bundles':
				raise CommandError(f"ID belongs to an application bundle: {app}")

			metadata = current
			break

		if metadata is None:
			raise CommandError(f"No metadata for app: {app}")

		result = {
			'store': store.country,
			'source': metadata.source,
			'timestamp': str(metadata.timestamp),
			'data': metadata.data,
		}

		self.echo(json.dumps(result, separators=(',', ':')))
