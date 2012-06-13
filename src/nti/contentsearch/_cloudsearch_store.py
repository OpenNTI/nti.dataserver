from __future__ import print_function, unicode_literals

import six
from zope import interface

from persistent import Persistent

from boto.cloudsearch import regions
from boto.cloudsearch import connect_to_region
from boto.cloudsearch.domain import Domain 
from boto.cloudsearch.search import SearchConnection
from boto.cloudsearch.document import DocumentServiceConnection

from nti.contentsearch.interfaces import ICloudSearchStore

import logging
logger = logging.getLogger( __name__ )
	
# -----------------------------------

AWS_CS_PARAMS = {'aws_access_key_id': (str, None),
				 'aws_secret_access_key': (str, None),
				 'is_secure': (bool, True),
				 'host': (str, 'cloudsearch.us-east-1.amazonaws.com'), 
				 'port': (int, None), 
				 'proxy': (str, None), 
				 'proxy_port': (int, None),
				 'proxy_user': (str, None),
				 'proxy_pass': (str, None) }

def find_aws_region(region):
	if region and isinstance(region, six.string_types):
		for r in regions():
			if r.name == region:
				region = r
				break
	# if no region grab first available
	if not region:
		region = regions()[0]
		
	return region
	
def get_search_service(domain=None, endpoint=None):
	return SearchConnection(domain=domain, endpoint=endpoint)

def get_document_service(domain=None, endpoint=None):
	return DocumentServiceConnection(domain=domain, endpoint=endpoint)

class CloudSearchStore(Persistent):
	interface.implements(ICloudSearchStore)
	
	def __init__(self, aws_access_key_id=None, aws_secret_access_key=None,
				 is_secure=True, host='cloudsearch.us-east-1.amazonaws.com', port=None, 
				 proxy=None, proxy_port=None, proxy_user=None, proxy_pass=None,
				 debug=0, https_connection_factory=None, path='/', region=None,
				 api_version=None, security_token=None):
		
		super(CloudSearchStore, self).__init__()
		kwargs = dict(locals())
		kwargs.pop('self' , None)
		kwargs.pop('region' , None)
		region = find_aws_region(region)
		self._v_connection = connect_to_region(region.name, **kwargs)
		self._set_aws_domains(self._v_connection)

	def _set_aws_domains(self, connection):
		self._v_domains = {}
		for d in self.get_aws_domains():
			self._v_domains[d['domain_name']] = Domain(connection, d)
					
	@property
	def connection(self):
		return self.get_connection()
	
	@property
	def ntisearch(self):
		return self.get_domain(domain_name='ntisearch')
	
	def get_connection(self):
		return self._v_connection
		
	def get_aws_domains(self):
		domains = self.connection.describe_domains()
		return domains
		
	def get_domain(self, domain_name):
		domain = self._v_domains.get(domain_name, None)
		return domain
	
if __name__ == '__main__':
	import os
	AWS_ACCESS_KEY_ID = os.environ.get('AWS_ACCESS_KEY_ID', 'AKIAJ42UUP2EUMCMCZIQ')
	AWS_SECRET_ACCESS_KEY = os.environ.get('AWS_SECRET_ACCESS_KEY', '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')
	cs = CloudSearchStore(AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY)
	
	from nti.contentsearch._cloudsearch_index import create_search_domain
	create_search_domain(cs.connection)
