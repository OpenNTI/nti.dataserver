from __future__ import print_function, unicode_literals

from cStringIO import StringIO

from pyramid.view import view_config

import zope.intid
from zope import component
from zope.catalog.interfaces import ICatalog

from nti.dataserver import authorization as nauth
from nti.dataserver.users import index as user_index

import logging
logger = logging.getLogger( __name__ )

def _get_userids(ent_catalog, ref_index='email'):
	ref_idx = ent_catalog.get('email', None)
	rev_index = getattr(ref_idx, '_rev_index', {})
	result = rev_index.keys() #
	return result
		
def _get_field_info(userid, ent_catalog, indexname):
	idx = ent_catalog.get(indexname, None)
	rev_index = getattr(idx, '_rev_index', {})
	result = rev_index.get(userid, u'')
	return result

def _get_user_info_extract():
	_ds_intid = component.getUtility( zope.intid.IIntIds )
	ent_catalog = component.getUtility(ICatalog, name=user_index.CATALOG_NAME)
	userids = _get_userids(ent_catalog)
	
	header = ['username', 'realname', 'alias', 'email']
	yield ','.join(header).encode('utf-8')
	
	for iid in userids:
		u = _ds_intid.queryObject(iid, None)
		if u is not None:
			alias = _get_field_info(iid, ent_catalog, 'alias')
			email = _get_field_info(iid, ent_catalog, 'email')
			realname = _get_field_info(iid, ent_catalog, 'realname')
			yield ','.join([u.username, realname, alias, email]).encode('utf-8')
				
@view_config(route_name='objects.generic.traversal',
			 name='user_info_extract',
			 request_method='GET',
			 permission=nauth.ACT_MODERATE)
def user_info_extract(request):
	
	# write to buffer
	sio = StringIO()
	for line in _get_user_info_extract():
		sio.write(line)
		sio.write("\n")
	sio.seek(0)
	
	response = request.response
	response.content_type = b'text/csv; charset=UTF-8'
	response.content_disposition = b'attachment; filename="report.csv"'
	response.body_file = sio
	return response
