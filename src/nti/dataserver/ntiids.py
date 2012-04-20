"""
Constants and types for dealing with our unique IDs.
$Revision$
"""

import zope.deprecation
zope.deprecation.moved( 'nti.ntiids.ntiids' )


from nti.dataserver import interfaces as nti_interfaces
from nti.dataserver import authorization_acl as nacl
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
		library = component.queryUtility( nti_interfaces.ILibrary )
		path = library.pathToNTIID( key ) if library else None
		if path:
			result = path[-1]
			result = nti_interfaces.ACLLocationProxy( result, result.__parent__, result.__name__, nacl.ACL( result ) )

	return result
