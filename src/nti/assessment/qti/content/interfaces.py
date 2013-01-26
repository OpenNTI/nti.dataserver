from __future__ import unicode_literals, print_function

from zope import schema
from zope import interface
from zope.interface.common.sequence import IFiniteSequence

from nti.assessment.qti.basic import interfaces as basic_interfaces
from nti.assessment.qti.attributes import interfaces as attr_interfaces
	
class IobjectFlow(interface.Interface):
	pass

class Iinline(interface.Interface):
	pass
			
class Iblock(interface.Interface):
	pass
	
class Iflow(IobjectFlow, attr_interfaces.IflowAttrGroup):
	pass
	
class IinlineStatic(Iinline):
	pass
	
class IblockStatic(Iblock):
	pass
	
class IflowStatic(Iflow):
	pass
	
class IsimpleInline(basic_interfaces.IbodyElement, IflowStatic, IinlineStatic, IFiniteSequence):
	inline = schema.List(schema.Object(Iinline), 'inline objects contained', min_length=0)
	
class IsimpleBlock(IflowStatic, basic_interfaces.IbodyElement, IblockStatic, IFiniteSequence):
	block = schema.List(schema.Object(Iblock), 'block objects contained', min_length=0)
	
class IatomicInline(IflowStatic, basic_interfaces.IbodyElement, IinlineStatic):
	pass
	
class IAtomicBlock(basic_interfaces.IbodyElement, IflowStatic, IblockStatic, IFiniteSequence):
	inline = schema.List(schema.Object(Iinline), 'The ordered inline objects contained', min_length=0)

class ItextRun(IflowStatic, IinlineStatic, basic_interfaces.ITextOrVariable, basic_interfaces.IConcrete):
	pass
	
# xhtml elements

class Iabbr(IsimpleInline, basic_interfaces.IConcrete):
	pass
	
class Iacronym(IsimpleInline, basic_interfaces.IConcrete):
	pass
	
class Iaddress(IAtomicBlock, basic_interfaces.IConcrete):
	pass

class Iblockquote(IsimpleBlock, attr_interfaces.IblockquoteAttrGroup, basic_interfaces.IConcrete):
	pass
	
class Ibr(IatomicInline, basic_interfaces.IConcrete):
	pass
	
class Icite(IsimpleInline, basic_interfaces.IConcrete):
	pass
	
class Icode(IsimpleInline, basic_interfaces.IConcrete):
	pass
	
class Idfn(IsimpleInline, basic_interfaces.IConcrete):
	pass
	
class Idiv(IflowStatic, basic_interfaces.IbodyElement, IblockStatic, IFiniteSequence, basic_interfaces.IConcrete):
	flow = schema.List(schema.Object(Iflow), 'flow objects contained', min_length=0)
	
class Iem(IsimpleInline, basic_interfaces.IConcrete):
	pass
	
class Ih1(IAtomicBlock, basic_interfaces.IConcrete):
	pass

class Ih2(IAtomicBlock, basic_interfaces.IConcrete):
	pass

class Ih3(IAtomicBlock, basic_interfaces.IConcrete):
	pass	
	
class Ih4(IAtomicBlock, basic_interfaces.IConcrete):
	pass
	
class Ih5(IAtomicBlock, basic_interfaces.IConcrete):
	pass
	
class Ih6(IAtomicBlock, basic_interfaces.IConcrete):
	pass
	
class Ikbd(IsimpleInline, basic_interfaces.IConcrete):
	pass
	
class Ip(IAtomicBlock, basic_interfaces.IConcrete):
	pass
	
class Ipre(IAtomicBlock, basic_interfaces.IConcrete):
	"""
	Although pre inherits from atomicBlock it must not contain, either directly or indirectly,
	any of the following objects: img, object, big, small, sub, sup.
	"""
	pass
	
class Iq(IsimpleInline, attr_interfaces.IqAttrGroup, basic_interfaces.IConcrete):
	pass
	
class Isamp(IsimpleInline, basic_interfaces.IConcrete):
	pass
	
class Ispan(IsimpleInline, basic_interfaces.IConcrete):
	pass

class Istrong(IsimpleInline, basic_interfaces.IConcrete):
	pass
	
class Ivar(IsimpleInline, basic_interfaces.IConcrete):
	pass

# list elements

class IDLElement(basic_interfaces.IbodyElement):
	pass

class Idl(IblockStatic, basic_interfaces.IbodyElement, IflowStatic, IFiniteSequence, basic_interfaces.IConcrete):
	dlElement = schema.List(schema.Object(IDLElement), 'The ordered dl elements contained', min_length=0)
	
class Idt(IDLElement, IFiniteSequence, basic_interfaces.IConcrete):
	inline = schema.List(schema.Object(Iinline), 'The ordered inline elements contained', min_length=0)

class Idd(IDLElement, IFiniteSequence, basic_interfaces.IConcrete):
	flow = schema.List(schema.Object(Iflow), 'The ordered flow elements contained', min_length=0)

class Ili(basic_interfaces.IbodyElement, IFiniteSequence, basic_interfaces.IConcrete):
	flow = schema.List(schema.Object(Iflow), 'The ordered flow elements contained', min_length=0)

class Iol(IblockStatic, basic_interfaces.IbodyElement, IflowStatic, IFiniteSequence, basic_interfaces.IConcrete):
	li = schema.List(schema.Object(Ili), 'The ordered li elements contained', min_length=0)
	
