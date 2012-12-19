from __future__ import print_function, unicode_literals

import os
import six
import time
import uuid
import gevent
import platform

import zope.intid
from zope import schema
from zope import interface
from zope import component

from zope.cachedescriptors.property import Lazy

import zope.intid.interfaces as zope_intid_interfaces

from zope.lifecycleevent import interfaces as lce_interfaces

import zc.lockfile

from whoosh import query
from whoosh import fields
from whoosh import analysis
from whoosh import ramindex
from whoosh import index as whoosh_index

from nti.dataserver.users import Entity
from nti.dataserver import interfaces as nti_interfaces
from nti.dataserver.users import interfaces as user_interfaces

from nti.contentsearch._search_query import is_phrase_search
from nti.contentsearch._search_query import is_prefix_search
from nti.contentsearch import interfaces as search_interfaces
from nti.contentsearch import _whoosh_indexstorage as w_idxstorage

import logging
logger = logging.getLogger( __name__ )

# interfaces

class IWhooshEntityIndex(search_interfaces.IEntityIndex):
	
	index = schema.Object(interface.Interface, title='Whoosh index')
		
	def writer():
		"""return an whoosh index writer"""
		
	def open():
		"""open the index"""
		
	def close():
		"""close the index"""

# whoosh index
		
def create_user_schema():
	analyzer = analysis.NgramWordAnalyzer(minsize=2, maxsize=50, at='start')
	schema = fields.Schema(	creator = fields.ID(stored=True, unique=False),
							intid = fields.ID(stored=True, unique=True),
							# stored= False
							alias = fields.TEXT(stored=False, analyzer=analyzer, phrase=False),
							email = fields.TEXT(stored=False, analyzer=analyzer, phrase=False),
							realname = fields.TEXT(stored=False, analyzer=analyzer, phrase=False),
							username = fields.TEXT(stored=False, analyzer=analyzer, phrase=False))
	return schema
	
def _getattr(obj, name, default=None):
	result = getattr(obj, name, default)
	result = unicode(result) if result else None
	return result
		
def get_entity_info(entity):
	_ds_intid = component.getUtility( zope.intid.IIntIds )
	username = unicode(entity.username)
	
	# get intid as unicode
	intid = _ds_intid.queryId(entity, None)
	intid = unicode(intid) if intid else None
	
	# parse entity profile
	alias = realname = email = creator = None
	if nti_interfaces.IUser.providedBy(entity):
		profile = user_interfaces.IUserProfile(entity)
		email = _getattr(profile, 'email', None)
		alias = _getattr(profile, 'alias', None)
		realname = _getattr(profile, 'realname', None)
	else:
		# get friendly names
		names = user_interfaces.IFriendlyNamed( entity, None )
		alias = _getattr(names, 'alias', None)
		realname = _getattr(names, 'realname', None)
	
		# set creator
		creator = _getattr(entity, 'creator', None) or _getattr(entity, 'Creator', None)
		creator = unicode(creator.username) if nti_interfaces.IEntity.providedBy(creator) else creator
		
	# data to be indexed
	return {u'intid': intid, u'username': username, u'creator':creator,
			u'alias':alias, u'email':email, u'realname':realname}
	
def get_index_writer(index):
	return w_idxstorage.get_index_writer(index, w_idxstorage.writer_ctor_args)

def writer_commit(writer, **kwargs):
	if isinstance(writer, ramindex.RamIndex):
		writer.commit()
	else:
		commit_args = kwargs or w_idxstorage.writer_commit_args
		writer.commit(**commit_args)
			
def populate_index(index):
	dataserver = component.getUtility( nti_interfaces.IDataserver )
	_users = nti_interfaces.IShardLayout( dataserver ).users_folder
	writer = get_index_writer(index)
	for user in _users.values():
		data = get_entity_info(user)
		writer.add_document(**data)
		friendsLists = getattr(user, "friendsLists", {})
		for fl in friendsLists.values():
			data = get_entity_info(fl)
			writer.add_document(**data)
	writer_commit(writer, optimize=True)

def _get_lock(path, indexname, timeout=60, delay=0.5):
	name = indexname + ".zlock"
	name = os.path.join(path, name)
	start_time = time.time()
	while True:
		try:
			lock = zc.lockfile.LockFile(name)
			return lock
		except zc.lockfile.LockError:
			if (time.time() - start_time) >= timeout:
				raise Exception("Timeout occured.")
			gevent.sleep(delay)
			
def create_index(inmemory=False):
	schema = create_user_schema()
	if inmemory:
		result = ramindex.RamIndex(schema)
	else:
		indexname = "userindex"
		dirname = w_idxstorage.prepare_index_directory()
		lock = _get_lock(dirname, indexname)
		try:
			if not whoosh_index.exists_in(dirname, indexname):
				result = whoosh_index.create_in(dirname, schema, indexname)
				populate_index(result)
			else:
				result = whoosh_index.open_dir(dirname, indexname)
		finally:
			lock.close()
	return result

