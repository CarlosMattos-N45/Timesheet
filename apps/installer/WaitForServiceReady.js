// WaitForServiceReady.js — WiX CustomAction (JScript)
// Faz polling em http://127.0.0.1:<TIMESHEET_PORT>/api/v1/ready
// 60 tentativas × 1s = 1 minuto de timeout máximo
// Retorna 1 em sucesso, lança exceção em falha (aborta instalação)

function WaitForReady() {
    var session = Session;
    // Em custom actions deferred, a porta chega via CustomActionData (injetada por SetProperty)
    var port = session.Property("CustomActionData");
    if (!port || port === "") {
        port = "8765";
    }
    var url = "http://127.0.0.1:" + port + "/api/v1/ready";
    var maxAttempts = 60;
    var delayMs = 1000;

    var ready = false;

    for (var i = 0; i < maxAttempts; i++) {
        try {
            // MSXML2.ServerXMLHTTP.6.0 funciona em contexto de serviço (sem WinInet/proxy)
            var xhr = new ActiveXObject("MSXML2.ServerXMLHTTP.6.0");
            xhr.open("GET", url, false);
            // setTimeouts(resolveTimeout, connectTimeout, sendTimeout, receiveTimeout) em ms
            xhr.setTimeouts(2000, 2000, 2000, 2000);
            xhr.send();
            if (xhr.status === 200) {
                ready = true;
                break;
            }
        } catch (e) {
            // Serviço ainda não está pronto — aguardar
        }
        // Busy-wait: WScript.Sleep não existe em custom actions JScript do msiexec
        var end = new Date().getTime() + delayMs;
        while (new Date().getTime() < end) { /* aguardar */ }
    }

    if (!ready) {
        session.Log("WaitForServiceReady: backend nao ficou pronto em " + maxAttempts + "s na porta " + port);
        return 1603; // ERROR_INSTALL_FAILURE
    }

    session.Log("WaitForServiceReady: backend pronto em " + url);
    return 1; // success
}
