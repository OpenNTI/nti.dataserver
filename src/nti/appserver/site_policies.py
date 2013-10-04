import zope.deferredimport
zope.deferredimport.initialize()
zope.deferredimport.deprecatedFrom(
	"Unbreak mathcounts stuff",
	"nti.app.sites.mathcounts.interfaces",
	"IMathcountsUser",
	"IMathcountsCoppaUserWithoutAgreement",
	"IMathcountsCoppaUserWithAgreement",
	"IMathcountsCoppaUserWithAgreementUpgraded",
	"IMathcountsCoppaUserWithoutAgreementUserProfile",
	"IMathcountsCoppaUserWithAgreementUserProfile")
