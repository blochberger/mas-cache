from setuptools import setup

setup(
	name='mas-cache',
	version='0.0.1',
	install_requires=[
		'django',
		'psycopg2-binary',
	],
	entry_points=dict(
		console_scripts=[
			'manage=manage:main',
		],
	),
)
