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
			# To guarantee that the greenlets run, we must
			# keep a reference to them. We clear this when they finish,
			# or we are asked to die. We only start them after we have
			# a reference to them stored to avoid a race condition.
			jobs = []
			while True:
				event = self._queue.get()
				if event:
					try:
						job = self._handle_event(event)
						if job:
							jobs.append( job )
							job.link( jobs.remove )
							job.start()
					except Exception:
						logger.exception("When handling event %s" % event )
				else:
					logger.info("Exit signal for index agent worker received")
					for job in jobs:
						job.kill(block=True)
					del jobs[:]
					break

		self._agent = gevent.spawn( _worker )

	def _handle_event(self, event):
		"""
		Handle user content indexing events.
		:return: An unstarted greenlet.
		"""

		data = event.data

		if event.changeType in (Change.CREATED, Change.SHARED):
			job = gevent.Greenlet(self.indexmanager.index_user_content,
								  externalValue=data,
								  username= event.creator,
								  typeName=event.dataType)
		elif event.changeType == Change.MODIFIED:
			job = gevent.Greenlet(self.indexmanager.update_user_content,
								  externalValue=data,
								  username=event.creator,
								  typeName=event.dataType)
		elif event.changeType == Change.DELETED:
			job = gevent.Greenlet(self.indexmanager.delete_user_content,
								  externalValue=data,
								  username=event.creator,
								  typeName=event.dataType)
		else:
			job = None

		return job

	def _create_event(self, creator, changeType, dataType, data):
		return _IndexEvent(creator, changeType, dataType, data)

	def add_event( self, creator, changeType, dataType, data):
		event = self._create_event(creator, changeType, dataType, data)
		logger.debug("Index event %s received", event)
		self._queue.put_nowait( event )

	def close( self ):
		# Kill the background events and wait for them to
		# die, to help ensure we're in a nice consistent state.
		# If these things kept running after we're closed (and the indexmanager
		# is closed) they will get exceptions
		self._queue.put_nowait( None )
		self._agent.join()
