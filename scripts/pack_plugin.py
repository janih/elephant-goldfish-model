# Copyright 2026 Google LLC.
# SPDX-License-Identifier: Apache-2.0

"""Build runtime folders and reproducible ZIPs without development files."""

import argparse
import json
from pathlib import Path
import tempfile
import zipfile

SHARED = (
    "LICENSE", "README.md",
    "skills/*/SKILL.md", "skills/*/agents/openai.yaml",
    "skills/*/assets/*.svg", "skills/*/assets/*.png", "skills/*/references/*.md",
    "skills/*/references/*.json", "agents/*.md", "resources/*.md",
    "resources/document_standards/*.md", "docs/index.md", "docs/getting_started.md",
    "docs/harnesses.md", "docs/claude.md", "docs/codex.md", "docs/faq.md",
    "docs/privacy.md", "docs/releases.md",
    "assets/*.svg", "assets/*.png", "docs/assets/*.svg", "docs/assets/*.png",
)
HOST = {
    "claude": (".claude-plugin/plugin.json", "plugin.json",
               ".claude-plugin/icon.png", ".claude-plugin/agents/*.md"),
    "openai": (".codex-plugin/plugin.json", "plugin.json",),
    # Vibe loads the manifest from the bundle root, and the portable root
    # manifest omits $schema for omp, so the source manifest ships renamed.
    "vibe": (".vibe-plugin/plugin.json", "docs/vibe.md"),
}
RENAMES = {
    "vibe": {".vibe-plugin/plugin.json": "plugin.json"},
}
# Bundle paths that must ship for each target, including the root manifest.
REQUIRED_MANIFEST = {
    "claude": ("plugin.json", ".claude-plugin/plugin.json"),
    "openai": ("plugin.json", ".codex-plugin/plugin.json"),
    "vibe": ("plugin.json", "docs/vibe.md"),
}
SKILLS = (
    "egm-bootstrap", "egm-brainstorm", "egm-draft", "egm-drift-report",
    "egm-resolve", "egm-review", "egm-review-loop",
)
REQUIRED_SHARED = (
    "LICENSE", "README.md", "assets/icon.svg",
    "docs/index.md", "docs/getting_started.md", "docs/harnesses.md",
    "docs/claude.md", "docs/codex.md", "docs/faq.md", "docs/privacy.md",
    "resources/README.md", "resources/execution_instructions.md",
    "skills/egm-bootstrap/references/worker-return.schema.json",
    "skills/egm-bootstrap/references/templates.md",
    "skills/egm-draft/references/design_doc.md",
) + tuple(
    f"skills/{skill}/{name}"
    for skill in SKILLS
    for name in ("SKILL.md", "agents/openai.yaml", "assets/icon.svg")
) + tuple(
    f"agents/{name}.md" for name in (
        "bootstrap_orchestrator", "codebase_details", "comprehension",
        "design_critic", "implementation_readiness", "structural", "style",
        "synthesizer", "zoom_out",
    )
) + tuple(
    f"resources/document_standards/{name}-standard.md" for name in (
        "feature-spec", "heilmeier", "implementation-readiness",
        "re-implementation", "zoom-out",
    )
)


def build(root: Path, target: str, output: Path) -> tuple[Path, Path]:
  """Write a new runtime folder and ZIP; refuse unsafe inputs or overwrites."""
  root = root.resolve()
  folder = output.resolve() / f"egm-{target}"
  archive = folder.with_suffix(".zip")
  if any(path.exists() or path.is_symlink() for path in (folder, archive)):
    raise ValueError("Output folder or ZIP already exists")
  if folder == root or root.is_relative_to(folder):
    raise ValueError("Output must not contain the source tree")
  files = {}
  renames = RENAMES.get(target, {})
  for pattern in SHARED + HOST[target]:
    for path in root.glob(pattern):
      relative = path.relative_to(root)
      if any((root / Path(*relative.parts[:i])).is_symlink()
             for i in range(1, len(relative.parts) + 1)):
        raise ValueError(f"Symlink in runtime path: {relative}")
      if not path.resolve().is_relative_to(root):
        raise ValueError(f"Path outside source: {relative}")
      if path.is_file():
        destination = Path(renames.get(relative.as_posix(), relative.as_posix()))
        if destination in files:
          raise ValueError(f"Duplicate bundle path: {destination}")
        files[destination] = relative
  for name in REQUIRED_SHARED + REQUIRED_MANIFEST[target]:
    if Path(name) not in files:
      raise ValueError(f"Missing required file: {name}")
  manifest = json.loads((root / HOST[target][0]).read_text(encoding="utf-8"))
  if target == "vibe" and manifest.get("$schema") != (
      "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json"):
    raise ValueError("Vibe manifest must declare the agent-plugins 1.0.0 schema")
  portable = json.loads((root / "plugin.json").read_text(encoding="utf-8"))
  openai = portable.get("extensions", {}).get("com.openai", {})
  if manifest.get("hooks") or portable.get("hooks") or openai.get("hooks"):
    raise ValueError("Directory packages cannot contain hooks")
  for metadata in (manifest, portable, openai):
    if any(metadata.get(key) for key in ("mcpServers", "mcp", "apps")):
      raise ValueError("This runtime builder does not package MCP or app dependencies")
  agents = manifest.get("agents", [])
  if not isinstance(agents, (str, list)):
    raise ValueError(f"Invalid manifest agents: {agents!r}")
  references = [agents] if isinstance(agents, str) else list(agents)
  if target == "openai":
    # Codex reads the host manifest, so check it as well as the portable copy.
    interfaces = [manifest.get("interface", {})]
    if "interface" in openai:
      interfaces.append(openai["interface"])
    for interface in interfaces:
      for key in ("composerIcon", "logo"):
        if not interface.get(key):
          raise ValueError(f"Missing OpenAI interface reference: {key}")
        references.append(interface[key])
  elif target == "claude":
    references.append(manifest.get("icon", "./.claude-plugin/icon.png"))
  for reference in references:
    path = Path(reference)
    if path.is_absolute() or ".." in path.parts or path not in files:
      raise ValueError(f"Unbundled manifest reference: {reference}")
  output.mkdir(parents=True, exist_ok=True)
  folder.mkdir()
  with tempfile.TemporaryDirectory(prefix=".egm-", dir=output) as temporary:
    staged = Path(temporary) / archive.name
    with zipfile.ZipFile(staged, "x", zipfile.ZIP_DEFLATED) as bundle:
      for destination, relative in sorted(files.items()):
        data = (root / relative).read_bytes()
        runtime = folder / destination
        runtime.parent.mkdir(parents=True, exist_ok=True)
        runtime.write_bytes(data)
        runtime.chmod(0o644)
        info = zipfile.ZipInfo(destination.as_posix(), (1980, 1, 1, 0, 0, 0))
        info.create_system = 3
        info.external_attr = 0o100644 << 16
        info.compress_type = zipfile.ZIP_DEFLATED
        bundle.writestr(info, data)
    # Windows exclusive file creation can follow a dangling symlink. Linking
    # the completed ZIP claims the final directory entry without following it.
    archive.hardlink_to(staged)
  return folder, archive


if __name__ == "__main__":
  parser = argparse.ArgumentParser(description=__doc__)
  parser.add_argument("--target", required=True, choices=HOST)
  parser.add_argument("--output", required=True, type=Path)
  args = parser.parse_args()
  runtime, bundle = build(Path(__file__).resolve().parents[1],
                          args.target, args.output)
  print(f"Runtime: {runtime}\nZIP: {bundle}")
