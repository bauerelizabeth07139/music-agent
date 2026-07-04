"""Portable skill loader for Music Agent.

Discovers local skills from a manifest-based plugin structure and
exposes them as reusable capability objects. This keeps skills portable
across devices without hard-coded import paths.
"""

from __future__ import annotations

import importlib.util
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parent.parent / "skills"


@dataclass
class Skill:
    path: Path
    manifest: Dict[str, Any]
    module: Any

    @property
    def id(self) -> str:
        return str(self.manifest.get("id", self.path.name))

    @property
    def name(self) -> str:
        return str(self.manifest.get("name", self.path.name))

    @property
    def skill_type(self) -> str:
        return str(self.manifest.get("type", "unknown"))

    @property
    def version(self) -> str:
        return str(self.manifest.get("version", "0.0.0"))

    @property
    def runtime(self) -> Dict[str, Any]:
        return self.manifest.get("runtime", {})

    @property
    def install(self) -> Dict[str, Any]:
        return self.manifest.get("install", {})

    @property
    def inputs(self) -> Dict[str, Any]:
        return self.manifest.get("inputs", {})

    @property
    def outputs(self) -> Dict[str, Any]:
        return self.manifest.get("outputs", {})

    @property
    def license(self) -> str:
        return str(self.manifest.get("license", ""))


def _load_module(path: Path):
    if not path.exists():
        raise FileNotFoundError(f"Skill entry not found: {path}")
    spec = importlib.util.spec_from_file_location(path.stem, str(path))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_skills(root: Path = ROOT) -> List[Skill]:
    skills: List[Skill] = []
    if not root.exists():
        return skills
    for child in sorted(root.iterdir()):
        if not child.is_dir():
            continue
        manifest_path = child / "manifest.json"
        entry_path = child / "skill.py"
        if not manifest_path.exists() or not entry_path.exists():
            continue
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
            module = _load_module(entry_path)
            skills.append(Skill(path=child, manifest=manifest, module=module))
        except Exception:
            continue
    return skills


def get_skill_by_id(skill_id: str, root: Path = ROOT) -> Optional[Skill]:
    for skill in load_skills(root):
        if skill.id == skill_id:
            return skill
    return None


def get_skill_by_type(skill_type: str, root: Path = ROOT) -> Optional[Skill]:
    for skill in load_skills(root):
        if skill.skill_type == skill_type:
            return skill
    return None


def list_skill_summaries(root: Path = ROOT) -> List[Dict[str, Any]]:
    summaries = []
    for skill in load_skills(root):
        summaries.append({
            "id": skill.id,
            "name": skill.name,
            "type": skill.skill_type,
            "version": skill.version,
            "license": skill.license,
            "runtime": skill.runtime,
            "install": skill.install,
            "inputs": skill.inputs,
            "outputs": skill.outputs,
            "path": str(skill.path),
            "capabilities": skill.manifest.get("capabilities", {}),
            "metadata": skill.manifest.get("metadata", {}),
        })
    return summaries