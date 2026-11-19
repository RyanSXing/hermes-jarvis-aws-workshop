# Sign in without sharing secret keys

Do this before the event. A new AWS account can require email/phone/payment verification and activation. Its plan, service restrictions and available quota must permit this workshop. Account creation or changing plans is a separate decision; the deployment script does neither.

## You already have a working profile

Keep it. Ask your agent to inspect `aws --version` and verify `aws sts get-caller-identity --profile PROFILE --region us-east-1`. The result must identify the intended account. Renew an expired profile using its existing sign-in method. Do not switch an established SSO workflow to another login method without a reason.

## You have a personal account or ordinary AWS console sign-in

Use browser-based **`aws login`**, available with AWS CLI **2.32.0 or later**. Ask your agent to check the installed CLI version and existing identity, then request approval to run `aws login --profile workshop --region us-east-1` in your local terminal. You complete the browser sign-in/MFA yourself. The agent waits for it to finish, then checks STS under that profile.

This creates temporary CLI credentials from your console identity; you do not copy access keys. Non-root IAM users/roles need the appropriate local-development sign-in permission, documented as `SignInLocalDevelopmentAccess`. The host/administrator should review and grant it if necessary. Do not attach policies automatically without approval. [Official browser login instructions](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-sign-in.html).

If the CLI is too old, have your agent guide you through the official update and any OS password prompt first. Do not use a secret-key copy/paste workaround.

## Your host or company uses IAM Identity Center

The host gives you an access-portal/start URL, SSO region, account and role. Your agent configures a named profile with `aws configure sso --profile workshop`, then runs `aws sso login --profile workshop` when you are ready. You finish browser sign-in. The **SSO region** may differ from the **deployment region**; the workshop deployment remains `us-east-1`. [Official SSO instructions](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-sso.html).

## You only have the account's root sign-in

For an event, the simplest route is to ask the host for a prepared sandbox account/role or help establishing a non-root administrator sign-in **before arrival**. AWS recommends federation and protecting root with MFA. Current account experiences differ, so the agent should follow [AWS's account setup guide](https://docs.aws.amazon.com/IAM/latest/UserGuide/getting-started-account-iam.html) for your account rather than silently creating IAM users or an AWS Organization.

Root can sign in with `aws login`, but it has unrestricted authority. The workshop helper stops root usage by default. If you deliberately choose to continue as root after the explanation, explicitly tell the agent; it may add `--allow-root` to the workshop commands. That is separate from approval to deploy, install, test or delete. No root access keys are required or requested.

Do not send login URLs containing authorization codes, cookies, MFA codes, passwords, `.aws` files or API tokens to the host or agent chat. A sign-in mistake is fixed by selecting the right profile/account, not by opening EC2 ports.
