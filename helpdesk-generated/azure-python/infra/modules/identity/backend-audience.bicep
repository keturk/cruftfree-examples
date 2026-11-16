// Backend audience app registration for helpdesk-system (development).
// The trusted-caller audience: APIM and peer web apps acquire
// managed-identity tokens for THIS app's client ID; services validate the
// token's aud against it. Generated via the GA Microsoft Graph Bicep
// extension. Emitted ONLY when the application's gateway is a managed
// gateway (APIM) -- independent of any declared end-user identity block.
// Do not edit manually.

extension microsoftGraphV1

@description('Environment name')
param environment string

resource backendAudienceApp 'Microsoft.Graph/applications@v1.0' = {
  // uniqueName is REQUIRED and IMMUTABLE -- the idempotency key across re-converges.
  uniqueName: 'helpdesk-system-backend-${environment}'
  displayName: 'helpdesk-system-backend-development'
  api: {
    // v2 tokens: aud = this app's client ID (appId), iss = {loginEndpoint}/{tenant}/v2.0.
    // No passwordCredentials -- this is a pure audience, never a credential holder.
    requestedAccessTokenVersion: 2
  }
}


resource backendAudienceSp 'Microsoft.Graph/servicePrincipals@v1.0' = {
  appId: backendAudienceApp.appId
}

output backendClientId string = backendAudienceApp.appId
output backendServicePrincipalId string = backendAudienceSp.id
// Directory OBJECT id (distinct from appId) -- the write-back extension-registration
// deploymentScript targets POST/GET .../applications/{objectId}/extensionProperties,
// which requires this id, not the client id. Mirrors
// entra-app-registration.bicep.j2's own `applicationObjectId` output.
output backendApplicationObjectId string = backendAudienceApp.id
