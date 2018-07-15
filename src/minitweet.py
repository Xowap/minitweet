#!/usr/bin/env python3
from contextlib import contextmanager
from datetime import datetime
from argparse import ArgumentParser
from pathlib import Path
from furl import furl
from requests_html import HTML
from textwrap import wrap
import dbm

from birdy.twitter import UserClient
import miniflux


TWITTER_LIMIT = 280
TWITTER_LINK_SIZE = 30
WRAP = '[…]'
BEFORE = AFTER = '"'


class KeysCache(object):
    def __init__(self, db):
        self.db = db

    def _make_key(self, key):
        return '{}'.format(key)

    def has(self, key):
        return self._make_key(key) in self.db

    def store(self, key):
        self.db[self._make_key(key)] = datetime.utcnow().isoformat()


@contextmanager
def open_cache(cache_path):
    cache_path = Path(cache_path)

    cache_path.mkdir(parents=True, exist_ok=True)

    with dbm.open(str(cache_path / 'cache'), 'c') as db:
        yield KeysCache(db)


def list_articles(api_url, user, password):
    client = miniflux.Client(api_url, user, password)
    entries = client.get_entries(
        starred=True,
        limit=10,
        order='published_at',
        direction='desc',
    )

    for entry in entries['entries']:
        yield entry


def clean_url(url):
    return furl(url).remove(args=True, fragment=True).url


def extract_text(item):
    # noinspection PyBroadException
    try:
        h = HTML(html=item['content'])
        text = h.text
    except Exception:
        text = item['title']

    if not text:
        text = item['title']

    endings = len(BEFORE) + len(AFTER)
    max_length = TWITTER_LIMIT - TWITTER_LINK_SIZE - endings

    if len(text) <= max_length:
        return '{}{}{} {}'.format(
            BEFORE,
            text,
            AFTER,
            clean_url(item['url']),
        )
    else:
        text = wrap(text, width=(max_length - len(WRAP) - 1))[0]
        return '{}{} {}{} {}'.format(
            BEFORE,
            text,
            WRAP,
            AFTER,
            clean_url(item['url']),
        )


def send_to_twitter(args, tweet):
    client = UserClient(
        args.consumer_key,
        args.consumer_secret,
        args.access_token,
        args.access_token_secret,
    )

    client.api.statuses.update.post(status=tweet)


def parse_args():
    parser = ArgumentParser(description='Automatically sends Miniflux '
                                        'starred entries to a Twitter feed')

    parser.add_argument(
        '--cache-path',
        '-c',
        help='Directory to store the history of published feed items',
        required=True,
    )
    parser.add_argument(
        '--api-url',
        '-a',
        help='Miniflux API url',
        required=True,
    )
    parser.add_argument(
        '--user',
        '-u',
        help='Miniflux user name',
        required=True,
    )
    parser.add_argument(
        '--password',
        '-p',
        help='Miniflux user password',
        required=True,
    )
    parser.add_argument(
        '--consumer_key',
        '-k',
        help='Twitter consumer key',
        required=True,
    )
    parser.add_argument(
        '--consumer_secret',
        '-x',
        help='Twitter consumer secret',
        required=True,
    )
    parser.add_argument(
        '--access_token',
        '-t',
        help='Twitter access token',
        required=True,
    )
    parser.add_argument(
        '--access_token_secret',
        '-s',
        help='Twitter access token secret',
        required=True,
    )

    return parser.parse_args()


def main():
    args = parse_args()

    with open_cache(args.cache_path) as c:
        for item in list_articles(args.api_url, args.user, args.password):
            if not c.has(item['id']):
                c.store(item['id'])
                send_to_twitter(args, extract_text(item))


if __name__ == '__main__':
    main()
