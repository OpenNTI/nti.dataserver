"""
Constants and types for dealing with our unique IDs.
$Revision$
"""

import datetime

# Well-known IDs
DATE = "2011-10"
ROOT = "tag:nextthought.com,2011-10:Root"

TYPE_ROOM = 'MeetingRoom'
TYPE_MEETINGROOM = 'MeetingRoom'

TYPE_HTML = 'HTML'
TYPE_TRANSCRIPT = 'Transcript'

TYPE_CLASS = 'Class'
TYPE_CLASS_SECTION = 'ClassSection'

TYPE_MEETINGROOM_GROUP = 'MeetingRoom:Group'
TYPE_MEETINGROOM_CLASS = 'MeetingRoom:Class'
TYPE_MEETINGROOM_SECT  = 'MeetingRoom:ClassSection'

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

def make_ntiid( date=DATE, provider=None, nttype=None, specific=None ):
	"""
	:return: A new NTIID formatted as of the given date.
	:param number date: A value from :meth:`time.time`. If missing (0 or `None`), today will be used.
		If a string, then that string should be a portion of an ISO format date, e.g., 2011-10.
	:param string provider: Optional provider name. We will sanitize it for our format.
	:param string nttype: Required NTIID type.
	:param string specific: Optional type-specific part.
	"""
	if not nttype: raise ValueError( 'Must supply type' )
	date_string = None
	if isinstance( date, basestring ):
		date_string = date
	else:
		date = datetime.date.fromtimestamp( date ) if date else datetime.date.today()
		date_string = date.isoformat()

	# TODO: This is not a reversible transformation. Who should do this?
	provider = provider.replace( ' ', '_' ).replace( '-', '_' ) + '-' if provider else ''
	specific = '-' + specific if specific else ''

	result = 'tag:nextthought.com,%s:%s%s%s' % (date_string, provider, nttype, specific )
	validate_ntiid_string( result )
	return result

def _parse( ntiid ):
	"""
	:return: 3-tuple (provider, type, specific)
	"""
	try:
		validate_ntiid_string( ntiid )
		our_parts = ntiid.split( ':', 2 )[-1].split( '-' )
		if len( our_parts ) == 1:
			# only the type
			return (None, our_parts[0], None)
		if len( our_parts ) == 2:
			# type and type spec.
			return (None, our_parts[0], our_parts[1])
		return our_parts
	except ValueError:
		return (None,None,None)

def get_provider( ntiid ):
	"""
	:return: The string of the provider part of the ntiid if it could be parsed, else None.
	"""
	return _parse( ntiid )[0]

def get_type( ntiid ):
	"""
	:return: The string of the type part of the ntiid if it could be parsed, else None.
	"""
	return _parse( ntiid )[1]

def get_parts( ntiid ):
	"""
	:return: A three-tuple (provider, type, type-specific) if the ntiid could be parsed,
		or three-tuple of None.

	EOD
	"""
	return _parse( ntiid )
