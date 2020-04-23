import json

from textwrap import dedent

from django.core.management import CommandError, CommandParser

from core.management import CoreCommand
from mas_cache.management import AppStoreType, GenreType
from mas_cache.models import (
	AppStore,
	Chart,
	ChartEntry,
	ChartType,
	Genre,
)


CHART_CHOICES = ['free', 'paid']


class Command(CoreCommand):

	help = """
		Print or export latest Mac App Store (MAS) charts.
	"""

	def add_arguments(self, parser: CommandParser):
		formats = parser.add_mutually_exclusive_group()
		formats.add_argument(
			'--list',
			action='store_true',
			help="""
				Print only the application IDs in order of their chart position.
				This is useful for automatically installing applications with
				the appstaller utility of maap: https://github.com/0xbf00/maap
			""",
		)
		formats.add_argument(
			'--json',
			action='store_true',
			help="""
				Print the list of applications in JSON format. Only IDs for
				applications will be included and not the metadata itself.
				Metadata can be retrieved by accessing the database or by using
				the iTunes Search API: https://itunes.apple.com/lookup?id=<app_id>.
			""",
		)

		parser.add_argument(
			'--skip-bundles',
			action='store_true',
			help="""
				Disables outputing bundles of applications, e. g., Microsoft
				Office 365, which includes multiple applications, such as Word
				and Excel.
			""",
		)
		parser.add_argument(
			'--skip-unknown',
			action='store_true',
			help="""
				Disables outputting of applications for which no metadata could
				be retrieved. The metadata contains information such as the
				application's name and bundle identifier.
			""",
		)
		parser.add_argument(
			'-t', '--type',
			choices=CHART_CHOICES,
			default='free',
			help="""
				The type of the chart to display. (default: free)
			""",
		)
		parser.add_argument(
			'-g', '--genre',
			type=GenreType,
			default=Genre.objects.get(itunes_id=36),
			help="""
				Output charts for a specified genre. The value passed needs to
				be a valid iTunes genre identifier. (default: App Store [36])
			""",
		)
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

	def head(self, name: str, info: str):
		self.secho(name, fg='white', bold=True, ending=': ')
		self.secho(info)

	def handle(self, *args, **options):
		output_list: bool = options['list']
		output_json: bool = options['json']
		skip_bundles: bool = options['skip_bundles']
		skip_unknown: bool = options['skip_unknown']
		genre: Genre = options['genre']
		store: AppStore = options['store']
		chart_type = ChartType(CHART_CHOICES.index(options['type']))

		charts = Chart.objects.filter(
			genre=genre,
			store=store,
			chart_type=chart_type,
		).order_by('-timestamp')

		if not charts.exists():
			raise CommandError("No charts found.")

		chart = charts.first()

		entries = ChartEntry.objects.filter(chart=chart).order_by('position')

		filtered_entries = entries
		if skip_bundles:
			filtered_entries = [e for e in filtered_entries if not e.application.is_bundle]
		if skip_unknown:
			filtered_entries = [e for e in filtered_entries if e.application.is_known]

		if output_list:
			for entry in filtered_entries:
				self.echo(str(entry.application.itunes_id))
		elif output_json:
			result = {
				'type': chart.chart_type.to_api(),
				'genre': genre.itunes_id,
				'store': store.country,
				'timestamp': str(chart.timestamp),
				'entries': [
					{
						'position': entry.position + 1,
						'app_id': entry.application.itunes_id,
					}
					for entry in filtered_entries
				]
			}
			self.echo(json.dumps(result, separators=(',', ':')))
		else:
			self.head("Store", str(store))
			self.head("Genre", str(genre))
			self.head("Type", " " + CHART_CHOICES[chart_type])
			self.head("State", str(chart.timestamp))
			self.secho("")
			self.secho(f"Pos {'ID':<11s} {'Bundle ID':<50s} Name", fg='white', bold=True)
			for pos, entry in enumerate(filtered_entries):
				app = entry.application
				bundle_id = self.display(app.bundle_identifier)
				name = self.display(app.name)
				self.secho(f"{pos+1:3d} {app.itunes_id:11d} {bundle_id:50s} {name:s}")
