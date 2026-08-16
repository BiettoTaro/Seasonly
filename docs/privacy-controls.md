# Automated data export and account deletion

## User contract

Seasonly exposes two authenticated self-service controls:

```text
POST   /api/v1/users/me/data-export
DELETE /api/v1/users/me
```

Both require the current account password in the JSON body and are protected by the authentication
rate limiter. Deletion additionally requires the exact confirmation value `DELETE`. A valid bearer
token alone is insufficient for either sensitive action.

The iOS profile screen presents password reconfirmation immediately before each action. Export
opens the system JSON file picker. Deletion shows the data categories affected, requires the typed
confirmation, permanently removes the database account, and then clears the local Keychain
session.

## Export format and scope

The response is a versioned `seasonly-user-data-v1` JSON object. It is returned with
`Cache-Control: no-store` and a `Content-Disposition` attachment filename. JSON is a commonly used,
machine-readable format; the ICO notes that secure remote download in a commonly used electronic
format can provide a copy of personal information where the person accepts that method
(Information Commissioner's Office, 2025).

The export contains:

- account identity, status and timestamps;
- the complete profile, including location, onboarding, diet, allergy and preference fields;
- consent records and their lifecycle timestamps;
- favourites, recipe history and planned meals with recipe identifiers and names;
- retained recommendation events;
- refresh-session and password-reset-request metadata.

Password hashes, refresh-token hashes, password-reset-token hashes, bearer tokens and the
re-entered password are never returned. Public recipe content is not copied in full; recipe names
are included only to make user activity understandable.

The endpoint is a self-service copy of information held in the Seasonly application database. It
does not prevent a person from making an access request by another permitted method, and it does
not by itself supply every item of supplementary information that may be required for a formal
subject access request. The ICO describes the right of access as including both a copy of personal
information and supplementary information (Information Commissioner's Office, 2026).

## Deletion scope

Deletion is an immediate hard delete of the authenticated user row. PostgreSQL foreign keys use
`ON DELETE CASCADE` for every user-owned application table:

- profile, allergens, dietary rules, cuisine and protein preferences;
- allergy and personalization consent records;
- refresh and password-reset tokens;
- favourites, recipe history and planned meals;
- recommendation events.

Once the transaction commits, existing access tokens no longer authenticate because every
authenticated request reloads the user from PostgreSQL. The iOS app also clears its local Keychain
tokens after the successful response.

The control deletes Seasonly's primary application records. Deployment-provider access logs,
database backups or third-party email-delivery records are outside this database transaction and
must follow their own documented retention and erasure processes. The right to erasure is
conditional rather than absolute, so any future legal-retention requirement must be assessed
before changing this unconditional prototype behaviour (Information Commissioner's Office, 2026).

## Verification

Automated checks cover:

- authentication, rate-limited route configuration and request validation;
- password verification before private records are read;
- exact `DELETE` confirmation;
- complete export categories and the absence of password/token hashes;
- incorrect-password rejection;
- database deletion and commit ordering;
- JSON download headers;
- iOS request encoding, compilation and unit tests.

The final PostgreSQL integration smoke created a temporary account with profile, consent, recipe
activity, recommendation and security records. Its export contained every expected category and no
password or token hashes. After hard deletion, all counts were zero across `users`,
`user_profiles`, profile preferences, consents, security tokens, recipe activity and
`recommendation_events`. The temporary harness and account were removed after verification.

## References

Information Commissioner's Office (2025) *How can we supply information to the requester?*
Available at:
https://ico.org.uk/for-organisations/uk-gdpr-guidance-and-resources/individual-rights/right-of-access/how-can-we-supply-information-to-the-requester/
(Accessed: 24 July 2026).

Information Commissioner's Office (2026) *A guide to subject access*. Available at:
https://ico.org.uk/for-organisations/uk-gdpr-guidance-and-resources/subject-access-requests/a-guide-to-subject-access/
(Accessed: 24 July 2026).

Information Commissioner's Office (2026) *Your right to get your data deleted*. Available at:
https://ico.org.uk/for-the-public/your-right-to-get-your-data-deleted/
(Accessed: 24 July 2026).
