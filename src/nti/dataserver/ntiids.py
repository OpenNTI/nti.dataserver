"""
Constants and types for dealing with our unique IDs.
$Revision$
"""

from zope.deprecation import deprecated

from nti.ntiids.ntiids import TYPE_MEETINGROOM_CLASS
deprecated( "TYPE_MEETINGROOM_CLASS", "Prefer nti.ntiids.ntiids.TYPE_MEETINGROOM_CLASS" )
from nti.ntiids.ntiids import unicode_literals
deprecated( "unicode_literals", "Prefer nti.ntiids.ntiids.unicode_literals" )
from nti.ntiids.ntiids import InvalidNTIIDError
deprecated( "InvalidNTIIDError", "Prefer nti.ntiids.ntiids.InvalidNTIIDError" )
from nti.ntiids.ntiids import datetime
deprecated( "datetime", "Prefer nti.ntiids.ntiids.datetime" )
from nti.ntiids.ntiids import TYPE_MEETINGROOM_GROUP
deprecated( "TYPE_MEETINGROOM_GROUP", "Prefer nti.ntiids.ntiids.TYPE_MEETINGROOM_GROUP" )
from nti.ntiids.ntiids import TYPE_MEETINGROOM
deprecated( "TYPE_MEETINGROOM", "Prefer nti.ntiids.ntiids.TYPE_MEETINGROOM" )
from nti.ntiids.ntiids import numbers
deprecated( "numbers", "Prefer nti.ntiids.ntiids.numbers" )
from nti.ntiids.ntiids import TYPE_ROOM
deprecated( "TYPE_ROOM", "Prefer nti.ntiids.ntiids.TYPE_ROOM" )
from nti.ntiids.ntiids import DATE
deprecated( "DATE", "Prefer nti.ntiids.ntiids.DATE" )
from nti.ntiids.ntiids import TYPE_TRANSCRIPT_SUMMARY
deprecated( "TYPE_TRANSCRIPT_SUMMARY", "Prefer nti.ntiids.ntiids.TYPE_TRANSCRIPT_SUMMARY" )
from nti.ntiids.ntiids import validate_ntiid_string
deprecated( "validate_ntiid_string", "Prefer nti.ntiids.ntiids.validate_ntiid_string" )
from nti.ntiids.ntiids import TYPE_MEETINGROOM_SECT
deprecated( "TYPE_MEETINGROOM_SECT", "Prefer nti.ntiids.ntiids.TYPE_MEETINGROOM_SECT" )
from nti.ntiids.ntiids import TYPE_QUIZ
deprecated( "TYPE_QUIZ", "Prefer nti.ntiids.ntiids.TYPE_QUIZ" )
from nti.ntiids.ntiids import TYPE_OID
deprecated( "TYPE_OID", "Prefer nti.ntiids.ntiids.TYPE_OID" )
from nti.ntiids.ntiids import is_valid_ntiid_string
deprecated( "is_valid_ntiid_string", "Prefer nti.ntiids.ntiids.is_valid_ntiid_string" )
from nti.ntiids.ntiids import NTIID
deprecated( "NTIID", "Prefer nti.ntiids.ntiids.NTIID" )
from nti.ntiids.ntiids import collections
deprecated( "collections", "Prefer nti.ntiids.ntiids.collections" )
from nti.ntiids.ntiids import ROOT
deprecated( "ROOT", "Prefer nti.ntiids.ntiids.ROOT" )
from nti.ntiids.ntiids import get_provider
deprecated( "get_provider", "Prefer nti.ntiids.ntiids.get_provider" )
from nti.ntiids.ntiids import is_ntiid_of_type
deprecated( "is_ntiid_of_type", "Prefer nti.ntiids.ntiids.is_ntiid_of_type" )
from nti.ntiids.ntiids import escape_provider
deprecated( "escape_provider", "Prefer nti.ntiids.ntiids.escape_provider" )
from nti.ntiids.ntiids import TYPE_TRANSCRIPT
deprecated( "TYPE_TRANSCRIPT", "Prefer nti.ntiids.ntiids.TYPE_TRANSCRIPT" )
from nti.ntiids.ntiids import get_parts
deprecated( "get_parts", "Prefer nti.ntiids.ntiids.get_parts" )
from nti.ntiids.ntiids import print_function
deprecated( "print_function", "Prefer nti.ntiids.ntiids.print_function" )
from nti.ntiids.ntiids import TYPE_CLASS_SECTION
deprecated( "TYPE_CLASS_SECTION", "Prefer nti.ntiids.ntiids.TYPE_CLASS_SECTION" )
from nti.ntiids.ntiids import get_type
deprecated( "get_type", "Prefer nti.ntiids.ntiids.get_type" )
from nti.ntiids.ntiids import time
deprecated( "time", "Prefer nti.ntiids.ntiids.time" )
from nti.ntiids.ntiids import make_ntiid
deprecated( "make_ntiid", "Prefer nti.ntiids.ntiids.make_ntiid" )
from nti.ntiids.ntiids import TYPE_HTML
deprecated( "TYPE_HTML", "Prefer nti.ntiids.ntiids.TYPE_HTML" )
from nti.ntiids.ntiids import TYPE_CLASS
deprecated( "TYPE_CLASS", "Prefer nti.ntiids.ntiids.TYPE_CLASS" )


from nti.dataserver import interfaces as nti_interfaces
from nti.dataserver import authorization_acl as nacl
from nti.contentlibrary import interfaces as lib_interfaces
from zope import component

def find_object_with_ntiid(key, dataserver=None):
	"Attempts to find an object with the given NTIID. No security is implied."
	# TODO: Where should this live? Should we have registered adapters or something
	# for every type of NTIID? Probably yes
	if not is_valid_ntiid_string( key ):
		return None

	result = None
	dataserver = dataserver or component.queryUtility( nti_interfaces.IDataserver )
	if dataserver:
		if is_ntiid_of_type( key, TYPE_OID ):
			result = dataserver.get_by_oid( key, ignore_creator=True )
		else:
			provider = get_provider( key )
			# TODO: Knowledge about where providers are
			user = dataserver.root['users'].get( provider )
			if not user:
				# Is it a Provider?
				user = dataserver.root['providers'].get( provider )
			if user:
				result = user.get_by_ntiid( key )

	if result is None:
		# Nothing we could find specifically using a normal NTIID lookup.
		# Is it something in the library?
		# TODO: User-specific libraries
		library = component.queryUtility( lib_interfaces.IContentPackageLibrary )
		path = library.pathToNTIID( key ) if library else None
		if path:
			result = path[-1]
			result = nti_interfaces.ACLLocationProxy( result, result.__parent__, result.__name__, nacl.ACL( result ) )

	return result
