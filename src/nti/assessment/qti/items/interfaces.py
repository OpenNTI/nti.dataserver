from __future__ import unicode_literals, print_function


from nti.assessment.qti.basic import interfaces as basic_interfaces
from nti.assessment.qti.attributes import interfaces as attr_interfaces

class IitemSessionControl(attr_interfaces.IitemSessionControlAttrGroup, basic_interfaces.IConcrete):
	pass

