from django.utils.regex_helper import _lazy_re_compile


QUOTE_MAP = {i: "_%02X" % i for i in b'":/_#?;@&=+$,"[]<>%\n\\'}
UNQUOTE_MAP = {v: chr(k) for k, v in QUOTE_MAP.items()}
UNQUOTE_RE = _lazy_re_compile(
    "_(?:%s)" % "|".join([x[1:] for x in UNQUOTE_MAP]))


def quote(s):
    """
    Ensure that primary key values do not confuse the admin URLs by escaping
    any '/', '_' and ':' and similarly problematic characters.
    Similar to urllib.parse.quote(), except that the quoting is slightly
    different so that it doesn't get automatically unquoted by the web browser.
    """
    return s.translate(QUOTE_MAP) if isinstance(s, str) else s


def unquote(s):
    """Undo the effects of quote()."""
    return UNQUOTE_RE.sub(lambda m: UNQUOTE_MAP[m[0]], s)
