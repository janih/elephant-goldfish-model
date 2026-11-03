<!--
Copyright 2026 Google LLC.
SPDX-License-Identifier: Apache-2.0
-->

# Pi integration

## Install and locate the plugin

Pi (pi.dev) distributes plugins as packages installed from git, npm, or a
local path. Install the whole repository as a package:

```sh
pi install git:github.com/google/elephant-goldfish-model
```

Pi clones the repository and its package discovery loads every skill under
`skills/`. Confirm the install with `pi list`, then start a new session
(or run `/reload` in a running one) and check that the seven `egm-*`
skills appear. The install is personal by default; add `--local` to record
it in the project's `.pi/settings.json` instead, which Pi loads only
after you grant project trust. Update later with
`pi update --extensions`. For a curated offline install, build the runtime
bundle and install it from the local path:

```sh
git clone https://github.com/google/elephant-goldfish-model.git
cd elephant-goldfish-model
python3 scripts/pack_plugin.py --target pi --output /tmp/egm-pi
pi install /tmp/egm-pi/egm-pi
```

The bundle root carries the pi package manifest
(`.pi-plugin/package.json` in the repository, shipped as `package.json`),
which declares `pi.skills: ["./skills"]`; Pi would also discover the
conventional `skills/` directory on its own. Install the whole plugin:
the skills read `agents/` and `resources/document_standards/` from the
package root at run time.

Invoke a skill through its command: `/skill:egm-brainstorm`. Text after
the command reaches the skill as a request, for example
`/skill:egm-review design_draft.md`. Skills keep
`disable-model-invocation: true`; Pi honors it, so the model cannot load
them on its own and each skill runs only through its command. If the
commands do not appear in the slash menu, check the `enableSkillCommands`
setting, or type `/skill:egm-review` manually. To run another EGM skill
mid-review (for example `egm-resolve`), run its `/skill:` command and
follow it in the same session. Keep drafting and orchestration in the
main context.

From `<package>/skills/<skill>/SKILL.md`, the package root is three
parent directories above the file. Resolve bundled `agents/`,
`resources/`, and `docs/` paths against that root. Resolve `references/`
against the active skill's directory. Resolve user documents and
generated artifacts against the user's working directory. Never
substitute similarly named files in the user's project for bundled
personas or standards.

If the user's prompt or agent instructions file (`AGENTS.md`) has a line
`EGM artifact directory: <path>`, write briefs, drafts, and reports to
that folder. Pi reads `AGENTS.md` natively, so the line works from the
prompt or from the project or user instruction file. Resolve a relative
path against the working directory. If a path from `AGENTS.md` resolves
outside the working directory, after following symbolic links, ask the
user to confirm it before creating the folder or writing there. If they
decline or no one can confirm, use the working directory and say why.
Create the folder if it does not exist.

## Fresh-context reviewers

Pi's core has no built-in subagent tool. Subagents come from extensions:
for example the `subagent` example extension in the pi repository
registers a `subagent` tool that runs each delegate in a separate pi
process with a fresh context window. The plugin ships no extension code
and registers no named reviewer agents, so follow the skills' fallback:
spawn a general-purpose subagent, tell it to read `agents/<file>.md`
first, and pass absolute paths to the persona, standards, target
document, and explicitly selected reading list. Do not pass the parent
transcript, private reasoning, or answers the document is supposed to
explain. A role such as `egm-design` maps to `agents/design_critic.md`,
not `agents/design.md`.

Persona and standards files live in the installed package directory,
outside the project. Approve reviewer reads through Pi's normal
permission prompts. Do not disable permission checks or install
extensions you have not reviewed. A reviewer that cannot read its persona
or standard must report the limitation and stop; it has not reviewed.

Wait for actual reviewer completion before synthesizing findings.
Propagate failures and timeouts; a launched reviewer is not a completed
review. If a subagent tool cannot spawn further subagents, dispatch
reviewers directly from the main context while preserving the same
isolation, instead of launching a synthesizer child. If no subagent tool
is available, stop the Goldfish review and report that limitation; a
review in the same context is not a Goldfish review.

Fresh context does not isolate the filesystem or instruction files. Pi
loads project and user `AGENTS.md` files into the main context, and
whether an extension's subagent processes include instruction files
depends on that extension; no exclusion control is verified here, so
treat instruction-file exclusion as unverified, as for Codex
([#237](https://github.com/google/elephant-goldfish-model/issues/237)).
Do not retrieve conversation history to supply missing design context. An
isolation test should use a unique parent-only marker and check the
actual child result, not the parent's claim.

## Questions and artifacts

The shared skills' question payloads describe the intended interaction,
not a literal Pi API. Map them to a structured question tool when an
extension provides one, or ask one plain-text question and wait for the
answer. Preserve the skill's readiness and section approval gates; tool
unavailability is not approval.

Write briefs, drafts, and reports to the user's working directory (or the
artifact directory above), and tell the user the file path in chat. The
per-session scratchpad is not the artifact directory: it belongs to one
session, and the deliverables must outlive it.

## Verification

Run the offline packaging checks with `pytest tests/unit`. The pi target
builds `egm-pi/` and `egm-pi.zip` from the same shared sources as the
Claude, OpenAI, and Vibe runtimes; the pi package manifest lives at
`.pi-plugin/package.json` in the repository and ships as the bundle's
root `package.json`. Installing the plugin alone does not establish
end-to-end workflow support: Goldfish reviews additionally require an
extension that spawns fresh-context subagents. See the
[harness test record](https://github.com/google/elephant-goldfish-model/blob/main/TESTING.md#harness-test-record)
for tested surfaces and limits.
