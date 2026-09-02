"""Generate a deterministic local dependency audit report and a basic SBOM."""

from __future__ import annotations

import json
import pathlib
import re
import sys
from importlib import metadata


ROOT = pathlib.Path(__file__).resolve().parents[1]
REQ_DIR = ROOT / "requirements"
DOCS_DIR = ROOT / "docs"
AUDIT_MD = DOCS_DIR / "dependency_audit.md"
SBOM_JSON = DOCS_DIR / "sbom_basic.json"

REQ_NAME_RE = re.compile(r"^\s*([A-Za-z0-9_.-]+)")


def normalize_name(name: str) -> str:
    return name.replace("_", "-").lower()


def parse_requirements_file(path: pathlib.Path, seen: set[pathlib.Path] | None = None) -> list[str]:
    seen = seen or set()
    path = path.resolve()
    if path in seen:
        return []
    seen.add(path)

    entries: list[str] = []
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("-r "):
            nested = (path.parent / line[3:].strip()).resolve()
            entries.extend(parse_requirements_file(nested, seen))
            continue
        entries.append(line)
    return entries


def requirement_name(requirement: str) -> str:
    match = REQ_NAME_RE.match(requirement)
    if not match:
        raise ValueError(f"No pude extraer el nombre del requirement: {requirement}")
    return match.group(1)


def load_installed_distributions() -> dict[str, dict[str, str]]:
    result: dict[str, dict[str, str]] = {}
    for dist in metadata.distributions():
        name = dist.metadata.get("Name") or dist.metadata.get("Summary") or dist.name
        if not name:
            continue
        normalized = normalize_name(name)
        result[normalized] = {
            "name": name,
            "version": dist.version,
            "summary": (dist.metadata.get("Summary") or "").strip(),
            "license": (
                dist.metadata.get("License-Expression")
                or dist.metadata.get("License")
                or ""
            ).strip(),
        }
    return dict(sorted(result.items()))


def build_requirement_section(title: str, requirement_lines: list[str], installed: dict[str, dict[str, str]]) -> tuple[list[dict[str, str]], str]:
    rows: list[dict[str, str]] = []
    markdown_lines = [
        f"### {title}",
        "",
        "| Requirement | Resolved | License | Summary |",
        "| --- | --- | --- | --- |",
    ]
    for req in requirement_lines:
        normalized = normalize_name(requirement_name(req))
        dist = installed.get(normalized)
        resolved = dist["version"] if dist else "(missing)"
        summary = dist["summary"] if dist and dist["summary"] else ""
        license_name = dist["license"] if dist and dist["license"] else "(not declared in package metadata)"
        rows.append(
            {
                "requirement": req,
                "normalized_name": normalized,
                "resolved_version": resolved,
                "license": license_name,
                "summary": summary,
            }
        )
        markdown_lines.append(f"| `{req}` | `{resolved}` | {license_name} | {summary} |")
    markdown_lines.append("")
    return rows, "\n".join(markdown_lines)


def build_findings(base_reqs: list[str], installed: dict[str, dict[str, str]]) -> list[str]:
    findings: list[str] = []
    missing = []
    for req in base_reqs:
        normalized = normalize_name(requirement_name(req))
        if normalized not in installed:
            missing.append(req)
    if missing:
        findings.append(
            "Faltan dependencias runtime declaradas en el venv actual: "
            + ", ".join(f"`{req}`" for req in missing)
        )
    else:
        findings.append("Todas las dependencias runtime declaradas estan presentes en el venv local.")

    unpinned = [req for req in base_reqs if ">=" in req and "==" not in req]
    if unpinned:
        findings.append(
            "Las dependencias runtime usan minimos (`>=`) y no estan pinneadas; el entorno no es totalmente reproducible todavia."
        )

    findings.append(
        "Este archivo es un inventario del entorno que lo genero. La verificacion de advisories se ejecuta por separado con `python -m pip_audit -r requirements\\audit.txt`."
    )
    findings.append(
        "Las licencias se leen de `License-Expression` o `License` en los metadatos instalados. Un campo vacio requiere consultar la distribucion upstream."
    )
    findings.append(
        "La licencia MIT de Instanashelock no relicencia dependencias ni herramientas de build; consulte `THIRD_PARTY_NOTICES.md`."
    )
    return findings


def render_markdown(
    base_rows: list[dict[str, str]],
    dev_rows: list[dict[str, str]],
    build_rows: list[dict[str, str]],
    findings: list[str],
    installed: dict[str, dict[str, str]],
    base_md: str,
    dev_md: str,
    build_md: str,
) -> str:
    installed_lines = [
        "### Installed inventory",
        "",
        "| Package | Version | License |",
        "| --- | --- | --- |",
    ]
    for pkg in installed.values():
        license_name = pkg["license"] or ""
        installed_lines.append(f"| `{pkg['name']}` | `{pkg['version']}` | {license_name} |")
    installed_lines.append("")

    finding_lines = ["## Findings", ""]
    for finding in findings:
        finding_lines.append(f"- {finding}")
    finding_lines.append("")

    return "\n".join(
        [
            "# Dependency Audit",
            "",
            "Inventario local reproducible del entorno revisado para desarrollo y release de Instanashelock.",
            "",
            "## Direct requirements",
            "",
            base_md,
            dev_md,
            build_md,
            "\n".join(installed_lines),
            "\n".join(finding_lines),
            "## Regeneration",
            "",
            "```powershell",
            r".\scripts\audit.ps1",
            "```",
            "",
            "La regeneracion tambien ejecuta `pip-audit`; un resultado limpio no garantiza ausencia de vulnerabilidades.",
            "",
        ]
    )


def build_sbom_payload(
    base_rows: list[dict[str, str]],
    dev_rows: list[dict[str, str]],
    build_rows: list[dict[str, str]],
    findings: list[str],
    installed: dict[str, dict[str, str]],
) -> dict:
    return {
        "format": "instanashelock-basic-sbom",
        "runtime_requirements": base_rows,
        "development_requirements": dev_rows,
        "build_requirements": build_rows,
        "installed_packages": list(installed.values()),
        "findings": findings,
        "regenerate_with": r".\scripts\audit.ps1",
        "python_version": sys.version.split()[0],
    }


def main() -> int:
    DOCS_DIR.mkdir(exist_ok=True)

    installed = load_installed_distributions()
    base_reqs = parse_requirements_file(REQ_DIR / "base.txt")
    dev_reqs = parse_requirements_file(REQ_DIR / "dev.txt")
    build_reqs = parse_requirements_file(REQ_DIR / "build.txt")

    base_rows, base_md = build_requirement_section("Runtime", base_reqs, installed)
    dev_rows, dev_md = build_requirement_section("Development", dev_reqs, installed)
    build_rows, build_md = build_requirement_section("Build", build_reqs, installed)
    findings = build_findings(base_reqs, installed)

    markdown = render_markdown(
        base_rows,
        dev_rows,
        build_rows,
        findings,
        installed,
        base_md,
        dev_md,
        build_md,
    )
    AUDIT_MD.write_text(markdown, encoding="utf-8")

    sbom_payload = build_sbom_payload(base_rows, dev_rows, build_rows, findings, installed)
    SBOM_JSON.write_text(json.dumps(sbom_payload, indent=2, sort_keys=True), encoding="utf-8")

    print(f"Wrote {AUDIT_MD.relative_to(ROOT)} and {SBOM_JSON.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
