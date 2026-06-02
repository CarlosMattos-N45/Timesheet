## Arquitetura Interna

Organização em módulos e camadas do código-fonte.

---

```mermaid
%%{init: {'theme': 'neutral'} }%%
flowchart TD
  subgraph Backend["Backend (Python 3.12 + FastAPI)"]
    direction TB
    subgraph auth["auth"]
      R_auth[Router] --> S_auth[Service] --> Repo_auth[Repository]
    end
    subgraph terceiros["terceiros"]
      R_terc[Router] --> S_terc[Service] --> Repo_terc[Repository]
    end
    subgraph jornadas["jornadas"]
      R_jorn[Router] --> S_jorn[Service] --> Repo_jorn[Repository]
    end
    subgraph marcacoes["marcacoes"]
      R_marc[Router] --> S_marc[Service] --> Repo_marc[Repository]
    end
    subgraph atividades["atividades"]
      R_atv[Router] --> S_atv[Service] --> Repo_atv[Repository]
    end
    subgraph relatorios["relatorios"]
      R_rel[Router] --> S_rel[Service] --> Repo_rel[Repository]
    end
    subgraph auditoria["auditoria"]
      R_aud[Router] --> S_aud[Service] --> Repo_aud[Repository]
    end
    subgraph scheduler["scheduler (APScheduler)"]
      SCH[Scheduler Job]
    end
    S_jorn -.->|usa| S_marc
    S_rel -.->|usa| S_jorn
    S_rel -.->|envia email| SMTP_svc["smtplib\n+ Jinja2"]
    S_rel -.->|gera PDF| PDF_svc["WeasyPrint\n+ Jinja2"]
    SCH -.->|dispara| S_rel
    S_marc -.->|registra| S_aud
    S_jorn -.->|registra| S_aud
    Repo_auth & Repo_terc & Repo_jorn & Repo_marc & Repo_atv & Repo_rel & Repo_aud --> DB[("SQLite + SQLCipher\ntimesheet.sqlite")]
    SCH --> DB_SCH[("SQLite\nscheduler.sqlite")]
  end

  subgraph Frontend["Frontend (React 18 + TypeScript)"]
    direction TB
    Pages["Pages\n/login /jornadas /relatorios\n/cadastro /configuracoes"] --> Hooks["TanStack Query\nhooks"] --> API_client["Axios\n+ JWT interceptor"]
  end

  subgraph Agent["Agente (.NET 8 WPF)"]
    direction TB
    WPF_UI["WPF UI\n+ NotifyIcon tray"] <-->|"Named Pipes"| SvcHost["Service Host\n(Windows Service)"]
    SvcHost --> Domain["Domain\nstate machine"]
    Domain --> InfraHTTP["Infra HTTP\nPolly circuit breaker"]
    Domain --> InfraSQLite["Infra SQLite\nEF Core"]
    InfraSQLite --> DB_Agent[("SQLite\nagent-queue.sqlite")]
  end

  API_client -->|"REST /api/v1/"| Backend
  InfraHTTP -->|"REST /api/v1/"| Backend
  WinLogin["Windows Login\nEvent"] --> SvcHost
  Inactivity["Win32 GetLastInputInfo\npolling 30s"] --> SvcHost
```

---

_Criado em: 2026-06-02 18:40:00_
