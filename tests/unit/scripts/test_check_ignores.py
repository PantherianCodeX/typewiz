# Copyright 2025 CrownOps Engineering
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from scripts.check_ignores import MAX_JUSTIFICATION_LINE_LENGTH
from scripts.check_ignores import main as check_main
from scripts.check_license_headers import HEADER_BLOCK

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

    from _pytest.capture import CaptureFixture


def _run_checker(tmp_path: Path, content: str) -> int:
    target = tmp_path / "sample.py"
    target.write_text(content, encoding="utf-8")
    # Restrict scan to the temporary directory
    return check_main([str(tmp_path)])


def test_checker_accepts_properly_justified_ignores(tmp_path: Path) -> None:
    content = """from __future__ import annotations


def good() -> None:
    # ignore JUSTIFIED: demonstration of properly justified ignore
    value = 1 / 0  # pragma: no cover


def also_good() -> None:
    # ignore JUSTIFIED: this ignore demonstrates a ruff noqa
    import os  # noqa: F401
"""
    exit_code = _run_checker(tmp_path, content)
    assert exit_code == 0


def test_checker_flags_missing_justification(tmp_path: Path) -> None:
    content = """from __future__ import annotations


def bad() -> None:
    value = 1 / 0  # pragma: no cover
"""
    exit_code = _run_checker(tmp_path, content)
    assert exit_code == 1


def test_checker_flags_empty_justification(tmp_path: Path) -> None:
    content = """from __future__ import annotations


def bad() -> None:
    # ignore JUSTIFIED:
    value = 1 / 0  # pragma: no cover
"""
    exit_code = _run_checker(tmp_path, content)
    assert exit_code == 1


def test_checker_rejects_non_adjacent_justification(tmp_path: Path) -> None:
    content = """from __future__ import annotations


def bad() -> None:
    # ignore JUSTIFIED: too far away

    # some other comment
    value = 1 / 0  # pragma: no cover
"""
    exit_code = _run_checker(tmp_path, content)
    assert exit_code == 1


def test_json_sources_labels_for_all_tools(tmp_path: Path, capsys: CaptureFixture[str]) -> None:
    content = """from __future__ import annotations


def ruff_case() -> None:
    value = 1  # noqa: F401


def pylint_case() -> None:
    value = 2  # pylint: disable=unused-variable


def mypy_case(raw: object) -> None:
    value = raw  # type: ignore[assignment]
    _ = value


def pyright_case(config: dict) -> None:
    value = config.get("key")  # pyright: ignore[reportUnknownArgumentType]
    _ = value


def coverage_case() -> None:
    value = 3  # pragma: no cover


def safety_case() -> None:
    secret = "x"  # nosec B105
    _ = secret
"""
    target = tmp_path / "sample.py"
    target.write_text(content, encoding="utf-8")

    exit_code = check_main(["--json", str(tmp_path)])
    captured = capsys.readouterr()
    assert exit_code == 1  # missing justifications

    payload = json.loads(captured.out)
    # Collect all unique sources tuples from violations.
    seen_sources = {tuple(item["sources"]) for item in payload}

    # We don't care which IGN00x code each has, only that every logical source
    # shows up exactly as expected.
    assert ("ruff",) in seen_sources
    assert ("pylint",) in seen_sources
    assert ("mypy",) in seen_sources
    assert ("pyright",) in seen_sources
    assert ("coverage",) in seen_sources
    assert ("safety",) in seen_sources


def test_checker_json_output(tmp_path: Path, capsys: CaptureFixture[str]) -> None:
    content = """from __future__ import annotations


def bad() -> None:
    value = 1 / 0  # pragma: no cover
"""
    target = tmp_path / "sample.py"
    target.write_text(content, encoding="utf-8")
    # Use explicit --json to ensure JSON output is produced
    args: Sequence[str] = ["--json", str(tmp_path)]
    exit_code = check_main(args)
    captured = capsys.readouterr()
    assert exit_code == 1
    payload = json.loads(captured.out)
    assert isinstance(payload, list)
    assert payload
    first = payload[0]
    assert {"file", "line", "column", "code", "message", "sources"} <= set(first.keys())
    # JSON mode should not emit human-readable summaries
    assert "[ratchetr]" not in captured.out


