# Configurazione server MCP 21st.dev

Questo repository include il server MCP **21st** configurato in `.mcp.json`.
Il server legge la chiave API dalla variabile d'ambiente `API_KEY_21ST`.

```json
{
  "mcpServers": {
    "21st": {
      "type": "http",
      "url": "https://21st.dev/api/mcp",
      "headers": {
        "x-api-key": "${API_KEY_21ST}"
      }
    }
  }
}
```

## Come attivarlo

1. **Genera una chiave API** su [21st.dev](https://21st.dev) (account → API keys).
   - ⚠️ Non incollare mai la chiave in chat o nel codice: va tenuta solo come
     variabile d'ambiente / secret. Se una chiave viene esposta, revocala e
     rigenerala.

2. **Imposta la variabile d'ambiente `API_KEY_21ST`** nelle impostazioni del tuo
   **environment** su [claude.ai/code](https://claude.ai/code):
   - Apri l'environment collegato a questo repository.
   - Sezione *Environment variables / Secrets*.
   - Nome: `API_KEY_21ST` — Valore: la tua chiave (`21st_sk_...`).
   - Il nome deve corrispondere esattamente a quello in `.mcp.json`.

3. **Avvia una nuova sessione** sullo stesso environment.
   Il server MCP e le variabili d'ambiente vengono letti solo all'avvio della
   sessione: una sessione già in corso non rileva le modifiche.

## Come verificare

In una nuova sessione, i tool del server appaiono con prefisso `mcp__21st__*`.
Se non compaiono, controlla che:
- la variabile `API_KEY_21ST` sia effettivamente impostata nell'environment;
- la chiave sia valida (non revocata/scaduta);
- la sessione sia stata avviata **dopo** aver impostato la variabile.

## Documentazione

- Claude Code su web (environment, variabili d'ambiente):
  https://code.claude.com/docs/en/claude-code-on-the-web
