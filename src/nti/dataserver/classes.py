#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Objects for classrooms.

$Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)


import itertools

from zope import interface
from zope.component.factory import Factory
from zope.container.btree import BTreeContainer
from zope.container.interfaces import INameChooser
import BTrees

# pylint chokes on from . import ... stuff,
# which means it assumes old-style classes, which
# is annoying.
from nti.ntiids import ntiids
from nti.externalization.datastructures import ExternalizableInstanceDict
from nti.externalization.externalization import toExternalObject

from nti.dataserver import enclosures
from nti.dataserver import datastructures
from nti.dataserver import contenttypes
#from nti.dataserver.contenttypes.note import BodyFieldProperty
from nti.dataserver import mimetype

from nti.dataserver import interfaces as nti_interfaces
from zope.annotation import interfaces as an_interfaces

from nti.dataserver import links

from nti.utils.property import alias

from persistent import Persistent
from persistent.list import PersistentList

class ClassScript(contenttypes._UserContentRoot,ExternalizableInstanceDict):
	"""
	Default implementation of :class:`IClassScript`
	"""
	interface.implements(nti_interfaces.IClassScript,nti_interfaces.IZContained)

	__parent__ = None
	__name__ = None

	def __init__( self, body=() ):
		"""
		:param body: An iterable of parts for the body.
		"""
		super(ClassScript,self).__init__()
		self.body = PersistentList( body ) # TODO: Convert to contenttypes.note.BodyFieldProperty

	def updateFromExternalObject( self, parsed, *args, **kwargs ):
		super(ClassScript, self).updateFromExternalObject( parsed, *args, **kwargs )

		# TODO: Same issue with Note about resolving objects that may already
		# exist. Part of that goes away with BodyFieldProperty. Part of that
		# needs its same _ext_resolve implementation
		assert all( [isinstance(x, (basestring,contenttypes.Canvas)) for x in self.body] )

def _add_accepts( collection, ext_collection, accepts=() ):
	if accepts is not None:
		ext_collection['accepts'] = [mimetype.nti_mimetype_from_object( x ) for x in accepts]
		if nti_interfaces.ISimpleEnclosureContainer.providedBy( collection ):
			ext_collection['accepts'].append('image/*')
			ext_collection['accepts'].append('application/pdf')
			ext_collection['accepts'].append(ClassScript.mime_type)
	return ext_collection

def _add_container_iface( obj, iface ):
	if not iface.providedBy( obj ):
		interface.alsoProvides( obj, iface )
		obj.container_name = obj.__name__

@interface.implementer(nti_interfaces.IClassInfo,
					   nti_interfaces.ISimpleEnclosureContainer,
					   nti_interfaces.IZContained,
					   an_interfaces.IAttributeAnnotatable)