def test_checker_accepts_multi_line_justification(tmp_path: Path) -> None:
    content = """from __future__ import annotations


def good() -> None:
    # ignore JUSTIFIED: first line of reason
    # second line of reason
    value = 1 / 0  # pragma: no cover
"""
    exit_code = _run_checker(tmp_path, content)
    assert exit_code == 0


def test_justification_line_too_long_is_rejected(tmp_path: Path) -> None:
    long_line = (
        "# ignore JUSTIFIED: this justification line is intentionally made longer than the "
        "configured maximum width to trigger IGN030 and should be wrapped"
    )
    content = f"""from __future__ import annotations


def bad() -> None:
    {long_line}
    value = 1 / 0  # pragma: no cover
"""
    exit_code = _run_checker(tmp_path, content)
    assert exit_code == 1


def test_multi_line_justification_with_long_second_line_is_rejected(tmp_path: Path) -> None:
    second_line = (
        "# second justification line is intentionally made longer than the configured maximum "
        "width to trigger IGN030 and should be wrapped"
    )
    content = f"""from __future__ import annotations


def bad() -> None:
    # ignore JUSTIFIED: header line is within the configured width limit
    {second_line}
    value = 1 / 0  # pragma: no cover
"""
    exit_code = _run_checker(tmp_path, content)
    assert exit_code == 1


def test_justification_too_long_reports_column_at_first_excess_char(
    tmp_path: Path, capsys: CaptureFixture[str]
) -> None:
    prefix = "# ignore JUSTIFIED: "
    padding = "x" * (MAX_JUSTIFICATION_LINE_LENGTH + 1 - len(prefix))
    content = f"""from __future__ import annotations


def bad() -> None:
    {prefix}{padding}
    value = 1 / 0  # pragma: no cover
"""
    target = tmp_path / "sample.py"
    target.write_text(content, encoding="utf-8")
    exit_code = check_main(["--json", str(tmp_path)])
    captured = capsys.readouterr()
    assert exit_code == 1
    payload = json.loads(captured.out)
    violation = next(item for item in payload if item["code"] == "IGN030")
    # Four spaces of indentation plus the first MAX_JUSTIFICATION_LINE_LENGTH characters.
    assert violation["line"] == 5
    assert violation["column"] == 4 + MAX_JUSTIFICATION_LINE_LENGTH + 1


def test_checker_accepts_all_ignore_kinds(tmp_path: Path) -> None:
    content = """# ignore JUSTIFIED: per-file ruff ignore demo
# ruff: noqa

# ignore JUSTIFIED: per-file pylint skip demo
# pylint: skip-file

from __future__ import annotations


def ruff_line() -> None:
    # ignore JUSTIFIED: ruff per-line noqa
    value = 1 / 0  # noqa: F401


def pylint_line() -> None:
    # ignore JUSTIFIED: pylint per-line disable
    value = 1  # pylint: disable=unused-variable


def type_ignore_line(raw: object) -> None:
    # ignore JUSTIFIED: mypy type ignore example
    value = raw  # type: ignore[assignment]
    _ = value


def pyright_ignore_line(config: dict) -> None:
    # ignore JUSTIFIED: pyright ignore example
    value = config.get("key")  # pyright: ignore[reportUnknownArgumentType]
    _ = value


def combined_ignores() -> None:
    # ignore JUSTIFIED: combined ignore markers
    value = 1 / 0  # pragma: no cover  # type: ignore[assignment]  # noqa: F401
    _ = value


def bandit_nosec_ignore() -> None:
    # ignore JUSTIFIED: bandit nosec marker requires justification
    secret = "auto"  # nosec B105
    _ = secret
"""
    exit_code = _run_checker(tmp_path, content)
    assert exit_code == 0


def test_checker_flags_top_of_file_ignore_without_justification(tmp_path: Path) -> None:
    content = """# pragma: no cover


def foo() -> None:
    pass
"""
    exit_code = _run_checker(tmp_path, content)
    assert exit_code == 1


def test_checker_flags_duplicate_justification_prefix_in_block(tmp_path: Path) -> None:
    content = """from __future__ import annotations


def bad() -> None:
    # ignore JUSTIFIED: first line
    # ignore JUSTIFIED: should not repeat
    value = 1  # noqa: ANN001
"""
    exit_code = _run_checker(tmp_path, content)
    assert exit_code == 1


