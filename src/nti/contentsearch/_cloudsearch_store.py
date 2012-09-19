from __future__ import print_function, unicode_literals

import os
import six

from zope import interface

from boto.cloudsearch import regions
from boto.cloudsearch import connect_to_region
from boto.cloudsearch.domain import Domain 
from boto.cloudsearch.search import SearchConnection
from boto.cloudsearch.document import DocumentServiceConnection

from nti.contentsearch.interfaces import ICloudSearchStore

import logging
logger = logging.getLogger( __name__ )
	
AWS_CS_PARAMS = {'aws_access_key_id': (str, None),
				 'aws_secret_access_key': (str, None),
				 'is_secure': (bool, True),
				 'host': (str, 'cloudsearch.us-east-1.amazonaws.com'), 
				 'port': (int, None), 
				 'proxy': (str, None), 
				 'proxy_port': (int, None),
				 'proxy_user': (str, None),
				 'proxy_pass': (str, None),
				 'region' : (str, None) }

def find_aws_region(region):
	if isinstance(region, six.string_types):
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

def create_cloudsearch_store(aws_access_key_id=None, 
							 aws_secret_access_key=None,
							 search_domain='ntisearch',
				 			 is_secure=True,
				 			 host='cloudsearch.us-east-1.amazonaws.com', 
				 			 port=None, 
				 			 proxy=None,
				 			 proxy_port=None,
				 			 proxy_user=None,
				 			 proxy_pass=None,
				 			 debug=0,
				 			 https_connection_factory=None, 
				 			 path='/', 
				 			 region=None,
							 api_version=None,
							 security_token=None):
	
	kwargs = dict(locals())
	kwargs.pop('region' , None)
	kwargs.pop('search_domain' , None)
	return _CloudSearchStore(region=region, search_domain=search_domain, **kwargs)
	
@interface.implementer(ICloudSearchStore)
class _CloudSearchStore(object):
	
	def __init__(self, region=None, search_domain='ntisearch', **kwargs):
		super(_CloudSearchStore, self).__init__()
		region = find_aws_region(region)
		self._search_domain = search_domain
		self.connection = connect_to_region(region.name, **kwargs)
		self._set_aws_domains(self._v_connection)

	def _set_aws_domains(self, connection):
		self.domains = {}
		for d in self.get_aws_domains():
			self.domains[d['domain_name']] = Domain(connection, d)
		
	def get_search_domain(self):
		return self.get_domain(domain_name=self._search_domain)
	
	def get_aws_domains(self):
		domains = self.connection.describe_domains()
		return domains
		
	def get_domain(self, domain_name):
		domain = self.domains.get(domain_name, None)
		return domain
		
def _create_default_cloudsearch_store():
	params = {}
	for k, v in AWS_CS_PARAMS.items():
		func, df = v
		val = os.getenv(k, None)
		val = func(val) if val is not None else df
		params[k] = val
		
	if 	params.get('aws_access_key_id', None) and \
		params.get('aws_secret_access_key', None):
		return create_cloudsearch_store(**params)
	return None
