=====================
 Groups and Security
=====================

In general, security is handled through Pyramid's authorization
policy, using ACLs inherited through the lineage of objects. Some
details about this are documented in :mod:`nti.dataserver.authorization`.

Authentication and Groups
=========================

Pyramid's security is based on being able to get the "effective
principals" of the acting user. In essence, this is the closure of all
groups that the user belongs to (see
:class:`zope.security.interfaces.IGroupClosureAwarePrincipal` for a
similar concept).

Our implementation currently handles this through the use of
:class:`nti.dataserver.interfaces.IGroupMember` named adapters.
Details are contained in
:func:`nti.dataserver.authentication.effective_principals`.


.. automodule:: nti.dataserver.authentication
