<!--
Copyright 2026 Google LLC.
SPDX-License-Identifier: Apache-2.0
-->

# Mistral Vibe integration

## Install and locate the plugin

Mistral Vibe discovers plugins as directories, not marketplace entries.
Build the runtime folder and copy it into a plugins directory:

```sh
git clone https://github.com/google/elephant-goldfish-model.git
cd elephant-goldfish-model
python3 scripts/pack_plugin.py --target vibe --output /tmp/egm-vibe
mkdir -p ~/.vibe/plugins
rm -rf ~/.vibe/plugins/egm
cp -R /tmp/egm-vibe/egm-vibe ~/.vibe/plugins/egm
```

Use `~/.vibe/plugins/egm/` for every project, or
`<project>/.vibe/plugins/egm/` inside a trusted project folder for that
project only. Removing the old folder first avoids stale files from a
previous version. Start a new session, or run `/reload-plugins` in a running
one, and confirm that `egm` appears in `/plugins`. Install the whole plugin:
the skills read `agents/` and `resources/document_standards/` from the
plugin root at run time.

Invoke a skill from the slash menu: type `/` and select the EGM skill, listed
with its plugin as `egm:egm-brainstorm`. Skills keep
`disable-model-invocation: true`; Vibe honors it, so the skills stay in the
slash menu but the model cannot load them through the `skill` tool. To run
another EGM skill mid-review (for example `egm-resolve`), read its
`SKILL.md` and follow it in the same thread, as in Claude Code. Keep
drafting and orchestration in the main context.

From `<plugin>/skills/<skill>/SKILL.md`, the plugin root is three parent
directories above the file. Resolve bundled `agents/`, `resources/`, and
`docs/` paths against that root. Resolve `references/` against the active
skill's directory. Resolve user documents and generated artifacts against
the user's working directory. Never substitute similarly named files in the
user's project for bundled personas or standards.

If the user's prompt or agent instructions file (`AGENTS.md`) has a line
`EGM artifact directory: <path>`, write briefs, drafts, and reports to that
folder. Resolve a relative path against the working directory. If a path from
`AGENTS.md` resolves outside the working directory, after following symbolic
links, ask the user to confirm it before creating the folder or writing there.
If they decline or no one can confirm, use the working directory and say why.
Create the folder if it does not exist.

## Fresh-context reviewers

Vibe spawns subagents through `agents_spawn`. Each subagent starts with a
fresh context and receives only the instructions passed at spawn time. The
plugin does not register named reviewer agents, so follow the skills'
fallback: spawn a general-purpose subagent, tell it to read
`agents/<file>.md` first, and pass absolute paths to the persona, standards,
target document, and explicitly selected reading list. Do not pass the
parent transcript, private reasoning, or answers the document is supposed to
explain. A role such as `egm-design` maps to `agents/design_critic.md`, not
`agents/design.md`.

Persona and standards files live in the installed plugin directory, outside
the project. Approve reviewer reads through Vibe's normal permission prompts.
Do not disable permission checks or grant access to every installed plugin.
A reviewer that cannot read its persona or standard must report the
limitation and stop; it has not reviewed.

Wait for actual reviewer completion before synthesizing findings. Propagate
failures and timeouts; a launched reviewer is not a completed review. If a
subagent cannot spawn further subagents, dispatch reviewers directly from
the main context while preserving the same isolation, instead of launching a
synthesizer child. If no subagent tool is available, stop the Goldfish review
and report that limitation; a review in the same context is not a Goldfish
review.

Fresh context does not isolate the filesystem or instruction files. Vibe
does not expose a verified control that excludes project or user `AGENTS.md`
files from subagent context, so treat instruction-file exclusion as
unverified, as for Codex
([#237](https://github.com/google/elephant-goldfish-model/issues/237)).
Do not retrieve conversation history to supply missing design context. An
isolation test should use a unique parent-only marker and check the actual
child result, not the parent's claim.

## Questions and artifacts

The shared skills' question payloads describe the intended interaction, not a
literal Vibe API. Map them to the structured question tool when it is
available in the current mode, or ask one plain-text question and wait for
the answer. Preserve the skill's readiness and section approval gates; tool
unavailability is not approval.

Write briefs, drafts, and reports to the user's working directory (or the
artifact directory above), and tell the user the file path in chat. The
per-session scratchpad is not the artifact directory: it belongs to one
session, and the deliverables must outlive it.

## Verification

Run the offline packaging checks with `pytest tests/unit`. The vibe target
builds `egm-vibe/` and `egm-vibe.zip` from the same shared sources as the
Claude and OpenAI runtimes; the Vibe manifest lives at
`.vibe-plugin/plugin.json` in the repository and ships as the bundle's root
`plugin.json`. Installing the plugin alone does not establish end-to-end
workflow support. See the
[harness test record](https://github.com/google/elephant-goldfish-model/blob/main/TESTING.md#harness-test-record)
for tested surfaces and limits.
