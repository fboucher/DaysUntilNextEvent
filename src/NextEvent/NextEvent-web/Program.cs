using Microsoft.FluentUI.AspNetCore.Components;
using NextEvent_web.Components;
using Azure.Storage.Blobs;
using Microsoft.AspNetCore.Authentication.OpenIdConnect;
using AspireApp.Web;
using System.IdentityModel.Tokens.Jwt;
using Microsoft.AspNetCore.Authentication.Cookies;
using Microsoft.IdentityModel.Protocols.OpenIdConnect;



var builder = WebApplication.CreateBuilder(args);

builder.AddServiceDefaults();

var oidcScheme = OpenIdConnectDefaults.AuthenticationScheme;
builder.Services.AddAuthentication(OpenIdConnectDefaults.AuthenticationScheme)
                .AddKeycloakOpenIdConnect(serviceName: "keycloak", realm: "devrealm", oidcScheme, options =>
                {
                    options.ClientId = "next-event-client";
                    options.ResponseType = OpenIdConnectResponseType.Code;
                    options.RequireHttpsMetadata = false;
                    options.TokenValidationParameters.NameClaimType = JwtRegisteredClaimNames.Name;
                    options.SaveTokens = true;
                    options.SignInScheme = CookieAuthenticationDefaults.AuthenticationScheme;
                })
                .AddCookie(CookieAuthenticationDefaults.AuthenticationScheme);

builder.Services.AddCascadingAuthenticationState();


builder.AddAzureBlobClient("BlobConnection");

// Add services to the container.
builder.Services.AddRazorComponents()
    .AddInteractiveServerComponents();
builder.Services.AddFluentUIComponents();

var app = builder.Build();

// Configure the HTTP request pipeline.
if (!app.Environment.IsDevelopment())
{
    app.UseExceptionHandler("/Error", createScopeForErrors: true);
    // The default HSTS value is 30 days. You may want to change this for production scenarios, see https://aka.ms/aspnetcore-hsts.
    app.UseHsts();
}
else
{
    var blobService = app.Services.GetRequiredService<BlobServiceClient>();
    var docsContainer = blobService.GetBlobContainerClient("fileuploads");

    await docsContainer.CreateIfNotExistsAsync();
}

app.UseHttpsRedirection();

app.UseStaticFiles();
app.UseAntiforgery();

app.UseAuthentication();
app.UseAuthorization();


app.MapRazorComponents<App>()
    .AddInteractiveServerRenderMode();

app.MapDefaultEndpoints();

app.MapLoginAndLogout();

app.Run();
