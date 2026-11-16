# Identity Configuration — application (development)

This document describes the identity provider configuration for the **application** application
in the **development** deployment environment.

> **Generated file — do not edit manually.** Regenerate by running `cruftfree generate`.

---

## Providers

### identity

| Field | Value |
|---|---|
| Provider Type | `cognito` |
| Audience | `customer` |
| Mode | `platformManaged` |
| Credential | `jwt` |
| Issuer | `https://cognito-idp.us-east-1.amazonaws.com/us-east-1_MarramIdentity` |
| Revocation Mode | `none` |
| Public Client Metadata | `identity-client-identity.development.json` |

#### Revocation Guarantee

Tokens remain valid until their expiry time (TTL). Revoked credentials are NOT invalidated immediately — the revocation window equals the token TTL.

#### External Prerequisites (Manual Setup Required)

The following infrastructure must be provisioned manually before this provider is operational.
CruftFree generates client code and configuration; it does not provision the provider itself.

- AWS Cognito User Pool provisioned in the target AWS account.
- App client registered in the User Pool with the correct redirect URIs.
- Cognito domain or custom domain configured.

### machine

| Field | Value |
|---|---|
| Provider Type | `external` |
| Audience | `machine` |
| Mode | `external` |
| Credential | `jwt` |
| Issuer | `https://machine-auth.marram.example.com` |
| Revocation Mode | `none` |

#### Revocation Guarantee

Tokens remain valid until their expiry time (TTL). Revoked credentials are NOT invalidated immediately — the revocation window equals the token TTL.

#### External Prerequisites (Manual Setup Required)

The following infrastructure must be provisioned manually before this provider is operational.
CruftFree generates client code and configuration; it does not provision the provider itself.

- External identity provider is provisioned and accessible at the configured issuer URL.
- Client ID and client secret registered with the external provider.
- JWKS endpoint accessible for token validation.

### paymentKeys

| Field | Value |
|---|---|
| Provider Type | `apiKey` |
| Audience | `customer` |
| Mode | `self` |
| Credential | `apiKey` |
| Key Header | `X-Payment-Api-Key` |
| Key Store Service | `hotel.PaymentMock` |
| Verify Route | `/internal/identity/api-keys/paymentKeys/verify` |

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
| Key Store Service | `hotel.EmailMock` |
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

### channelKeys

| Field | Value |
|---|---|
| Provider Type | `apiKey` |
| Audience | `customer` |
| Mode | `self` |
| Credential | `apiKey` |
| Key Header | `X-Channel-Api-Key` |
| Key Store Service | `hotel.ChannelMock` |
| Verify Route | `/internal/identity/api-keys/channelKeys/verify` |

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
