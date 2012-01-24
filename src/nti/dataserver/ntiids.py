"""
Constants and types for dealing with our unique IDs.
$Revision$
"""

import datetime
import numbers
import time
import collections

# Well-known IDs
DATE = "2011-10"
ROOT = "tag:nextthought.com,2011-10:Root"

TYPE_OID = 'OID'

TYPE_ROOM = 'MeetingRoom'
TYPE_MEETINGROOM = 'MeetingRoom'

TYPE_HTML = 'HTML'

TYPE_CLASS = 'Class'
TYPE_CLASS_SECTION = 'ClassSection'

TYPE_MEETINGROOM_GROUP = 'MeetingRoom:Group'
TYPE_MEETINGROOM_CLASS = 'MeetingRoom:Class'
TYPE_MEETINGROOM_SECT  = 'MeetingRoom:ClassSection'
# Transcripts and TranscriptSummaries. Note that
# they are not subtypes of a common type because they
# contain quite different information and are used
# in different ways.
TYPE_TRANSCRIPT = 'Transcript'
TYPE_TRANSCRIPT_SUMMARY = 'TranscriptSummary'


# Validation
_illegal_chars_ = r"/\";=?<>#%'{}|^[]"

def validate_ntiid_string( string ):
	"""
	Ensures the string is a valid NTIID, else raises ValueError.
	:return: The `string`.
	"""
	if not string or not string.startswith( 'tag:nextthought.com,20' ):
		raise ValueError( 'Missing start value: ' + str(string) )

	parts = string.split( ':', 2 ) # Split twice. Allow for : in the specific part
	if len( parts ) != 3:
		raise ValueError( 'Wrong number of colons: ' + string )

	if len( parts[2].split( '-' ) ) > 3:
		raise ValueError( 'Wrong number of dashes: ' + string )

	for char in _illegal_chars_:
		if char in string:
			raise ValueError( 'Contains illegal char' + char )
	return string

validate_ntiid_string( ROOT )

def is_valid_ntiid_string( string ):
	try:
		validate_ntiid_string( string )
		return True
	except ValueError:
		return False

def is_ntiid_of_type( ntiid, nttype ):
	"""
	:return: A True value if the ntiid is valid and has a type
		portion equivalent to the given nttype (i.e., ignoring
		subtypes).

	EOD
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

	EOD
	"""
	try:
		return provider.replace( ' ', '_' ).replace( '-', '_' )
	except AttributeError:
		return provider

def make_ntiid( date=DATE, provider=None, nttype=None, specific=None, base=None ):
	"""
	:return: A new NTIID formatted as of the given date.
	:param number date: A value from :meth:`time.time`. If missing (0 or `None`), today will be used.
		If a string, then that string should be a portion of an ISO format date, e.g., 2011-10.
	:param string provider: Optional provider name. We will sanitize it for our format.
	:param string nttype: Required NTIID type (if no base is given)
	:param string specific: Optional type-specific part.
	:param string base: If given, an NTIID string from which provider, nttype, specific, and date
		will be taken if they are not directly specified.
	"""
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

	base_parts = get_parts( base )

	# TODO: This is not a reversible transformation. Who should do this?
	provider = escape_provider( str(provider) ) + '-' if provider else (base_parts.provider + '-' if base_parts.provider else '')
	specific = '-' + specific if specific else ('-' + base_parts.specific if base_parts.specific else '')
	nttype = nttype or base_parts.nttype

	result = 'tag:nextthought.com,%s:%s%s%s' % (date_string, provider, nttype, specific )
	validate_ntiid_string( result )
	return result

NTIID = collections.namedtuple( 'NTIID', 'provider, nttype, specific,date' )

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

def get_parts( ntiid ):
	"""
	:return: An NTIID named three-tuple (provider, type, type-specific) if the ntiid could be parsed,
		or named three-tuple of None.

	EOD
	"""
	return _parse( ntiid )
