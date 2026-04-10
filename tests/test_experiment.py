from __future__ import annotations

import shutil
import tempfile
import unittest
from pathlib import Path

from narrio.experiment import ExperimentRequest, compare_combo, execute_experiment, inspect_run
from narrio.paths import prompt_file, sources_dir, styles_root


class ExperimentTest(unittest.TestCase):
    def test_dry_run_creates_manifest_and_is_inspectable(self) -> None:
        request = ExperimentRequest(
            content_type="article",
            markdown="请停下「计数器」思维.md",
            dry_run=True,
        )
        result = execute_experiment(request)
        self.assertEqual(result["status"], "dry_run")
        manifest = inspect_run(result["run_dir"])
        self.assertEqual(manifest["status"], "dry_run")
        self.assertEqual(manifest["selection"]["markdown"], "请停下「计数器」思维.md")
        shutil.rmtree(Path(result["run_dir"]).parents[1], ignore_errors=True)

    def test_compare_combo_reads_run_summaries(self) -> None:
        request = ExperimentRequest(
            content_type="article",
            markdown="AI写作指南1.0：智力的容器大于智力本身.md",
            dry_run=True,
        )
        result = execute_experiment(request)
        comparison = compare_combo("article", result["combo_id"])
        self.assertTrue(any(item["run_id"] == result["run_id"] for item in comparison))
        shutil.rmtree(Path(result["run_dir"]).parents[1], ignore_errors=True)

    def test_prompt_file_prefers_canonical(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="narrio-test-")).resolve()
        try:
            (root / "assets" / "prompts").mkdir(parents=True, exist_ok=True)
            (root / "assets" / "prompts" / "X.md").write_text("canonical", encoding="utf-8")
            self.assertEqual(prompt_file("X.md", root), root / "assets" / "prompts" / "X.md")
        finally:
            shutil.rmtree(root, ignore_errors=True)

    def test_styles_root_only_uses_canonical(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="narrio-test-")).resolve()
        try:
            (root / "assets" / "styles" / "OpenAI").mkdir(parents=True, exist_ok=True)
            self.assertEqual(styles_root(root), root / "assets" / "styles")
        finally:
            shutil.rmtree(root, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
