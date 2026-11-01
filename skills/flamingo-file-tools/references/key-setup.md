# One-time private key setup

Use the customer's own existing RapidAPI application key and subscription to the selected API. No key is included in this skill. An already configured `RAPIDAPI_KEY` in the actual Python execution environment remains supported; no new setup is needed in that case.

## Check the execution host first

The user's Terminal and the agent's Python command must run on the **same computer and OS account**, with the same accessible filesystem. An exported variable in a separate Terminal does not necessarily reach an already running desktop agent. A file on a laptop does not configure a remote sandbox.

The private-file route below works for a local macOS/Linux agent, or an execution host the user can access through their own private Terminal. A remote environment may instead have an existing private secret setting for `RAPIDAPI_KEY`. If neither private route exists, explain that access cannot be configured in this host. Do not ask for a key or credential-file upload in chat, start another agent, or weaken file permissions.

## Enter the key outside chat

1. The agent fetches [scripts/setup_key.py](../scripts/setup_key.py) through Agensi and writes its exact contents unchanged to a temporary file. Keep it until the user finishes.
2. Give the user one command containing the **actual quoted absolute path** to that temporary script, such as `python3 "/actual/temporary/path/setup_key.py"`. They run it in their own Terminal on the same execution host, rather than an agent tool's input box.
3. In the [RapidAPI console](https://rapidapi.com/console), the user selects their existing application and opens its Authorizations page. They copy their application key and paste it only at the setup script's hidden prompt. Do not request a provider proxy secret or create a new authorization merely for setup. [RapidAPI key documentation](https://docs.rapidapi.com/v2/docs/keys-and-key-rotation).
4. The helper requires an interactive Terminal with hidden input. It stops if that cannot be provided. It creates a new private local file at `~/.config/flamingo-api/rapidapi.key` and reports only its absolute path and status. The key is stored locally with private file permissions; it is not written into an Agensi skill or shared project. An existing destination is never overwritten or rotated.
5. The user can return “done” and the printed **path** in the same chat. They must not send the key or attach the credential file. The agent removes only the temporary setup script afterward and keeps the user's separate credential configuration.

If the destination already exists, use the user's existing private configuration or explain the refusal. Do not delete or replace it silently. Setup checks local format/storage only; it does not contact RapidAPI, verify authentication or subscriptions, or authorize a file upload.

## Use the selected file

Append `--key-file` and the actual quoted absolute path to the selected processing command. For example, an already authorized CSV export uses this shape:

```text
python3 "/temporary/access_client.py" --workspace "/selected/workspace" --file "selected.accdb" --format csv --key-file "/printed/private/path/rapidapi.key" --consent-upload
```

The agent supplies the actual command; the user should not need to construct it. Each client is independent of the setup script. Only the processing client reads the selected key file; do not read it into model context. Explicit file selection takes precedence over the environment, with no fallback if it fails. The client also refuses selected processing inputs containing the credential.

The original upload, quota and result-review requirements still apply. A successful setup is local readiness, not a successful API request.
