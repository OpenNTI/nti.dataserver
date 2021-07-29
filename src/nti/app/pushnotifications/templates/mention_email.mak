Hi ${display_name}!
<%
parent_display_name = notable.__parent__.display_name
provenance_text = ''
if parent_display_name:
    provenance_text = parent_display_name()
elif notable.container.display_name:
    provenance_text = notable.container.display_name()
if provenance_text:
    provenance_text = '%s/' % provenance_text
%>
${notable.creator} mentioned you in ${notable_context}.
${provenance_text}${notable.display_name()}
% if notable.snippet:
"${notable.snippet}"
% endif

View online: ${notable.href}

This message was sent to ${email_to}.  If you have any questions, feel free to message us at ${support_email}.

% if unsubscribe_link:
You currently receive periodic email updates at ${email_to} for ${site_name} activity.
Unsubscribe: ${unsubscribe_link}
% endif