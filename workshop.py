#!/usr/bin/env python3
"""Deploy one private Hermes/Jarvis workshop using Python's standard library and AWS CLI.

Read-only commands never invoke a model. Mutating commands require --approve and
the expected --account. Receipts are saved before submission; an uncertain call
is observed, never silently retried. Local state belongs in ignored .workshop/.
"""
from __future__ import annotations

import argparse
import base64
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import io
import json
import lzma
import os
from pathlib import Path
import re
import shlex
import shutil
import socket
import subprocess
import sys
import tarfile
import tempfile
import time
import uuid

REGION = "us-east-1"
JARVIS_REVISION = "7c4ee7fcfa9b9b429ce092ec127d332494549982"
APP = "/home/ubuntu/jarvis-hermes"
NODE = "/home/ubuntu/.local/share/jarvis-node/node-v22.23.5-linux-x64/bin/node"
MAX_SSM_BYTES = 48 * 1024
CHUNK_CHARS = 30_000
MUTATIONS = {"deploy", "install", "verify", "test", "connect", "destroy"}
TERMINAL_COMMANDS = {"Success", "Failed", "Cancelled", "TimedOut", "DeliveryTimedOut", "ExecutionTimedOut", "Undeliverable", "Terminated", "InvalidPlatform", "AccessDenied"}


class WorkshopError(RuntimeError):
    pass


