from __future__ import print_function, unicode_literals

import os

from zope import component
from zope import interface

from boto.cloudsearch import regions
from boto.cloudsearch.domain import Domain
from boto.cloudsearch import connect_to_region 
from boto.cloudsearch.search import SearchConnection
from boto.cloudsearch.document import DocumentServiceConnection

from nti.contentsearch import interfaces as search_interfaces
from nti.contentsearch._redis_indexstore import _RedisStorageService

import logging
logger = logging.getLogger( __name__ )

def find_aws_region(region_name):
	result = None
	_regions = regions()
	if region_name:
		for r in _regions:
			if r.name == region_name:
				result = r
				break
	# if no region grab first available
	if result is None:
		result = _regions[0]
		
	return result
	
def get_search_service(domain=None, endpoint=None):
	return SearchConnection(domain=domain, endpoint=endpoint)

def get_document_service(domain=None, endpoint=None):
	return DocumentServiceConnection(domain=domain, endpoint=endpoint)
	
@interface.implementer(search_interfaces.ICloudSearchStore)
class _CloudSearchStore(object):
	
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
		region = kwargs.pop('region_name', None)
		region = find_aws_region(region)
		self._v_connection = connect_to_region(region.name, **kwargs)
		self._set_aws_domains(self._v_connection)
		
	def _set_aws_domains(self, connection):
		self._v_domains = {}
		for d in self.get_aws_domains():
			domain_name = d['domain_name']
			domain = Domain(connection, d)
			self._v_domains[domain_name] = domain
		
	def get_aws_domains(self):
		domains = self.connection.describe_domains()
		return domains
		
	def get_domain(self, domain_name=None):
		domain_name = domain_name or self.search_domain
		result = self._v_domains.get(domain_name, None)
		return result
	
	def get_document_service(self, domain_name=None):
		domain = self.get_domain(domain_name)
		result = get_document_service(domain) if domain else None
		return result
	
	def get_search_service(self, domain_name=None):
		domain = self.get_domain(domain_name)
		result = get_search_service(domain) if domain else None
		return result


@interface.implementer(search_interfaces.ICloudSearchStoreService)
class _CloudSearchStorageService(_RedisStorageService):
	
	_store = None
	
	def _get_store(self):
		if self._store is None:
			self._store = component.getUtility( search_interfaces.ICloudSearchStore  )
		return self._store
	
	@property
	def default_queue_name(self):
		return self.queue_name
		
	# search/index service
	
	def add(self, _id, version, external):
		msg = repr(('add', _id, version, external))
		self._put_msg(msg)
	
	update = add
	
	def delete(self, _id, version):
		msg = repr(('delete', _id, version, None))
		self._put_msg(msg)
		
	def commit(self):
		return None
	
	def search(self, *args, **kwargs):
		service = self._get_store().get_search_service()
		result = service.search(*args, **kwargs)
		return result
	
	# redis
	
	def process_messages(self, msgs):
		service = self._get_store().get_document_service()
		for m in msgs:
			op, oid, version, external =  m
			if op in ('add', 'update'):
				service.add(oid, version, external)
			elif op == 'delete':
				service.delete(oid, version)
		result = service.commit()
		return result
	
@interface.implementer(search_interfaces.ICloudSearchStore)
def _create_cloudsearch_store():
	aws_access_key_id = os.environ.get('aws_access_key_id', None)
	aws_secret_access_key = os.environ.get('aws_secret_access_key', None)
	if aws_access_key_id and aws_secret_access_key:
		result = _CloudSearchStore(	aws_access_key_id=aws_access_key_id,
									aws_secret_access_key=aws_secret_access_key)
	else:
		result = _CloudSearchStore()
	return result
