#!/usr/bin/env python
"""
Constants and types for dealing with our unique IDs.
$Revision$
"""
from __future__ import print_function, unicode_literals

logger = __import__('logging').getLogger(__name__)

import datetime
import numbers
import time
import collections
import warnings

from zope import interface
from zope import component
from nti.ntiids import interfaces

# Well-known IDs
DATE = "2011-10"
#: When NTIIDs (usually of a particular type) are arranged into
#: a tree, or a forest of trees, this NTIID specifies the conceptual
#: root of the entire tree or forest.
ROOT = "tag:nextthought.com,2011-10:Root"

#: Used as an opaque identifier to a specific object. This will
#: not incorporate the object's name or path (when those concepts make
#: sense). Instead, it points to an object by identity.
TYPE_OID = 'OID'

#: Currenly unused
TYPE_UUID = 'UUID'

#: The intid type is not currently used. Instead,
#: intid is included as a part of the OID, preventing
#: access using a stale URL after an object is deleted
TYPE_INTID = 'INTID'

#: Used as an opaque identifier to refer to an object that was
#: once (weakly) referenced, but can no longer be found. Only the system
#: will ever generate these, and these are never valid to send
#: as input to the system; they can never be resolved.
#: In general, references to the same missing object will produce
#: the same missing NTIID; however, in some cases, it may be possible
#: for references to different missing objects to produce the same missing
#: NTIID. Context will usually make it clear if this has happened.
TYPE_MISSING = 'Missing'

#: Named entities are globally accessible knowing nothing
#: more than a simple string name. There should be a defined
#: subtype for each namespace and/or specific kind of
#: named entity
TYPE_NAMED_ENTITY = 'NamedEntity'

#: Subtype of named entities identifying a particular user account
TYPE_NAMED_ENTITY_USER = TYPE_NAMED_ENTITY + ':User'

#: Subtype of named entities identifying a particular community
TYPE_NAMED_ENTITY_COMMUNITY = TYPE_NAMED_ENTITY + ':Community'

TYPE_ROOM = 'MeetingRoom'
TYPE_MEETINGROOM = TYPE_ROOM

TYPE_HTML = 'HTML'
TYPE_QUIZ = 'Quiz'

TYPE_CLASS = 'Class'
TYPE_CLASS_SECTION = 'ClassSection'

TYPE_MEETINGROOM_GROUP = TYPE_ROOM + ':Group'
TYPE_MEETINGROOM_CLASS = TYPE_ROOM + ':Class'
TYPE_MEETINGROOM_SECT  = TYPE_ROOM + ':ClassSection'
#: Transcripts and TranscriptSummaries. Note that
#: they are not subtypes of a common type because they
#: contain quite different information and are used
#: in different ways.
TYPE_TRANSCRIPT = 'Transcript'
TYPE_TRANSCRIPT_SUMMARY = 'TranscriptSummary'


# Validation
_illegal_chars_ = r"/\";=?<>#%'{}|^[]" # Space is technically legal (?)


class InvalidNTIIDError(ValueError):
	pass

def validate_ntiid_string( string ):
	"""
	Ensures the string is a valid NTIID, else raises :class:`InvalidNTIIDError`.

	:return: The `string`.
	"""
	try:
		string = string if isinstance(string,unicode) else unicode(string, 'utf-8') # cannot decode unicode
	except (UnicodeDecodeError,TypeError):
		raise InvalidNTIIDError( "String contains non-utf-8 values " + repr(string) )

	if not string or not string.startswith( 'tag:nextthought.com,20' ):
		raise InvalidNTIIDError( 'Missing correct start value: ' + repr(string) )


	parts = string.split( ':', 2 ) # Split twice. Allow for : in the specific part
	if len( parts ) != 3:
		raise InvalidNTIIDError( 'Wrong number of colons: ' + string )

	if len( parts[2].split( '-' ) ) > 3:
		raise InvalidNTIIDError( 'Wrong number of dashes: ' + string )

	for char in _illegal_chars_:
		if char in string:
			raise InvalidNTIIDError( 'Contains illegal char ' + char )
	return string

validate_ntiid_string( ROOT )

def is_valid_ntiid_string( string ):
	try:
		validate_ntiid_string( string )
		return True
	except InvalidNTIIDError:
		return False

def is_ntiid_of_type( ntiid, nttype ):
	"""
	Check if the given ``ntiid`` is valid and of the given type
	(ignoring subtypes).

	:return: A True value if the ntiid is valid and has a type
		portion equivalent to the given nttype (i.e., ignoring
		subtypes).
	"""
	result = None
	the_type = get_type( ntiid )
	if nttype and (the_type or '').split( ':', 2 )[0] == nttype:
		result = the_type

	return result

def escape_provider( provider ):
	"""
	Makes a provider name safe for use in an NTIID by escaping
	characters not safe for a URL, such as _ and ' '. When
	comparing provider names with those that come fram an NTIID,
	you should always call this function.

	:return: The escaped provider, or the original value if it could not be escaped.

	"""
	try:
		return provider.replace( ' ', '_' ).replace( '-', '_' )
	except AttributeError:
		return provider