def test_checker_flags_pragmas_not_at_comment_start(tmp_path: Path) -> None:
    content = """from __future__ import annotations


def bad() -> None:
    # ignore JUSTIFIED: pragma should not be hidden behind other text
    value = 1  # explanation before pragma # noqa: ANN001
"""
    exit_code = _run_checker(tmp_path, content)
    assert exit_code == 1


def test_checker_requires_justification_for_nosec(tmp_path: Path) -> None:
    content = """from __future__ import annotations


def bad() -> None:
    password = "auto"  # nosec B105
    _ = password
"""
    exit_code = _run_checker(tmp_path, content)
    assert exit_code == 1


def test_checker_allows_pragmas_at_comment_start_or_after_pragmas(tmp_path: Path) -> None:
    content = """from __future__ import annotations


def good() -> None:
    # ignore JUSTIFIED: pragma starts the comment body
    value = 1  # noqa: ANN001  # pylint: disable=unused-variable
"""
    exit_code = _run_checker(tmp_path, content)
    assert exit_code == 0


def test_file_level_ignore_block_placed_below_license(tmp_path: Path) -> None:
    content = (
        HEADER_BLOCK
        + """# ignore JUSTIFIED: per-file ignore block below license
# ruff: noqa


def foo() -> None:
    pass
"""
    )
    exit_code = _run_checker(tmp_path, content)
    assert exit_code == 0


def test_file_level_ignore_block_wrong_position(tmp_path: Path) -> None:
    content = (
        HEADER_BLOCK
        + """


def foo() -> None:
    pass


# ignore JUSTIFIED: late file-level ignore
# ruff: noqa
"""
    )
    exit_code = _run_checker(tmp_path, content)
    assert exit_code == 1


def test_file_level_ignore_block_missing_trailing_blank_line(tmp_path: Path) -> None:
    content = (
        HEADER_BLOCK
        + """# ignore JUSTIFIED: per-file ignore block lacks trailing blank line
# ruff: noqa
def foo() -> None:
    pass
"""
    )
    exit_code = _run_checker(tmp_path, content)
    assert exit_code == 1


def test_file_level_mypy_ignore_errors_block(tmp_path: Path) -> None:
    content = (
        HEADER_BLOCK
        + """# ignore JUSTIFIED: mypy file-level ignore
# type: ignore[attr-defined]


def foo() -> None:
    pass
"""
    )
    exit_code = _run_checker(tmp_path, content)
    assert exit_code == 0


def test_file_level_mypy_ignore_errors_wrong_position(tmp_path: Path) -> None:
    content = (
        HEADER_BLOCK
        + """


def foo() -> None:
    pass


# ignore JUSTIFIED: late mypy file-level ignore
# type: ignore[attr-defined]
"""
    )
    exit_code = _run_checker(tmp_path, content)
    assert exit_code == 1


def test_file_level_nosec_block_wrong_position(tmp_path: Path) -> None:
    content = (
        HEADER_BLOCK
        + """


def foo() -> None:
    secret = "x"


# ignore JUSTIFIED: late safety file-level ignore
# nosec B105
"""
    )
    exit_code = _run_checker(tmp_path, content)
    assert exit_code == 1


def test_file_level_block_with_multiple_pragmas_is_rejected(tmp_path: Path) -> None:
    content = (
        HEADER_BLOCK
        + """# ignore JUSTIFIED: file-level ignore with duplicate pragma lines
# ruff: noqa
# pylint: skip-file


def foo() -> None:
    pass
"""
    )
    exit_code = _run_checker(tmp_path, content)
    assert exit_code == 1


def test_file_level_block_with_combined_pragmas_is_accepted(tmp_path: Path) -> None:
    content = (
        HEADER_BLOCK
        + """# ignore JUSTIFIED: file-level ignore combining ruff and pylint directives
# ruff: noqa  # pylint: disable=too-many-lines


def foo() -> None:
    pass
"""
    )
    exit_code = _run_checker(tmp_path, content)
    assert exit_code == 0


