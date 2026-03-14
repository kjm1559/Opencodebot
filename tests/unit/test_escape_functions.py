import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../src'))

from telegram_controller import escape_markdown_v2, escape_only_dots


def test_escape_markdown_v2_backslash_first():
    result = escape_markdown_v2('\\')
    assert result == '\\\\'
    assert escape_markdown_v2('a\\b') == 'a\\\\b'


def test_escape_markdown_v2_dot():
    assert escape_markdown_v2('.') == '\.'
    assert escape_markdown_v2('hello.world') == 'hello\.world'


def test_escape_markdown_v2_special_chars():
    chars = '_*$()~`>#+-=|{}'
    for c in chars:
        escaped = escape_markdown_v2(c)
        expected = '\\' + c
        assert escaped == expected, f'Char {c} not properly escaped'


def test_escape_markdown_v2_text():
    assert escape_markdown_v2('Hello World') == 'Hello World'
    assert escape_markdown_v2('') == ''


def test_escape_only_dots_ellipsis():
    assert escape_only_dots('truncated...') == 'truncated...'
    assert escape_only_dots('see more...') == 'see more...'


def test_escape_only_dots_single_dot():
    assert escape_only_dots('.') == '\.'
    assert escape_only_dots('a.b') == 'a\.b'


def test_escape_only_dots_file_with_ellipsis():
    result = escape_only_dots('file.txt and more...')
    assert '\.' in result
    assert '...' in result


def test_escape_only_dots_version_no_ellipsis():
    result = escape_only_dots('version 1.0.0 released')
    assert '...' not in result
    assert result.count('\.') == 3


def test_escape_only_dots_four_dots():
    result = escape_only_dots('test....')
    assert '...' in result
    assert '\.' in result


def test_escape_only_dots_special_chars_and_ellipsis():
    text = 'Check *_file*(path)...'
    result = escape_only_dots(text)
    assert '...' in result
    assert '\_' in result
    assert '\*' in result
    assert '\(' in result
    assert '\)' in result
