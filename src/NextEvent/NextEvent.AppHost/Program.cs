using Azure.Provisioning.Storage;
using Azure.Storage.Blobs;
using Microsoft.Extensions.Hosting;

var builder = DistributedApplication.CreateBuilder(args);
IResourceBuilder<Aspire.Hosting.Azure.AzureStorageResource>? storage = null;

if(!builder.Environment.IsDevelopment())
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


var web = builder.AddProject<Projects.NextEvent_web>("nextevent-web")
                    .WithExternalHttpEndpoints()
                    .WithReference(blobs);

builder.AddDockerComposeEnvironment("container");

builder.Build().Run();
