# Third-party notices

This workshop combines an AWS deployment adaptation with a small overlay for Jarvis. Upstream source is downloaded at the revisions recorded in `versions.json`; the package does not vendor dependency directories, compiled bundles, model weights, credentials, or upstream audio assets.

## Jarvis

Source: [wasihussain914/jarvis at 7c4ee7fcfa9b9b429ce092ec127d332494549982](https://github.com/wasihussain914/jarvis/tree/7c4ee7fcfa9b9b429ce092ec127d332494549982).

The upstream MIT notice identifies **Copyright (c) 2026 Aditya Dewaskar**. The repository owner is not substituted for this copyright holder. The exact notice is preserved in [LICENSES/JARVIS-MIT.txt](LICENSES/JARVIS-MIT.txt), and the upstream checkout retains its original `LICENSE`.

The overlay modifies `src/lib/voice.ts`, `src/ui/Hud.tsx`, and `src/ui/Suggestions.tsx`. These changes add reliable push-to-talk release behavior, instructions for the workshop, and examples appropriate to a conversation-only interface. The new Hermes bridge and installation helpers replace the runtime connection to Claude Code; upstream project dependencies remain governed by their own licenses.

## Hermes Agent

Source: [NousResearch/hermes-agent at 3ef6bbd201263d354fd83ec55b3c306ded2eb72a](https://github.com/NousResearch/hermes-agent/tree/3ef6bbd201263d354fd83ec55b3c306ded2eb72a), corresponding to the supported `hermes-agent==0.19.0` runtime.

The upstream MIT notice identifies **Copyright (c) 2025 Nous Research**. A copy is preserved in [LICENSES/HERMES-AGENT-MIT.txt](LICENSES/HERMES-AGENT-MIT.txt). Hermes itself is installed separately; the overlay uses its existing API and configuration interfaces.

## AWS reference project

Source: [JiaDe-Wu/sample-hermes-agent-on-aws-with-bedrock at c9c5a46654e97d45c8bfb6f6f4ec66852cbe0f2b](https://github.com/JiaDe-Wu/sample-hermes-agent-on-aws-with-bedrock/tree/c9c5a46654e97d45c8bfb6f6f4ec66852cbe0f2b).

The workshop's infrastructure is adapted from this reference. Its MIT notice states **Copyright (c) 2026** without naming a holder. That wording is preserved exactly in [LICENSES/AWS-REFERENCE-MIT.txt](LICENSES/AWS-REFERENCE-MIT.txt). This workshop is an adaptation, not an official upstream release.

## Runtime dependencies

Node.js is downloaded from its official distribution and checked against that release's published SHA-256 manifest. The pinned Jarvis checkout's `package-lock.json` controls its npm dependencies; Hermes and aiohttp are installed as Python packages. Their distributions include their own license notices. Amazon Bedrock model and service use is subject to the applicable AWS terms and pricing.
