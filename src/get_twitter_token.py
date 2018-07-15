#!/usr/bin/env python3
from http.server import (
    BaseHTTPRequestHandler,
    HTTPServer,
)
from threading import Thread
from urllib.parse import (
    urlparse,
    parse_qs,
)

from birdy.twitter import UserClient
from argparse import ArgumentParser


CONSUMER_KEY = '1NkxCmCRXDIOlQMLDhyP1wp4C'
CONSUMER_SECRET = 'yxp1q9eRzsbE2BHbEptAd3ZJwosmQ20btHFH3MHlf0tTnQkVoj'
CALLBACK_URL = 'https://127.0.0.1:8000/callback'


def parse_args():
    parser = ArgumentParser(description='Helper to get Twitter OAuth tokens')

    parser.add_argument(
        '--consumer-key',
        '-k',
        required=True,
    )
    parser.add_argument(
        '--consumer-secret',
        '-s',
        required=True,
    )
    parser.add_argument(
        '--port',
        '-p',
        type=int,
        default=8042,
    )

    return parser.parse_args()


class AuthMaker(object):
    def __init__(self):
        self.client = None
        self.consumer_key = None
        self.consumer_secret = None
        self.access_token = None
        self.access_token_secret = None
        self.token = None
        self.oauth_verifier = None

    def step1(self, key, secret):
        self.consumer_key = key
        self.consumer_secret = secret
        self.client = UserClient(self.consumer_key, self.consumer_secret)

    def step2(self, callback_url):
        self.token = self.client.get_authorize_token(callback_url)
        self.access_token = self.token.oauth_token
        self.access_token_secret = self.token.oauth_token_secret

        print('Please go to: {}'.format(self.token.auth_url))

    def step3(self, oauth_verifier):
        self.oauth_verifier = oauth_verifier
        self.client = UserClient(
            self.consumer_key,
            self.consumer_secret,
            self.access_token,
            self.access_token_secret,
        )
        self.token = self.client.get_access_token(oauth_verifier)

        print('---- ok ----')
        print('ACCESS_TOKEN = {}'.format(self.token.oauth_token))
        print('ACCESS_TOKEN_SECRET = {}'.format(self.token.oauth_token_secret))


class TwitterAuthHandler(BaseHTTPRequestHandler):
    auth_maker = None

    # noinspection PyPep8Naming
    def do_GET(self):
        parts = urlparse(self.path)
        qs = parse_qs(parts.query)

        self.send_response(200)
        self.send_header(b'Content-Type', b'application/json')
        self.end_headers()
        self.wfile.write(b'{"status":"ok"}\n')

        self.auth_maker.step3(qs.get('oauth_verifier')[0])

        KillerThread().start()


class KillerThread(Thread):
    # noinspection PyMethodOverriding
    def run(self):
        exit(0)


def main():
    maker = AuthMaker()

    class H(TwitterAuthHandler):
        auth_maker = maker

    args = parse_args()

    maker.step1(args.consumer_key, args.consumer_secret)
    maker.step2('http://127.0.0.1:{}/'.format(args.port))

    addr = ('', args.port)
    httpd = HTTPServer(addr, H)
    httpd.serve_forever()


if __name__ == '__main__':
    main()