class ClassInfo( datastructures.PersistentCreatedModDateTrackingObject,
				 ExternalizableInstanceDict,
				 enclosures.SimpleEnclosureMixin,
				 datastructures.ContainedMixin):

	__metaclass__ = mimetype.ModeledContentTypeAwareRegistryMetaclass

	__external_can_create__ = True

	def __init__( self, ID=None ):
		# All classes will have at least one section. The sections
		# will vary per year.
		# The section list is a IContainer
		# so it fires events
		self._sections = BTreeContainer()

		# This container is kept unnamed so that URLs come out right
		# FIXME: This is not really right. We want this to be named for a clean
		# separation
		self._sections.__name__ = ''
		self._sections.__parent__ = self
		_add_container_iface( self._sections, nti_interfaces.ISectionInfoContainer )

		# The sections container must be in place before we init super

		super(ClassInfo,self).__init__()

		self.Description = ""
		#self.Provider = 'NTI' # Provider abbreviation, suitable for NTIID
		self.ID = ID # Provider specific, e.g., CS2051
		#self._v_parent = None

	@property
	def Sections(self):
		return self._sections.values()

	def _get_Provider(self):
		return self.creator
	def _set_Provider(self, np):
		self.creator = np
	Provider = property(_get_Provider,_set_Provider)

	# We own the sections, and their provider/creator
	# is /our/ provider/creator. Make sure they stay in sync
	# (During the process of creation from external sources,
	# creator can get changed several times, possibly after this
	# object is off the stack and updateFromExternalObject is no longer
	# able to do anything).
	def _get_creator(self):
		return self.__dict__['creator']
	def _set_creator(self,nc):
		self.__dict__['creator'] = nc
		for section in self.Sections:
			section.Provider = nc
	creator = property(_get_creator,_set_creator)


	__name__ = alias('ID')
	id = alias('ID')
	__parent__ = None

	def add_section( self, section ):
		# TODO: Historical and time based (reuse of IDs)? We're requiring
		# IDs to be unique (unless we use a name chooser).
		# at least make that explicit
		assert section.ID not in self._sections
		if self.ID:
			section.containerId = self.NTIID
		self._sections[section.ID] = section

	def __getitem__( self, key ):
		return self._sections[key]

	def __len__( self ):
		return len( self._sections )
	def __delitem__(self, key):
		raise TypeError()
	def __setitem__( self, key ):
		raise TypeError()
	def __nonzero__( self ):
		return True


	def __setstate__( self, state ):
		if 'Sections' in state:
			self._sections = BTreeContainer()
			self._sections.__name__ = ''
			self._sections.__parent__ = self
			_add_container_iface( self._sections, nti_interfaces.ISectionInfoContainer )
			for s in state['Sections']:
				self._sections[s.ID] = s
				if self.ID:
					s.containerId = self.NTIID
			del state['Sections']
			state['_sections'] = self._sections
		super(ClassInfo,self).__setstate__( state )
		_add_container_iface( self._sections, nti_interfaces.ISectionInfoContainer )
		if self._sections.__name__ == 'Sections':
			self._sections.__name__ = ''

	@property
	def NTIID(self):
		# If we are inserted into a container without having been given an ID,
		# one is generated for us, and we cannot use it correctly in our NTIID
		try:
			if ntiids.is_valid_ntiid_string( self.ID ):
				return ntiids.make_ntiid( date=ntiids.DATE, provider=self.Provider,
										  nttype=ntiids.TYPE_CLASS,
										  base=self.ID )

			return ntiids.make_ntiid( date=ntiids.DATE, provider=self.Provider,
									  nttype=ntiids.TYPE_CLASS, specific=self.ID )
		except ntiids.InvalidNTIIDError:
			logger.exception( "ClassInfo created with invalid name %s", self.ID )
			return None

	def toExternalDictionary( self, mergeFrom=None ):
		result = super(ClassInfo,self).toExternalDictionary( mergeFrom=mergeFrom )
		# TODO: Add better support for externalizing OOBTreeItems (IReadSequence)
		result['Sections'] = toExternalObject( list(self.Sections) )

		#### XXX
		# Temporary hacks
		return _add_accepts( self, result )

	def updateFromExternalObject( self, parsed, *args, **kwargs ):
		super(ClassInfo,self).updateFromExternalObject( parsed, *args, **kwargs )
		# Anything they didn't send must go
		sent_sids = []
		updated = False
		if 'Sections' in parsed:
			for ext_sect in parsed['Sections']:
				# The DS doesn't really update the correct nested objects in place, it creates new ones
				# So we must manage the update ourself so that relationships don't break
				if isinstance(ext_sect,SectionInfo): ext_sect = toExternalObject( ext_sect )
				# Choose a name if one not provided. We assume this
				# must be an addition.
				sid = ext_sect.get( 'ID' )
				if not sid:
					sid = INameChooser(self._sections).chooseName( self.ID + '.1', ext_sect )

				sent_sids.append( sid )
				sect = self[sid] if sid in self._sections else SectionInfo( ID=sid )
				updated |= sect.updateFromExternalObject( ext_sect )
				sect.Provider = self.Provider
				if sid not in self._sections: self.add_section( sect )

		# Notice this happens after we choose any names, to try to avoid
		# dups
		del_sids = [existing_id for existing_id in self._sections if existing_id not in sent_sids]
		for k in del_sids:
			updated = True
			del self._sections[k]
		return updated



nti_interfaces.IClassInfo.setTaggedValue( nti_interfaces.IHTC_NEW_FACTORY,
										  Factory( lambda extDict: ClassInfo(),
												   interfaces=(nti_interfaces.IClassInfo,)) )

@interface.implementer(nti_interfaces.ISectionInfo,
					   nti_interfaces.ISimpleEnclosureContainer,
					   nti_interfaces.IZContained,
					   nti_interfaces.IUsernameIterable,
					   an_interfaces.IAttributeAnnotatable)
