% if brand:
	WEBSITE: ${brand}
% endif

% if resolve_url:
	VIEW DISCUSSION: ${resolve_url}
% endif

% if sender_content.get('message', False):
	${sender_content['message']}
% endif

If you feel this email was sent in error, you may email ${support_email}.
