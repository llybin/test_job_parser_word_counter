
import argparse
import string
import re
from collections import Counter
from unicodedata import normalize

import bs4
import requests
from bs4 import BeautifulSoup
from many_stop_words import get_stop_words


class URLValidator(object):
    url_regex = re.compile(
            r'^(?:http|ftp)s?://' # http:// or https://
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|'  # domain...
            r'localhost|'  # localhost...
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
            r'(?::\d+)?'  # optional port
            r'(?:/?|[/?]\S+)$', re.IGNORECASE)

    @staticmethod
    def validate(url: str) -> bool:
        return re.match(URLValidator.url_regex, url) is not None


class Parser(object):
    url = None
    soup = None

    def __init__(self, url: str):
        self.url = url

        r = requests.get(url)
        r.raise_for_status()

        self.soup = BeautifulSoup(r.content, features="html.parser")

    @property
    def page_title(self) -> str:
        if self.soup.title:
            title_str = self.soup.title.string
            if title_str:
                return normalize('NFKD', title_str)

        return ''

    @property
    def div_directly_text(self) -> str:
        """
        Get only directly text in div tags
        :return:
        """
        div_text = []

        for row in self.soup.find_all('div'):
            # https://stackoverflow.com/questions/4995116/only-extracting-text-from-this-element-not-its-children
            text = ''.join([t for t in row.contents if type(t) == bs4.element.NavigableString])
            div_text.append(normalize('NFKD', text))

        return ' '.join(div_text)


class WordCounter(object):
    stop_words = None

    def __init__(self):
        self.stop_words = get_stop_words('en')

    @staticmethod
    def clean_string(text: str) -> str:
        """
        Clean out non ascii letters, replace on space for splitting words.
        Now works only for english
        TODO: use regex
        :param text:
        :return:
        """
        return ''.join(map(lambda x: x if x in string.ascii_letters else ' ', text))

    def get_most_common(self, text: str) -> list:
        """
        Get list of words sorted by most common, exclude stop words and punctuation
        :param text:
        :return:
        """
        text = self.clean_string(text)

        words_list = map(lambda x: x.lower(), text.split())

        words_list = filter(lambda x: x not in self.stop_words, words_list)

        c = Counter(words_list)

        return c.most_common()


if __name__ == '__main__':
    # TODO: cover tests, compare stdout result, functional tests
    parser = argparse.ArgumentParser()
    parser.add_argument('url')
    args = parser.parse_args()

    if not URLValidator.validate(args.url):
        print("Please, enter correct URL with schema")
        exit(-1)

    try:
        parser = Parser(args.url)
    except requests.exceptions.RequestException:
        print("Site is not available")
        exit(-2)

    print(parser.page_title)

    print()

    cw = WordCounter()

    for w in cw.get_most_common(parser.div_directly_text):
        print(f"{w[0]:<8}\t{w[1]}")
