# Your own voice assistant: Hermes + Jarvis on AWS

Give this folder to your coding agent. It contains the instructions and automation to build a private voice assistant in **your own AWS account**.

[Download the kit as a ZIP](https://github.com/RyanSXing/hermes-jarvis-aws-workshop/archive/refs/heads/main.zip), or clone `https://github.com/RyanSXing/hermes-jarvis-aws-workshop.git`.

You will get:

- **Hermes Agent** running on one Amazon EC2 computer.
- **Amazon Bedrock Nova Micro** providing the AI answers. The computer uses an IAM role, so you do not put AWS keys in the app.
- **Jarvis** in your browser: hold **Space**, speak, then release to send; hear the reply aloud.
- **Session Manager** for a secure terminal and browser connection, with no public inbound ports.
- A cleanup command that removes the workshop's cloud resources.

This edition is for conversation: explanations, brainstorming, rewriting and learning. Web search, live weather, email, Discord, camera/phone control and image generation are not enabled. The Jarvis API has no agent tools. Browser speech recognition may use the browser vendor's servers; use harmless practice prompts.

## Start here

1. Download and unzip this project, or clone its repository.
2. Open this folder in a coding agent that can read files and run a terminal.
3. Paste the following instruction:

> Set up this Hermes + Jarvis AWS workshop for me. Read AGENTS.md, README.md and docs/SETUP.md first, then follow the included workshop.py workflow. Inspect my environment and AWS identity before making changes. Explain the resources and estimated cost in simple language. Ask for my approval before creating AWS resources, changing the instance, running a billable model test, or deleting anything. Never ask me to paste secret keys into chat. Continue through deployment, private connection, and one approved prompt. Verify the result, tell me what is still untested, and show me cleanup instructions. Do not change the pinned versions or replace the private tunnel with public ports.

Your agent can do the technical work. You still handle AWS/browser sign-in, approve costs, allow microphone access and speak the final voice test. Expect roughly **20–40 minutes**, with extra time if you need an AWS account or permissions.

## Before you attend

Bring an AWS account with permission to use EC2, CloudFormation, IAM, Systems Manager and Bedrock; a laptop; Chrome; a microphone; Python 3.10+; AWS CLI v2; and the AWS Session Manager plugin. Your agent can check these and guide installation. A non-root workshop administrator sign-in is recommended. Event accounts supplied by the host also work.

Budget approximately **$0.03/hour per running setup**, plus model use, data transfer and tax. Four running hours are about **$0.12** for the machine, disk and address. These are estimates, not a free-tier promise or spending cap. [Cost details and sources](docs/COSTS.md).

## Guides

- [Step-by-step setup](docs/SETUP.md) and [AWS sign-in help](docs/AWS_SIGN_IN.md)
- [Agent instructions](AGENTS.md)
- [Event host checklist](docs/HOST_GUIDE.md)
- [Troubleshooting](docs/TROUBLESHOOTING.md)
- [Delete the workshop](docs/CLEANUP.md)
- [What has been tested](docs/VALIDATION.md)
- [Versions and upstream attribution](THIRD_PARTY_NOTICES.md)

The integration and voice repair ran successfully in the original workshop. This portable package adds account checks and repeatable setup. A fresh-account rehearsal is still required before using it for an event; see the validation report. Closing the browser or tunnel **does not stop AWS charges**.
