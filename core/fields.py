from typing import Any, Dict, Optional, Tuple, Type, TypeVar

from django.db import models
from django.utils.translation import gettext_lazy as _


IntegerChoices = TypeVar('IntegerChoices', bound=models.IntegerChoices)


class IntegerChoicesField(models.IntegerField):

	description = "A list of numeric choices."

	def __init__(self, choices_class: Type[IntegerChoices], *args, **kwargs):
		assert 'choices' not in kwargs, "Please do not specify choices manually."

		self.choices_class = choices_class

		kwargs['choices'] = choices_class.choices

		super().__init__(*args, **kwargs)

	def deconstruct(self) -> Tuple[str, str, Tuple[Any, ...], Dict[str, Any]]:
		name, path, args, kwargs = super().deconstruct()

		del kwargs['choices']

		kwargs['choices_class'] = self.choices_class

		return name, path, args, kwargs

	def from_db_value(self, value: Optional[int], expression, connection) -> Optional[IntegerChoices]:
		if value is None:
			return value
		return self.choices_class(value)

	def to_python(self, value: Optional[int]) -> Optional[IntegerChoices]:
		if value is None:
			return value
		return self.choices_class(value)

	def get_prep_value(self, value: IntegerChoices) -> int:
		return int(value)
