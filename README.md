# mas-cache

This utility allows you to scan the cache files of the Mac App Store (MAS) for applications. This is useful for doing research on macOS applications, e. g., if you want to analyse the top free apps.

The goal is somewhat similar to what [mas-crawl](https://github.com/0xbf00/mas-crawl) achieves by crawling MAS preview pages. Unfortunately, that approach currently does not work.

## Installation

```sh
python -m venv .env
. .env/bin/activate
pip install --upgrade pip
pip install --editable .

# Configure
cp settings.example.json core/settings.json
vim core/settings.json
# Note that SECRET_KEY can be generated with:
#    from django.core.management.utils import get_random_secret_key
#    get_random_secret_key()

manage migrate
```

## Usage

In order to populate the cache, open the App Store application and browse a bit. Then simply run:

```sh
manage scan
```

Since the cache is cleared quite aggressively, you should run the command often, e. g., after you open a page in the MAS (and fully scrolled down).

Once you scanned the applications, you can print the list of top free apps:

```sh
manage charts --skip-bundles --skip-unknown
```

The output will look something like:

```
Store: de
Genre: App Store
Type:  free
State: 2020-04-20 15:28:40+00:00

Pos ID          Bundle ID                                          Name
  1   409201541 com.apple.iWork.Pages                              Pages
  2   408981434 com.apple.iMovieApp                                iMovie
  3   682658836 com.apple.garageband10                             GarageBand
  4   409183694 com.apple.iWork.Keynote                            Keynote
  5   409203825 com.apple.iWork.Numbers                            Numbers
  6  1147396723 desktop.WhatsApp                                   WhatsApp Desktop
  7   462054704 com.microsoft.Word                                 Microsoft Word
  8  1381523962 com.herzick.mac                                    Houseparty
  9   462062816 com.microsoft.Powerpoint                           Microsoft PowerPoint
 10   462058435 com.microsoft.Excel                                Microsoft Excel
[…]
```

If you want to install the applications, I recommend to take a look at [maap](https://github.com/0xbf00/maap). You can export the application IDs as list, which can then be used with `appstaller`:

```sh
manage charts --skip-bundles --list
```

You can also export the list as JSON:

```sh
manage charts --skip-bundles --json
```

To get the latest metadata (JSON) for an application, you can run the following command:

```sh
manage metadata 409201541
```

Alternatively, you can query the [iTunes Search API](https://affiliate.itunes.apple.com/resources/documentation/itunes-store-web-service-search-api/), although the formats are different:

```sh
curl 'https://itunes.apple.com/lookup?id=409201541'
```

If you want to lookup many application, I recommend to use [mas-crawl](https://github.com/0xbf00/mas-crawl).
