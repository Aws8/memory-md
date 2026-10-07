import pytest

MEMORY_MD = """# Memory: Test

- Test user prefers bullet summaries [source: https://example.com/s/1; added: 2026-09-15]

## Index
- [[team]]
- [[projects/payments]]
"""


@pytest.fixture
def mem_repo(tmp_path):
    """A minimal spec-compliant memory repo."""
    root = tmp_path / "mem"
    (root / "projects").mkdir(parents=True)
    (root / "MEMORY.md").write_text(MEMORY_MD, encoding="utf-8")
    (root / "team.md").write_text(
        "# Team\n"
        "\n"
        "- Priya owns pricing [source: https://example.com/s/2; added: 2026-09-20]\n"
        "- See [[projects/payments]] for launch details\n",
        encoding="utf-8",
    )
    (root / "projects" / "payments.md").write_text(
        "# Payments\n"
        "\n"
        "- Launch deadline is 2026-10-15 [source: https://example.com/s/3; added: 2026-09-21]\n",
        encoding="utf-8",
    )
    return root


@pytest.fixture
def messy_repo(tmp_path):
    """A repo with every lint problem."""
    root = tmp_path / "messy"
    (root / "projects").mkdir(parents=True)
    (root / "MEMORY.md").write_text(
        "# Memory\n"
        "\n"
        "- something [bad-date-format]\n"
        "\n"
        "## Index\n"
        "- [[team]]\n"
        "- [[team]]\n"
        "- [[nowhere/ghost]]\n"
        "- [[notes/x#missing-heading]]\n",
        encoding="utf-8",
    )
    (root / "team.md").write_text(
        "# Team\n"
        "\n"
        "- Priya owns pricing [source: https://x; added: not-a-date]\n"
        "- Entry with no metadata at all\n"
        "- another bare entry\n",
        encoding="utf-8",
    )
    (root / "orphan.md").write_text("# Orphan\n- nobody links me [added: 2020-01-01]\n", encoding="utf-8")
    (root / "notes").mkdir(exist_ok=True)
    (root / "notes" / "x.md").write_text("# X\n- hi [added: 2026-01-01]\n", encoding="utf-8")
    return root