def _create_or_update_entity(iwu_index, entity):
	result = entity is not None
	if result:
		data = get_entity_info(entity)
		writer = iwu_index.writer()
		if not iwu_index.exists(entity.username):
			writer.add_document(**data)
		else:
			writer.update_document(**data)
		writer_commit(writer)
	return result

@component.adapter(nti_interfaces.IEntity, lce_interfaces.IObjectCreatedEvent)
def on_entity_created( entity, event ):
	iwu_index = component.getUtility(IWhooshEntityIndex)
	if _create_or_update_entity(iwu_index, entity):
		iwu_index.on_entity_created(entity.username)
	
def _update_entity(iwu_index, entity):
	result = entity is not None
	if result:
		writer = iwu_index.writer()
		data = get_entity_info(entity)
		writer.update_document(**data)
		writer_commit(writer)
	return result
	
@component.adapter(nti_interfaces.IEntity, lce_interfaces.IObjectModifiedEvent)
def on_entity_modified( entity, event ):
	iwu_index = component.getUtility(IWhooshEntityIndex)
	if _update_entity(iwu_index, entity):
		iwu_index.on_entity_modified(entity.username)
	
def _delete_entity(iwu_index, intid):
	count = 0
	if intid is not None:
		writer = iwu_index.writer()
		count = writer.delete_by_term('intid', unicode(intid))
		writer_commit(writer)
	return count
	
@component.adapter(nti_interfaces.IEntity, zope_intid_interfaces.IntIdRemovedEvent)
def on_entity_deleted( entity, event ):	
	_ds_intid = component.getUtility( zope.intid.IIntIds )
	intid = _ds_intid.queryId(entity, None)
	iwu_index = component.getUtility(IWhooshEntityIndex)
	count = _delete_entity(iwu_index, intid)
	if count: iwu_index.on_entity_deleted(intid)

def _get_entity(entity):
	if isinstance(entity, six.string_types):
		result = Entity.get_entity(entity)
	elif isinstance(entity, (int,long)):
		_ds_intid = component.getUtility( zope.intid.IIntIds )
		result = _ds_intid.queryObject(entity)
	else:
		result = entity if nti_interfaces.IEntity.providedBy(entity) else None
	return result

@interface.implementer(IWhooshEntityIndex)
class _WhooshEntityIndex(object):

	_redis = None
	_pubsub = None
	_reader = None
	
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
		# process any changes
		self._reader = self._setup_listener()
		return index
	
	@Lazy
	def _uuid(self):
		if isinstance(self.index, ramindex.RamIndex):
			result = unicode(uuid.uuid4())
		else:
			result = unicode(platform.node())
		return result
	
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
			
	def parse(self, fieldname, term):
		if is_prefix_search(term):
			term = query.Wildcard(fieldname, term)
		elif is_phrase_search(term):
			rex = analysis.RegexTokenizer()
			words = [token.text.lower() for token in rex(unicode(term))]
			term = query.Phrase(fieldname, words)
		else:
			term = query.Term(fieldname, term)
		return term
	
	def query(self, search_term, remote_user=None, provided=None):
		result = []
		search_term = unicode(search_term)
		_ds_intid = component.getUtility( zope.intid.IIntIds )
		remote_user = remote_user.username if nti_interfaces.IEntity.providedBy(remote_user) else remote_user
		remote_user = remote_user.lower() if isinstance(remote_user, six.string_types) else None
		
		ors = [	self.parse('email', search_term),
				self.parse('alias', search_term),
				self.parse('realname', search_term),
				self.parse('username', search_term)]
		bq = query.Or(ors)
		with self.index.searcher() as s:
			hits = s.search(bq)
			for h in hits:
				intid = long(h['intid'])
				entity = _ds_intid.queryObject(intid, None)
				if entity is not None:
					if nti_interfaces.IFriendsList.providedBy(entity):
						creator = h['creator'] or u''
						entity = entity if creator.lower() == remote_user else None
						
				if entity and (provided is None or provided(entity)):
						result.append(entity)
	
		return result
		
	def on_entity_created(self, username):
		msg = repr((0, username, self._uuid))
		self._publish(msg)
		
	def on_entity_modified(self, username):
		msg = repr((1, username, self._uuid))
		self._publish(msg)
		
	def on_entity_deleted(self, userid):
		msg = repr((2, unicode(userid), self._uuid))
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
		op, userid, uid = eval(msg)
		if uid != self._uuid:
			if op in (0, 1):
				_sleep = 0.1
				_retries = 5
				def f():
					entity = _get_entity(userid)
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
				_delete_entity(self, userid)
