# Zoho CRM agent guidance

Use the module and field metadata actions before creating or updating records;
Zoho custom modules and fields are workspace-specific. Prefer read actions to
resolve IDs before writes. Treat create, update, delete, send, convert, merge,
mass, workflow, sharing, and webhook actions as material side effects. Bulk
launch actions return jobs that must be followed with the matching status and
result actions.

The connector is OAuth BYOK and no-bill. The connected user's permissions,
selected OAuth scopes, Zoho edition, API limits, organization, environment, and
data-center domain govern what succeeds.
