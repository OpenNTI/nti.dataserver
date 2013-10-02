import zope.deferredimport
zope.deferredimport.initialize()
zope.deferredimport.deprecatedFrom(
	"Unbreak mathcounts stuff",
	"nti.appserver.policies.interfaces",
	"IMathcountsUser",
	"IMathcountsCoppaUserWithoutAgreement",
	"IMathcountsCoppaUserWithAgreement",
	"IMathcountsCoppaUserWithAgreementUpgraded",
	"IMathcountsCoppaUserWithoutAgreementUserProfile",
	"IMathcountsCoppaUserWithAgreementUserProfile")
