#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""

Based on original Java code:
    java/src/com/google/i18n/phonenumbers/PhoneNumberMatch.java
    java/src/com/google/i18n/phonenumbers/PhoneNumberMatcher.java    
    Copyright (C) 2011 The Libphonenumber Authors

.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

logger = __import__('logging').getLogger(__name__)

import re

#: The ITU says the maximum length should be 15, but we have found longer
#: numbers in Germany.
_MAX_LENGTH_FOR_NSN = 17

#: The maximum length of the country calling code.
_MAX_LENGTH_COUNTRY_CODE = 3

#: Regular expression of acceptable punctuation found in phone numbers, used to find numbers in
#: text and to decide what is a viable phone number. This excludes diallable characters.
#: This consists of dash characters, white space characters, full stops, slashes, square brackets,
#: parentheses and tildes. It also includes the letter 'x' as that is found as a placeholder for
#: carrier information in some phone numbers. Full-width variants are also present.
_VALID_PUNCTUATION = (
    u"-x\u2010-\u2015\u2212\u30FC\uFF0D-\uFF0F "
    u"\u00A0\u00AD\u200B\u2060\u3000()\uFF08\uFF09\uFF3B\uFF3D.\\[\\]/~\u2053\u223C\uFF5E"
)


def _limit(lower, upper):
    """
    Returns a regular expression quantifier with an upper and lower limit.
    """
    if lower < 0 or upper <= 0 or upper < lower:
        raise Exception("Illegal argument to _limit")
    return u"{%d,%d}" % (lower, upper)

#: Build the MATCHING_BRACKETS and PATTERN regular expression patterns. The
#: building blocks below exist to make the patterns more easily understood.
_OPENING_PARENS = u"(\\[\uFF08\uFF3B"
_CLOSING_PARENS = u")\\]\uFF09\uFF3D"
_NON_PARENS = u"[^" + _OPENING_PARENS + _CLOSING_PARENS + u"]"

#: Limit on the number of pairs of brackets in a phone number.
_BRACKET_PAIR_LIMIT = _limit(0, 3)

#: Pattern to check that brackets match. Opening brackets should be closed
#: within a phone number.  This also checks that there is something inside the
#: brackets. Having no brackets at all is also fine.
#
#: An opening bracket at the beginning may not be closed, but subsequent ones
#: should be.  It's also possible that the leading bracket was dropped, so we
#: shouldn't be surprised if we see a closing bracket first. We limit the sets
#: of brackets in a phone number to four.
_MATCHING_BRACKETS = re.compile(u"(?:[" + _OPENING_PARENS + u"])?" + u"(?:" + _NON_PARENS + u"+" +
                                u"[" + _CLOSING_PARENS + u"])?" +
                                _NON_PARENS + u"+" +
                                u"(?:[" + _OPENING_PARENS + u"]" + _NON_PARENS +
                                u"+[" + _CLOSING_PARENS + u"])" + _BRACKET_PAIR_LIMIT +
                                _NON_PARENS + u"*")

#: Limit on the number of consecutive punctuation characters.
_PUNCTUATION_LIMIT = _limit(0, 4)

#" The maximum number of digits allowed in a digit-separated block. As we allow
#: all digits in a single block, set high enough to accommodate the entire
#: national number and the international country code.
_DIGIT_BLOCK_LIMIT = (_MAX_LENGTH_FOR_NSN + _MAX_LENGTH_COUNTRY_CODE)

#: A punctuation sequence allowing white space.
_PUNCTUATION = u"[" + _VALID_PUNCTUATION + u"]" + _PUNCTUATION_LIMIT

_PLUS_CHARS = u"+\uFF0B"

_DIGITS = u'\\d'

_RFC3966_EXTN_PREFIX = u";ext="

#: Pattern to capture digits used in an extension. Places a maximum length of
#: "7" for an extension.
_CAPTURING_EXTN_DIGITS = u"(" + _DIGITS + u"{1,7})"

#: One-character symbols that can be used to indicate an extension.
_SINGLE_EXTN_SYMBOLS_FOR_MATCHING = u"x\uFF58#\uFF03~\uFF5E"

_SINGLE_EXTN_SYMBOLS_FOR_PARSING = u",;" + _SINGLE_EXTN_SYMBOLS_FOR_MATCHING


def _create_extn_pattern(single_extn_symbols):
    """
    Helper initialiser method to create the regular-expression pattern to
    match extensions, allowing the one-char extension symbols provided by
    single_extn_symbols."""
    # There are three regular expressions here. The first covers RFC 3966
    # format, where the extension is added using ";ext=". The second more
    # generic one starts with optional white space and ends with an optional
    # full stop (.), followed by zero or more spaces/tabs/commas and then the
    # numbers themselves. The other one covers the special case of American
    # numbers where the extension is written with a hash at the end, such as
    # "- 503#".  Note that the only capturing groups should be around the
    # digits that you want to capture as part of the extension, or else
    # parsing will fail!  Canonical-equivalence doesn't seem to be an option
    # with Android java, so we allow two options for representing the accented
    # o - the character itself, and one in the unicode decomposed form with
    # the combining acute accent.
    return (_RFC3966_EXTN_PREFIX + _CAPTURING_EXTN_DIGITS + u"|" +
            u"[ \u00A0\\t,]*(?:e?xt(?:ensi(?:o\u0301?|\u00F3))?n?|" +
            u"\uFF45?\uFF58\uFF54\uFF4E?|" +
            u"[" + single_extn_symbols + u"]|int|anexo|\uFF49\uFF4E\uFF54)" +
            u"[:\\.\uFF0E]?[ \u00A0\\t,-]*" + _CAPTURING_EXTN_DIGITS + u"#?|" +
            u"[- ]+(" + _DIGITS + u"{1,5})#")


