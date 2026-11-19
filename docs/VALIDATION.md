# Validation and limits

Prepared on **2026-11-18**. This report distinguishes the original working installation from the new portable workshop package.

## Previously observed on the original installation

- One Ubuntu 24.04 `t3.small` ran Hermes 0.19.0 with boto3 1.44.6, using the EC2 role and `us.amazon.nova-micro-v1:0`.
- CloudFormation completed; SSM was online; the security group had no inbound rules; IMDSv2 was required; the 30 GiB gp3 root disk was encrypted and set to delete with the instance.
- The Jarvis frontend built successfully on Node 22.23.5. Its 20 bridge/client tests passed on EC2, including real loopback HTTP/WebSocket checks with fake model responses.
- The voice repair passed 12 additional regression tests and its frontend rebuild on EC2.
- One approved bridge → Hermes → Bedrock test returned a completed answer. A real user-spoken request, displayed answer and browser audio playback were observed through the laptop's Session Manager tunnel.

Private account IDs, instance IDs, tokens and original deployment records are intentionally excluded from this shareable repository. These observations establish the integration's provenance; they are **not** a fresh deployment of this portable CLI/template.

## Checked for this package

- CloudFormation YAML parsing, resource/intrinsic references and security invariants were checked locally. Extracted bootstrap Bash syntax passed. Mocked success, command failure, subprocess failure and pipeline failure produced the expected CloudFormation signals; signed PUT payload and bounded retry handling were checked.
- Runtime suite: **32 tests discovered; 24 passed locally, 8 socket tests skipped** because the local sandbox does not permit the required listener checks. The installer explicitly enables and runs all 32 tests on EC2 before starting the services.
- Shell/JavaScript syntax, Python parsing, version-manifest parsing and the smoke-prompt **dry run** passed. The dry run neither connects nor invokes a model.
- The optional UI example prompts were changed to conversation-only examples. The final frontend build with this change must pass during installation and rehearsal.
- CLI guard suite: **28/28 tests passed**, with AWS subprocess calls replaced by fakes. These cover account/region/root checks, approval gates, exact-stack deletion, receipts written before submission, uncertain-response recovery without duplicate writes or prompts, multipart transfer, and security/cost drift. They do not contact AWS or incur model usage.
- Release packaging checks source files, excludes per-attendee state/dependencies, rejects symlinks and common secret material, and creates a ZIP file manifest. A separate review checks for the original deployment's identifiers.

## Not yet verified for the portable package

No new AWS stack was created, no fresh install was run, and no new model prompt was submitted while preparing this package. `cfn-lint` and `cfn-guard` were not installed in the authoring environment; their checks were not run. AWS service-side validation is performed by `plan` in the attendee's account, but that still cannot guarantee IAM/SCP permissions, quotas or successful bootstrap.

A complete **fresh-account rehearsal is required before the event**, including the new upload/resume automation, install, paid test, actual laptop speech, reconnection and deletion. Follow [HOST_GUIDE.md](HOST_GUIDE.md). Mac/browser operation was observed for the original installation; Windows and Linux laptop flows have not been tested end to end here.

Core versions and the Jarvis source revision are pinned. Ubuntu's “current 24.04” AMI, OS packages, pip tooling and some transitive Python dependencies remain upstream-resolved rather than fully locked. Future package/model availability can change. Rehearse the exact event release near the event date, and re-review any version changes instead of updating silently.

## Repeatable local checks

From this repository root, with Python 3.10+:

```sh
python3 -m unittest discover -s tests -v
python3 scripts/package.py --output ../hermes-jarvis-aws-workshop.zip
```

To run the runtime suite, use a disposable full checkout of the pinned Jarvis commit, overlay these files, install its locked npm dependencies, and run:

```sh
HERMES_NETWORK_TESTS=1 node --test test/hermes-client.test.mjs test/hermes-bridge.test.mjs test/browser-voice.test.mjs
```

These tests use fake model answers. Running the separate `integration/smoke-prompt.mjs --approved-one-prompt` against live services does invoke Bedrock and requires approval.
