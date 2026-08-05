import textwrap, pytest
from doc_digest.config import load_config

def _write(tmp_path, body):
    p = tmp_path / "d.toml"; p.write_text(textwrap.dedent(body)); return p

def test_loads_projects_and_defaults(tmp_path):
    cfg = load_config(_write(tmp_path, """
        base = "~/hub"
        exclude = ["**/node_modules/**"]
        sdd_globs = ["docs/superpowers/**"]
        [[project]]
        name = "Mentible"
        include = ["docs", "Plans"]
    """))
    assert cfg.projects[0].name == "Mentible"
    assert cfg.projects[0].include == ["docs", "Plans"]
    assert cfg.sdd_globs == ["docs/superpowers/**"]
    assert cfg.doc_exts == [".md", ".txt", ".rst"]   # default
    assert str(cfg.base).endswith("/hub")            # ~ expanded

def test_missing_base_raises(tmp_path):
    with pytest.raises(ValueError):
        load_config(_write(tmp_path, '[[project]]\nname="x"\ninclude=["docs"]\n'))

def test_no_projects_raises(tmp_path):
    with pytest.raises(ValueError):
        load_config(_write(tmp_path, 'base="~/hub"\n'))