class AWSError(WorkshopError):
    def __init__(self, service: str, action: str, detail: str):
        self.service, self.action, self.detail = service, action, detail
        super().__init__(f"AWS {service} {action} failed: {detail.strip()[:2000]}")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def atomic_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    if path.is_symlink():
        raise WorkshopError(f"Refusing symbolic-link state file: {path}")
    fd, temporary = tempfile.mkstemp(prefix=".workshop-", dir=path.parent)
    try:
        if hasattr(os, "fchmod"):
            os.fchmod(fd, 0o600)
        else:  # Windows does not expose fchmod.
            os.chmod(temporary, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(value, stream, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


class AWS:
    def __init__(self, profile: str, region: str):
        self.profile, self.region = profile, region
        self.env = dict(os.environ, AWS_PAGER="", AWS_CLI_AUTO_PROMPT="off",
                        AWS_MAX_ATTEMPTS="1", AWS_RETRY_MODE="standard")

    def command(self, service: str, action: str, *args: str) -> list[str]:
        profile = [] if self.profile == "-" else ["--profile", self.profile]
        return ["aws", service, action, *args, *profile, "--region", self.region, "--no-cli-pager"]

    def call(self, service: str, action: str, *args: str) -> dict:
        try:
            result = subprocess.run(self.command(service, action, *args, "--output", "json"),
                                    check=False, capture_output=True, text=True, env=self.env,
                                    timeout=90)
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise AWSError(service, action, type(exc).__name__) from exc
        if result.returncode:
            raise AWSError(service, action, result.stderr or f"exit {result.returncode}")
        try:
            return json.loads(result.stdout) if result.stdout.strip() else {}
        except json.JSONDecodeError as exc:
            raise AWSError(service, action, "The response was not valid JSON; outcome may be uncertain.") from exc


class StateStore:
    def __init__(self, root: Path, name: str):
        self.directory = root / ".workshop" / name
        if (root / ".workshop").is_symlink() or self.directory.is_symlink():
            raise WorkshopError("Refusing symbolic-link workshop state directories.")
        self.path = self.directory / "state.json"

    def read(self) -> dict | None:
        if self.path.is_symlink():
            raise WorkshopError("Refusing symbolic-link state file.")
        if not self.path.exists():
            return None
        try:
            value = json.loads(self.path.read_text())
        except (OSError, json.JSONDecodeError) as exc:
            raise WorkshopError("Workshop state is unreadable. Do not replace it or resubmit an uncertain action.") from exc
        if not isinstance(value, dict) or value.get("format") != 1:
            raise WorkshopError("Unsupported workshop state. Review it before continuing.")
        return value

    def save(self, state: dict) -> None:
        atomic_json(self.path, state)

    @contextmanager
    def lock(self):
        self.directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        lock = self.directory / "command.lock"
        try:
            descriptor = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        except FileExistsError as exc:
            raise WorkshopError(f"Another command or an interrupted local process owns {lock}. Verify no workshop command is running before removing this local lock; do not clear state.json.") from exc
        try:
            with os.fdopen(descriptor, "w") as stream:
                stream.write(f"pid={os.getpid()}\n")
            yield
        finally:
            lock.unlink(missing_ok=True)


def deterministic_archive(overlay: Path) -> bytes:
    if not overlay.is_dir() or overlay.is_symlink():
        raise WorkshopError("The reviewed overlay/ directory is missing or is a symbolic link.")
    raw = io.BytesIO()
    count = 0
    with tarfile.open(fileobj=raw, mode="w", format=tarfile.USTAR_FORMAT) as archive:
        for path in sorted(overlay.rglob("*")):
            relative = path.relative_to(overlay)
            if path.is_symlink() or any(part.startswith(".") or part == "node_modules" for part in relative.parts):
                raise WorkshopError(f"Unexpected private/linked overlay entry: {relative}")
            if path.is_dir():
                continue
            if not path.is_file():
                raise WorkshopError(f"Overlay entry is not a regular file: {relative}")
            content = path.read_bytes()
            info = tarfile.TarInfo(relative.as_posix())
            info.size, info.mode, info.mtime = len(content), 0o644, 0
            info.uid = info.gid = 0
            info.uname = info.gname = ""
            archive.addfile(info, io.BytesIO(content))
            count += 1
    if not count:
        raise WorkshopError("The overlay is empty.")
    return lzma.compress(raw.getvalue(), preset=9)


def stack_missing(error: AWSError) -> bool:
    return "ValidationError" in error.detail and "does not exist" in error.detail.lower()


class Workshop:
    def __init__(self, args: argparse.Namespace, root: Path):
        self.args, self.root = args, root
        self.aws = AWS(args.profile, args.region)
        self.store = StateStore(root, args.stack)
        self.identity: dict = {}
        self.state: dict | None = None

    def authorize(self) -> None:
        if self.args.region != REGION:
            raise WorkshopError("This workshop supports only us-east-1. No AWS request was made.")
        if not re.fullmatch(r"[A-Za-z][A-Za-z0-9-]{0,127}", self.args.stack):
            raise WorkshopError("Use a unique stack name: start with a letter, then letters, digits, or hyphens (max 128).")
        if self.args.command in MUTATIONS and (not self.args.approve or not self.args.account):
            raise WorkshopError("This action requires separate user approval, then --approve --account EXPECTED_12_DIGIT_ACCOUNT.")
        if self.args.account and not re.fullmatch(r"\d{12}", self.args.account):
            raise WorkshopError("--account must be the expected 12-digit AWS account ID.")
        self.identity = self.aws.call("sts", "get-caller-identity")
        account = self.identity.get("Account", "")
        if not re.fullmatch(r"\d{12}", account):
            raise WorkshopError("AWS did not return a valid account identity.")
        if self.args.account and self.args.account != account:
            raise WorkshopError("The active AWS account does not match --account. Nothing was changed.")
        if self.args.command in MUTATIONS and self.identity.get("Arn", "").endswith(":root") and not self.args.allow_root:
            raise WorkshopError("This sign-in is the account root user. Prefer a non-root administrator; only use --allow-root after explicitly choosing root for this workshop.")
        self.state = self.store.read()
        self.validate_state()

    def validate_state(self) -> None:
        if self.state and any(self.state.get(key) != expected for key, expected in
                              (("account", self.identity["Account"]), ("region", REGION), ("stack_name", self.args.stack))):
            raise WorkshopError("Saved workshop state belongs to a different account, region, or stack. Nothing was changed.")
        if self.state and self.state.get("stack_id"):
            self.check_stack_id(self.state["stack_id"])

    def check_stack_id(self, stack_id: str) -> None:
        prefix = f"arn:aws:cloudformation:{REGION}:{self.identity['Account']}:stack/{self.args.stack}/"
        if not isinstance(stack_id, str) or not stack_id.startswith(prefix) or not re.fullmatch(r"[A-Za-z0-9-]+", stack_id[len(prefix):]):
            raise WorkshopError("StackId does not match the verified account, region, and exact stack name.")

    def save(self) -> None:
        assert self.state is not None
        self.store.save(self.state)

    def describe(self, name: str) -> dict | None:
        try:
            result = self.aws.call("cloudformation", "describe-stacks", "--stack-name", name)
        except AWSError as exc:
            if stack_missing(exc):
                return None
            raise
        stacks = result.get("Stacks", [])
        if len(stacks) != 1:
            raise WorkshopError("CloudFormation did not return exactly one stack.")
        return stacks[0]

    def current_stack(self, ready: bool = False) -> dict:
        if not self.state:
            raise WorkshopError("No recorded workshop exists here. Run plan, then deploy after approval.")
        if not self.state.get("stack_id"):
            candidate = self.describe(self.args.stack)
            token = self.state.get("create", {}).get("token")
            tags = {item["Key"]: item["Value"] for item in (candidate or {}).get("Tags", [])}
            if not candidate or not token or tags.get("WorkshopRun") != token:
                raise WorkshopError("The earlier create request has an unknown outcome. Do not resubmit. Inspect CloudFormation using the saved request token; an unrelated stack will never be adopted.")
            self.check_stack_id(candidate["StackId"])
            self.state["stack_id"] = candidate["StackId"]
            self.state["create"]["status"] = "recovered"
            self.save()
        stack_id = self.state["stack_id"]
        self.check_stack_id(stack_id)
        stack = self.describe(stack_id)
        if not stack:
            raise WorkshopError("The recorded StackId is unavailable. Do not target a replacement stack with the same name.")
        if stack.get("StackId") != stack_id:
            raise WorkshopError("CloudFormation returned a different StackId; refusing to continue.")
        if ready and stack.get("StackStatus") != "CREATE_COMPLETE":
            raise WorkshopError(f"Stack is {stack.get('StackStatus')}; wait for CREATE_COMPLETE before this action.")
        self.state["stack_status"] = stack.get("StackStatus")
        self.state["outputs"] = {item["OutputKey"]: item["OutputValue"] for item in stack.get("Outputs", [])}
        self.save()
        return stack

    def inspect_instance(self) -> dict:
        self.current_stack(ready=True)
        instance_id = self.state["outputs"].get("InstanceId", "")
        if not re.fullmatch(r"i-[0-9a-f]{8}(?:[0-9a-f]{9})?", instance_id):
            raise WorkshopError("The recorded stack has no valid InstanceId output.")
        response = self.aws.call("ec2", "describe-instances", "--instance-ids", instance_id)
        instances = [item for reservation in response.get("Reservations", []) for item in reservation.get("Instances", [])]
        if len(instances) != 1 or instances[0].get("InstanceId") != instance_id:
            raise WorkshopError("EC2 did not return the exact recorded instance.")
        instance = instances[0]
        tags = {item["Key"]: item["Value"] for item in instance.get("Tags", [])}
        if tags.get("aws:cloudformation:stack-id") != self.state["stack_id"]:
            raise WorkshopError("The instance does not belong to the exact recorded stack.")
        if instance.get("State", {}).get("Name") != "running":
            raise WorkshopError("The existing workshop instance is not running; no new instance will be created.")
        if instance.get("InstanceType") != "t3.small":
            raise WorkshopError("Expected the reviewed t3.small instance size.")
        credits = self.aws.call("ec2", "describe-instance-credit-specifications", "--instance-ids", instance_id).get("InstanceCreditSpecifications", [])
        if len(credits) != 1 or credits[0].get("InstanceId") != instance_id or credits[0].get("CpuCredits") != "standard":
            raise WorkshopError("Expected standard CPU credits to avoid unlimited-credit charges.")
        if instance.get("MetadataOptions", {}).get("HttpTokens") != "required":
            raise WorkshopError("Expected IMDSv2-required instance metadata; review the instance configuration.")
        groups = [item["GroupId"] for item in instance.get("SecurityGroups", [])]
        if not groups:
            raise WorkshopError("The instance has no reported security group.")
        security = self.aws.call("ec2", "describe-security-groups", "--group-ids", *groups)
        returned = security.get("SecurityGroups", [])
        if {item.get("GroupId") for item in returned} != set(groups) or any(item.get("IpPermissions") for item in returned):
            raise WorkshopError("Expected security groups with no inbound rules; review before continuing.")
        roots = [item for item in instance.get("BlockDeviceMappings", []) if item.get("DeviceName") == instance.get("RootDeviceName")]
        if len(roots) != 1 or roots[0].get("Ebs", {}).get("DeleteOnTermination") is not True:
            raise WorkshopError("The root disk is not confirmed to delete with the instance.")
        volume_id = roots[0]["Ebs"]["VolumeId"]
        volumes = self.aws.call("ec2", "describe-volumes", "--volume-ids", volume_id).get("Volumes", [])
        if len(volumes) != 1 or volumes[0].get("VolumeId") != volume_id or volumes[0].get("Encrypted") is not True or volumes[0].get("VolumeType") != "gp3" or volumes[0].get("Size") != 30:
            raise WorkshopError("Expected one encrypted 30-GiB gp3 root volume.")
        managed = self.aws.call("ssm", "describe-instance-information", "--filters", f"Key=InstanceIds,Values={instance_id}").get("InstanceInformationList", [])
        if len(managed) != 1 or managed[0].get("InstanceId") != instance_id or managed[0].get("PingStatus") != "Online":
            raise WorkshopError("The recorded instance is not online in Systems Manager.")
        return {"InstanceId": instance_id, "InstanceType": "t3.small", "CpuCredits": "standard", "SecurityGroups": groups, "InboundRules": [], "IMDSv2": "required", "EncryptedRootVolume": volume_id, "RootVolumeGiB": 30, "SSM": "Online"}

    def doctor(self) -> dict:
        return {"account": self.identity["Account"], "identity": self.identity.get("Arn"),
                "profile": self.args.profile, "region": REGION, "stack_name": self.args.stack,
                "root_identity": self.identity.get("Arn", "").endswith(":root"),
                "session_manager_plugin": bool(shutil.which("session-manager-plugin")),
                "aws_changed": False, "model_invoked": False}

    def plan(self) -> dict:
        template = self.root / "infra/workshop.yaml"
        if not template.is_file():
            raise WorkshopError("infra/workshop.yaml is missing.")
        validation = self.aws.call("cloudformation", "validate-template", "--template-body", f"file://{template}")
        existing = self.describe(self.args.stack)
        return {**self.doctor(), "template": str(template), "template_sha256": hashlib.sha256(template.read_bytes()).hexdigest(),
                "template_capabilities": validation.get("Capabilities", []), "stack_name_available": existing is None,
                "existing_stack_will_not_be_overwritten": True,
                "planned_resources": "One t3.small EC2, encrypted 30-GiB gp3 root disk, outbound-capable VPC/subnet/gateway/route, no-inbound security group, EC2 IAM role/profile, bootstrap wait resources.",
                "estimated_usd_per_hour_before_credits": 0.03,
                "cost_note": "Approximate EC2 + disk + public IPv4 estimate; Bedrock usage and possible data transfer are additional. Verify current regional pricing before approval."}

    def deploy(self) -> dict:
        if self.state:
            raise WorkshopError("This stack already has local state. Use status to observe it; deploy never resubmits or overwrites an earlier request.")
        planned = self.plan()
        if not planned["stack_name_available"]:
            raise WorkshopError("That stack name already exists. Choose a new unique name; it will not be updated or adopted.")
        token = "workshop-" + uuid.uuid4().hex
        self.state = {"format": 1, "account": self.identity["Account"], "region": REGION,
                      "profile": self.args.profile, "stack_name": self.args.stack, "created_at": utc_now(),
                      "create": {"token": token, "status": "submitting", "template_sha256": planned["template_sha256"]}, "operations": {}}
        self.save()
        result = self.aws.call("cloudformation", "create-stack", "--stack-name", self.args.stack,
                               "--template-body", f"file://{self.root / 'infra/workshop.yaml'}",
                               "--capabilities", "CAPABILITY_IAM", "--client-request-token", token,
                               "--tags", "Key=Workshop,Value=hermes-jarvis", f"Key=WorkshopRun,Value={token}")
        self.check_stack_id(result.get("StackId", ""))
        self.state["stack_id"] = result["StackId"]
        self.state["create"]["status"] = "submitted"
        self.save()
        return {"submitted": "deploy", "StackId": result["StackId"], "next": "Run status until CREATE_COMPLETE. No model request was sent."}

    def payload(self, instance_id: str, command: str, comment: str, timeout: int) -> dict:
        result = {"InstanceIds": [instance_id], "DocumentName": "AWS-RunShellScript", "Comment": comment,
                  "Parameters": {"commands": [command], "executionTimeout": [str(timeout)]},
                  "MaxConcurrency": "1", "MaxErrors": "0", "TimeoutSeconds": 60}
        if len(json.dumps(result, separators=(",", ":")).encode()) > MAX_SSM_BYTES:
            raise WorkshopError("Prepared SSM request exceeds the 48-KiB workshop limit; nothing was submitted.")
        return result

    def submit(self, operation: str, instance_id: str, command: str, timeout: int) -> dict:
        operations = self.state.setdefault("operations", {})
        if operation in operations:
            return self.poll(operation)
        comment = f"hermes-jarvis:{operation}:{uuid.uuid4().hex}"
        payload = self.payload(instance_id, command, comment, timeout)
        receipt = {"status": "submitting", "instance_id": instance_id, "comment": comment,
                   "submitted_at": utc_now(), "payload_sha256": hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()}
        operations[operation] = receipt
        path = self.store.directory / f"{operation}-request.json"
        atomic_json(path, payload)
        self.save()  # Exists before SendCommand, including lost-response cases.
        response = self.aws.call("ssm", "send-command", "--cli-input-json", f"file://{path}").get("Command", {})
        command_id = response.get("CommandId", "")
        if not re.fullmatch(r"[0-9a-f-]{36}", command_id):
            raise WorkshopError("SSM returned no valid command ID. The saved receipt remains unresolved; do not resubmit.")
        receipt.update(command_id=command_id, status=response.get("Status", "Pending"))
        self.save()
        return {"operation": operation, **receipt}

    def poll(self, operation: str) -> dict:
        receipt = self.state["operations"][operation]
        if not receipt.get("command_id"):
            commands = self.aws.call("ssm", "list-commands", "--instance-id", receipt["instance_id"]).get("Commands", [])
            matches = [item for item in commands if item.get("Comment") == receipt["comment"] and
                       item.get("DocumentName") == "AWS-RunShellScript" and item.get("InstanceIds") == [receipt["instance_id"]]]
            if len(matches) != 1:
                return {"operation": operation, "status": "unknown", "note": "An earlier submission has no unique visible receipt. Nothing was resent.", "comment": receipt["comment"]}
            command_id = matches[0].get("CommandId", "")
            if not re.fullmatch(r"[0-9a-f-]{36}", command_id):
                raise WorkshopError("The recovered SSM command ID is invalid. Nothing was resent.")
            receipt["command_id"] = command_id
            self.save()
        try:
            result = self.aws.call("ssm", "get-command-invocation", "--command-id", receipt["command_id"], "--instance-id", receipt["instance_id"])
        except AWSError as exc:
            if "InvocationDoesNotExist" in exc.detail:
                return {"operation": operation, "status": "awaiting_visibility", "command_id": receipt["command_id"]}
            raise
        if result.get("CommandId") != receipt["command_id"] or result.get("InstanceId") != receipt["instance_id"]:
            raise WorkshopError("SSM returned a different command or instance; refusing to accept its result.")
        receipt.update(status=result.get("Status"), response_code=result.get("ResponseCode"), observed_at=utc_now())
        self.save()
        summary = {"operation": operation, "command_id": receipt["command_id"], "status": receipt["status"], "response_code": receipt["response_code"]}
        if self.args.show_output:
            summary.update(output=result.get("StandardOutputContent", ""), error=result.get("StandardErrorContent", ""))
        return summary

    def install_script(self, archive_path: str, digest: str, stage: str) -> str:
        ubuntu = f"""set -euo pipefail
cd /home/ubuntu
test ! -e jarvis-hermes || {{ echo 'Checkout exists; inspect it before making changes.'; exit 1; }}
git clone https://github.com/wasihussain914/jarvis.git jarvis-hermes
cd jarvis-hermes
git checkout --detach {JARVIS_REVISION}
tar -xJf {shlex.quote(archive_path)}
AWS_REGION={REGION} bash integration/install-ec2.sh
"""
        return f"""set -eu
umask 077
printf '%s  %s\\n' {shlex.quote(digest)} {shlex.quote(archive_path)} | sha256sum -c -
chown ubuntu:ubuntu {shlex.quote(archive_path)}
runuser -l ubuntu -c {shlex.quote('bash -c ' + shlex.quote(ubuntu))} > /home/ubuntu/jarvis-install.log 2>&1 || {{ tail -n 80 /home/ubuntu/jarvis-install.log; exit 1; }}
tail -n 80 /home/ubuntu/jarvis-install.log
rm -rf {shlex.quote(stage)}
"""

    def install(self) -> dict:
        instance = self.inspect_instance()["InstanceId"]
        archive = deterministic_archive(self.root / "overlay")
        digest = hashlib.sha256(archive).hexdigest()
        encoded = base64.b64encode(archive).decode()
        batch = self.state.get("installation")
        if batch and batch["archive_sha256"] != digest:
            raise WorkshopError("The overlay changed after installation began. Do not mix transfer parts or overwrite the recorded installation.")
        if "install" in self.state.get("operations", {}):
            return self.poll("install")
        if not batch:
            batch = {"token": uuid.uuid4().hex, "archive_sha256": digest, "archive_bytes": len(archive)}
            self.state["installation"] = batch
            self.save()
        stage = f"/home/ubuntu/.cache/hermes-jarvis-workshop/{batch['token']}"
        archive_path = stage + "/overlay.tar.xz"
        prepare = f"set -eu\numask 077\ninstall -d -m 700 -o ubuntu -g ubuntu {shlex.quote(stage)}\n"
        complete = self.install_script(archive_path, digest, stage)
        single = prepare + f"printf %s {shlex.quote(encoded)} | base64 -d > {shlex.quote(archive_path)}\n" + complete
        try:
            self.payload(instance, single, "hermes-jarvis:install:" + "0" * 32, 1800)
        except WorkshopError:
            chunks = [encoded[index:index + CHUNK_CHARS] for index in range(0, len(encoded), CHUNK_CHARS)]
            batch["transfer_parts"] = len(chunks)
            self.save()
            for index, chunk in enumerate(chunks):
                operation = f"install-part-{index + 1}"
                command = prepare + f"printf %s {shlex.quote(chunk)} > {shlex.quote(stage + f'/part-{index:03d}.b64')}\n"
                result = self.submit(operation, instance, command, 60)
                deadline = time.monotonic() + 45
                while result["status"] not in TERMINAL_COMMANDS and result["status"] != "unknown" and time.monotonic() < deadline:
                    result = self.poll(operation)
                    if result["status"] not in TERMINAL_COMMANDS and result["status"] != "unknown":
                        time.sleep(2)
                if result["status"] != "Success" or result.get("response_code") != 0:
                    return {"installation": "transfer_not_complete", "receipt": result, "next": "Use status to inspect. Re-run approved install to continue after a successful known part; failed or unknown parts are never resent."}
            part_paths = " ".join(shlex.quote(stage + f"/part-{index:03d}.b64") for index in range(len(chunks)))
            final = f"set -eu\numask 077\ncat {part_paths} | base64 -d > {shlex.quote(archive_path)}\n" + complete
            return self.submit("install", instance, final, 1800)
        return self.submit("install", instance, single, 1800)

    def status(self) -> dict:
        stack = self.current_stack()
        return {"account": self.identity["Account"], "StackId": stack["StackId"], "stack_status": stack["StackStatus"],
                "outputs": self.state.get("outputs", {}),
                "operations": [self.poll(name) for name in list(self.state.get("operations", {}))],
                "destroy": self.state.get("destroy"), "model_invoked_by_status": False}

    def verify(self) -> dict:
        checks = self.inspect_instance()
        if self.state.get("operations", {}).get("install", {}).get("status") != "Success":
            if "install" in self.state.get("operations", {}):
                self.poll("install")
            if self.state.get("operations", {}).get("install", {}).get("status") != "Success":
                raise WorkshopError("Installation is not confirmed successful. Inspect status before verification.")
        command = "runuser -l ubuntu -c " + shlex.quote(f"cd {APP} && bash integration/verify-ec2.sh")
        # Each invocation is a read-only host check, but still requires explicit
        # approval because SSM creates and executes a command record.
        operation = "verify-" + uuid.uuid4().hex[:8]
        return {"aws_checks": checks, "host_checks": self.submit(operation, checks["InstanceId"], command, 60), "model_invoked": False}

    def test_prompt(self) -> dict:
        instance = self.inspect_instance()["InstanceId"]
        if "test" in self.state.get("operations", {}):
            return {"already_submitted": True, "receipt": self.poll("test"), "model_request_resent": False}
        if "install" not in self.state.get("operations", {}) or self.poll("install")["status"] != "Success":
            raise WorkshopError("Installation must succeed before the separately approved model test.")
        command = "runuser -l ubuntu -c " + shlex.quote(f"cd {APP} && {NODE} integration/smoke-prompt.mjs --approved-one-prompt")
        return self.submit("test", instance, command, 300)

    def connect(self) -> dict:
        with self.store.lock():
            self.state = self.store.read()
            self.validate_state()
            instance = self.inspect_instance()["InstanceId"]
        if not shutil.which("session-manager-plugin"):
            raise WorkshopError("Install the AWS Session Manager plugin on this local computer first: https://docs.aws.amazon.com/systems-manager/latest/userguide/session-manager-working-with-install-plugin.html")
        with socket.socket() as probe:
            try:
                probe.bind(("127.0.0.1", 8787))
            except OSError as exc:
                raise WorkshopError("Local port 8787 is in use. Close the earlier tunnel or conflicting application first.") from exc
        print("Keep this terminal open. Open http://127.0.0.1:8787 in Chrome or Edge. Control-C closes the tunnel; EC2 charges continue.", flush=True)
        args = self.aws.command("ssm", "start-session", "--target", instance, "--document-name", "AWS-StartPortForwardingSession",
                                "--parameters", '{"portNumber":["8787"],"localPortNumber":["8787"]}')
        completed = subprocess.run(args, env=self.aws.env, check=False)
        if completed.returncode:
            raise WorkshopError(f"Session Manager exited with code {completed.returncode}; no session was retried.")
        return {"tunnel": "closed", "model_invoked_by_connect": False}

    def destroy(self) -> dict:
        stack = self.current_stack()
        if not self.args.stack_id or self.args.stack_id != self.state["stack_id"]:
            raise WorkshopError("Review status, then supply --stack-id with the exact recorded StackId. A stack name is not sufficient deletion approval.")
        if self.state.get("destroy"):
            return {"already_submitted": True, "StackId": self.state["stack_id"], "stack_status": stack["StackStatus"], "note": "No deletion was resubmitted. Inspect status and any DELETE_FAILED events."}
        token = "delete-" + uuid.uuid4().hex
        self.state["destroy"] = {"token": token, "status": "submitting", "submitted_at": utc_now()}
        self.save()
        self.aws.call("cloudformation", "delete-stack", "--stack-name", self.state["stack_id"], "--client-request-token", token)
        self.state["destroy"]["status"] = "submitted"
        self.save()
        return {"submitted": "destroy", "StackId": self.state["stack_id"],
                "next": "Run status until DELETE_COMPLETE. Instance/disk data is deleted; AWS-managed SSM/CloudTrail history follows AWS retention. No retained workshop log bucket was created."}


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("command", choices=["doctor", "plan", "deploy", "install", "status", "verify", "test", "connect", "destroy"])
    result.add_argument("--profile", required=True, help="AWS CLI profile, or '-' for existing ambient credentials in CloudShell")
    result.add_argument("--region", required=True, help="Explicitly use us-east-1; other regions are rejected")
    result.add_argument("--stack", required=True, help="Your unique stack name; no default or personal account IDs are embedded")
    result.add_argument("--approve", action="store_true", help="Use only after the user approved this specific action and any model cost")
    result.add_argument("--account", help="Expected 12-digit AWS account ID; required for approved actions")
    result.add_argument("--allow-root", action="store_true", help="Explicitly use an already chosen root sign-in; prefer a non-root administrator")
    result.add_argument("--stack-id", help="Exact recorded StackId, required to confirm destroy")
    result.add_argument("--show-output", action="store_true", help="Show SSM output in status; inspect locally before sharing logs")
    return result


def main(argv: list[str] | None = None, *, root: Path | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        workshop = Workshop(args, root or Path(__file__).resolve().parent)
        # Validate account and approval before taking a local lock or changing AWS.
        workshop.authorize()
        methods = {"doctor": workshop.doctor, "plan": workshop.plan, "deploy": workshop.deploy,
                   "install": workshop.install, "status": workshop.status, "verify": workshop.verify,
                   "test": workshop.test_prompt, "connect": workshop.connect, "destroy": workshop.destroy}
        if args.command in {"doctor", "plan", "connect"}:
            output = methods[args.command]()
        else:
            with workshop.store.lock():
                # Re-read after locking so parallel processes cannot both submit.
                workshop.state = workshop.store.read()
                workshop.validate_state()
                output = methods[args.command]()
        print(json.dumps(output, indent=2))
        return 0
    except (WorkshopError, OSError) as exc:
        print(f"Workshop stopped: {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\nStopped locally. Any submitted AWS operation keeps its saved receipt; inspect status before continuing.", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
