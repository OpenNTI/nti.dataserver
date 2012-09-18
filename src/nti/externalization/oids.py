#!/usr/bin/env python
"""
Functions for externalizing OIDs.
$Revision$
"""
from __future__ import print_function, absolute_import, unicode_literals

import six

from zope.container._zope_container_contained import isProxy as _isContainedProxy
from zope.container._zope_container_contained import getProxiedObject as _getContainedProxiedObject
from zope.proxy import removeAllProxies

from zope.security.management import system_user

from ZODB.interfaces import IConnection

from nti.ntiids import ntiids


def toExternalOID( self, default=None, add_to_connection=False ):
	"""
	For a persistent object, returns its persistent OID in a pasreable
	external format. If the object has not been saved, and
	`add_to_connection` is `False` (the default) returns the `default`.

	:param add_to_connection: If the object is persistent but not yet added to a connection,
		setting this to true will attempt to add it to the nearest connection in
		its containment tree, thus letting it have an OID.
	"""
	oid = None
	if hasattr( self, 'toExternalOID' ):
		oid = self.toExternalOID( )
	elif hasattr(self, '_p_oid'):
		oid = getattr( self, '_p_oid' )
		jar = None
		if not oid and add_to_connection:
			try:
				jar = IConnection(self)
				jar.add( self )
				oid = getattr( self, '_p_oid' )
			except Exception as e:
				pass

		if oid:
			# The object ID is defined to be 8 charecters long. It gets
			# padded with null chars to get to that length; we strip
			# those out. Finally, it probably has chars that
			# aren't legal it UTF or ASCII, so we go to hex and prepend
			# a flag, '0x'
			oid = oid.lstrip(b'\x00')
			oid = '0x' + oid.encode('hex')
			jar = jar or getattr( self, '_p_jar', None )
			if jar:
				db_name = jar.db().database_name
				oid = oid + ':' + db_name.encode( 'hex' )
	return oid or default

to_external_oid = toExternalOID

def fromExternalOID( ext_oid ):
	"""
	:return: A tuple of OID, database name. Name may be empty.
	:param string ext_oid: As produced by :func:`toExternalOID`.
	"""
	# But, for legacy reasons, we accept directly the bytes given
	# in _p_oid, so we have to be careful with our literals here
	# to avoid Unicode[en|de]codeError
	__traceback_info__ = ext_oid
	oid_string, name_s = ext_oid.split( b':' ) if b':' in ext_oid else (ext_oid, b"")
	# Translate the external format if needed
	if oid_string.startswith( b'0x' ):
		oid_string = oid_string[2:].decode( 'hex' )
		name_s = name_s.decode( 'hex' )
	# Recall that oids are padded to 8 with \x00
	oid_string = oid_string.rjust( 8, b'\x00' )
	return oid_string, name_s

from_external_oid = fromExternalOID

_ext_ntiid_oid = object()
def to_external_ntiid_oid( contained, default_oid=_ext_ntiid_oid, add_to_connection=False ):
	"""
	:return: An NTIID string utilizing the object's creator and persistent
		id.
	:param default_oid: The default value for the externalization of the OID.
		If this is None, and no external OID can be found (using :func:`toExternalOID`),
		then this function will return None. (If not given, this method will return some non-persistent value)
	:param add_to_connection: If the object is persistent but not yet added to a connection,
		setting this to true will attempt to add it to the nearest connection in
		its containment tree, thus letting it have an OID.
	"""
	# We really want the external OID, but for those weird time we may not be saved we'll
	# allow the ID of the object, unless we are explicitly overridden
	# TODO: can we replace the contained proxy specific logic with the generic methods
	# from zope.proxy? zope.proxy.removeAllProxies?
	if _isContainedProxy(contained):
		contained = _getContainedProxiedObject( contained )
	contained = removeAllProxies( contained )
	oid = toExternalOID( contained,
						 default=(default_oid if default_oid is not _ext_ntiid_oid else str(id(contained))),
						 add_to_connection=add_to_connection )
	if not oid:
		return None

	creator = getattr( contained, 'creator', system_user.id )
	return ntiids.make_ntiid( provider=(creator
										if isinstance( creator, six.string_types )
										else getattr( creator, 'username', system_user.id )),
								specific=oid,
								nttype=ntiids.TYPE_OID )
