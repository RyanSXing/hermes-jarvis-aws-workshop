# Workshop infrastructure

`workshop.yaml` is for **fresh stacks in `us-east-1`**. Deploy it through the
workshop CLI, which checks the Region before requesting creation. It has no
parameters and requires `CAPABILITY_IAM`. It contains no account ID, instance ID,
profile name, password, or API key.

The template declares 13 resources:

| Resources | Purpose |
| --- | --- |
| One EC2 instance | Ubuntu 24.04, `t3.small`, standard CPU credits |
| One security group | No inbound rules; outbound access for downloads and AWS |
| One IAM role and one instance profile | Session Manager and narrowly scoped Nova Micro access |
| One VPC and one subnet | An isolated workshop network |
| One internet gateway and its attachment | Outbound connectivity without a NAT gateway |
| One route table, default route, and subnet association | Make outbound routing ready before bootstrap |
| One wait-condition handle and one wait condition | Report local installation success or failure |

The instance also receives a 30 GiB encrypted gp3 root volume, a primary network
interface, and an automatically assigned public IPv4 address. These are part of
the EC2 configuration, not additional template resources. The disk and interface
delete with the instance; the public address is released. The template creates
no buckets, snapshots, Elastic IPs, private subnets, VPC endpoints, load balancers,
or log groups. The default behavior is to delete every workshop resource with
the stack. Save any files you need before approving deletion.

The public address enables outbound connections. It does not provide public
application access: the security group allows no inbound traffic. Session
Manager provides the terminal and local port-forwarding connection. The EC2
role uses IMDSv2 credentials; no static AWS keys are installed.

## Bootstrap and model

Bootstrap installs `hermes-agent==0.19.0` and `boto3==1.44.6`, then checks package
versions, imports, CLI help, and the local SSM service. It does not send a model
request or start a messaging/Jarvis gateway. Jarvis installation is a separate
CLI step. The wait condition has a 30-minute timeout. Any shell failure attempts
to send a failure signal; a network failure that prevents signaling eventually
times out. Stack completion must still be followed by checking that SSM reports
the instance as `Online`.

The model is `us.amazon.nova-micro-v1:0`. IAM invocation permissions cover its
`us-east-1` inference profile and the Nova Micro foundation model in `us-east-1`,
`us-east-2`, and `us-west-2`. Discovery list operations require wildcard resources;
they do not grant access to invoke other models. The terminal configuration uses
manual approvals and at most three agent turns. Jarvis's separate configuration
further restricts its API to zero tools.

Only the two direct Python application dependencies are pinned here. The Ubuntu
AMI is resolved from Canonical's public SSM parameter at deployment time, and
the OS package repository, AWS CLI download, and packaging-tool upgrades can
change. Rebuilding is therefore not a byte-for-byte reproduction of an older
instance.

Use a new stack for another workshop. This template is not an in-place software
updater: changing user data does not reliably rerun installation, and a new
bootstrap must not reuse an old wait-condition handle.

## Cost inputs

Before credits, an indicative `us-east-1` running cost is about **$0.03/hour**, plus
Bedrock requests and any chargeable data transfer. Inputs checked while preparing
this starter are:

| Item | Estimate |
| --- | --- |
| Linux `t3.small` On-Demand | $0.0209/hour |
| One public IPv4 address | $0.005/hour |
| 30 GiB gp3 storage | 30 × $0.08 = $2.40/month |

Using 730 hours/month, that is approximately $21.31/month for these three items
if left running continuously. Standard CPU credits avoid surplus CPU-credit
charges but can slow installations. Storage continues to cost money when an
instance is stopped. Credits and free-plan eligibility vary by account; do not
assume the workshop is free.

Check current [EC2 T3](https://aws.amazon.com/ec2/instance-types/t3/),
[public IPv4](https://aws.amazon.com/vpc/pricing/),
[EBS](https://aws.amazon.com/ebs/pricing/), and
[Bedrock](https://aws.amazon.com/bedrock/pricing/) pricing before deployment.

## Validation and provenance

Local checks performed on this new template cover YAML parsing, resource and
reference invariants, security settings, extracted Bash syntax, and mocked
success/failure signaling. The mock checks make no network requests. `cfn-lint`
and `cfn-guard` were unavailable in the packaging environment; those validation
layers were not run. No account-aware CloudFormation validation or deployment
was performed for this starter template. Local checks cannot verify account
quotas, permissions, AMI availability, or package-download success.

The template is adapted from the MIT-licensed
[reference project](https://github.com/JiaDe-Wu/sample-hermes-agent-on-aws-with-bedrock/tree/c9c5a46654e97d45c8bfb6f6f4ec66852cbe0f2b),
and from the workshop adaptation that was previously exercised on EC2. It keeps
that model configuration while removing optional messaging and endpoint
resources and fixing failure signaling. Retain the reference project's MIT
notice with redistributed copies; the starter's third-party notices carry the
upstream license text. The new portable template itself has not been deployed.
