"""
Objects for classrooms.
"""

from zope import interface
from zope import component
from zope.component.factory import Factory
from zope.component.interfaces import IFactory

# pylint chokes on from . import ... stuff,
# which means it assumes old-style classes, which
# is annoying.
import ntiids
import enclosures
import datastructures
import contenttypes
import interfaces as nti_interfaces

from persistent import Persistent
from persistent.list import PersistentList

class ClassScript(contenttypes._UserContentRoot,datastructures.ExternalizableInstanceDict):
	"""
	Default implementation of :class:`IClassScript`
	"""
	interface.implements(nti_interfaces.IClassScript)

	def __init__( self, body=() ):
		"""
		:param body: An iterable of parts for the body.
		"""
		super(ClassScript,self).__init__()
		self.body = PersistentList( body )

	def updateFromExternalObject( self, parsed, dataserver=None ):
		super(ClassScript, self).updateFromExternalObject( parsed, dataserver=dataserver )
		if self._is_update_sharing_only( parsed ):
			return

		# TODO: Same issue with Note about resolving objects that may already
		# exist.
		assert all( [isinstance(x, (basestring,contenttypes.Canvas)) for x in self.body] )



class ClassInfo( datastructures.PersistentCreatedModDateTrackingObject,
				 datastructures.ExternalizableInstanceDict,
				 enclosures.SimpleEnclosureMixin ):

	interface.implements(nti_interfaces.IClassInfo,
						 nti_interfaces.ISimpleEnclosureContainer,
						 nti_interfaces.ILocation)

	def __init__( self ):
		super(ClassInfo,self).__init__()
		# All classes will have at least one session. The sessions
		# will vary per year.
		self.Sections = PersistentList()
		self.Description = ""
		#self.Provider = 'NTI' # Provider abbreviation, suitable for NTIID
		self.ID = None # Provider specific, e.g., CS2051
		self._v_parent = None

	@property
	def Provider(self):
		return self.creator

	@property
	def __name__(self):
		return self.ID


	def _get__parent__(self):
		if getattr( self, '_v_parent', None ):
			return self._v_parent
		class Root(object): # XXX
			__name__ = ''
			__parent__ = None
		class DS(object): # XXX
			__name__ = 'dataserver2'
			__parent__ = Root()
		class X(object): # XXX
			__name__ = 'providers'
			__parent__ = DS()
		class Y(object): # XXX
			__name__ = self.Provider
			__parent__ = X()
		return Y()

	def _set__parent__(self, nv ):
		self._v_parent = nv
	__parent__ = property( _get__parent__, _set__parent__ )

	def add_section( self, section ):
		section.__parent__ = self
		self.Sections.append( section )

	def __setstate__( self, state ):
		super(ClassInfo,self).__setstate__( state )
		for s in self.Sections:
			if not getattr( s, '__name__', None ):
				s.__name__ = s.ID
			if not getattr( s, '__parent__', None ):
				s.__parent__ = self

	@property
	def NTIID(self):
		return ntiids.make_ntiid( date=ntiids.DATE, provider=self.Provider,
								  nttype=ntiids.TYPE_CLASS, specific=self.ID )

nti_interfaces.IClassInfo.setTaggedValue( nti_interfaces.IHTC_NEW_FACTORY,
										  Factory( lambda extDict: ClassInfo(),
												   interfaces=(nti_interfaces.IClassInfo,)) )

class SectionInfo( datastructures.PersistentCreatedModDateTrackingObject,
				   datastructures.ExternalizableInstanceDict,
				   enclosures.SimpleEnclosureMixin ):

	interface.implements(nti_interfaces.IClassInfo,
						 nti_interfaces.ISimpleEnclosureContainer,
						 nti_interfaces.ILocation )

	def __init__( self ):
		super(SectionInfo,self).__init__()
		self.InstructorInfo = None # The instructor for this session.
		self.Sessions = PersistentList() # NTIIDs of all the chat sessions
		self.Provider = 'NTI' # Provider abbreviation, suitable for NTIID
		self.ID = None # Complete provider specific value, e.g., CS2051.001
		self.OpenDate = None # Date the section opens/starts
		self.CloseDate = None # Date the section completes/finishes
		self.Description = "" # Section specific description
		self.Enrolled = PersistentList() # List of usernames enrolled
		self.__name__ = self.ID
		self.__parent__ = None

	@property
	def NTIID(self):
		return ntiids.make_ntiid( date=ntiids.DATE, provider=self.Provider,
								  nttype=ntiids.TYPE_MEETINGROOM_SECT, specific=self.ID )


class InstructorInfo( Persistent,
					  datastructures.ExternalizableInstanceDict ):

	def __init__( self ):
		super(InstructorInfo,self).__init__()
		self.Instructors = PersistentList() # list of the names of the instructors

