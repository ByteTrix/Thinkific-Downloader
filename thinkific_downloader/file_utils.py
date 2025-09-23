import os
import re
import unicodedata

__all__ = ["filter_filename", "beautify_filename", "unicode_decode"]

# Ported from PHP version
RESERVED_PATTERN = re.compile(r"[<>:\"/\\|?*]|[\x00-\x1F]|[\x7F\xA0\xAD]|[#\[\]@!$&'()+,;=]|[{}^~`]")
MULTI_SPACE_PATTERN = re.compile(r" +")
MULTI_UNDERSCORE_PATTERN = re.compile(r"_+")
MULTI_DASH_PATTERN = re.compile(r"-+")
MULTI_DOT_DASH_PATTERN = re.compile(r"-*\.-*")
MULTI_DOTS_PATTERN = re.compile(r"\.{2,}")
UNICODE_ESCAPE_PATTERN = re.compile(r"\\u([0-9a-fA-F]{4})")


def filter_filename(filename: str, beautify: bool = True) -> str:
    # Replace reserved / problematic chars with '-'
    filename = RESERVED_PATTERN.sub('-', filename)
    # Avoid leading dot/dash
    filename = filename.lstrip('.-')
    if beautify:
        filename = beautify_filename(filename)
    # Truncate to 255 bytes (UTF-8 safe) respecting extension
    root, ext = os.path.splitext(filename)
    encoded_ext = ext.encode('utf-8')
    limit = 255 - (len(encoded_ext) if ext else 0)
    trimmed = _utf8_trim(root, limit)
    return f"{trimmed}{ext}" if ext else trimmed


def beautify_filename(filename: str) -> str:
    filename = MULTI_SPACE_PATTERN.sub('-', filename)
    filename = MULTI_UNDERSCORE_PATTERN.sub('-', filename)
    filename = MULTI_DASH_PATTERN.sub('-', filename)
    filename = MULTI_DOT_DASH_PATTERN.sub('.', filename)
    filename = MULTI_DOTS_PATTERN.sub('.', filename)
    # Lowercase
    filename = filename.lower()
    # Trim trailing dot/dash
    filename = filename.strip('.-')
    return filename


def _utf8_trim(text: str, byte_limit: int) -> str:
    encoded = text.encode('utf-8')
    if len(encoded) <= byte_limit:
        return text
    # Walk back to valid boundary
    truncated = encoded[:byte_limit]
    while True:
        try:
            return truncated.decode('utf-8')
        except UnicodeDecodeError:
            truncated = truncated[:-1]


def _replace_unicode_escape(match: re.Match) -> str:
    code_point = int(match.group(1), 16)
    return chr(code_point)


def unicode_decode(s: str) -> str:
    return UNICODE_ESCAPE_PATTERN.sub(_replace_unicode_escape, s)
