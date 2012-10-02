from __future__ import print_function, unicode_literals

import six

from persistent import Persistent

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
				 'region' : (str, None),
				 'path' : (str, '/'),
				 'region' : (str, None),
				 'api_version': (str, None),
				 'security_token' : (str, None),
				 'debug': (int, 0)}

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

def create_cloudsearch_store(**kwargs):
	params = dict(kwargs)
	search_domain = params.pop('search_domain' , 'ntisearch')
	return _CloudSearchStore(search_domain=search_domain, **params)
	
@interface.implementer(ICloudSearchStore)
class _CloudSearchStore(Persistent, object):
	
	def __init__(self, search_domain='ntisearch', **kwargs):
		self.search_domain = search_domain
		self.reset_aws_connection(**kwargs)

	@property
	def connection(self):
		return self._v_connection
	
	@property
	def domains(self):
		return self._v_domains
	
	def reset_aws_connection(self, **kwargs):
		if kwargs:
			illegal_args = [k for k in kwargs.keys() if not k in AWS_CS_PARAMS.keys()]
			if illegal_args:
				raise ValueError('Unknown parameters: %s' % ', '.join(illegal_args))
			
			self.region = kwargs.pop('region', None)
			for k, v in AWS_CS_PARAMS.items():
				v = kwargs.get(k, v)
				setattr(self, k, v)
		
		# find and aws region
		region = find_aws_region(self.region)
		self.region = region.name
		
		# set aws conn params
		params = dict(self.__dict__)
		params.pop('region', None)
		self._v_connection = connect_to_region(region.name, **params)
		self._set_aws_domains(self._v_connection)
		
	def __setstate__(self, d):
		self.__dict__ = d
		self.reset_aws_connection()
		
	def _set_aws_domains(self, connection):
		self._v_domains = {}
		for d in self.get_aws_domains():
			self._v_domains[d['domain_name']] = Domain(connection, d)
		
	def get_search_domain(self):
		return self.get_domain(domain_name=self.search_domain)
	
	def get_aws_domains(self):
		domains = self.connection.describe_domains()
		return domains
		
	def get_domain(self, domain_name):
		domain = self._v_domains.get(domain_name, None)
		return domain

