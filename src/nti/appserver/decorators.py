#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from . import MessageFactory as _

import nameparser
nameparser_config = getattr(nameparser, "config")

from zope import component
from zope import interface

from zope.component.hooks import getSite

from zope.i18n import translate
from zope.i18n.interfaces import IUserPreferredLanguages

from pyramid.threadlocal import get_current_request

from nti.appserver.link_providers import provide_links

from nti.appserver.interfaces import ILogonPong
from nti.appserver.interfaces import IModeratorDealtWithFlag

from nti.dataserver.interfaces import IUser
from nti.dataserver.interfaces import IContainerContext
from nti.dataserver.interfaces import IContextAnnotatable
from nti.dataserver.interfaces import IDeletedObjectPlaceholder

from nti.externalization.singleton import SingletonDecorator
from nti.externalization.interfaces import StandardExternalFields
from nti.externalization.interfaces import IExternalObjectDecorator
from nti.externalization.interfaces import IExternalMappingDecorator

def _nameparser_suffixes(config):
	result = set(getattr(config, 'SUFFIXES', ()))
	result.update(getattr(config, 'SUFFIX_ACRONYMS', ()))
	result.update(getattr(config, 'SUFFIX_NOT_ACRONYMS', ()))
	return result

@component.adapter(ILogonPong)
@interface.implementer(IExternalObjectDecorator)
class _SiteNameAdder(object):

	__metaclass__ = SingletonDecorator

	def decorateExternalObject(self, context, mapping):
		site = getSite()
		mapping['Site'] = site.__name__ if site is not None else None

@component.adapter(IContextAnnotatable)
@interface.implementer(IExternalMappingDecorator)
class _ContainerContextDecorator(object):
	"""
	For :class:`~.IContextAnnotatable` objects, decorate the
	result with the context_id.
	"""
	__metaclass__ = SingletonDecorator

	def decorateExternalMapping(self, context, mapping):
		container_context = IContainerContext(context, None)
		if container_context:
			mapping['ContainerContext'] = container_context.context_id

@component.adapter(IUser)
@interface.implementer(IExternalMappingDecorator)
class _EnglishFirstAndLastNameDecorator(object):
	"""
	If a user's first preferred language is English,
	then assume that they provided a first and last name and return that
	in the profile data.

	.. note::
		This is an incredibly Western and even US centric way of
		looking at things. The restriction to those that prefer
		English as their language is an attempt to limit the damage.
	"""

	__metaclass__ = SingletonDecorator

	
	def decorateExternalMapping(self, original, external):
		realname = external.get('realname')
		if not realname or '@' in realname or realname == external.get('ID'):
			return

		preflangs = IUserPreferredLanguages(original, None)
		if preflangs and 'en' == (preflangs.getPreferredLanguages() or (None,))[0]:
			# FIXME: Duplicated from users.user_profile
			# CFA: another suffix we see from certain financial quorters
			suffixes = _nameparser_suffixes(nameparser_config) | set(('cfa',))
			constants = nameparser_config.Constants(suffixes=suffixes)

			human_name = nameparser.HumanName(realname, constants=constants)
			first = human_name.first or human_name.last
			last = human_name.last or human_name.first

			if first:
				external['NonI18NFirstName'] = first
				external['NonI18NLastName'] = last

@component.adapter(IUser)
@interface.implementer(IExternalMappingDecorator)
class _AuthenticatedUserLinkAdder(object):
	"""
	When we decorate an user, if the user is ourself, we want to provide
	the same links that we would at logon time, mostly as a convenience
	to the client.
	"""

	__metaclass__ = SingletonDecorator

	def decorateExternalMapping(self, original, external):
		request = get_current_request()
		if not request:
			return

		userid = request.authenticated_userid
		if not userid or original.username != userid:
			return

		links = list(external.get(StandardExternalFields.LINKS, ()))
		links.extend(provide_links(original, request))

		external[StandardExternalFields.LINKS] = links

@component.adapter(IDeletedObjectPlaceholder)
@interface.implementer(IExternalObjectDecorator)
class _DeletedObjectPlaceholderDecorator(object):
	"""
	Replaces the title, description, and body of deleted objects with I18N strings.
	Cleans up some other data too that we don't want out.
	"""

	_message = _("This item has been deleted.")

	_moderator_message = _("This item has been deleted by the moderator.")

	__metaclass__ = SingletonDecorator

	def decorateExternalObject(self, original, external):
		request = get_current_request()
		deleted_by_moderator = IModeratorDealtWithFlag.providedBy(original)
		message = translate(self._moderator_message if deleted_by_moderator else self._message, context=request)

		if 'title' in external:
			external['title'] = message
		if 'description' in external:
			external['description'] = message
		if 'body' in external:
			external['body'] = [message]

		if 'tags' in external:
			external['tags'] = ()

		if StandardExternalFields.LINKS in external:
			# These may or may not be rendered at this point
			links = []
			for l in external[StandardExternalFields.LINKS]:
				try:
					rel = l['rel']
				except KeyError:
					rel = l.rel
				if rel in ('replies',):
					# We want to allow access to non-deleted children
					# XXX FIXME This should probably be a per-interface whitelist?
					links.append(l)
			external[StandardExternalFields.LINKS] = links

		# Note that we are still externalizing with the original class and mimetype values;
		# to do otherwise would almost certainly break client assumptions about the type of data the APIs return.
		# But we do expose secondary information about this state:
		external['Deleted'] = True
		if deleted_by_moderator:
			external['DeletedByModerator'] = True
