from memory_md.cli import main


def test_lint_clean(mem_repo, capsys):
    rc = main(["lint", str(mem_repo)])
    out = capsys.readouterr().out
    assert rc == 0
    assert "0 error(s)" in out


def test_lint_messy_fails(messy_repo, capsys):
    rc = main(["lint", str(messy_repo)])
    out = capsys.readouterr().out
    assert rc == 1
    assert "broken-link" in out
    assert "orphan-file" in out


def test_lint_verbose_shows_info(mem_repo, capsys):
    rc = main(["lint", "-v", str(mem_repo)])
    out = capsys.readouterr().out
    assert rc == 0
    assert "info" in out


def test_graph_mermaid(mem_repo, capsys):
    rc = main(["graph", str(mem_repo)])
    out = capsys.readouterr().out
    assert rc == 0
    assert "graph LR" in out
    assert "MEMORY.md" in out
    assert "-->" in out


def test_graph_dot_and_list(mem_repo, capsys):
    assert main(["graph", "-f", "dot", str(mem_repo)]) == 0
    assert "digraph memory" in capsys.readouterr().out
    assert main(["graph", "-f", "list", str(mem_repo)]) == 0
    assert "MEMORY.md ->" in capsys.readouterr().out


def test_graph_json(mem_repo, capsys):
    import json

    rc = main(["graph", "-f", "json", str(mem_repo)])
    data = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert len(data["nodes"]) == 3
    assert {e["to"] for e in data["edges"]} == {"team.md", "projects/payments.md"}


def test_stats(mem_repo, capsys):
    rc = main(["stats", str(mem_repo)])
    out = capsys.readouterr().out
    assert rc == 0
    assert "entries:" in out
    assert "3" in out


def test_init_and_add(tmp_path, capsys):
    target = tmp_path / "newmem"
    rc = main(["init", str(target), "--name", "Aws"])
    assert rc == 0
    assert (target / "MEMORY.md").exists()
    # and the scaffolded repo passes lint (warnings allowed: it's fresh)
    rc = main(["lint", str(target)])
    out = capsys.readouterr().out
    assert "0 error(s)" in out
    # add an entry
    rc = main(["add", "projects/lawsone", "Lawsone ships weekly", "--source", "https://s/9", str(target)])
    assert rc == 0
    text = (target / "projects" / "lawsone.md").read_text()
    assert "- Lawsone ships weekly [source: https://s/9; added: " in text
    # add with index
    rc = main(["add", "projects/other", "second entry", "--index", str(target)])
    assert rc == 0
    assert "[[projects/other]]" in (target / "MEMORY.md").read_text()


def test_dream_cli(messy_repo, capsys):
    rc = main(["dream", str(messy_repo)])
    out = capsys.readouterr().out
    assert rc == 0
    assert "suggestion" in out or "stale" in out
