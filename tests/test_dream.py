from datetime import date

from memory_md.dream import dream
from memory_md.repo import MemoryRepo


def kinds(suggestions):
    return {s.kind for s in suggestions}


def test_clean_repo(mem_repo):
    suggestions = dream(MemoryRepo(mem_repo), today=date(2026, 10, 7))
    assert not any(s.kind in {"duplicate", "stale", "contradiction"} for s in suggestions)


def test_stale_and_duplicate(tmp_path):
    root = tmp_path / "d"
    root.mkdir()
    (root / "MEMORY.md").write_text("# M\n\n## Index\n- [[a]]\n")
    (root / "a.md").write_text(
        "# A\n"
        "- The API endpoint is api.internal/v2 [source: https://s/1; added: 2026-01-01]\n"
        "- API endpoint is api.internal/v2 [source: https://s/2; added: 2026-01-02]\n"
        "- Price cache rebuilds every 10 seconds [added: 2026-10-05]\n"
        "- Price cache rebuilds every 60 seconds [added: 2026-10-06]\n"
    )
    suggestions = dream(MemoryRepo(root), today=date(2026, 10, 7), stale_days=30)
    k = kinds(suggestions)
    assert "stale" in k
    assert "duplicate" in k
    assert "contradiction" in k  # same subject, 10 vs 60 seconds


def test_unindexed(tmp_path):
    root = tmp_path / "u"
    root.mkdir()
    (root / "MEMORY.md").write_text("# M\n\n## Index\n- [[a]]\n")
    (root / "a.md").write_text("# A\n- see [[b]] [added: 2026-10-01]\n")
    (root / "b.md").write_text("# B\n- x [added: 2026-10-01]\n")
    suggestions = dream(MemoryRepo(root))
    assert any(s.kind == "unindexed" and s.file.as_posix() == "b.md" for s in suggestions)