class SectionInfo( datastructures.PersistentCreatedModDateTrackingObject,
				   ExternalizableInstanceDict,
				   enclosures.SimpleEnclosureMixin ):

	__metaclass__ = mimetype.ModeledContentTypeAwareRegistryMetaclass

	__external_can_create__ = True
	# Let IDs come in, ClassInfo depends on it
	_excluded_in_ivars_ = ExternalizableInstanceDict._excluded_in_ivars_ - set( ('ID',) )

	containerId = None

	def __init__( self, ID=None ):
		super(SectionInfo,self).__init__()
		self.InstructorInfo = InstructorInfo() # The instructor for this session.
		self.Sessions = PersistentList() # NTIIDs of all the chat sessions
		self.Provider = 'NTI' # Provider abbreviation, suitable for NTIID
		self.ID = ID # Complete provider specific value, e.g., CS2051.001
		self.OpenDate = None # Date the section opens/starts
		self.CloseDate = None # Date the section completes/finishes
		self.Description = "" # Section specific description
		# NOTE: The below is wrong:
		# ...The enrolled list is a IContainer
		# ...so it fires events so students can know when they are enrolled.
		# It was an abuse of containers, leading to ContainedProxies wrapped around strings(!)
		# and gratuitious intids. This needs rethought. New objects use plain maps.
		self._enrolled = BTrees.family64.OO.BTree() #containers.EventlessBTreeContainer()
#		self._enrolled.__name__ = 'Enrolled'
#		self._enrolled.__parent__ = self
		# _add_container_iface( self._enrolled, nti_interfaces.IEnrolledContainer )
		#self._enrolled.container_name = self._enrolled.__name__
		self.__name__ = self.ID
		self.__parent__ = None


	def __eq__( self, other ):
		try:
			# Interestingly, BTreeContainer does a poor job implementing __eq__
			return self.ID == other.ID and self.Provider == other.Provider and self.InstructorInfo == other.InstructorInfo \
				and list(self._enrolled.keys()) == list(other._enrolled.keys())
		except AttributeError:
			return NotImplemented

	def enroll(self, student):
		self._enrolled[student] = student

	@property
	def links(self):
		if not self.__parent__:
			return ()
		return (links.Link( self.__parent__.__parent__, rel='parent' ),)


	@property
	def Enrolled(self):
		return self._enrolled.keys()

	def __iter__(self):
		# IUsernameIterable
		return itertools.chain( iter(self.Enrolled), self.InstructorInfo.Instructors)

	@property
	def NTIID(self):
		# If we are inserted into a container without having been given an ID,
		# one is generated for us, and we cannot use it correctly in our NTIID
		if ntiids.is_valid_ntiid_string( self.ID ):
			return ntiids.make_ntiid( date=ntiids.DATE, provider=self.Provider,
									  nttype=ntiids.TYPE_MEETINGROOM_SECT,
									  base=self.ID )

		return ntiids.make_ntiid( date=ntiids.DATE, provider=self.Provider,
								  nttype=ntiids.TYPE_MEETINGROOM_SECT, specific=self.ID )

	def toExternalDictionary( self, mergeFrom=None ):
		result = super(SectionInfo,self).toExternalDictionary( mergeFrom=mergeFrom )
		#### XXX
		# Temporary hacks
		result['Enrolled'] = toExternalObject( list(self.Enrolled) )
		return _add_accepts( self, result )


	def updateFromExternalObject( self, parsed, *args, **kwargs ):
		iinfo = parsed.pop( 'InstructorInfo', None )
		enrolled = parsed.pop( 'Enrolled', None )
		super(SectionInfo,self).updateFromExternalObject( parsed, *args, **kwargs )

		updated = False # we only consider the domain things we deal with here, not generic stuff
		if iinfo:
			updated |= self.InstructorInfo.updateFromExternalObject( iinfo )

		# TODO: Dealing with enrolled is a bit of a hack right now.
		# If they don't send enrolled at all, do nothing
		if enrolled is not None:
			enrolled = set(enrolled)
			# If they did send it, than anything missing is removed.
			# Anything else is added
			for current_student in list(self.Enrolled):
				if current_student not in enrolled:
					updated = True
					del self._enrolled[current_student]
			for new_student in enrolled:
				if new_student not in self._enrolled:
					updated = True
					self.enroll( new_student )

		return updated


class InstructorInfo( Persistent,
					  ExternalizableInstanceDict ):

	__metaclass__ = mimetype.ModeledContentTypeAwareRegistryMetaclass
	interface.implements(nti_interfaces.IInstructorInfo)

	def __init__( self ):
		super(InstructorInfo,self).__init__()
		self.Instructors = PersistentList() # list of the names of the instructors

	def __eq__( self, other ):
		try:
			return self.Instructors == other.Instructors
		except AttributeError:
			return NotImplemented
