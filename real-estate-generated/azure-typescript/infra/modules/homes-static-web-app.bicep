@description('Static Web App name')
param staticSiteName string

@description('Custom domain hostname, empty when none declared')
param customDomainName string

resource staticSite 'Microsoft.Web/staticSites@2025-03-01' = {
  name: staticSiteName
  // The resolved Static Web App hosting region: the deployment region when
  // Static Web Apps is available there, otherwise the declared
  // staticWebAppLocation -- never a region picked on the operator's behalf.
  location: 'eastus2'
  sku: {
    name: 'Standard'
    tier: 'Standard'
  }
  properties: {
    // Deployed by the generated deploy script's upload step
    // (`@azure/static-web-apps-cli` 2.0.10 `swa deploy` with the deployment
    // token resolved from its logical secret handle), never by ARM's own
    // `repositoryUrl`/`branch` repository-integration path -- CruftFree's own
    // build step already produced the bundle.
    provider: 'Custom'
    // A web app is public. Declared so that a deployment serves again a site
    // whose access `down` turned off (a clients-only deploy restores it itself).
    publicNetworkAccess: 'Enabled'
  }
}

resource staticSiteCustomDomain 'Microsoft.Web/staticSites/customDomains@2025-03-01' = {
  parent: staticSite
  name: customDomainName
  properties: {
    validationMethod: 'dns-txt-token'
  }
}

output staticSiteDefaultHostname string = staticSite.properties.defaultHostname
output staticSiteResourceId string = staticSite.id
