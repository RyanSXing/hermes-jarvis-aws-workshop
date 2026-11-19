# What gets created, and what it costs

Each attendee gets one independent stack in **US East (N. Virginia), `us-east-1`**. AWS calls a group of resources managed together a *CloudFormation stack*.

| Resource | Plain-language purpose | Main cost |
| --- | --- | --- |
| One EC2 `t3.small`, Ubuntu 24.04 | The computer running Hermes and Jarvis | About $0.0209/hour while running |
| One encrypted 30 GiB gp3 root disk | Stores software, configuration and local conversations | About $2.40/month, prorated while it exists |
| One automatically assigned public IPv4 address | Lets the computer download software and reach AWS services | $0.005/hour while allocated |
| VPC, subnet, internet gateway, route table/route and attachment/association | The computer's basic network | No separate hourly charge for these objects |
| Security group with empty inbound rules | Blocks unsolicited incoming connections | No separate charge |
| EC2 IAM role and instance profile | Let EC2 use SSM and the selected Bedrock model without stored AWS keys | No separate charge |
| CloudFormation wait handle and wait condition | Tell deployment whether initial setup worked | No separate resource-hour charge |
| Amazon Bedrock model calls | Produce answers | Tokens used, separately from the computer |

The disk and network interface/address are attached to the instance; they are not extra computers. The template does not create a NAT gateway, paid private endpoint, S3 bucket, database, load balancer, DNS name, logging destination or SSH key pair. The two Jarvis/Hermes services run on the same EC2 machine. Standard CPU credits avoid T3 Unlimited surplus-credit charges, but sustained work can slow down when credits are depleted.

## Planning estimate

Using a 730-hour month: `$0.0209 + $0.005 + $2.40 / 730 ≈ $0.0292/hour`, rounded to **$0.03/hour per attendee** before model use, data transfer, tax and credits.

| Running time | Approximate infrastructure cost per attendee |
| --- | --- |
| 4 hours | $0.12 |
| 24 hours | $0.70 |
| 730 hours | $21.31 |
| 30 attendees × 4 hours | $3.50 total |

Setup and idle time count too. These estimates assume this exact size and disk, not a larger instance. Free-tier credits and account eligibility vary; do not promise that the workshop is free. A spending estimate is not an enforced spending limit.

EC2's official T3 page listed $0.0209/hour for this region when checked on **2026-11-18**. Public IPv4 was $0.005/hour. The disk calculation uses $0.08/GiB-month. Recheck before an event: [EC2 T3 pricing](https://aws.amazon.com/ec2/instance-types/t3/), [EBS pricing](https://aws.amazon.com/ebs/pricing/), [AWS's N. Virginia gp3 comparison](https://docs.aws.amazon.com/emr/latest/ManagementGuide/emr-plan-storage-compare-volume-types.html), and [IPv4 pricing](https://aws.amazon.com/vpc/pricing/).

## Model usage

The pinned model is `us.amazon.nova-micro-v1:0`, a US inference profile. Its allowed destination regions are reflected in the instance policy. Review organizational restrictions before deployment.

AWS's published Nova Micro example rates are **$0.035 per million input tokens** and **$0.14 per million output tokens**. For illustration, 10,000 input plus 500 output tokens would cost about `$0.00042`. This is arithmetic, not a measured Hermes bill: instructions, conversation history and auxiliary calls add tokens. A short test is expected to be under one cent, but no dollar cap is enforced. Confirm the current region/model rate on [Bedrock pricing](https://aws.amazon.com/bedrock/pricing/); the example rates also appear in [AWS's Nova presentation](https://d1.awsstatic.com/onedam/marketing-channels/website/aws/en_US/events/approved/reinvent-2025/reinvent/2024/slides/aim/AIM398-NEW_Practical-generative-AI-using-Amazon-Nova.pdf).

Browser speech recognition and native speech synthesis require no ElevenLabs subscription or key in this kit. Browser support, network access and vendor processing terms still apply. The kit is not a fully offline voice system.

## Ending charges

Closing Jarvis, quitting the agent or closing the Session Manager tunnel leaves EC2 running. Stopping EC2 leaves its disk billable. Deleting the stack removes the workshop instance and its root disk, plus its network and IAM resources. No automatic shutdown timer is installed. Set a human reminder, and follow [CLEANUP.md](CLEANUP.md). Charges already incurred remain payable; billing reports can lag.
