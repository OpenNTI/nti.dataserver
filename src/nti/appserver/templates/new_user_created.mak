Hi ${profile.realname}!

Thank you for creating your new account and welcome to NextThought!

Username: ${user.username}
Log in at: ${request.application_url}

NextThought offers interactive content and rich features to make
learning both social and personal.

% if verify_href:
Please verify your email address. Doing so will
help us maintain the security of your account.
To verify your email address, use the following link: ${verify_href}

% endif
Sincerely,
NextThought

If you feel this email was sent in error, or this account was created
without your consent, you may email us at ${support_email}.
