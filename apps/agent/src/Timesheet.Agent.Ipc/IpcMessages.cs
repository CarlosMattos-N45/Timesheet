using System.Collections.Generic;
using System.Text.Json.Serialization;

namespace Timesheet.Agent.Ipc;

[JsonPolymorphic(TypeDiscriminatorPropertyName = "type")]
[JsonDerivedType(typeof(DialogRequest), "DIALOG_REQUEST")]
[JsonDerivedType(typeof(DialogResponse), "DIALOG_RESPONSE")]
[JsonDerivedType(typeof(ToastMessage), "TOAST")]
[JsonDerivedType(typeof(StatusPush), "STATUS_PUSH")]
public abstract record IpcMessage;

// kind: CONFIRM_INICIO_ANTECIPADO | CONFIRM_RETORNO_FORA_JANELA | PROMPT_FIM_JORNADA | PROMPT_ATIVIDADE
public sealed record DialogRequest(string Id, string Kind, Dictionary<string, string> Payload) : IpcMessage;

// answer: SIM | NAO | TIMEOUT; payload opcional (ex.: atividade do PROMPT_FIM_JORNADA)
public sealed record DialogResponse(string Id, string Answer, Dictionary<string, string>? Payload = null) : IpcMessage;

public sealed record ToastMessage(string Title, string Body, int DurationS) : IpcMessage;

public sealed record StatusPush(string Estado, int PendentesCount) : IpcMessage;
