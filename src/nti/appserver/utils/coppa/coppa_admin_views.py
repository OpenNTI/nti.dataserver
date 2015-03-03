#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Views relating to coppa administration.

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import zope.formlib.form

from zope import interface
from zope import component
from zope.publisher.interfaces.browser import IBrowserRequest

from zc.intid import IIntIds

from z3c.table import table
from z3c.table import column
from z3c.table import batch

from pyramid.view import view_config
from pyramid import httpexceptions  as hexc

from nti.appserver import _table_utils
from nti.appserver import MessageFactory as _
from nti.appserver.policies import site_policies

from nti.dataserver import authorization as nauth
from nti.dataserver import interfaces as nti_interfaces
from nti.dataserver.users import interfaces as user_interfaces

from nti.schema.interfaces import find_most_derived_interface

_USER_FILTER_PARAM = 'usersearch'

def _coppa_table_and_site( request, force_table=False ):
	content = ()
	iface = None
	site_policy, _pol_name = site_policies.find_site_policy( request )
	if site_policy and getattr(site_policy, 'IF_WOUT_AGREEMENT', None):
		iface = site_policy.IF_WOUT_AGREEMENT
		logger.debug( "Found site policy %s/%s; looking for users that are %s",
					  site_policy, _pol_name, iface )
		dataserver = request.registry.getUtility( nti_interfaces.IDataserver )
		users_folder = nti_interfaces.IShardLayout( dataserver ).users_folder

		# Poor mans user search. We match on the username, which is the most
		# common use case here
		if _USER_FILTER_PARAM in request.params:
			usersearch = request.params[_USER_FILTER_PARAM]
			usersearch = usersearch.lower()
			values = (users_folder[x] for x in users_folder.keys() if usersearch in x.lower())
		else:
			values = users_folder.values()

		content = [x for x in values if iface.providedBy( x )]

	else:
		logger.warn( "No site policy (%s/%s) or policy (%s) does not specify users to find",
					 site_policy, _pol_name, site_policy )

	if site_policy or force_table:
		logger.debug("Found %d users for site policy %s that are %s",
					 len(content), _pol_name, iface)
		# NOTE: We could implement an IValues adapter to be able
		# to be lazy about the content sequence yet still batch/page/etc
		the_table = CoppaAdminTable( content,
									 IBrowserRequest( request ) )
		the_table.__parent__ = request.context
		the_table.__name__ = 'coppa_admin.html'
		the_table.startBatchingAt = 50
		the_table.update()
	else:
		the_table = None

	return the_table, site_policy, _pol_name

def _coppa_table( request ):
	return _coppa_table_and_site( request, force_table=True )[0]

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
	the_table, site_policy, policy_name = _coppa_table_and_site( request )

	if not site_policy: #pragma: no cover
		msg = "Unable to find site policy in %s" % policy_name
		logger.warn( msg )
		request.session.flash( msg, queue='warn' )
	elif 'subFormTable.buttons.approve' not in request.POST:
		msg = "POST request to coppa_admin without Approve button?"
		logger.warn( msg )
		request.session.flash( msg, queue='warn' )
	elif not the_table.selectedItems:
		msg = "No selected items in coppa_admin POST"
		logger.warn( msg )
		request.session.flash( msg, queue='warn' )
	else:
		email_col = the_table.columnByName['coppa-admin-contactemail']
		for item in the_table.selectedItems:
			contact_email = email_col.getItemValue( item ) or ''
			contact_email = contact_email.strip()
			if not contact_email:
				msg = "No contact email provided for %s, not upgrading" % item
				logger.warn( msg )
				request.session.flash( msg, queue='warn' )
				continue

			msg = "Upgrading user %s to COPPA approved with contact email %s" % ( item, contact_email )
			logger.info( msg )
			request.session.flash( msg, queue='info' )
			user_interfaces.IUserProfile(item).contact_email = contact_email
			site_policy.upgrade_user( item )

	# Else, no action.
	# Redisplay the page with a get request to avoid the "re-send this POST?" problem
	get_path = request.path  + (('?' + request.query_string) if request.query_string else '')
	return hexc.HTTPFound(location=get_path)


class CoppaAdminTable(table.SequenceTable):
	batchProviderName = 'coppa-admin-batch'

class _CoppaAdminBatchProvider(batch.BatchProvider):
	"Batch provider that includes the name of our usersearch parameter in the batch links"
	_request_args = [_USER_FILTER_PARAM] + batch.BatchProvider._request_args

class RealnameColumn(_table_utils.AdaptingGetAttrColumn):
	header = _('Name')
	attrName = 'realname'
	adapt_to = user_interfaces.IFriendlyNamed
	weight = 3

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
		return 	self._values.get(self.getItemKey(item)) or \
				getattr(user_interfaces.IUserProfile(item), 'contact_email', None)

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


### Administrative profile review and editing
# TODO: This will eventually move somewhere else

@view_config( route_name='objects.generic.traversal',
			  renderer='templates/account_profile_view.pt',
			  permission=nauth.ACT_COPPA_ADMIN,
			  request_method='GET',
			  context=nti_interfaces.IUser,
			  name='account_profile_view')
def account_profile_view( request ):
	context = request.context
	profile_iface = user_interfaces.IUserProfileSchemaProvider( context ).getSchema()
	profile = profile_iface( context )
	profile_schema = find_most_derived_interface(profile,
												 profile_iface,
												 possibilities=interface.providedBy(profile))

	fields = zope.formlib.form.Fields( profile_schema, render_context=True )
	fields = fields.omit(*[k for k, v in profile_schema.namesAndDescriptions(all=True) \
						 if v.queryTaggedValue(user_interfaces.TAG_HIDDEN_IN_UI) ])

	widgets = zope.formlib.form.setUpWidgets( fields, 'form', context,
											  IBrowserRequest( request ),
											  # Without this, it needs request.form
											  ignore_request=True )

	return widgets
