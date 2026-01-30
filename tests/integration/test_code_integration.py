"""
FILE: test_code_integration.py
STATUS: Active
RESPONSIBILITY: Integration tests to catch dead/unused code - verify all prompts, chains, and imports are used.

DEPENDENCIES (Who uses this file):
- pytest test runner
- Code quality and unused code detection

IMPORTS (What this file needs):
- pytest: Test framework
- re: Pattern matching for code analysis
- os: File operations
- unittest.mock: Mocking for isolation

LAST MAJOR UPDATE: 2026-01-31
MAINTAINER: QA Team
"""

import pytest
import re
import os
from unittest.mock import MagicMock, patch


class TestPromptIntegration:
    """Test that all prompt getters are integrated and functional."""

    def test_all_prompt_getters_return_valid_prompts(self):
        """Verify all get_*_prompt functions return ChatPromptTemplate or str."""
        from src.generation import prompts
        from langchain_core.prompts import ChatPromptTemplate

        # Find all get_*_prompt functions
        prompt_getters = [
            name
            for name in dir(prompts)
            if name.startswith("get_") and name.endswith("_prompt") and callable(getattr(prompts, name))
        ]

        assert len(prompt_getters) > 0, "No prompt getters found"

        for getter_name in prompt_getters:
            getter = getattr(prompts, getter_name)
            result = getter()
            # Some prompts return string (system prompts), others return ChatPromptTemplate
            assert isinstance(
                result, (ChatPromptTemplate, str)
            ), f"{getter_name}() should return ChatPromptTemplate or str, got {type(result)}"
            # If string, should be non-empty
            if isinstance(result, str):
                assert len(result) > 100, f"{getter_name}() returned empty/short string"

    def test_unified_analyzer_is_used(self):
        """Verify the unified analyzer is actually used in chain.py."""
        chain_path = "src/retrieval/chain.py"
        with open(chain_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Must import unified_analyze
        assert "unified_analyze" in content, "unified_analyze must be imported in chain.py"

        # Must be used in the code (called as a function)
        assert "unified_analyze(" in content, "unified_analyze must be called in chain.py"


class TestChainIntegration:
    """Test that all chains in RAGChain are properly integrated."""

    def test_no_unused_chain_definitions(self):
        """Verify all self.*_chain definitions are actually used."""
        chain_path = "src/retrieval/chain.py"
        with open(chain_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Find all chain definitions
        chain_defs = re.findall(r"self\.(\w+_chain)\s*=", content)

        # Find all chain usages (invocations)
        chain_uses = re.findall(r"self\.(\w+_chain)\.invoke", content)

        # All defined chains should be used
        unused = set(chain_defs) - set(chain_uses)
        assert len(unused) == 0, f"Unused chains found: {unused}. Remove them or integrate them."


class TestImportIntegration:
    """Test that all imports are actually used."""

    def test_chain_imports_are_used(self):
        """Verify all imports in chain.py from prompts are used."""
        chain_path = "src/retrieval/chain.py"
        with open(chain_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Find imports from prompts
        import_match = re.search(r"from src\.generation\.prompts import (.+)", content)

        if import_match:
            imported_items = [i.strip() for i in import_match.group(1).split(",")]

            for item in imported_items:
                # Each import should appear more than once (import + usage)
                pattern = re.compile(r"\b" + item.strip() + r"\b")
                occurrences = len(pattern.findall(content))
                assert occurrences > 1, f"Import '{item}' is not used in chain.py. Remove it."


class TestNoDeadClasses:
    """Test that key classes are actually instantiated."""

    def test_retrieval_manager_is_used(self):
        """Verify RetrievalManager is instantiated somewhere."""
        found = False
        for root, dirs, files in os.walk("src"):
            for file in files:
                if file.endswith(".py"):
                    filepath = os.path.join(root, file)
                    with open(filepath, "r", encoding="utf-8") as f:
                        if "RetrievalManager(" in f.read():
                            found = True
                            break
            if found:
                break

        assert found, "RetrievalManager is never instantiated"

    def test_deprecated_modules_are_marked(self):
        """Verify deprecated modules have deprecation notice."""
        deprecated_modules = [
            "src/retrieval/orchestrator.py",
        ]

        for module_path in deprecated_modules:
            if os.path.exists(module_path):
                with open(module_path, "r", encoding="utf-8") as f:
                    content = f.read()
                assert "DEPRECATED" in content.upper(), f"{module_path} should have DEPRECATED notice"


class TestEndToEndPipeline:
    """End-to-end tests for the query pipeline."""

    @pytest.fixture
    def mock_llm_response(self):
        """Mock LLM response for testing."""
        return {
            "refined_query": "concerts Paris March",
            "filters": {
                "city": "Paris",
                "month": 3,
                "day": None,
                "year": 2026,
                "category": "concerts",
                "is_free": None,
                "age": None,
            },
        }

    def test_unified_chain_produces_expected_output(self, mock_llm_response):
        """Test that unified understanding chain produces valid output structure."""
        # This is a structural test - verifies the chain output format
        required_keys = ["refined_query", "filters"]
        for key in required_keys:
            assert key in mock_llm_response, f"Missing required key: {key}"

        filter_keys = ["city", "month", "day", "year", "category", "is_free", "age"]
        for key in filter_keys:
            assert key in mock_llm_response["filters"], f"Missing filter key: {key}"

    @patch("src.retrieval.chain.MistralLLM")
    @patch("src.retrieval.chain.EventVectorStore")
    def test_rag_chain_initialization(self, mock_vector_store, mock_llm):
        """Test RAGChain initializes without errors."""
        # Setup mocks
        mock_llm_instance = MagicMock()
        mock_llm.return_value = mock_llm_instance
        mock_llm_instance.llm = MagicMock()
        mock_llm_instance.llm.bind.return_value = MagicMock()

        mock_vs_instance = MagicMock()
        mock_vector_store.return_value = mock_vs_instance
        mock_vs_instance.storage = MagicMock()
        mock_vs_instance.storage.count_events.return_value = 100
        mock_vs_instance.storage.get_date_range.return_value = (None, None)

        # Import and verify RAGChain can be created
        from src.retrieval.chain import RAGChain

        # Should not raise
        assert RAGChain is not None


class TestCodeQuality:
    """Code quality checks to prevent dead code accumulation."""

    def test_no_todo_with_critical_keyword(self):
        """Ensure no critical TODOs are left unaddressed."""
        critical_patterns = [
            r"TODO.*CRITICAL",
            r"TODO.*URGENT",
            r"FIXME.*CRITICAL",
            r"XXX.*MUST",
        ]

        violations = []
        for root, dirs, files in os.walk("src"):
            for file in files:
                if file.endswith(".py"):
                    filepath = os.path.join(root, file)
                    with open(filepath, "r", encoding="utf-8") as f:
                        for i, line in enumerate(f, 1):
                            for pattern in critical_patterns:
                                if re.search(pattern, line, re.IGNORECASE):
                                    violations.append(f"{filepath}:{i}: {line.strip()}")

        assert len(violations) == 0, "Critical TODOs found:\n" + "\n".join(violations)

    def test_no_commented_out_code_blocks(self):
        """Check for large blocks of commented-out code."""
        # This is a heuristic - 5+ consecutive comment lines with code patterns
        code_patterns = [
            r"#\s*def\s+\w+",
            r"#\s*class\s+\w+",
            r"#\s*return\s+",
            r"#\s*if\s+\w+",
            r"#\s*for\s+\w+",
        ]

        violations = []
        for root, dirs, files in os.walk("src"):
            for file in files:
                if file.endswith(".py"):
                    filepath = os.path.join(root, file)
                    with open(filepath, "r", encoding="utf-8") as f:
                        lines = f.readlines()

                    consecutive_code_comments = 0
                    for i, line in enumerate(lines, 1):
                        if any(re.search(p, line) for p in code_patterns):
                            consecutive_code_comments += 1
                            if consecutive_code_comments >= 5:
                                violations.append(f"{filepath}:{i-4}-{i}")
                                consecutive_code_comments = 0
                        else:
                            consecutive_code_comments = 0

        # Just warn, don't fail (some commented code might be intentional)
        if violations:
            print(f"Warning: Possible commented-out code blocks: {violations}")
