#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Views relating to coppa administration.


$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
logger = __import__('logging').getLogger(__name__)
from . import MessageFactory as _

from zope import component
from zc.intid import IIntIds

import pyramid.httpexceptions  as hexc
from pyramid.view import view_config

from nti.appserver import _table_utils
from nti.appserver import site_policies

from nti.dataserver import interfaces as nti_interfaces
from nti.dataserver.users import interfaces as user_interfaces

from z3c.table import table
from z3c.table import column

from nti.dataserver import authorization as nauth

from nti.appserver.z3c_zpt import PyramidZopeRequestProxy

def _coppa_table( request ):
	content = ()
	site_policy, _pol_name = site_policies.find_site_policy( request )
	if site_policy and getattr(site_policy, 'IF_WOUT_AGREEMENT', None):
		logger.debug( "Found site policy %s/%s; looking for users that are %s",
					  site_policy, _pol_name, site_policy.IF_WOUT_AGREEMENT )
		dataserver = request.registry.getUtility( nti_interfaces.IDataserver )
		users_folder = nti_interfaces.IShardLayout( dataserver ).users_folder
		content = [x for x in users_folder.values() if site_policy.IF_WOUT_AGREEMENT.providedBy( x )]
	else:
		logger.warn( "No site policy (%s/%s) or policy (%s) does not specify users to find",
					 site_policy, _pol_name, site_policy )
	the_table = CoppaAdminTable( content,
								 PyramidZopeRequestProxy( request ) )
	the_table.__parent__ = request.context
	the_table.__name__ = 'coppa_admin.html'
	the_table.startBatchingAt = 50
	the_table.update()
	return the_table

@view_config( route_name='objects.generic.traversal',
			  renderer='templates/coppa_user_approval.pt',
			  permission=nauth.ACT_COPPA_ADMIN,
			  request_method='GET',
			  name='coppa_admin')
def coppa_admin( request ):
	return _coppa_table( request )

@view_config( route_name='objects.generic.traversal',
			  renderer='rest',
			  permission=nauth.ACT_COPPA_ADMIN,
			  request_method='POST',
			  name='coppa_admin')
def moderation_admin_post( request ):
	the_table = _coppa_table( request )

	if 'subFormTable.buttons.approve' in request.POST:
		site_policy, policy_name = site_policies.find_site_policy( request )
		if not site_policy: #pragma: no cover
			logger.warn( "Unable to find site policy in %s", policy_name )
		else:
			email_col = the_table.columnByName['coppa-admin-contactemail']
			for item in the_table.selectedItems:
				contact_email = email_col.getItemValue( item ) or ''
				contact_email = contact_email.strip()
				if not contact_email:
					# TODO: Need to put this is the flash queue or something so it can be displayed on the page
					logger.warn( "No contact email provided for %s, not upgrading", item )
					continue
				logger.info( "Upgrading user %s to COPPA approved with contact email %s", item, contact_email )
				user_interfaces.IUserProfile(item).contact_email = contact_email
				site_policy.upgrade_user( item )

	# Else, no action.
	# Redisplay the page with a get request to avoid the "re-send this POST?" problem
	get_path = request.path  + (('?' + request.query_string) if request.query_string else '')
	return hexc.HTTPFound(location=get_path)


class CoppaAdminTable(table.SequenceTable):
	pass

class RealnameColumn(_table_utils.AdaptingGetAttrColumn):
	header = _('Name')
	attrName = 'realname'
	adapt_to = user_interfaces.IFriendlyNamed

class ContactEmailColumn(column.Column):
	"""
	Column to accept the new contact email address.
	"""

	header = _('Contact Email')
	weight = 15

	def __init__( self, context, request, tbl ):
		super(ContactEmailColumn,self).__init__( context, request, tbl )
		self._values = {}

	def getSortKey(self, item):
		return self.getItemValue( item )

	def getItemKey(self, item):
	 	return '%s-contactemail-%s' % (self.id, component.getUtility(IIntIds).getId(item))

	def getItemValue(self, item):
		return self._values.get( self.getItemKey(item ) ) or getattr( user_interfaces.IUserProfile(item), 'contact_email', None )

	def update(self):
		for item in self.table.values:
			key = self.getItemKey( item )
			val = self.request.get( key )
			if val:
				self._values[key] = val

	def renderCell(self, item):
		selected = u''
#		if item in self.selectedItems:
#			selected = 'checked="checked"'
		return u'<input type="email" class="%s" name="%s" value="%s" %s />' \
			% ('contact-email-widget', self.getItemKey(item), self.getItemValue(item) or '',
			selected)
