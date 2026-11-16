# Identity Configuration — application (development)

This document describes the identity provider configuration for the **application** application
in the **development** deployment environment.

> **Generated file — do not edit manually.** Regenerate by running `cruftfree generate`.

---

## Providers

### identity

| Field | Value |
|---|---|
| Provider Type | `entra-id` |
| Audience | `customer` |
| Mode | `platformManaged` |
| Credential | `jwt` |
| Issuer | `https://login.microsoftonline.com/cobblestone.onmicrosoft.com/v2.0` |
| Revocation Mode | `none` |
| Public Client Metadata | `identity-client-identity.development.json` |

#### Revocation Guarantee

Tokens remain valid until their expiry time (TTL). Revoked credentials are NOT invalidated immediately — the revocation window equals the token TTL.

#### External Prerequisites (Manual Setup Required)

The following infrastructure must be provisioned manually before this provider is operational.
CruftFree generates client code and configuration; it does not provision the provider itself.

- Microsoft Entra ID (Azure Active Directory) tenant provisioned.
- App registration created in the tenant with the correct redirect URIs and API permissions.
- Admin consent granted for required Microsoft Graph permissions.

### machine

| Field | Value |
|---|---|
| Provider Type | `entra-id` |
| Audience | `machine` |
| Mode | `platformManaged` |
| Credential | `jwt` |
| Issuer | `https://login.microsoftonline.com/cobblestone.onmicrosoft.com/v2.0` |
| Revocation Mode | `none` |

#### Revocation Guarantee

Tokens remain valid until their expiry time (TTL). Revoked credentials are NOT invalidated immediately — the revocation window equals the token TTL.

#### External Prerequisites (Manual Setup Required)

The following infrastructure must be provisioned manually before this provider is operational.
CruftFree generates client code and configuration; it does not provision the provider itself.

- Microsoft Entra ID (Azure Active Directory) tenant provisioned.
- App registration created in the tenant with the correct redirect URIs and API permissions.
- Admin consent granted for required Microsoft Graph permissions.

### mortgageKeys

| Field | Value |
|---|---|
| Provider Type | `apiKey` |
| Audience | `customer` |
| Mode | `self` |
| Credential | `apiKey` |
| Key Header | `X-Mortgage-Api-Key` |
| Key Store Service | `realestate.MortgageMock` |
| Verify Route | `/internal/identity/api-keys/mortgageKeys/verify` |

#### Revocation Guarantee

Every request presenting a key is verified against the owning service's key store with exactly one lookup; no verifying service caches the result. Deactivating, expiring or deleting a key takes effect on the next request.

#### External Prerequisites (Manual Setup Required)

The following infrastructure must be provisioned manually before this provider is operational.
CruftFree generates client code and configuration; it does not provision the provider itself.

- The owning service, RDBMS block and entity declared in the provider's apiKey { } config (store/storeBlock/entity) exist and are reachable.
- Every service admitting this provider on a route declares the owning service in its discovery { } block.
- The application issues raw keys with Crypto.randomBytes(32) and stores only Crypto.sha256(rawKey) -- the raw key is never persisted.
- The provider's header is excluded from every httpSecurity.corsHeaders and gateway.cors.headers allow-list.

### signatureKeys

| Field | Value |
|---|---|
| Provider Type | `apiKey` |
| Audience | `customer` |
| Mode | `self` |
| Credential | `apiKey` |
| Key Header | `X-Signature-Api-Key` |
| Key Store Service | `realestate.SignatureMock` |
| Verify Route | `/internal/identity/api-keys/signatureKeys/verify` |

#### Revocation Guarantee

Every request presenting a key is verified against the owning service's key store with exactly one lookup; no verifying service caches the result. Deactivating, expiring or deleting a key takes effect on the next request.

#### External Prerequisites (Manual Setup Required)

The following infrastructure must be provisioned manually before this provider is operational.
CruftFree generates client code and configuration; it does not provision the provider itself.

- The owning service, RDBMS block and entity declared in the provider's apiKey { } config (store/storeBlock/entity) exist and are reachable.
- Every service admitting this provider on a route declares the owning service in its discovery { } block.
- The application issues raw keys with Crypto.randomBytes(32) and stores only Crypto.sha256(rawKey) -- the raw key is never persisted.
- The provider's header is excluded from every httpSecurity.corsHeaders and gateway.cors.headers allow-list.

### emailKeys

| Field | Value |
|---|---|
| Provider Type | `apiKey` |
| Audience | `customer` |
| Mode | `self` |
| Credential | `apiKey` |
| Key Header | `X-Email-Api-Key` |
| Key Store Service | `realestate.EmailMock` |
| Verify Route | `/internal/identity/api-keys/emailKeys/verify` |

#### Revocation Guarantee

Every request presenting a key is verified against the owning service's key store with exactly one lookup; no verifying service caches the result. Deactivating, expiring or deleting a key takes effect on the next request.

#### External Prerequisites (Manual Setup Required)

The following infrastructure must be provisioned manually before this provider is operational.
CruftFree generates client code and configuration; it does not provision the provider itself.

- The owning service, RDBMS block and entity declared in the provider's apiKey { } config (store/storeBlock/entity) exist and are reachable.
- Every service admitting this provider on a route declares the owning service in its discovery { } block.
- The application issues raw keys with Crypto.randomBytes(32) and stores only Crypto.sha256(rawKey) -- the raw key is never persisted.
- The provider's header is excluded from every httpSecurity.corsHeaders and gateway.cors.headers allow-list.

---

## Artifact Files

| Artifact | Path |
|---|---|
| Provider Plan | `config/generated/identity-providers.json` |
| Public Client Metadata (identity) | `config/generated/identity-client-identity.development.json` |

---

> **Secret handling:** Secret values are never stored in generated files. The provider plan
> references secrets by environment-variable name (`*_SECRET_REF`). Inject secrets at
> runtime via your secret management solution (e.g. AWS Secrets Manager, Azure Key Vault,
> Docker Secrets).
