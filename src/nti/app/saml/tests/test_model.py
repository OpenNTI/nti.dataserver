
import unittest

from hamcrest import assert_that
from hamcrest import is_

from ..client import _SAMLNameId
from ..model import SAMLIDPEntityBindings

from . import MockNameId



class TestBindings(unittest.TestCase):

	bindings = None

	def setUp(self):
		self.bindings = SAMLIDPEntityBindings()

	def test_bindings(self):

		nameid = MockNameId('mynameid')
		nameid.name_qualifier = 'nameq'
		nameid.sp_name_qualifier = 'spnameq'

		self.bindings.store_binding(_SAMLNameId(nameid))

		#we can query with a nameid
		assert_that(self.bindings.binding(nameid).nameid, is_('mynameid'))

		#we can also query by qualifier
		assert_that(self.bindings.binding(None, 'nameq', 'spnameq').nameid, is_('mynameid'))

		#we can clear the binding
		assert_that(len(self.bindings), is_(1))
		self.bindings.clear_binding(_SAMLNameId(nameid))
		assert_that(len(self.bindings), is_(0))

		#we fallback to provided qualifiers if needed
		nameid.name_qualifier = None
		nameid.sp_name_qualifier = None
		self.bindings.store_binding(_SAMLNameId(nameid), 'bar', 'baz')
		assert_that(self.bindings.binding(None, 'bar', 'baz').nameid, is_('mynameid'))

		#and we don't need an sp qualifier
		nameid.text = 'fizz'
		nameid.name_qualifier = None
		nameid.sp_name_qualifier = None
		self.bindings.store_binding(_SAMLNameId(nameid), 'fudge')
		assert_that(self.bindings.binding(None, 'fudge').nameid, is_('fizz'))




