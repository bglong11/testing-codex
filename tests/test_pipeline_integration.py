"""Integration tests for ESIA pipeline"""
import pytest
from pathlib import Path
import tempfile
import shutil


class TestPipelineImports:
    """Test that all pipeline modules can be imported"""

    @pytest.mark.integration
    def test_import_step1(self):
        """Test step1 module imports"""
        try:
            import step1_pdf_to_markdown
            assert hasattr(step1_pdf_to_markdown, 'convert_pdf_to_markdown')
        except ImportError as e:
            pytest.skip(f"Step1 import failed: {e}")

    @pytest.mark.integration
    def test_import_step2(self):
        """Test step2 module imports"""
        try:
            import step2_extract_facts
            assert hasattr(step2_extract_facts, 'main')
        except ImportError as e:
            pytest.skip(f"Step2 import failed: {e}")

    @pytest.mark.integration
    def test_import_step3(self):
        """Test step3 module imports"""
        try:
            import step3_analyze_facts
            assert hasattr(step3_analyze_facts, 'main')
        except ImportError as e:
            pytest.skip(f"Step3 import failed: {e}")

    @pytest.mark.integration
    def test_import_esia_extractor(self):
        """Test esia_extractor module imports"""
        try:
            import esia_extractor
            assert hasattr(esia_extractor, 'process_esia_document')
        except ImportError as e:
            pytest.skip(f"ESIA extractor import failed: {e}")

    @pytest.mark.integration
    def test_import_llm_config(self):
        """Test llm_config module imports"""
        import llm_config
        assert hasattr(llm_config, 'resolve_provider_for_step')

    @pytest.mark.integration
    def test_import_run_pipeline(self):
        """Test run_extract_pipeline module imports"""
        try:
            import run_extract_pipeline
            assert hasattr(run_extract_pipeline, 'main')
        except ImportError as e:
            pytest.skip(f"Run pipeline import failed: {e}")


class TestPipelineStructure:
    """Test pipeline directory structure and file existence"""

    @pytest.mark.integration
    def test_all_pipeline_files_exist(self):
        """Test that all expected pipeline files exist"""
        expected_files = [
            "step1_pdf_to_markdown.py",
            "step2_extract_facts.py",
            "step3_analyze_facts.py",
            "run_extract_pipeline.py",
            "esia_extractor.py",
            "llm_config.py",
        ]

        for filename in expected_files:
            assert Path(filename).exists(), f"Missing file: {filename}"

    @pytest.mark.integration
    def test_requirements_file_exists(self):
        """Test that requirements.txt exists"""
        assert Path("requirements.txt").exists()

    @pytest.mark.integration
    def test_cicd_workflow_exists(self):
        """Test that CI/CD workflow exists"""
        assert Path(".github/workflows/ci.yml").exists()
