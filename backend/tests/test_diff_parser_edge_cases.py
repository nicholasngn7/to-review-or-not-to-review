"""Edge-case tests for the unified diff parser.

These complement `test_diff_parser.py` with the awkward inputs a real reviewer
would eventually hit: empty/malformed text, binary and mode-only changes, renames
with edits, paths containing spaces, CRLF endings, multiple hunks, and /dev/null
sides.
"""

from app.services.diff_parser import parse_diff


def test_empty_diff_yields_no_files():
    parsed = parse_diff("")
    assert parsed.files == []
    assert parsed.stats.files_changed == 0
    assert parsed.stats.added_lines == 0
    assert parsed.stats.removed_lines == 0
    assert parsed.stats.total_hunks == 0


def test_whitespace_only_diff_yields_no_files():
    parsed = parse_diff("   \n\n\t\n")
    assert parsed.files == []
    assert parsed.stats.files_changed == 0


def test_malformed_prose_is_ignored_gracefully():
    text = "this is not a diff\njust some notes\n@@ not a real header @@\nmore prose"
    parsed = parse_diff(text)
    # Nothing parseable -> no files, and crucially no exception.
    assert parsed.files == []
    assert parsed.stats.total_hunks == 0


def test_binary_diff_is_a_file_with_no_hunks():
    text = (
        "diff --git a/assets/logo.png b/assets/logo.png\n"
        "index 1234567..89abcde 100644\n"
        "Binary files a/assets/logo.png and b/assets/logo.png differ\n"
    )
    parsed = parse_diff(text)
    assert len(parsed.files) == 1
    f = parsed.files[0]
    assert f.change_type == "modified"
    assert f.old_path == "assets/logo.png"
    assert f.new_path == "assets/logo.png"
    assert f.hunks == []
    assert parsed.stats.added_lines == 0
    assert parsed.stats.removed_lines == 0


def test_mode_only_change_has_no_hunks():
    text = (
        "diff --git a/scripts/run.sh b/scripts/run.sh\n"
        "old mode 100644\n"
        "new mode 100755\n"
    )
    parsed = parse_diff(text)
    assert len(parsed.files) == 1
    f = parsed.files[0]
    assert f.change_type == "modified"
    assert f.hunks == []
    assert parsed.stats.added_lines == 0
    assert parsed.stats.removed_lines == 0


def test_rename_with_edits():
    text = (
        "diff --git a/old_name.py b/new_name.py\n"
        "similarity index 88%\n"
        "rename from old_name.py\n"
        "rename to new_name.py\n"
        "index 1234567..89abcde 100644\n"
        "--- a/old_name.py\n"
        "+++ b/new_name.py\n"
        "@@ -1,3 +1,3 @@\n"
        " import os\n"
        "-x = 1\n"
        "+x = 2\n"
        " y = 3\n"
    )
    parsed = parse_diff(text)
    assert len(parsed.files) == 1
    f = parsed.files[0]
    assert f.change_type == "renamed"
    assert f.old_path == "old_name.py"
    assert f.new_path == "new_name.py"
    assert len(f.hunks) == 1
    assert parsed.stats.added_lines == 1
    assert parsed.stats.removed_lines == 1


def test_paths_with_spaces_are_recovered_from_marker_lines():
    # The `diff --git` line is ambiguous for paths with spaces; the parser relies
    # on the --- / +++ marker lines to recover the real path.
    text = (
        "diff --git a/my folder/my file.py b/my folder/my file.py\n"
        "index 1234567..89abcde 100644\n"
        "--- a/my folder/my file.py\n"
        "+++ b/my folder/my file.py\n"
        "@@ -1,1 +1,2 @@\n"
        " x = 1\n"
        "+y = 2\n"
    )
    parsed = parse_diff(text)
    assert len(parsed.files) == 1
    f = parsed.files[0]
    assert f.old_path == "my folder/my file.py"
    assert f.new_path == "my folder/my file.py"
    assert parsed.stats.added_lines == 1


def test_crlf_line_endings_are_handled():
    text = (
        "diff --git a/a.txt b/a.txt\r\n"
        "--- a/a.txt\r\n"
        "+++ b/a.txt\r\n"
        "@@ -1,1 +1,2 @@\r\n"
        " x\r\n"
        "+y\r\n"
    )
    parsed = parse_diff(text)
    assert len(parsed.files) == 1
    hunk = parsed.files[0].hunks[0]
    contents = {line.kind: line.content for line in hunk.lines}
    # No stray carriage returns left in the parsed content.
    assert contents["context"] == "x"
    assert contents["added"] == "y"
    assert "\r" not in contents["added"]


def test_multiple_hunks_in_one_file():
    text = (
        "diff --git a/app/multi.py b/app/multi.py\n"
        "--- a/app/multi.py\n"
        "+++ b/app/multi.py\n"
        "@@ -1,2 +1,3 @@\n"
        " a\n"
        "+b\n"
        " c\n"
        "@@ -10,2 +11,3 @@\n"
        " d\n"
        "+e\n"
        " f\n"
    )
    parsed = parse_diff(text)
    assert len(parsed.files) == 1
    f = parsed.files[0]
    assert len(f.hunks) == 2
    assert parsed.stats.total_hunks == 2
    assert parsed.stats.added_lines == 2
    # Second hunk's line numbers start where its header says.
    assert f.hunks[1].old_start == 10
    assert f.hunks[1].new_start == 11


def test_dev_null_added_file_has_no_old_path():
    text = (
        "diff --git a/created.py b/created.py\n"
        "new file mode 100644\n"
        "--- /dev/null\n"
        "+++ b/created.py\n"
        "@@ -0,0 +1,2 @@\n"
        "+line one\n"
        "+line two\n"
    )
    parsed = parse_diff(text)
    f = parsed.files[0]
    assert f.change_type == "added"
    assert f.old_path is None
    assert f.new_path == "created.py"
    assert f.hunks[0].old_start == 0
    assert parsed.stats.added_lines == 2
    assert parsed.stats.removed_lines == 0


def test_dev_null_deleted_file_has_no_new_path():
    text = (
        "diff --git a/removed.py b/removed.py\n"
        "deleted file mode 100644\n"
        "--- a/removed.py\n"
        "+++ /dev/null\n"
        "@@ -1,2 +0,0 @@\n"
        "-line one\n"
        "-line two\n"
    )
    parsed = parse_diff(text)
    f = parsed.files[0]
    assert f.change_type == "deleted"
    assert f.old_path == "removed.py"
    assert f.new_path is None
    assert parsed.stats.removed_lines == 2
    assert parsed.stats.added_lines == 0