_EXTN_PATTERNS_FOR_PARSING = _create_extn_pattern(
    _SINGLE_EXTN_SYMBOLS_FOR_PARSING)

#: Flags to use when compiling regular expressions for phone numbers.
_REGEX_FLAGS = re.UNICODE | re.IGNORECASE

#: The minimum and maximum length of the national significant number.
_MIN_LENGTH_FOR_NSN = 2

_STAR_SIGN = u'*'

#: Simple ASCII digits map used to populate _ALPHA_PHONE_MAPPINGS and
#: _ALL_PLUS_NUMBER_GROUPING_SYMBOLS.
_ASCII_DIGITS_MAP = {u"0": u"0", u"1": u"1",
                     u"2": u"2", u"3": u"3",
                     u"4": u"4", u"5": u"5",
                     u"6": u"6", u"7": u"7",
                     u"8": u"8", u"9": u"9"}

#: Only upper-case variants of alpha characters are stored.
_ALPHA_MAPPINGS = {u"A": u"2",
                   u"B": u"2",
                   u"C": u"2",
                   u"D": u"3",
                   u"E": u"3",
                   u"F": u"3",
                   u"G": u"4",
                   u"H": u"4",
                   u"I": u"4",
                   u"J": u"5",
                   u"K": u"5",
                   u"L": u"5",
                   u"M": u"6",
                   u"N": u"6",
                   u"O": u"6",
                   u"P": u"7",
                   u"Q": u"7",
                   u"R": u"7",
                   u"S": u"7",
                   u"T": u"8",
                   u"U": u"8",
                   u"V": u"8",
                   u"W": u"9",
                   u"X": u"9",
                   u"Y": u"9",
                   u"Z": u"9", }

#: For performance reasons, amalgamate both into one map.
_ALPHA_PHONE_MAPPINGS = dict(_ALPHA_MAPPINGS, **_ASCII_DIGITS_MAP)

U_EMPTY_STRING = u""

#: We accept alpha characters in phone numbers, ASCII only, upper and lower
#: case.
_VALID_ALPHA = (U_EMPTY_STRING.join(_ALPHA_MAPPINGS.keys()) +
                U_EMPTY_STRING.join([_k.lower() for _k in _ALPHA_MAPPINGS.keys()]))


_VALID_PHONE_NUMBER = (
    _DIGITS + (u"{%d}" % _MIN_LENGTH_FOR_NSN) + u"|" +
    u"[" + _PLUS_CHARS + u"]*(?:[" + _VALID_PUNCTUATION + _STAR_SIGN + u"]*" + _DIGITS + u"){3,}[" +
    _VALID_PUNCTUATION + _STAR_SIGN + _VALID_ALPHA + _DIGITS + u"]*"
)

#: We append optionally the extension pattern to the end here, as a valid phone
#: number may have an extension prefix appended, followed by 1 or more digits.
_VALID_PHONE_NUMBER_PATTERN = re.compile(_VALID_PHONE_NUMBER + u"(?:" +
                                         _EXTN_PATTERNS_FOR_PARSING +
                                         u")?", _REGEX_FLAGS)


def fullmatch(pattern, string):
    """
    Try to apply the pattern at the start of the string, returning a match
    object if the whole string matches, or None if no match was found.
    """
    # Build a version of the pattern with a non-capturing group around it.
    # This is needed to get m.end() to correctly report the size of the
    # matched expression (as per the final doctest above).
    grouped_pattern = re.compile(r"^(?:%s)$" % pattern.pattern, pattern.flags)
    m = grouped_pattern.match(string)
    if m and m.end() < len(string):
        # Incomplete match (which should never happen because of the $ at the
        # end of the regexp), treat as failure.
        m = None  # pragma no cover
    return m


def is_viable_phone_number(number):
    """
    Checks to see if a string could possibly be a phone number.
    At the moment, checks to see that the string begins with at least 2
    digits, ignoring any punctuation commonly found in phone numbers.  This
    method does not require the number to be normalized in advance - but does
    assume that leading non-number symbols have been removed, such as by the
    method _extract_possible_number.
    Arguments:
    number -- string to be checked for viability as a phone number
    Returns True if the number could be a phone number of some sort, otherwise
    False
    """
    if len(number) < _MIN_LENGTH_FOR_NSN:
        return False
    match = fullmatch(_VALID_PHONE_NUMBER_PATTERN, number)
    return bool(match)
