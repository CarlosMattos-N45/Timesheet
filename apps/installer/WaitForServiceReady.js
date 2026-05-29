// WaitForServiceReady.js — WiX CustomAction (JScript)
// Faz polling em http://127.0.0.1:<TIMESHEET_PORT>/api/v1/ready
// 60 tentativas × 1s = 1 minuto de timeout máximo
// Retorna 1 em sucesso, lança exceção em falha (aborta instalação)

function WaitForReady() {
    var session = Session;
    var port = session.Property("TIMESHEET_PORT");
    if (!port || port === "") {
        port = "8765";
    }
    var url = "http://127.0.0.1:" + port + "/api/v1/ready";
    var maxAttempts = 60;
    var delayMs = 1000;

    var xhr = new ActiveXObject("MSXML2.XMLHTTP");
    var ready = false;

    for (var i = 0; i < maxAttempts; i++) {
        try {
            xhr.open("GET", url, false);
            xhr.setRequestTimeout(2000);
            xhr.send();
            if (xhr.status === 200) {
                ready = true;
                break;
            }
        } catch (e) {
            // Serviço ainda não está pronto — aguardar
        }
        // Delay de 1 segundo entre tentativas
        WScript.Sleep(delayMs);
    }

    if (!ready) {
        session.Log("WaitForServiceReady: backend nao ficou pronto em " + maxAttempts + "s na porta " + port);
        return 1603; // ERROR_INSTALL_FAILURE
    }

    session.Log("WaitForServiceReady: backend pronto em " + url);
    return 1; // success
}
