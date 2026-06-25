"""Tests for the unified diff parser."""

from app.services.diff_parser import parse_diff

MODIFIED_DIFF = """\
diff --git a/app/calc.py b/app/calc.py
index 1234567..89abcde 100644
--- a/app/calc.py
+++ b/app/calc.py
@@ -1,5 +1,6 @@
 def add(a, b):
-    return a + b
+    # add two numbers
+    return a + b + 0
 
 def sub(a, b):
     return a - b
"""

ADDED_DIFF = """\
diff --git a/new_module.py b/new_module.py
new file mode 100644
index 0000000..e69de29
--- /dev/null
+++ b/new_module.py
@@ -0,0 +1,3 @@
+def hello():
+    return "hi"
+
"""

DELETED_DIFF = """\
diff --git a/old_module.py b/old_module.py
deleted file mode 100644
index e69de29..0000000
--- a/old_module.py
+++ /dev/null
@@ -1,2 +0,0 @@
-def goodbye():
-    return "bye"
"""

RENAMED_DIFF = """\
diff --git a/old_name.py b/new_name.py
similarity index 100%
rename from old_name.py
rename to new_name.py
"""

MULTI_FILE_DIFF = MODIFIED_DIFF + ADDED_DIFF + DELETED_DIFF


def test_modified_file_single_hunk():
    parsed = parse_diff(MODIFIED_DIFF)
    assert len(parsed.files) == 1
    f = parsed.files[0]
    assert f.change_type == "modified"
    assert f.old_path == "app/calc.py"
    assert f.new_path == "app/calc.py"
    assert len(f.hunks) == 1
    hunk = f.hunks[0]
    assert hunk.old_start == 1
    assert hunk.new_start == 1
    kinds = [line.kind for line in hunk.lines]
    assert "added" in kinds
    assert "removed" in kinds
    assert "context" in kinds


def test_added_file():
    parsed = parse_diff(ADDED_DIFF)
    f = parsed.files[0]
    assert f.change_type == "added"
    assert f.old_path is None
    assert f.new_path == "new_module.py"
    # Only added lines, no removals.
    assert parsed.stats.added_lines == 3
    assert parsed.stats.removed_lines == 0


def test_deleted_file():
    parsed = parse_diff(DELETED_DIFF)
    f = parsed.files[0]
    assert f.change_type == "deleted"
    assert f.old_path == "old_module.py"
    assert f.new_path is None
    assert parsed.stats.removed_lines == 2
    assert parsed.stats.added_lines == 0


def test_renamed_file_no_hunks():
    parsed = parse_diff(RENAMED_DIFF)
    f = parsed.files[0]
    assert f.change_type == "renamed"
    assert f.old_path == "old_name.py"
    assert f.new_path == "new_name.py"
    assert f.hunks == []


def test_multiple_files():
    parsed = parse_diff(MULTI_FILE_DIFF)
    assert len(parsed.files) == 3
    change_types = [f.change_type for f in parsed.files]
    assert change_types == ["modified", "added", "deleted"]
    assert parsed.stats.files_changed == 3


def test_line_number_tracking():
    parsed = parse_diff(MODIFIED_DIFF)
    hunk = parsed.files[0].hunks[0]
    by_kind = {"added": [], "removed": [], "context": []}
    for line in hunk.lines:
        by_kind[line.kind].append(line)

    # Added lines have a new line number but no old line number.
    for line in by_kind["added"]:
        assert line.new_line_no is not None
        assert line.old_line_no is None

    # Removed lines have an old line number but no new line number.
    for line in by_kind["removed"]:
        assert line.old_line_no is not None
        assert line.new_line_no is None

    # Context lines have both.
    for line in by_kind["context"]:
        assert line.old_line_no is not None
        assert line.new_line_no is not None

    # First context line ("def add(a, b):") sits at line 1 in both files.
    first_context = by_kind["context"][0]
    assert first_context.old_line_no == 1
    assert first_context.new_line_no == 1


def test_stats_calculated_correctly():
    parsed = parse_diff(MULTI_FILE_DIFF)
    stats = parsed.stats
    # modified: +2/-1, added: +3, deleted: -2  => +5 / -3
    assert stats.added_lines == 5
    assert stats.removed_lines == 3
    assert stats.total_hunks == 3
    assert stats.files_changed == 3