class Iul(IblockStatic, basic_interfaces.IbodyElement, IflowStatic, IFiniteSequence, basic_interfaces.IConcrete):
	li = schema.List(schema.Object(Ili), 'The ordered li elements contained', min_length=0)
		
# object elements

class Iobject(basic_interfaces.IbodyElement, IflowStatic, IinlineStatic, IFiniteSequence,
			  attr_interfaces.IobjectAttrGroup, basic_interfaces.IConcrete):
	objectFlow = schema.List(schema.Object(IobjectFlow), 'The ordered objectflow elements contained', min_length=0)

class Iparam(IobjectFlow, attr_interfaces.IparamAttrGroup, basic_interfaces.IConcrete):
	pass
	
# presentation Elements

class Ib(IsimpleInline, basic_interfaces.IConcrete):
	pass

class Ibig(IsimpleInline, basic_interfaces.IConcrete):
	pass

class Ihr(IblockStatic, basic_interfaces.IbodyElement, IflowStatic, basic_interfaces.IConcrete):
	pass

class Ii(IsimpleInline, basic_interfaces.IConcrete):
	pass

class Ismall(IsimpleInline, basic_interfaces.IConcrete):
	pass

class Isub(IsimpleInline, basic_interfaces.IConcrete):
	pass

class Isup(IsimpleInline, basic_interfaces.IConcrete):
	pass	

class Itt(IsimpleInline, basic_interfaces.IConcrete):
	pass

# table elements

class Icaption(basic_interfaces.IbodyElement, IFiniteSequence, basic_interfaces.IConcrete):
	inline = schema.List(schema.Object(Iinline), 'The ordered inline elements contained', min_length=0)

class Icol(basic_interfaces.IbodyElement, attr_interfaces.IcolAttrGroup, basic_interfaces.IConcrete):
	pass	
	
class Icolgroup(basic_interfaces.IbodyElement, attr_interfaces.IcolgroupAttrGroup, IFiniteSequence, basic_interfaces.IConcrete):
	col = schema.List(schema.Object(Icol), 'The ordered col elements contained', min_length=0)

class ItableCell(basic_interfaces.IbodyElement, attr_interfaces.ItableCellAttrGroup, IFiniteSequence):
	flow = schema.List(schema.Object(Iflow), 'The ordered flow elements contained', min_length=0)

class Itd(ItableCell, basic_interfaces.IConcrete):
	pass
	
class Ith(ItableCell, basic_interfaces.IConcrete):
	pass
	
class Itr( basic_interfaces.IbodyElement, IFiniteSequence, basic_interfaces.IConcrete):
	tableCell = schema.List(schema.Object(ItableCell), 'tableCell elements contained', min_length=0)
	
class Ithead( basic_interfaces.IbodyElement, IFiniteSequence, basic_interfaces.IConcrete):
	tr = schema.List(schema.Object(Itr), 'The ordered tr elements contained', min_length=1)
	
class Itfoot( basic_interfaces.IbodyElement, IFiniteSequence, basic_interfaces.IConcrete):
	tr = schema.List(schema.Object(Itr), 'The ordered tr elements contained', min_length=1)
	
class Itbody( basic_interfaces.IbodyElement, IFiniteSequence, basic_interfaces.IConcrete):
	tr = schema.List(schema.Object(Itr), 'The ordered tr elements contained', min_length=1)
	
class Itable(IblockStatic, basic_interfaces.IbodyElement, IflowStatic, attr_interfaces.ItableAttrGroup,
			 basic_interfaces.IConcrete):
	caption = schema.Object(Icaption, title='the table caption')
	col = schema.List(schema.Object(Icol), title='Table direct col (Must not contain any colgroup elements)', min_length=0, required=False)
	colgroup = schema.List(schema.Object(Icolgroup), title='Table direct colgroups (Must not contain any col elements)', min_length=0, required=False)
	thead = schema.Object(Ithead, title='table head', required=False)
	tfoot = schema.Object(Itfoot, title='table head', required=False)
	tbody = schema.List(schema.Object(Itbody), title='table body',  min_length=1, required=True)

# image Element

class Iimg(IatomicInline, attr_interfaces.IimgAttrGroup, basic_interfaces.IConcrete):
	pass

# hypertext Element

class Ia(IatomicInline, attr_interfaces.IaAttrGroup, basic_interfaces.IConcrete):
	pass

# math element

class Imath(IblockStatic, IflowStatic, IinlineStatic, basic_interfaces.IConcrete):
	pass

# variable element

class IfeedbackElement(attr_interfaces.IFeedbackAttrGroup):
	pass

class IfeedbackBlock(IfeedbackElement, IsimpleBlock, basic_interfaces.IConcrete):
	pass

class IfeedbackInline(IfeedbackElement, IsimpleInline, basic_interfaces.IConcrete):
	pass
	
class IrubricBlock(attr_interfaces.IviewAttrGroup, basic_interfaces.IConcrete):
	pass

# formatting items with stylesheets

class Istylesheet(attr_interfaces.IstylesheetAttrGroup, basic_interfaces.IConcrete):
	pass
	
class IitemBody(basic_interfaces.IbodyElement, basic_interfaces.IConcrete):
	blocks = schema.List(schema.Object(Iblock), title='The item body blocks', required=False)
