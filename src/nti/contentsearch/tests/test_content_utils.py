import os
import json
import unittest

from zope import component

from nti.chatserver.messageinfo import MessageInfo

from nti.dataserver.users import User
from nti.dataserver.contenttypes import Note
from nti.dataserver.contenttypes import Canvas
from nti.dataserver.contenttypes import Redaction
from nti.dataserver.contenttypes import Highlight
from nti.dataserver.contenttypes import CanvasTextShape

from nti.ntiids.ntiids import make_ntiid

from nti.contentsearch.tests import ConfiguringTestBase
from nti.contentsearch.interfaces import IContentResolver2
from nti.contentsearch._content_utils import get_content
from nti.contentsearch._content_utils import get_multipart_content

import nti.dataserver.tests.mock_dataserver as mock_dataserver
from nti.dataserver.tests.mock_dataserver import WithMockDSTrans

from hamcrest import (assert_that, is_, is_not, close_to)

class TestContentUtils(ConfiguringTestBase):

	@classmethod
	def setUpClass(cls):	
		path = os.path.join(os.path.dirname(__file__), 'message_info.json')
		with open(path, "r") as f:
			cls.messageinfo = json.load(f)
			
		path = os.path.join(os.path.dirname(__file__), 'note2.json')
		with open(path, "r") as f:
			cls.note = json.load(f)

	def test_get_content(self):
		assert_that(get_content(None), is_(u''))
		assert_that(get_content({}), is_(u''))
		assert_that(get_content('Zanpakuto Zangetsu'), is_('Zanpakuto Zangetsu'))
		assert_that(get_content('\n\tZanpakuto,Zangetsu'), is_('Zanpakuto Zangetsu'))
		assert_that(get_content('<html><b>Zangetsu</b></html>'), is_('Zangetsu'))
		assert_that( get_content('orange-haired'), is_('orange-haired'))

		assert_that(get_content('U.S.A. vs Japan'), is_('U.S.A. vs Japan'))
		assert_that(get_content('$12.45'), is_('$12.45'))
		assert_that(get_content('82%'), is_('82%'))

		u = unichr(40960) + u'bleach' + unichr(1972)
		assert_that(get_content(u), is_('bleach'))
		
	def _create_note(self, msg, username, containerId=None, tags=('ichigo',), canvas=None):
		note = Note()
		note.tags = tags
		note.body = [unicode(msg)]
		if canvas:
			note.body.append(canvas)
		note.creator = username
		note.containerId = containerId or make_ntiid(nttype='bleach', specific='manga')
		return note
	
	@WithMockDSTrans
	def test_note_adapter(self):
		containerId = make_ntiid(nttype='bleach', specific='manga')
		usr = User.create_user( mock_dataserver.current_mock_ds, username='nt@nti.com', password='temp' )
		note = self._create_note('nothing can be explained', usr.username, containerId)
		mock_dataserver.current_transaction.add(note)
		note = usr.addContainedObject( note ) 
		adapted = component.getAdapter(note, IContentResolver2)
		assert_that(adapted.get_content(), is_('nothing can be explained'))
		assert_that(adapted.get_references(), is_([]))
		assert_that(adapted.get_ntiid(), is_not(None))
		assert_that(adapted.get_external_oid(), is_not(None))
		assert_that(adapted.get_creator(), is_('nt@nti.com'))
		assert_that(adapted.get_containerId(), is_(containerId))
		assert_that(adapted.get_keywords(), is_(['ichigo']))
		assert_that(adapted.get_sharedWith(), is_([]))
		assert_that(adapted.get_last_modified(), is_not(None))
	
	@WithMockDSTrans
	def test_note_adapter_canvas(self):
		c = Canvas()
		ct = CanvasTextShape()
		ct.text = 'Mike Wyzgowski'
		c.append(ct)
		containerId =  make_ntiid(nttype='bleach', specific='manga')
		usr = User.create_user( mock_dataserver.current_mock_ds, username='nt@nti.com', password='temp' )
		note = self._create_note('New Age', usr.username, containerId, canvas=c)
		mock_dataserver.current_transaction.add(note)
		note = usr.addContainedObject( note ) 
		adapted = component.getAdapter(note, IContentResolver2)
		assert_that(adapted.get_content(), is_('New Age Mike Wyzgowski'))
		
	@WithMockDSTrans
	def test_redaction_adpater(self):
		username = 'kuchiki@bleach.com'
		containerId = make_ntiid(nttype='bleach', specific='manga')
		user = User.create_user(mock_dataserver.current_mock_ds, username=username, password='temp' )
		redaction = Redaction()
		redaction.selectedText = u'Fear'
		redaction.replacementContent = 'redaction'
		redaction.redactionExplanation = 'Have overcome it everytime I have been on the verge of death'
		redaction.creator = username
		redaction.containerId = containerId
		redaction = user.addContainedObject( redaction )
		adapted = component.getAdapter(redaction, IContentResolver2)
		assert_that(adapted.get_content(), is_('redaction Have overcome it everytime I have been on the verge of death Fear'))
		assert_that(adapted.get_references(), is_([]))
		assert_that(adapted.get_ntiid(), is_not(None))
		assert_that(adapted.get_external_oid(), is_not(None))
		assert_that(adapted.get_creator(), is_('kuchiki@bleach.com'))
		assert_that(adapted.get_containerId(), is_(containerId))
		assert_that(adapted.get_keywords(), is_([]))
		assert_that(adapted.get_sharedWith(), is_([]))
		assert_that(adapted.get_last_modified(), is_not(None))
		
	@WithMockDSTrans
	def test_highlight_adpater(self):
		username = 'urahara@bleach.com'
		containerId = make_ntiid(nttype='bleach', specific='manga')
		user = User.create_user(mock_dataserver.current_mock_ds, username=username, password='temp' )
		highlight = Highlight()
		highlight.selectedText = u'Kon saw it! The Secret of a Beautiful Office Lady'
		highlight.creator = username
		highlight.containerId = containerId
		highlight = user.addContainedObject( highlight )
		adapted = component.getAdapter(highlight, IContentResolver2)
		assert_that(adapted.get_content(), is_('Kon saw it The Secret of a Beautiful Office Lady'))
		assert_that(adapted.get_references(), is_([]))
		assert_that(adapted.get_ntiid(), is_not(None))
		assert_that(adapted.get_external_oid(), is_not(None))
		assert_that(adapted.get_creator(), is_('urahara@bleach.com'))
		assert_that(adapted.get_containerId(), is_(containerId))
		assert_that(adapted.get_keywords(), is_([]))
		assert_that(adapted.get_sharedWith(), is_([]))
		assert_that(adapted.get_last_modified(), is_not(None))
		
	@WithMockDSTrans
	def test_messageinfo_adapter_canvas(self):
		c = Canvas()
		ct = CanvasTextShape()
		ct.text = 'Ichigo VS Ulquiorra'
		c.append(ct)
		mi = MessageInfo()
		mi.Body = ['Beginning of Despair, the Unreachable Blade', c]
		adapted = component.getAdapter(mi, IContentResolver2)
		assert_that(adapted.get_content(), is_('Beginning of Despair the Unreachable Blade Ichigo VS Ulquiorra'))
		
	def test_dict_adpater(self):
		adapted = component.getAdapter(self.note, IContentResolver2)
		assert_that(adapted.get_content(), is_('Eddard Stark Lord of Winterfell'))
		assert_that(adapted.get_references(), is_([]))
		assert_that(adapted.get_ntiid(), is_('tag:nextthought.com,2011-10:carlos.sanchez@nextthought.com-OID-0x0932:5573657273'))
		assert_that(adapted.get_external_oid(), is_('tag:nextthought.com,2011-10:carlos.sanchez@nextthought.com-OID-0x0932:5573657273'))
		assert_that(adapted.get_creator(), is_('carlos.sanchez@nextthought.com'))
		assert_that(adapted.get_containerId(), is_('tag:nextthought.com,2011-10:AOPS-HTML-prealgebra.0'))
		assert_that(adapted.get_keywords(), is_([]))
		assert_that(adapted.get_sharedWith(), is_([]))
		assert_that(adapted.get_last_modified(), is_(close_to(1334000544.120, 0.05)))
		
	def xtest_get_text_from_mutil_part_body(self):
		js = self.messageinfo
		msg = get_multipart_content(js['Body'])
		assert_that(msg, is_(u'Zanpakuto and Zangetsu'))
		assert_that(get_multipart_content('Soul Reaper'), is_(u'Soul Reaper'))

if __name__ == '__main__':
	unittest.main()
