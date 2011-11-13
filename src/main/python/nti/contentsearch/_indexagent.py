import logging
logger = logging.getLogger( __name__ )

import gevent
from gevent.queue import Queue

from nti.dataserver.users import Change

class _IndexEvent(object):
	def __init__(self, creator, changeType, dataType, data):
		self.data = data
		self.creator = creator
		self.dataType = dataType
		self.changeType = changeType

	def __str__( self ):
		return '("%s", "%s", "%s",  %s)' % (self.creator, self.changeType, self.dataType,  self.data)

	def __repr__( self ):
		return '_IndexEvent(%s)' % self.__str__()

class IndexAgent(object):

	def __init__( self, indexmanager ):
		self._queue = Queue()
		self.indexmanager = indexmanager
		def _worker():
			while True:
				event = self._queue.get()
				if event:
					try:
						self._handle_event(event)
					except Exception:
						logger.exception("When handling event %s" % event )
				else:
					logger.info("Exit signal for index agent worker received")
					break

		self._agent = gevent.spawn( _worker )

	def _handle_event(self, event):
		"""
		Handle user content indexing events.
		"""

		data = event.data

		# TODO: These must be kept alive or they may never run!
		if event.changeType in (Change.CREATED, Change.SHARED):
			gevent.Greenlet.spawn(self.indexmanager.index_user_content,
									externalValue=data,
									username= event.creator,
									typeName=event.dataType)
		elif event.changeType == Change.MODIFIED:
			gevent.Greenlet.spawn(self.indexmanager.update_user_content,
									externalValue=data,
									username=event.creator,
									typeName=event.dataType)
		elif event.changeType == Change.DELETED:
			gevent.Greenlet.spawn(self.indexmanager.delete_user_content,
									externalValue=data,
									username=event.creator,
									typeName=event.dataType)


	def add_event( self, creator, changeType, dataType, data):
		event = _IndexEvent(creator, changeType, dataType, data)
		logger.debug("Index event %s received", event)
		self._queue.put_nowait( event )

	def close( self ):
		self._queue.put_nowait( None )