# TODO: A function to "escape" the local/specific part. Unfortunately, it's
# non-reversible so its less an escape and more a permutation.
# NOTE: While string.translate is tempting,
# it cannot be used because we allow the local parts to be Unicode and string.translate
# works on bytes

def make_ntiid( date=DATE, provider=None, nttype=None, specific=None, base=None ):
	"""
	Create a new NTIID.

	:param number date: A value from :meth:`time.time`. If missing (0 or `None`), today will be used.
		If a string, then that string should be a portion of an ISO format date, e.g., 2011-10.
	:param str provider: Optional provider name. We will sanitize it for our format.
	:param str nttype: Required NTIID type (if no base is given)
	:param str specific: Optional type-specific part.
	:param str base: If given, an NTIID string from which provider, nttype, specific, and date
		will be taken if they are not directly specified. If not a valid NTIID, will be ignored.

	:return: A new NTIID string formatted as of the given date.
	"""

	if base is not None and not is_valid_ntiid_string( base ):
		base = None

	if not nttype and not base:
		raise ValueError( 'Must supply type' )


	date_string = None
	if date is DATE and base is not None:
		date_string = get_parts(base).date
	elif isinstance( date, basestring ):
		date_string = date
	else:
		# Account for 0/None
		date_seconds = date if isinstance( date, numbers.Real ) and date > 0 else time.time()

		# Always get the date in UTC/GMT by converting the epoch into a GMT tuple.
		# Then turn into a date object since that's the easiest way to get ISO format.
		date = datetime.date( *time.gmtime(date_seconds)[0:3] )
		date_string = date.isoformat()

	if date_string is None:
		__traceback_info__ = date, base
		raise ValueError( "Unable to derive date string" )

	base_parts = get_parts( base )

	# TODO: This is not a reversible transformation. Who should do this?
	provider = escape_provider( str(provider) ) + '-' if provider else (base_parts.provider + '-' if base_parts.provider else '')
	specific = '-' + specific if specific else ('-' + base_parts.specific if base_parts.specific else '')
	nttype = nttype or base_parts.nttype

	__traceback_info__ =  (date_string, provider, nttype, specific )
	result = 'tag:nextthought.com,%s:%s%s%s' % __traceback_info__
	validate_ntiid_string( result )
	return result

NTIID = collections.namedtuple( 'NTIID', 'provider, nttype, specific,date' )
interface.classImplements( NTIID, interfaces.INTIID )

def _parse( ntiid ):
	"""
	:return: 4-tuple (provider, type, specific, date)
	"""
	try:
		validate_ntiid_string( ntiid )
		_, tag_part, our_parts = ntiid.split( ':', 2 )
		date = tag_part.split(',')[-1]
		our_parts = our_parts.split( '-' )
		if len( our_parts ) == 1:
			# only the type
			return NTIID(None, our_parts[0], None, date)
		if len( our_parts ) == 2:
			# type and type spec.
			return NTIID(None, our_parts[0], our_parts[1], date)
		return NTIID( our_parts[0], our_parts[1], our_parts[2], date )
	except ValueError:
		return NTIID(None,None,None,None)

def get_provider( ntiid ):
	"""
	:return: The string of the provider part of the ntiid if it could be parsed, else None.
	"""
	return _parse( ntiid ).provider

def get_type( ntiid ):
	"""
	:return: The string of the type part of the ntiid if it could be parsed, else None.
	"""
	return _parse( ntiid ).nttype

def get_specific( ntiid ):
	"""
	:return: The string of the type-specific part of the ntiid if it could be parsed, else None.
	"""
	return _parse( ntiid ).specific

def get_parts( ntiid ):
	"""
	:return: An NTIID named four-tuple (provider, type, type-specific, date) if the ntiid could be parsed,
		or named four-tuple of None.

	EOD
	"""
	return _parse( ntiid )

def find_object_with_ntiid(key, **kwargs):
	"""
	Attempts to find an object with the given NTIID. No security is implied; traversal is not
	necessarily used.

	:param string key: The NTIID to find.
	:param dict kwargs: Keyword arguments; this is to assist translation from legacy APIs and
		they are not currently used. If you send any, :mod:`warnings` will issue a warning.
	:return: The object found, or None if no object can be found or the ntiid passed is invalid.
	"""

	if not is_valid_ntiid_string( key ):
		logger.warn( "Invalid ntiid string %s", key )
		return None
	if kwargs:
		warnings.warn( "Function currently takes no kwargs" )

	ntiid = _parse( key )
	resolver = component.queryUtility( interfaces.INTIIDResolver, name=ntiid.nttype )
	if not resolver:
		logger.warn( "No ntiid resolver for '%s' in '%s'", ntiid.nttype, key )
		return None
	return resolver.resolve( key )
