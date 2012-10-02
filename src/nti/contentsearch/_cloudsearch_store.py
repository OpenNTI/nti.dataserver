from __future__ import print_function, unicode_literals

import six

import zlib
import gevent
import transaction
from persistent import Persistent

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
	
@interface.implementer(search_interfaces.ICloudSearchStore)
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
		self._v_search_service = {}
		self._v_document_service = {}
		for d in self.get_aws_domains():
			domain_name = d['domain_name']
			domain = Domain(connection, d)
			self._v_domains[domain_name] = domain
			self._v_search_service[domain_name] = get_search_service(domain)
			self._v_document_service[domain_name] = get_document_service(domain)
		
	def get_default_domain(self):
		return self.get_domain(domain_name=self.search_domain)
	
	get_search_domain = get_default_domain
	
	def get_default_document_service(self):
		result = self._v_document_service.get(self.search_domain, None)
		return result
	
	def get_default_search_service(self):
		return self.get_domain(domain_name=self.search_domain)
	
	def get_aws_domains(self):
		domains = self.connection.describe_domains()
		return domains
		
	def get_domain(self, domain_name):
		result = self._v_domains.get(domain_name, None)
		return result

class CloudSearchStorageService(object):

	MAX_MESSAGES = 100
	SLEEP_WAIT_TIME = 30
	EXPIRATION_TIME_IN_SECS = 60 * 2
	
	_redis = None
	
	def __init__( self ):
		self.index_listener = self._spawn_index_listener()

	def _get_redis( self ):
		if self._redis is None:
			self._redis = component.getUtility( nti_interfaces.IRedisClient )
		return self._redis
	
	@property
	def store(self):
		return component.getUtility( search_interfaces.ICloudSearchStore )
	
	# document service
	
	def add(self, _id, version, external):
		msg = repr(('add', _id, version, external))
		self._put_msg(msg)
	
	def delete(self, _id, version):
		msg = repr(('delete', _id, version, None))
		self._put_msg(msg)
	
	def commit(self):
		return None # no-op
	
	# redis
	
	def _get_index_msgs( self, queue_name='cloudsearch'):
		result = None
		
		# get all messages 
		msgs, _ = self._redis.pipeline().lrange( queue_name, 0, self.MAX_MESSAGES).delete(  queue_name ).execute()
		if msgs:
#			def after_commit( success ):
#				if not success:
#					logger.warn( "Pushing messages back onto %s on abort", queue_name )
#					msgs.reverse()
#					# insert at the head of the list 
#					self._redis.lpush( queue_name, *msgs )
#			transaction.get().addAfterCommitHook( after_commit )
#		
			result = (eval(zlib.decompress(x)) for x in msgs)
		else:
			result = () 

		return result
	
	
	def _put_msg(self, msg):
		if msg is not None:
			msg = zlib.compress( msg )
			transactions.do(target=self, call=self._put_msg_to_redis, args=(msg,) )
	
	def _put_msg_to_redis( self, msg, queue_name='cloudsearch' ):
		self._get_redis().pipeline().rpush( queue_name, msg ).expire(queue_name, self.EXPIRATION_TIME_IN_SECS).execute()

	def _spawn_index_listener(self):
		
		def read_index_msgs():
			while True:
						
				# wait for idx ops
				gevent.sleep(self.SLEEP_WAIT_TIME)
				
				try:
					transaction.begin()
					msgs = self._get_index_msgs()
					if msgs:
						self._dispatch_messages_to_cs( *msgs )
					transaction.commit()
				except Exception:
					logger.exception( "Failed to read and process index messages" )

		return gevent.spawn( read_index_msgs )
	
	def _dispatch_messages_to_cs(self, msgs):
		service = self.store.get_default_document_service()
		for m in msgs:
			op, _id, version, external =  m
			if op == 'add':
				service.add(_id, version, external)
			elif op == 'delete':
				service.delete(_id, version)
		result = service.commit()
		if result.errors: # check for parsing validation errors
			s = '\n'.join(result.errors[:5]) # don't show all error
			logger.error(s) # log errors only 
			#TODO: save result / messages to a file
		
