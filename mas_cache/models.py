from typing import Any, Dict, Optional

from django.contrib.postgres.fields import JSONField
from django.core.validators import RegexValidator
from django.db import models
from django.utils.timezone import datetime
from django.utils.translation import gettext_lazy as _

from core.fields import IntegerChoicesField


# Validators


def CountryCodeValidator() -> RegexValidator:
	return RegexValidator(r'^[a-z]{2}$')


# Enums


CHART_TYPE_API = ['top-free', 'top-paid']


class ChartType(models.IntegerChoices):
	FREE = 0, _("Top Free Apps")
	PAID = 1, _("Top Paid Apps")

	@classmethod
	def from_api(cls, value: str) -> 'ChartType':
		if value not in CHART_TYPE_API:
			raise ValueError(f"Unknown chart type: {value}")
		return cls(CHART_TYPE_API.index(value))

	def to_api(self) -> str:
		return CHART_TYPE_API[int(self)]


# Models


class Application(models.Model):
	itunes_id = models.PositiveIntegerField(primary_key=True)

	@property
	def latest_metadata(self) -> Optional['Metadata']:
		metadata = Metadata.objects.filter(
			application=self,
			data__isnull=False,
		).order_by('-timestamp')
		if not metadata.exists():
			return None
		return metadata.first()

	@property
	def is_known(self) -> bool:
		metadata = self.latest_metadata
		if metadata is None:
			return False
		return 'attributes' in metadata.data

	@property
	def is_bundle(self) -> bool:
		metadata = self.latest_metadata
		if metadata is None:
			return False
		return metadata.data.get('type', None) == 'app-bundles'

	@property
	def timestamp(self) -> Optional[datetime]:
		metadata = self.latest_metadata
		if metadata is None:
			return None
		return metadata.timestamp

	@property
	def attributes(self) -> Dict[str, Any]:
		metadata = self.latest_metadata
		if metadata is None:
			return {}
		return metadata.data.get('attributes', {})

	def platform_attributes(self, platform: str = 'osx') -> Dict[str, Any]:
		return self.attributes.get('platformAttributes', {}).get(platform, {})

	@property
	def name(self) -> Optional[str]:
		return self.attributes.get('name', None)

	@property
	def bundle_identifier(self) -> Optional[str]:
		return self.platform_attributes().get('bundleId', None)

	def __str__(self) -> str:
		if self.name is None:
			return str(self.itunes_id)
		return self.name


class Genre(models.Model):
	itunes_id = models.PositiveSmallIntegerField(primary_key=True)
	name = models.CharField(max_length=255, blank=True, null=True, default=None)
	parent = models.ForeignKey(
		'Genre',
		on_delete=models.CASCADE,
		related_name='children',
		blank=True,
		null=True,
		default=None,
	)

	def __str__(self) -> str:
		if self.name is None:
			return str(self.itunes_id)
		return self.name


class AppStore(models.Model):
	country = models.CharField(
		max_length=2,
		primary_key=True,
		validators=[CountryCodeValidator],
	)

	applications = models.ManyToManyField(
		Application,
		related_name='stores',
		through='Metadata',
		through_fields=('store', 'application'),
	)

	def __str__(self) -> str:
		return f"{self.country}"


class Metadata(models.Model):
	application = models.ForeignKey(Application, on_delete=models.CASCADE)
	store = models.ForeignKey(AppStore, on_delete=models.CASCADE)
	source = models.URLField(max_length=4096)
	timestamp = models.DateTimeField()
	data = JSONField()

	class Meta:
		unique_together = (('application', 'store', 'source', 'timestamp'),)


class Chart(models.Model):
	genre = models.ForeignKey(
		Genre,
		on_delete=models.CASCADE,
		related_name='charts',
	)
	store = models.ForeignKey(
		AppStore,
		on_delete=models.CASCADE,
		related_name='charts',
	)
	chart_type = IntegerChoicesField(ChartType)
	timestamp = models.DateTimeField()

	class Meta:
		unique_together = (('genre', 'store', 'chart_type', 'timestamp'),)


class ChartEntry(models.Model):
	chart = models.ForeignKey(
		Chart,
		on_delete=models.CASCADE,
		related_name='entries',
	)
	application = models.ForeignKey(Application, on_delete=models.CASCADE)
	position = models.PositiveSmallIntegerField()

	class Meta:
		unique_together = (
			('chart', 'application'),
			('chart', 'position'),
			('chart', 'application', 'position'),
		)
