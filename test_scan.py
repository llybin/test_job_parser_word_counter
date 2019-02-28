import unittest
import requests
import requests_mock

from scan import Parser, URLValidator, WordCounter


class URLValidatorTest(unittest.TestCase):

    def test_ok(self):
        self.assertTrue(URLValidator.validate('http://ya.ru'))
        self.assertTrue(URLValidator.validate('https://ya.ru'))
        self.assertTrue(URLValidator.validate('https://ya.ru/1'))
        self.assertTrue(URLValidator.validate('https://ya.ru:80/1'))
        self.assertTrue(URLValidator.validate('https://ya.ru/1/2'))
        self.assertTrue(URLValidator.validate('https://1.2.3.4'))
        self.assertTrue(URLValidator.validate('https://1.2.3.4:8080'))
        self.assertTrue(URLValidator.validate('https://1.2.3.4:8080/1/2/'))

    def test_not_ok(self):
        self.assertFalse(URLValidator.validate('http'))
        self.assertFalse(URLValidator.validate('http://'))
        self.assertFalse(URLValidator.validate('http://:80'))
        self.assertFalse(URLValidator.validate('ya.ru'))
        self.assertFalse(URLValidator.validate('1.2.3.4'))
        self.assertFalse(URLValidator.validate('1.2.3.4:45'))
        self.assertFalse(URLValidator.validate('1.2.3.4:ss'))
        self.assertFalse(URLValidator.validate('htt://ya.ru'))
        self.assertFalse(URLValidator.validate('http://ya.ru:aa'))


class ParserTest(unittest.TestCase):

    def test_missing_schema(self):
        with self.assertRaises(requests.exceptions.RequestException):
            Parser('')

    def test_invalid_url(self):
        with self.assertRaises(requests.exceptions.RequestException):
            Parser('http://')

    @requests_mock.mock()
    def test_site_not_opened(self, req_mock):
        req_mock.get(
            'http://test.ru',
            status_code=404
        )

        with self.assertRaises(requests.exceptions.HTTPError):
            Parser('http://test.ru')


class ParserTitleTest(unittest.TestCase):
    @requests_mock.mock()
    def test_no(self, req_mock):
        req_mock.get(
            'http://test.ru',
            text='<html></html>'
        )

        parser = Parser('http://test.ru')
        self.assertEqual(parser.page_title, '')

    @requests_mock.mock()
    def test_empty(self, req_mock):
        req_mock.get(
            'http://test.ru',
            text='<html><head><title></title></head></html>'
        )

        parser = Parser('http://test.ru')
        self.assertEqual(parser.page_title, '')

    @requests_mock.mock()
    def test_empty_content(self, req_mock):
        req_mock.get(
            'http://test.ru'
        )

        parser = Parser('http://test.ru')
        self.assertEqual(parser.page_title, '')

    @requests_mock.mock()
    def test_ok(self, req_mock):
        req_mock.get(
            'http://test.ru',
            text='<html><head><title>My test &#8212; title</title></head></html>'
        )

        parser = Parser('http://test.ru')
        self.assertEqual(parser.page_title, 'My test — title')

    @requests_mock.mock()
    def test_normalize(self, req_mock):
        req_mock.get(
            'http://test.ru',
            text='<html><head><title>My test &#8212;&nbsp;title</title></head></html>'
        )

        parser = Parser('http://test.ru')
        self.assertEqual(parser.page_title, 'My test — title')


class ParserDivTextTest(unittest.TestCase):
    @requests_mock.mock()
    def test_directly_text_normalize(self, req_mock):
        req_mock.get(
            'http://test.ru',
            text=f'''<html><head><title>My test &#8212; title</title></head><body>
<div>This is my test text, if it works &#8212;&nbsp;great! If not, then I will be upset :)</div>
</body></html>''')

        parser = Parser('http://test.ru')
        self.assertEqual(
            parser.div_directly_text,
            'This is my test text, if it works — great! If not, then I will be upset :)'
        )

    @requests_mock.mock()
    def test_directly_text(self, req_mock):
        req_mock.get(
            'http://test.ru',
            text=f'''<html><head><title>My test &#8212; title</title></head><body>
<div>This is my test text, if it works &#8212; great! If not, then I will be upset :)</div>
</body></html>''')

        parser = Parser('http://test.ru')
        self.assertEqual(
            parser.div_directly_text,
            'This is my test text, if it works — great! If not, then I will be upset :)'
        )

    @requests_mock.mock()
    def test_no_directly_text(self, req_mock):
        req_mock.get(
            'http://test.ru',
            text=f'''<html><head><title>My test &#8212; title</title></head><body>
<div><p>This is my test text, if it works &#8212; great! If not, then I will be upset :)</p></div>
</body></html>''')

        parser = Parser('http://test.ru')
        self.assertEqual(parser.div_directly_text, '')

    @requests_mock.mock()
    def test_part_directly_text(self, req_mock):
        req_mock.get(
            'http://test.ru',
            text=f'''<html><head><title>My test &#8212; title</title></head><body>
<div>This is my test text, if it works &#8212; great!<p>If not, then I will be upset :)</p></div>
</body></html>''')

        parser = Parser('http://test.ru')
        self.assertEqual(parser.div_directly_text, 'This is my test text, if it works — great!')

    @requests_mock.mock()
    def test_div_in_div_text(self, req_mock):
        req_mock.get(
            'http://test.ru',
            text=f'''<html><head><title>My test &#8212; title</title></head><body>
<div>This is my test text, if it works &#8212; great!<div>If not, then I will be upset :)</div></div>
</body></html>''')

        parser = Parser('http://test.ru')
        self.assertEqual(
            parser.div_directly_text,
            'This is my test text, if it works — great! If not, then I will be upset :)'
        )


class WordCounterCleanTextTest(unittest.TestCase):

    def test_ansi(self):
        punctuation = r"""!"#$%&'()*+,-./:;<=>?@[\]^_`{|}~"""
        whitespace = ' \t\n\r\v\f'

        self.assertEqual(
            WordCounter.clean_string(f"a{punctuation}b{whitespace}c"),
            'a                                b      c')

    # def test_ru(self):
    #     self.assertEqual(
    #         WordCounter.clean_string("привет"),
    #         "привет")


class WordGetMostCommonTest(unittest.TestCase):
    wc = None

    def setUp(self):
        self.wc = WordCounter()

    def test_ok(self):
        self.assertEqual(
            self.wc.get_most_common('privet man Privet girl'),
            [
                ('privet', 2),
                ('man', 1),
                ('girl', 1),
            ]
        )
