# Delete the workshop

Deleting the CloudFormation stack removes this workshop's computer, disk, network and IAM role/profile. Jarvis, Hermes, their local secret, logs and conversation files on that disk are erased too. Save anything you need first. This does not delete your AWS account or reverse charges already incurred.

## Let your agent do it

Give your agent this instruction from the **same project folder used for deployment**:

> Read docs/CLEANUP.md and the private .workshop state. Check my AWS account and show the exact stack ARN and resources you will delete. Explain that the EC2 disk and conversation history will be erased. Ask for my approval, then delete only that recorded workshop stack and verify that its instance and disk are gone. Do not delete unrelated resources or silently retain anything.

## Commands

Stop the local tunnel with **Control-C**. Inspect your stack first:

```sh
python3 workshop.py status --profile PROFILE --region us-east-1 --stack STACK
```

Copy the exact `StackId` ARN from this attendee's recorded state/status. Before deletion, have the agent record the instance ID and its root-volume ID privately, using the earlier `verify` result or an EC2 read-only lookup. That lets it check the actual disk afterward as well as the stack status. After you approve deletion:

```sh
python3 workshop.py destroy --profile PROFILE --region us-east-1 --stack STACK --account ACCOUNT_ID --stack-id EXACT_STACK_ARN --approve
```

The long ARN identifies this particular stack, even if someone later reuses its name. Do not substitute another attendee's ARN. `destroy` submits deletion; it does not wait for AWS to finish. Run `status` again until deletion completes. If a terminal is interrupted, inspect the same stack; don't create or delete a replacement.

Confirm `DELETE_COMPLETE`, EC2 terminated, and its former root volume no longer present. The template has no `Retain` policy and the root disk has `DeleteOnTermination: true`. If deletion reports `DELETE_FAILED`, read the specific failed resource and resolve the dependency. The helper deliberately will not resubmit an existing deletion receipt: after you approve the retry, use CloudFormation's console or `aws cloudformation delete-stack --stack-name EXACT_STACK_ARN --profile PROFILE --region us-east-1` to retry that **same recorded ARN**. Do not force-delete or retain a billable resource just to make the display green.

After deletion, `.workshop/` may still contain local account IDs, receipts and diagnostics. Those files incur no AWS charges; keep them privately until deletion is confirmed, then remove them locally if desired. They must not be included when you share this kit.

## If the local progress folder is lost

In the AWS console, select the correct account and `us-east-1`, open **CloudFormation**, find your unique workshop stack, and review its resources and ARN. Ask the host to help establish ownership if uncertain. After approval, delete that exact stack in the console and wait for completion. Do not use account-wide cleanup commands. [AWS CloudFormation deletion documentation](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/cfn-console-delete-stack.html).

The kit does not create snapshots, external log destinations, backups or other retained billable resources. If you or an administrator added any, review them separately; deleting this stack cannot delete unrelated/manual additions. AWS control-plane history and existing account-level audit systems may retain records according to their own policies.
