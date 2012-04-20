#!/usr/bin/env python
"""
Functions for externalizing OIDs.
$Revision$
"""


import logging
logger = logging.getLogger( __name__ )

import six


from zope.container._zope_container_contained import isProxy as _isContainedProxy
from zope.container._zope_container_contained import getProxiedObject as _getContainedProxiedObject


from zope.security.management import system_user

from nti.ntiids import ntiids


def toExternalOID( self, default=None ):
	""" For a persistent object, returns its persistent OID in a pasreable
	external format. If the object has not been saved, returns the default. """
	oid = default
	if hasattr( self, 'toExternalOID' ):
		oid = self.toExternalOID( )
	elif hasattr(self, '_p_oid') and getattr(self, '_p_oid'):
		# The object ID is defined to be 8 charecters long. It gets
		# padded with null chars to get to that length; we strip
		# those out. Finally, it probably has chars that
		# aren't legal it UTF or ASCII, so we go to hex and prepend
		# a flag, '0x'
		oid = getattr(self, '_p_oid').lstrip('\x00')
		oid = '0x' + oid.encode('hex')
		if hasattr(self, '_p_jar') and getattr(self, '_p_jar'):
			db_name = self._p_jar.db().database_name
			oid = oid + ':' + db_name.encode( 'hex' )
	return oid

def fromExternalOID( ext_oid ):
	"""
	:return: A tuple of OID, database name. Name may be empty.
	:param string ext_oid: As produced by :func:`toExternalOID`.
	"""
	oid_string, name_s = ext_oid.split( ':' ) if ':' in ext_oid else (ext_oid, "")
	# Translate the external format if needed
	if oid_string.startswith( '0x' ):
		oid_string = oid_string[2:].decode( 'hex' )
		name_s = name_s.decode( 'hex' )
	# Recall that oids are padded to 8 with \x00
	oid_string = oid_string.rjust( 8, '\x00' )
	return oid_string, name_s

_ext_ntiid_oid = object()
def to_external_ntiid_oid( contained, default_oid=_ext_ntiid_oid ):
	"""
	:return: An NTIID string utilizing the object's creator and persistent
		id.
	:param default_oid: The default value for the externalization of the OID.
		If this is None, and no external OID can be found (using :func:`toExternalOID`),
		then this function will return None.
	"""
	# We really want the external OID, but for those weird time we may not be saved we'll
	# allow the ID of the object, unless we are explicitly overridden
	if _isContainedProxy(contained):
		 contained = _getContainedProxiedObject( contained )
	oid = toExternalOID( contained, default=(default_oid if default_oid is not _ext_ntiid_oid else str(id(contained))) )
	if not oid:
		return None

	creator = getattr( contained, 'creator', system_user.id )
	return ntiids.make_ntiid( provider=(creator
										if isinstance( creator, six.string_types )
										else getattr( creator, 'username', system_user.id )),
								specific=oid,
								nttype=ntiids.TYPE_OID )