def test_file_level_pyright_strict_block(tmp_path: Path) -> None:
    content = (
        HEADER_BLOCK
        + """# ignore JUSTIFIED: pyright file-level directive
# pyright: strict


def foo() -> None:
    pass
"""
    )
    exit_code = _run_checker(tmp_path, content)
    assert exit_code == 0


def test_file_level_pyright_strict_wrong_position(tmp_path: Path) -> None:
    content = (
        HEADER_BLOCK
        + """


def foo() -> None:
    pass


# ignore JUSTIFIED: late pyright file-level directive
# pyright: strict
"""
    )
    exit_code = _run_checker(tmp_path, content)
    assert exit_code == 1


def test_uppercase_noqa_and_pragma_are_detected(tmp_path: Path) -> None:
    content = """from __future__ import annotations


def upper_noqa() -> None:
    # ignore JUSTIFIED: uppercase NOQA is treated as ignore
    value = 1  # NOQA
    _ = value


def coverage_ignore() -> None:
    # ignore JUSTIFIED: coverage pragma is treated as ignore even with varied spacing/casing
    value = 2  # pragma: no cover
    _ = value
"""
    exit_code = _run_checker(tmp_path, content)
    assert exit_code == 0


def test_explanatory_comment_mentioning_noqa_is_not_treated_as_ignore(tmp_path: Path) -> None:
    content = """from __future__ import annotations


def explain_noqa() -> None:
    # This comment mentions noqa but is not a pragma; noqa keeps Ruff from blocking the demo
    value = 1
    _ = value
"""
    exit_code = _run_checker(tmp_path, content)
    assert exit_code == 0


def test_pyright_example_requires_trailing_blank_after_file_level_block(tmp_path: Path) -> None:
    content = """# Copyright 2025 CrownOps Engineering
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# ignore JUSTIFIED: File contains purposely bad code for demonstation purposes
# pragma: no cover  # type: ignore  # ruff: noqa: PGH003  # pylint: skip-file
\"\"\"Demonstration of typing issues that pyright can detect.\"\"\"
"""
    exit_code = _run_checker(tmp_path, content)
    assert exit_code == 1


def test_file_level_pyright_without_license_does_not_enforce_placement(tmp_path: Path) -> None:
    content = """# ignore JUSTIFIED: pyright file-level directive without license header
# pyright: strict

from __future__ import annotations


def foo() -> None:
    pass
    """
    exit_code = _run_checker(tmp_path, content)
    assert exit_code == 0


def test_inline_ignore_requires_two_spaces_before_hash(tmp_path: Path) -> None:
    content = """from __future__ import annotations


def bad_spacing() -> None:
    # ignore JUSTIFIED: inline ignore should have two spaces before '#'
    value = 1 # noqa: F401
"""
    exit_code = _run_checker(tmp_path, content)
    assert exit_code == 1


def test_inline_ignore_with_two_spaces_is_accepted(tmp_path: Path) -> None:
    content = """from __future__ import annotations


def good_spacing() -> None:
    # ignore JUSTIFIED: inline ignore uses two spaces before '#'
    value = 1  # noqa: F401
"""
    exit_code = _run_checker(tmp_path, content)
    assert exit_code == 0


def test_comment_only_ignore_requires_space_after_hash(tmp_path: Path) -> None:
    content = """from __future__ import annotations


def bad_comment_prefix() -> None:
    # ignore JUSTIFIED: comment-only ignore must start with '# '
    #noqa: F401
    value = 1
"""
    exit_code = _run_checker(tmp_path, content)
    assert exit_code == 1


def test_additional_pragmas_require_double_space_before_hash(tmp_path: Path) -> None:
    content = """from __future__ import annotations


def bad_multi_pragma_spacing() -> None:
    # ignore JUSTIFIED: additional pragmas must use '  #'
    value = 1  # noqa: F401 # noqa: E501
"""
    exit_code = _run_checker(tmp_path, content)
    assert exit_code == 1


def test_duplicate_pragmas_for_same_source_are_rejected(tmp_path: Path) -> None:
    content = """from __future__ import annotations


def duplicate_source() -> None:
    # ignore JUSTIFIED: multiple pragmas for the same source are not allowed
    value = 1  # noqa: F401  # noqa: E501
"""
    exit_code = _run_checker(tmp_path, content)
    assert exit_code == 1
