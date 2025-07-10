targetScope = 'subscription'

param resourceGroupName string

param location string

param principalId string

resource rg 'Microsoft.Resources/resourceGroups@2023-07-01' = {
  name: resourceGroupName
  location: location
}

module storage 'storage/storage.bicep' = {
  name: 'storage'
  scope: rg
  params: {
    location: location
  }
}

module storage_roles 'storage-roles/storage-roles.bicep' = {
  name: 'storage-roles'
  scope: rg
  params: {
    location: location
    storage_outputs_name: storage.outputs.name
    principalType: ''
    principalId: ''
  }
}