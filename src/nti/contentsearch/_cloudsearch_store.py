from __future__ import print_function, unicode_literals

import os

import zlib
import gevent

from zope import component
from zope import interface

from boto.cloudsearch import regions
from boto.cloudsearch import connect_to_region
from boto.cloudsearch.domain import Domain 
from boto.cloudsearch.search import SearchConnection
from boto.cloudsearch.document import DocumentServiceConnection

from nti.utils import transactions
from nti.dataserver import interfaces as nti_interfaces

from nti.contentsearch import interfaces as search_interfaces

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

SLEEP_WAIT_TIME = 15
EXPIRATION_TIME_IN_SECS = 60 * 2

@interface.implementer(search_interfaces.ICloudSearchStoreService)
class _CloudSearchStorageService(object):
	
	_redis = None
	_store = None
	
	def __init__( self ):
		self.index_listener = self._spawn_index_listener()

	def _get_redis( self ):
		if self._redis is None:
			self._redis = component.getUtility( nti_interfaces.IRedisClient )
		return self._redis
	
	def _get_store(self):
		if self._store is None:
			self._store = component.getUtility( search_interfaces.ICloudSearchStore  )
		return self._store
	
	# document service
	
	def add(self, _id, version, external):
		msg = repr(('add', _id, version, external))
		self._put_msg(msg)
	
	def delete(self, _id, version):
		msg = repr(('delete', _id, version, None))
		self._put_msg(msg)
	
	def commit(self):
		return None # no-op
	
	# search service
	
	def search(self, *args, **kwargs):
		service = self._get_store().get_search_service()
		result = service.search(*args, **kwargs)
		return result
	
	# redis
	
	def _get_index_msgs( self, queue_name='cloudsearch'):
		msgs = self._get_redis().pipeline().lrange( queue_name, 0, -1).execute()
		result = (eval(zlib.decompress(x)) for x in msgs[0]) if msgs else ()
		return result
	
	def _put_msg(self, msg):
		if msg is not None:
			msg = zlib.compress( msg )
			transactions.do(target=self, call=self._put_msg_to_redis, args=(msg,) )
	
	def _put_msg_to_redis( self, msg, queue_name='cloudsearch' ):
		self._get_redis().pipeline().rpush( queue_name, msg ).expire(queue_name, EXPIRATION_TIME_IN_SECS).execute()
	
	def _remove_from_redis(self, msgs, queue_name='cloudsearch'):
		self._get_redis().pipeline().ltrim( queue_name, len(msgs), -1).execute()
		
	def _spawn_index_listener(self):
		
		def read_index_msgs():
			while True:
						
				# wait for idx ops
				gevent.sleep(SLEEP_WAIT_TIME)
				
				try:
					msgs = self._get_index_msgs()
					if msgs:
						service = self._get_store().get_default_document_service()
						result = self.dispatch_messages_to_cs( msgs, service )
						if result.errors: # check for parsing validation errors
							s = '\n'.join(result.errors[:5]) # don't show all error
							logger.error(s) # log errors only 
							#TODO: save result / messages to a file
						
						# remove processed
						self._remove_from_redis(msgs)
						
				except Exception:
					logger.exception( "Failed to read and process index messages" )

		return gevent.spawn( read_index_msgs )
	
	@classmethod
	def dispatch_messages_to_cs(cls, msgs, service):
		for m in msgs:
			op, _id, version, external =  m
			if op == 'add':
				service.add(_id, version, external)
			elif op == 'delete':
				service.delete(_id, version)
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
