# Find the failed step

Use `status` first and keep `.workshop/` intact. Avoid repeated deploy/install/test commands while the previous outcome is unknown. An agent should use saved command IDs to inspect the same operation.

| What you see | What to check |
| --- | --- |
| Wrong AWS account | Stop. Verify the exact profile with STS; sign in to the intended account before any mutation. Changing the region does not change the account. |
| Expired sign-in | Renew the existing profile's browser/SSO session. Never paste keys into chat. |
| `AccessDenied` during deployment | Read the failing API/resource. The provisioner needs deployment permissions; ask the host about the role, permission boundary or SCP. Do not grant broad permissions as a blind fix. |
| Stack rolls back or setup times out | Read CloudFormation events. If the instance remains accessible, inspect `/var/log/cloud-init-output.log` without exposing the signal URL. Downloads, account restrictions, package availability or resource quota can fail. Do not create another stack until the first is accounted for. |
| EC2 is running but SSM is offline | Allow initial bootstrap time; check its instance role, SSM agent, outbound internet/DNS and region. Opening inbound SSH is not the fix. |
| Install fails or an existing checkout is found | Read the saved SSM output and `/home/ubuntu/jarvis-install.log`. The installer intentionally refuses to overwrite a live installation. Review and approve a targeted repair; do not delete its state and retry blindly. |
| Model access error after healthy install | Check the exact Nova Micro inference profile, EC2 role and organizational region/model restrictions. The US profile may route among the permitted US regions. Discovery success does not prove invocation permission or quota. |
| `SessionManagerPlugin is not found` | Install AWS's official Session Manager plugin on the **laptop**, then reopen its terminal if PATH changed. |
| Local port 8787 is busy | An old tunnel or another program may own it. Identify that process and close only the intended old tunnel. Do not kill unrelated processes or expose a public port. |
| Browser cannot load `127.0.0.1:8787` | Keep the laptop tunnel open; verify the correct instance and that both remote services are active. A CloudShell tunnel does not forward to your laptop. |
| Page hears nothing | Click INITIALISE, allow microphone access and wait for STANDBY first. Then keep Chrome focused and hold Space while speaking. Check the selected microphone and browser speech restrictions. |
| Captions appear but no answer | Release Space. Check that the bundled voice fix is installed, then inspect bridge/API health and diagnostics. Do not assume visible captions mean the backend received the request. |
| Answer appears as text but is silent | Check system/browser volume, muted tab, selected output device and speech-synthesis availability. After initialization, press lowercase **t** with no modifier to hear the native audio test: it uses fixed text, not a model prompt. |
| Answer says it cannot get weather/email | Expected: this API is conversation-only. Try “Explain EC2 in one sentence.” |
| Request hangs or says a run is already active | Inspect the existing Hermes run/bridge state and saved SSM command. No automatic duplicate prompt is sent. Do not delete the active-run receipt to unlock it while the old run may be billed. |
| Jarvis forgets an older part of the conversation | The bridge sends at most six previous completed turns as recent history. Refreshing the page starts a new browser conversation; it does not stop EC2. |
| Cleanup fails | Inspect the failed resource and manual dependencies. After resolving a confirmed `DELETE_FAILED` and obtaining retry approval, retry the same recorded ARN using the AWS console/manual CLI in CLEANUP.md. The helper deliberately will not resubmit its deletion receipt. Do not force-retain billable resources. |

For an approved diagnosis on EC2, these inspect services without generating a model response:

```sh
sudo systemctl status jarvis-hermes-api.service jarvis-hermes-bridge.service --no-pager
sudo ss -ltnp '( sport = :8642 or sport = :8787 )'
curl --fail http://127.0.0.1:8787/health
```

Both ports must listen on `127.0.0.1`, not `0.0.0.0` or a public address. Logs may contain user text and private diagnostics; review locally and redact before sharing. Never print `/home/ubuntu/.config/jarvis-hermes/api.env` or return API credentials in a screenshot/chat.

For confirmed errors requiring a model retest, explain the repair and ask for a new one-prompt approval. One user prompt can involve more than one billable model call. Do not loop tests until one happens to pass.
