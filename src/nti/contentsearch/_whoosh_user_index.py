from __future__ import print_function, unicode_literals

import uuid
import gevent
from hashlib import md5

import zope.intid
from zope import schema
from zope import interface
from zope import component

from zope.cachedescriptors.property import Lazy

from zope.lifecycleevent.interfaces import IObjectCreatedEvent
from zope.lifecycleevent.interfaces import IObjectRemovedEvent
from zope.lifecycleevent.interfaces import IObjectModifiedEvent

from whoosh import fields
from whoosh import analysis
from whoosh import ramindex
from whoosh import index as whoosh_index

from nti.dataserver.users import Entity
from nti.dataserver import interfaces as nti_interfaces
from nti.dataserver.users import interfaces as user_interfaces

from nti.contentsearch import _whoosh_indexstorage as w_idxstorage

import logging
logger = logging.getLogger( __name__ )

def create_user_schema():
	analyzer = analysis.NgramWordAnalyzer(minsize=2, maxsize=50, at='start')
	schema = fields.Schema(	intid = fields.ID(stored=True, unique=True),
							username = fields.ID(stored=True, unique=True),
							alias = fields.TEXT(stored=False, analyzer=analyzer, phrase=False),
							email = fields.TEXT(stored=False, analyzer=analyzer, phrase=False),
							realname = fields.TEXT(stored=False, analyzer=analyzer, phrase=False),
							t_username = fields.TEXT(stored=False, analyzer=analyzer, phrase=False))
	return schema
		
def create_index(inmemory=True):
	schema = create_user_schema()
	if inmemory:
		result = ramindex.RamIndex(schema)
	else:
		m = md5()
		m.update(str(uuid.uuid4()))
		indexname = str(m.hexdigest())
		path = w_idxstorage.prepare_index_directory()
		result = whoosh_index.create_in(path, schema, indexname)
	return result
	
def get_index_writer(index):
	return w_idxstorage.get_index_writer(index, w_idxstorage.writer_ctor_args)

def writer_commit(writer):
	if isinstance(writer, ramindex.RamIndex):
		writer.commit()
	else:
		writer.commit(**w_idxstorage.writer_commit_args)

def populate_index(index):
	dataserver = component.getUtility( nti_interfaces.IDataserver )
	_users = nti_interfaces.IShardLayout( dataserver ).users_folder
	writer = get_index_writer(index)
	for user in _users.values():
		data = get_user_info(user)
		writer.add_document(**data)
	writer_commit(writer)

def get_user_info(user):
	_ds_intid = component.getUtility( zope.intid.IIntIds )
	username = user.username
	
	# get intid as unicode
	intid = _ds_intid.queryId(user, None)
	intid = unicode(intid) if intid else None
	
	# parse user profile
	alias = realname = email = u''
	if nti_interfaces.IUser.providedBy(user):
		profile = user_interfaces.IUserProfile(user)
		email = getattr(profile, 'email', None)
		alias = getattr(profile, 'alias', None)
		realname = getattr(profile, 'realname', None)
	
	# data to be indexed
	return {'intid': intid, 'username': username, 
			'alias':alias, 'email':email, 'realname':realname, 
			't_username': username}
	
def _create_or_update_entity(iwu_index, entity):
	result = entity is not None and not nti_interfaces.IFriendsList.providedBy(entity)
	if result:
		data = get_user_info(entity)
		writer = iwu_index.writer()
		if not iwu_index.exists(entity.username):
			writer.add_document(**data)
		else:
			writer.update_document(**data)
		writer_commit(writer)
	return result

@component.adapter(nti_interfaces.IEntity, IObjectCreatedEvent)
def on_entity_created( entity, event ):
	iwu_index = component.getUtility(IWhooshUserIndex)
	if _create_or_update_entity(iwu_index, entity):
		iwu_index.on_user_created(entity.username)
	
def _update_entity(iwu_index, entity):
	result = entity is not None and not nti_interfaces.IFriendsList.providedBy(entity)
	if result:
		writer = iwu_index.writer()
		data = get_user_info(entity)
		writer.update_document(**data)
		writer_commit(writer)
	return result
	
