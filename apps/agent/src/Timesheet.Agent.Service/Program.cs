using Microsoft.Extensions.Hosting;

var builder = Host.CreateApplicationBuilder(args);
builder.Services.AddWindowsService(opts =>
{
    opts.ServiceName = "TimesheetAgent";
});
var host = builder.Build();
host.Run();
