# Build your workshop assistant

The easiest path is to open this folder in your coding agent and use the prompt in [README.md](../README.md). These steps also let a person run the workshop manually.

## 1. Check your laptop and AWS sign-in

Use Python **3.10 or newer**, AWS CLI **v2**, Chrome and the Session Manager plugin. Git is needed on EC2 and installed by the template; on your laptop it is optional if you downloaded the ZIP. On Windows, substitute `py -3` for `python3` if needed. Commands below work in a terminal from this project's folder; replace uppercase placeholders with your own values.

Install tools from their official pages:

- [Python downloads](https://www.python.org/downloads/)
- [AWS CLI v2 installation](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html)
- [Session Manager plugin installation by operating system](https://docs.aws.amazon.com/systems-manager/latest/userguide/session-manager-working-with-install-plugin.html)

Your agent can help install them, but you enter any laptop administrator password yourself. A working laptop microphone and permission to use the browser's speech-recognition service are also needed.

Use a non-root administrator sign-in in your own sandbox account or the workshop account supplied by the host. See [AWS_SIGN_IN.md](AWS_SIGN_IN.md) for the complete personal-account, root-only and host-account paths. For an ordinary console sign-in, an agent can use browser-based `aws login` after checking AWS CLI 2.32.0+ and getting your permission. If your organization provides IAM Identity Center, configure and sign in to its profile:

```sh
aws configure sso --profile workshop
aws sso login --profile workshop
```

Your host supplies the SSO start URL, account and role. Do not invent those values. If you already have another working profile, use it instead. SSO is one option, not a requirement to create an AWS organization. An agent can guide other current AWS browser-based sign-in methods using official documentation. Never paste AWS keys into chat or this project. [AWS CLI SSO instructions](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-sso.html).

Verify the exact account and region:

```sh
aws sts get-caller-identity --profile PROFILE --region us-east-1
python3 workshop.py doctor --profile PROFILE --region us-east-1 --stack STACK
python3 workshop.py plan --profile PROFILE --region us-east-1 --stack STACK
```

Choose a unique stack name such as `hermes-alex-a7d2`. Keep that same name for every step. The CLI stores private progress under `.workshop/STACK/`. Keep this folder until cleanup is finished; do not commit or send it to other attendees.

Your agent also checks that the intended model profile is visible, without sending a prompt:

```sh
aws bedrock get-inference-profile --inference-profile-identifier us.amazon.nova-micro-v1:0 --profile PROFILE --region us-east-1
```

This [read-only lookup](https://docs.aws.amazon.com/cli/latest/reference/bedrock/get-inference-profile.html) does not prove the instance can invoke the model: IAM permissions, organization policies and model quotas are checked separately or by the later approved test.

## 2. Review and approve the cloud computer

Read [the resource and cost explanation](COSTS.md). The template creates one small computer, its disk, a small network and the permissions it needs. It also creates setup-status tracking resources. The computer can reach the internet to download software, but its firewall allows **zero incoming connections**. You reach it through AWS Session Manager.

The agent should show your account, region, stack name and estimate, then ask for approval. Once you approve:

```sh
python3 workshop.py deploy --profile PROFILE --region us-east-1 --stack STACK --account ACCOUNT_ID --approve
```

The stack's setup can take around 10–25 minutes. Use `status` to inspect its progress or resume watching after a terminal interruption. Do not create a second stack because the first command timed out.

```sh
python3 workshop.py status --profile PROFILE --region us-east-1 --stack STACK
```

Wait for `CREATE_COMPLETE` and the instance to become available in Systems Manager. Errors must be diagnosed before proceeding.

## 3. Install Jarvis on that computer

This adds software to the same EC2 instance; it creates no additional cloud infrastructure. Approve this change if it was not included in your deployment approval, then run:

```sh
python3 workshop.py install --profile PROFILE --region us-east-1 --stack STACK --account ACCOUNT_ID --approve
python3 workshop.py status --profile PROFILE --region us-east-1 --stack STACK
```

The installer downloads the pinned Jarvis source, adds the Hermes bridge and voice repair, runs its tests, builds the page and starts two services. The internal API key is generated on EC2 and never belongs in your browser or chat. No prompt is sent during installation.

Allow several minutes. A large overlay is transferred in small parts. If the helper returns `transfer_not_complete`, inspect `status`; once the saved part is `Success`, rerun the same approved `install` command to continue. This resumes known parts rather than resending them. Stop and inspect unknown or failed parts. Continue only when the final `install` operation reports `Success`. The agent then runs the approved diagnostics:

```sh
python3 workshop.py verify --profile PROFILE --region us-east-1 --stack STACK --account ACCOUNT_ID --approve
python3 workshop.py status --profile PROFILE --region us-east-1 --stack STACK --show-output
```

The checks inspect the private services and AWS security settings without asking the model anything.

## 4. Approve one model test

Bedrock charges for model usage. The test sends:

> Reply with one short sentence: Hello from Hermes on Amazon Bedrock. Do not use tools.

It is usually a fraction of a cent with this model, but the script does not impose a dollar cap and Hermes can make extra background model calls. After separate approval:

```sh
python3 workshop.py test --profile PROFILE --region us-east-1 --stack STACK --account ACCOUNT_ID --approve
python3 workshop.py status --profile PROFILE --region us-east-1 --stack STACK --show-output
```

A successful result contains a completed, nonempty Hermes answer. If it fails or times out, inspect the saved result before considering another paid request.

## 5. Open Jarvis and speak

Approve the private Session Manager connection (or include it in the setup approval). Run this **on your laptop**, then keep the terminal open:

```sh
python3 workshop.py connect --profile PROFILE --region us-east-1 --stack STACK --account ACCOUNT_ID --approve
```

Open **http://127.0.0.1:8787** in Chrome. Click **INITIALISE**, allow the microphone, and wait for the startup animation to finish and **STANDBY** to appear. Then hold **Space** while speaking and release it to send. The first Space on an unstarted page only powers it on; it does not send a question. For example:

> Hey Jarvis, explain what an AI agent is in one sentence.

Each spoken request uses Bedrock. The first request may take longer. You should see a reply and hear it spoken. Keep Chrome focused while using Space. The page should say **Conversation only**. Try explanations, rewriting and brainstorming; it cannot check live weather or access your inbox.

If you only see your own words and no answer, use [troubleshooting](TROUBLESHOOTING.md). If the text reply appears but is silent, check browser audio/volume; that is different from a model failure.

Press **Control-C** in the tunnel terminal when finished with the browser connection. The EC2 computer keeps running and charging until you stop/delete it. Use [cleanup](CLEANUP.md) after the workshop.

## Optional: a terminal on EC2

Use the instance ID from `status`:

```sh
aws ssm start-session --profile PROFILE --region us-east-1 --target INSTANCE_ID
```

Inside the remote terminal:

```sh
sudo su - ubuntu
source ~/hermes-venv/bin/activate
hermes chat --help
```

`hermes chat --help` is only help text. `hermes chat` starts interactive Hermes; sending messages consumes model usage and the CLI has more tools than the conversation-only web API. Keep the workshop exercise in Jarvis unless you deliberately approve a broader tool demonstration. Exit the chat and shells with `/exit` and `exit` as appropriate.

## If using AWS CloudShell

Deployment/install commands can run in CloudShell after the agent inspects its authenticated identity and CLI options. Use its existing credentials; do not upload your credential files. Upload this clean project or clone the published repository. Preserve `.workshop/` state on the machine performing deployment. The laptop tunnel still runs locally: install AWS CLI/plugin, sign in to the same account, and use the recorded instance ID with `aws ssm start-session --document-name AWS-StartPortForwardingSession` as documented by AWS. A browser on your laptop cannot reach CloudShell's `127.0.0.1`.

Use `--profile -` for CloudShell's existing ambient credentials instead of a named laptop profile. The account check still applies. If state is moved to the laptop, transfer it privately and recheck the account before use.