@component.adapter(nti_interfaces.IEntity, IObjectModifiedEvent)
def on_entity_modified( entity, event ):
	iwu_index = component.getUtility(IWhooshUserIndex)
	if _update_entity(iwu_index, entity):
		iwu_index.on_user_modified(entity.username)
	
def _delete_entity(iwu_index, entity):
	writer = iwu_index.writer()
	username = entity.username if nti_interfaces.IEntity.providedBy(entity) else entity
	count = writer.delete_by_term('username', username)
	writer_commit(writer)
	return count, username
	
@component.adapter(nti_interfaces.IEntity, IObjectRemovedEvent)
def on_entity_deleted( entity, event ):
	iwu_index = component.getUtility(IWhooshUserIndex)
	count, username = _delete_entity(iwu_index, entity)
	if count:
		iwu_index.on_user_deleted(username)

class IWhooshUserIndex(interface.Interface):
	
	index = schema.Object(interface.Interface, title='Whoosh index')
	
	def doc_count(self):
		"""return number of entities in the index"""
		
	def exists(username):
		"""check if the user name is in this index"""
		
	def writer():
		"""return an whoosh index writer"""
		
	def open():
		"""open the index"""
		
	def close():
		"""close the index"""
			
	def on_user_created(username):
		"""callback for user creation"""

	def on_user_modified(username):
		"""callback for user modification"""
		
	def on_user_deleted(self, username):
		"""callback for user deletion"""
	
@interface.implementer(IWhooshUserIndex)
class _WhooshUserIndex(object):

	_redis = None
	_pubsub = None
	_reader = None
	_uuid = unicode(uuid.uuid4())
	
	queue_name = u'nti/usersearch'
		
	def _get_redis(self):
		if self._redis is None:
			self._redis = component.getUtility( nti_interfaces.IRedisClient )
		return self._redis
	
	@Lazy
	def index(self):
		# listen to any changes
		self._setup_pubsub()
		# read data from db
		index = create_index()
		populate_index(index)
		# process any changes
		self._reader = self._setup_listener()
		return index
	
	def doc_count(self):
		with self.index.searcher() as s:
			return s.doc_count()
	
	def exists(self, username):
		with self.index.searcher() as s:
			doc_number = s.document_number(username=unicode(username))
			return doc_number is not None	
		
	def writer(self):
		return get_index_writer(self.index)

	def open(self):
		assert(self.index)
		return self
	
	def close(self):
		if getattr(self, '_reader', None):
			self._pubsub.unsubscribe(self.queue_name)
			self._reader.kill()
			
	# call backs to publish changes
	
	def on_user_created(self, username):
		msg = repr((0, username, self._uuid))
		self._publish(msg)
		
	def on_user_modified(self, username):
		msg = repr((1, username, self._uuid))
		self._publish(msg)
		
	def on_user_deleted(self, username):
		msg = repr((2, username, self._uuid))
		self._publish(msg)
					
	def _publish(self, msg):
		self._get_redis().publish(self.queue_name, msg)
		
	def _setup_pubsub(self):
		self._pubsub = self._get_redis().pubsub()
		self._pubsub.subscribe(self.queue_name)

	def _setup_listener( self ):
			
		def read_changes():
			while True:
				try:
					for msg in self._pubsub.listen():
						self._on_recv_change( msg )
				except Exception:
					logger.exception( 'error reading user redis changes' )
				
		reader = gevent.spawn( read_changes )
		return reader
	
	def _on_recv_change(self, msg):
		
		if msg.get('type', None) != 'message' or msg.get('channel', None) != self.queue_name:
			return
		
		msg = msg.get('data')
		op, username, uid = eval(msg)
		if uid != self._uuid:
			if op in (0, 1):
				_sleep = 0.1
				_retries = 5
				def f():
					entity = Entity.get_entity(username)
					result = entity is not None
					if result:
						_create_or_update_entity(self, entity)
					return result

				trxrunner = component.getUtility(nti_interfaces.IDataserverTransactionRunner)
				for _ in xrange(1, _retries+1):
					result = trxrunner(f)
					if not result:
						gevent.sleep(_sleep)
					else:
						break
			else:
				_delete_entity(self, username)
