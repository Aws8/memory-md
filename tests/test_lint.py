from memory_md.lint import ERROR, INFO, WARNING, lint, summarize
from memory_md.repo import MemoryRepo


def rules(findings):
    return {f.rule for f in findings}


def test_clean_repo_has_no_errors(mem_repo):
    findings = lint(MemoryRepo(mem_repo))
    assert not any(f.severity == ERROR for f in findings)
    assert not any(f.severity == WARNING for f in findings)


def test_missing_memory_md(tmp_path):
    d = tmp_path / "empty"
    d.mkdir()
    findings = lint(MemoryRepo(d))
    assert "no-memory-md" in rules(findings)
    assert any(f.severity == ERROR for f in findings)


def test_messy_repo(messy_repo):
    findings = lint(MemoryRepo(messy_repo))
    r = rules(findings)
    assert "broken-link" in r
    assert "dead-anchor" in r
    assert "duplicate-index-entry" in r
    assert "orphan-file" in r
    assert "bad-added-date" in r
    s = summarize(findings)
    assert s[ERROR] == 1  # exactly the ghost link
    assert s[INFO] >= 2  # bare entries


def test_bloated_memory_md(tmp_path):
    root = tmp_path / "bloat"
    root.mkdir()
    lines = ["# Memory"] + [f"- entry {i} [added: 2026-01-01]" for i in range(120)]
    lines += ["", "## Index", "- [[a]]"]
    (root / "MEMORY.md").write_text("\n".join(lines))
    (root / "a.md").write_text("# A\n- x [added: 2026-01-01]\n")
    findings = lint(MemoryRepo(root))
    assert "memory-md-bloat" in rules(findings)


def test_git_findings(mem_repo):
    import subprocess

    subprocess.run(["git", "init"], cwd=mem_repo, capture_output=True)
    findings = lint(MemoryRepo(mem_repo))
    r = rules(findings)
    assert "uncommitted-changes" in r or "no-remote" in r
