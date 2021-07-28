Hi ${display_name}!
<%
parent_display_name = notable.__parent__.__parent__.display_name
provenance_text=('%s / ' % parent_display_name()) if parent_display_name else ""
%>
${notable.creator} mentioned you in ${notable_context}.
${provenance_text}${notable.__parent__.display_name()}
% if notable.snippet:
"${notable.snippet}"
% endif

View online: ${notable.href}

This message was sent to ${email_to}.  If you have any questions, feel free to message us at ${support_email}.

% if unsubscribe_link:
You currently receive periodic email updates at ${email_to} for ${site_name} activity.
Unsubscribe: ${unsubscribe_link}
% endif