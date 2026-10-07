from pathlib import Path

from memory_md.repo import MemoryRepo, find_repo, parse_metadata, slugify


def test_parse_metadata():
    assert parse_metadata("source: https://x; added: 2026-09-03") == {
        "source": "https://x",
        "added": "2026-09-03",
    }
    assert parse_metadata("added: 2026-01-01") == {"added": "2026-01-01"}
    assert parse_metadata("just a note") is None
    # URL values with colons must not split
    assert parse_metadata("source: https://a.b/c:8080/d") == {"source": "https://a.b/c:8080/d"}


def test_slugify():
    assert slugify("Team Structure") == "team-structure"
    assert slugify("Autocompletion, Phase 2!") == "autocompletion-phase-2"


def test_load_and_resolve(mem_repo):
    repo = MemoryRepo(mem_repo)
    assert repo.entrypoint is not None
    assert repo.resolve("team").relpath == Path("team.md")
    assert repo.resolve("projects/payments").relpath == Path("projects/payments.md")
    assert repo.resolve("missing") is None


def test_links_and_entries(mem_repo):
    repo = MemoryRepo(mem_repo)
    team = repo.files[Path("team.md")]
    assert any(l.path == "projects/payments" for l in team.links)
    ep = repo.entrypoint
    entry = ep.entries[0]
    assert entry.text == "Test user prefers bullet summaries"
    assert entry.metadata["source"] == "https://example.com/s/1"
    assert entry.metadata["added"] == "2026-09-15"


def test_index_links(mem_repo):
    repo = MemoryRepo(mem_repo)
    paths = {l.path for l in repo.index_links()}
    assert paths == {"team", "projects/payments"}


def test_reachable(mem_repo):
    repo = MemoryRepo(mem_repo)
    assert repo.reachable() == {Path("MEMORY.md"), Path("team.md"), Path("projects/payments.md")}


def test_code_fence_ignored(tmp_path):
    root = tmp_path / "r"
    root.mkdir()
    (root / "MEMORY.md").write_text("# M\n\n```\n- [[fake]]\n```\n\n## Index\n- [[real]]\n")
    (root / "real.md").write_text("# R\n- ok [added: 2026-01-01]\n")
    repo = MemoryRepo(root)
    assert all(l.path != "fake" for l in repo.entrypoint.links)
    # only the real index bullet is an entry; the fenced one is ignored
    assert [e.text for e in repo.entrypoint.entries] == ["[[real]]"]


def test_find_repo_walks_up(mem_repo):
    deep = mem_repo / "projects"
    repo = find_repo(deep)
    assert repo.root == mem_repo.resolve()
