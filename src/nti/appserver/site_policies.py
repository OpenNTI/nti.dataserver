import zope.deferredimport
zope.deferredimport.initialize()
zope.deferredimport.deprecatedFrom(
	"Code should not access this directly; move your tests to the mathcounts site package."
	" The only valid use is existing ZODB objects",
	"nti.app.sites.mathcounts.interfaces",
	"IMathcountsUser",
	"IMathcountsCoppaUserWithoutAgreement",
	"IMathcountsCoppaUserWithAgreement",
	"IMathcountsCoppaUserWithAgreementUpgraded",
	"IMathcountsCoppaUserWithoutAgreementUserProfile",
	"IMathcountsCoppaUserWithAgreementUserProfile")
