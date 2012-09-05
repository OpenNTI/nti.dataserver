#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Views relating to coppa administration.


$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
logger = __import__('logging').getLogger('__name__')


import pyramid.httpexceptions  as hexc
from pyramid.view import view_config

from nti.appserver import _table_utils
from nti.appserver import site_policies

from nti.dataserver import interfaces as nti_interfaces
from nti.dataserver.users import interfaces as user_interfaces
from z3c.table import table

from nti.dataserver import authorization as nauth


from nti.appserver.z3c_zpt import PyramidZopeRequestProxy

def _coppa_table( request ):
	content = ()
	site_policy, _ = site_policies.find_site_policy( request )
	if site_policy and getattr(site_policy, 'IF_WOUT_AGREEMENT', None):
		dataserver = request.registry.getUtility( nti_interfaces.IDataserver )
		users_folder = nti_interfaces.IShardLayout( dataserver ).users_folder
		content = [x for x in users_folder.values() if site_policy.IF_WOUT_AGREEMENT.providedBy( x )]
	the_table = CoppaAdminTable( content,
								 PyramidZopeRequestProxy( request ) )
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
			for item in the_table.selectedItems:
				site_policy.upgrade_user( item )

	# Else, no action.
	# Redisplay the page with a get request to avoid the "re-send this POST?" problem
	get_path = request.path  + (('?' + request.query_string) if request.query_string else '')
	return hexc.HTTPFound(location=get_path)


class CoppaAdminTable(table.SequenceTable):
	pass

class RealnameColumn(_table_utils.AdaptingGetAttrColumn):
	header = 'Name'
	attrName = 'realname'
	adapt_to = user_interfaces.IFriendlyNamed
