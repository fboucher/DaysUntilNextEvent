using Azure.Provisioning.Storage;
using Azure.Storage.Blobs;
using Microsoft.Extensions.Hosting;

var builder = DistributedApplication.CreateBuilder(args);
IResourceBuilder<Aspire.Hosting.Azure.AzureStorageResource>? storage = null;

if (!builder.Environment.IsDevelopment())
{
    storage = builder.AddAzureStorage("storage")
                        .ConfigureInfrastructure(infra =>
                        {
                            var storageAccount = infra.GetProvisionableResources()
                                                    .OfType<StorageAccount>()
                                                    .Single();
                            storageAccount.AllowBlobPublicAccess = true;
                            storageAccount.AllowSharedKeyAccess = true;
                            storageAccount.Sku = new StorageSku { Name = StorageSkuName.StandardLrs };
                        });
}

var blobs = (builder.Environment.IsDevelopment()) ? builder.AddConnectionString("BlobConnection") : storage!.AddBlobs("BlobConnection");


var kcUsername = builder.AddParameter("keycloak-username");
var kcPassword = builder.AddParameter("keycloak-password", secret: true);
var keycloak = builder.AddKeycloak(name: "keycloak", adminUsername: kcUsername, adminPassword: kcPassword)
                        .WithDataVolume();

var realm = keycloak.WithRealmImport("../realms/devrealm.json", true);

var web = builder.AddProject<Projects.NextEvent_web>("nextevent-web")
                    .WithExternalHttpEndpoints()
                    .WithReference(blobs)
                    .WithReference(keycloak)
                    .WaitFor(keycloak)
                    .WithReference(realm);

builder.AddDockerComposeEnvironment("dev");

builder.Build().Run();
