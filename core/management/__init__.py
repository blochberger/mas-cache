from typing import Optional, Tuple

from django.core.management import BaseCommand
from django.utils.termcolors import colorize


class CoreCommand(BaseCommand):

	def display(self, value: Optional[str]) -> str:
		if value is None:
			return '-'
		return value

	def echo(self, msg: str):
		self.stdout.write(msg)

	def secho(
		self,
		msg: str,
		err: bool = False,
		bold: bool = False,
		ending: Optional[str] = None,
		**kwargs,
	):
		out = self.stdout
		if err:
			out = self.stderr
		opts: Tuple[str, ...] = ()
		if bold:
			opts += ('bold',)
		out.write(colorize(msg, **kwargs), ending=ending)

	def success(self, msg: str):
		self.secho(self.style.SUCCESS(msg))

	def warn(self, msg: str):
		self.secho(self.style.WARNING(msg), err=True)
