import difflib
import json
import os
import sqlite3
import sys

from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from urllib.parse import parse_qs, urlparse

from django.core.exceptions import ValidationError
from django.core.management import CommandError
from django.db import transaction
from django.utils import timezone
from django.utils.timezone import datetime

from core.management import CoreCommand
from mas_cache.models import (
	AppStore,
	Application,
	Chart,
	ChartEntry,
	ChartType,
	Genre,
	Metadata,
)


ReceiverData = Union[bytes, str]


class Command(CoreCommand):

	help = """
		Scan the cache of the Mac App Store (MAS) for application, charts, and
		application metadata. Since the MAS aggressively clears the cache, the
		command should be run multiple times while browsing the MAS.
	"""

	def __init__(self, *args, **kwargs) -> None:
		super().__init__(*args, **kwargs)

		self.container = os.path.expanduser('~/Library/Containers/com.apple.appstore/Data')
		self._cache_db: Optional[sqlite3.Connection] = None

	def __del__(self):
		if self._cache_db:
			self._cache_db.close()

	@property
	def cache_dir(self) -> str:
		return os.path.join(self.container, 'Library/Caches/com.apple.appstore')

	@property
	def cache_data_dir(self) -> str:
		return os.path.join(self.cache_dir, 'fsCachedData')

	@property
	def cache_db(self) -> sqlite3.Connection:
		if self._cache_db is None:
			fn = os.path.join(self.cache_dir, 'Cache.db')
			self._cache_db = sqlite3.connect(fn)
		return self._cache_db

	def get_cached_resource(
		self,
		receiver_data: ReceiverData,
		should_be_on_fs: bool,
	) -> Dict[str, Any]:
		if isinstance(receiver_data, str):
			resource_id: str = receiver_data

			if not should_be_on_fs:
				self.warn(f"Resource might not be cached, trying to locate anyway: {resource_id}")

			resource_fn = os.path.join(self.cache_data_dir, resource_id)

			with open(resource_fn, 'rb') as fp:
				return json.load(fp)

		assert isinstance(receiver_data, bytes)

		return json.loads(receiver_data.decode())

	@transaction.atomic
	def add_application_data(
		self,
		data: Dict[str, Any],
		source: str,
		timestamp: datetime,
		store: AppStore,
	):
		assert 'id' in data
		app_id = int(data['id'])

		app, app_created = Application.objects.get_or_create(itunes_id=app_id)

		metadatas = Metadata.objects.filter(
			application=app,
			store=store,
			source=source,
			timestamp=timestamp,
		)
		if metadatas.exists():
			assert metadatas.count() == 1
			metadata = metadatas.first()

			existing_data = json.dumps(metadata.data, sort_keys=True, indent=2).splitlines()
			new_data = json.dumps(data, sort_keys=True, indent=2).splitlines()
			if existing_data != new_data:
				self.warn(f"Cached entries are different:\n  App: {app}\n  Store: {store}\n  Source: {source}\n  Timestamp: {timestamp}")
				diff = difflib.ndiff(existing_data, new_data)
				for line in diff:
					if line.startswith('- '):
						self.secho(line, fg='red')
					elif line.startswith('  '):
						self.secho(line)
					elif line.startswith('+ '):
						self.secho(line, fg='green')
					elif line.startswith('? '):
						self.secho(line, fg='white')
					else:
						assert False
				self.secho("Update [u] / Keep [k] / Abort [a]:", fg='white', bold=True)
				answer = input("Select an option: ")
				while True:
					if answer in ['u', 'k', 'a']:
						break
					answer = input("Please select a valid option: ")
				if answer == 'u':  # Update
					metadata.data = data
					metadata.full_clean()
					metadata.save()
				elif answer == 'k':  # Keep
					assert not app_created
					return
				elif answer == 'a':  # Abort
					raise CommandError("Aborted")
				else:
					assert False, f"Unhandled answer: {answer}"
		else:
			metadata = Metadata(
				application=app,
				store=store,
				source=source,
				timestamp=timestamp,
				data=data,
			)
			metadata.full_clean()
			metadata.save()

		if app_created:
			self.success(f"Added new application: {app}")

	@transaction.atomic
	def add_genre(
		self,
		itunes_id: int,
		name: Optional[str] = None,
		parent: Optional[Genre] = None,
	) -> Genre:
		genre, created = Genre.objects.get_or_create(itunes_id=itunes_id)

		updated = False
		if name is not None and genre.name != name:
			genre.name = name
			updated = True
		if parent is not None and genre.parent != parent:
			genre.parent = parent
			updated = True

		if updated:
			genre.full_clean()
			genre.save()

		if created:
			self.success(f"Added genre: {genre}")
		else:
			if updated:
				self.success(f"Updated genre: {genre}")

		return genre

	def process_resource(self, resource: Dict[str, Any], source: str, timestamp: datetime):
		# Deconstruct URL
		url = urlparse(source)
		path = Path(url.path)
		assert 3 < len(path.parts), f"Unknown URL: {url}"
		mode = path.parts[2]
		country = path.parts[3]

		store, store_created = AppStore.objects.get_or_create(country=country)
		if store_created:
			self.success(f"Added new store: {store}")

		if mode == 'catalog':
			# Deconstruct URL further
			assert 4 < len(path.parts), f"Unknown URL: {url}"
			sub_mode = path.parts[4]

			if sub_mode in ['apps', 'contents']:
				data = resource['data']
				for app_data in data:
					self.add_application_data(app_data, source, timestamp, store)
			elif sub_mode == 'charts':
				# Extract genre
				query = parse_qs(url.query)
				assert 'genre' in query
				assert len(query['genre']) == 1
				genre = self.add_genre(int(query['genre'][0]))

				# Split charts by type
				charts_data = resource['results']['apps']
				charts: Dict[ChartType, List[Dict[str, Any]]] = {}
				for chart in charts_data:
					chart_type = ChartType.from_api(chart['chart'])
					charts[chart_type] = chart['data']

				# Store apps. For some of them, the metadata has been prefetched.
				for data in charts.values():
					for app_data in data:
						self.add_application_data(app_data, source, timestamp, store)

				for chart_type, chart_data in charts.items():
					# Check whether the chart is already known
					if Chart.objects.filter(
						genre=genre,
						store=store,
						chart_type=chart_type,
						timestamp=timestamp,
					).exists():
						return

					with transaction.atomic():
						chart = Chart(
							genre=genre,
							store=store,
							chart_type=chart_type,
							timestamp=timestamp,
						)
						chart.full_clean()
						chart.save()

						for position, app_data in enumerate(chart_data):
							app_id = int(app_data['id'])
							app = Application.objects.get(itunes_id=app_id)
							entry = ChartEntry(
								chart=chart,
								application=app,
								position=position,
							)
							entry.full_clean()
							entry.save()
					self.success(f"Successfully added chart: {chart}")
			else:
				assert False, f"Unhandled {mode} sub-mode: {sub_mode}"
		elif mode == 'editorial':
			assert 4 < len(path.parts)
			sub_mode = path.parts[4]
			if sub_mode == 'categories':
				categories = resource['results']['categories']
				for category in categories:
					parent = self.add_genre(
						itunes_id=int(category['genre']),
						name=category['name'],
					)
					for child in category['children']:
						self.add_genre(
							itunes_id=int(child['genre']),
							name=child['name'],
							parent=parent,
						)
			else:
				editorials: List[Dict[str, Any]] = resource['data']
				for editorial in editorials:
					editorial_type = editorial['type']
					if editorial_type == 'groupings':
						# TODO Handle groupings... apps are nested deep.
						continue
					assert editorial_type == 'rooms', source
					data = editorial['relationships']['contents']['data']
					for app_data in data:
						self.add_application_data(app_data, source, timestamp, store)
		else:
			assert False, f"Unhandled mode: {mode}"

	def handle(self, *args, **options):
		if sys.platform != 'darwin':
			raise CommandError("This command only works on macOS.")

		c = self.cache_db.cursor()

		rows = c.execute('''
			SELECT
				cfurl_cache_response.request_key,
				cfurl_cache_response.time_stamp,
				cfurl_cache_receiver_data.receiver_data,
				cfurl_cache_receiver_data.isDataOnFS
			FROM
				cfurl_cache_response, cfurl_cache_receiver_data
			WHERE
				cfurl_cache_response.entry_ID == cfurl_cache_receiver_data.entry_ID
				AND cfurl_cache_response.request_key LIKE 'https://api.apps.apple.com/v1/%';
		''')

		for row in rows.fetchall():
			source: str = row[0]
			timestamp = datetime.fromisoformat(row[1])
			receiver_data: Union[bytes, str] = row[2]
			should_be_on_fs = bool(row[3])

			if not timezone.is_aware(timestamp):
				timestamp = timezone.make_aware(timestamp, timezone=timezone.utc)

			resource = self.get_cached_resource(receiver_data, should_be_on_fs)

			self.process_resource(resource, source, timestamp)
