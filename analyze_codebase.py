"""Analyze codebase for dead code, unused imports, and refactoring opportunities."""

import ast
import os
from pathlib import Path
from collections import defaultdict
import re

class CodeAnalyzer(ast.NodeVisitor):
    """Analyze Python AST for unused imports and dead code."""

    def __init__(self, filepath):
        self.filepath = filepath
        self.imports = {}  # {name: line_number}
        self.from_imports = {}  # {name: (module, line_number)}
        self.names_used = set()
        self.function_defs = {}  # {name: line_number}
        self.class_defs = {}  # {name: line_number}
        self.issues = []

    def visit_Import(self, node):
        """Track import statements."""
        for alias in node.names:
            name = alias.asname if alias.asname else alias.name
            self.imports[name] = node.lineno
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        """Track from...import statements."""
        for alias in node.names:
            name = alias.asname if alias.asname else alias.name
            self.from_imports[name] = (node.module, node.lineno)
        self.generic_visit(node)

    def visit_Name(self, node):
        """Track name usage."""
        if isinstance(node.ctx, ast.Load):
            self.names_used.add(node.id)
        self.generic_visit(node)

    def visit_FunctionDef(self, node):
        """Track function definitions."""
        self.function_defs[node.name] = node.lineno
        self.generic_visit(node)

    def visit_ClassDef(self, node):
        """Track class definitions."""
        self.class_defs[node.name] = node.lineno
        self.generic_visit(node)

    def analyze(self, tree):
        """Analyze the AST."""
        self.visit(tree)

        # Find unused imports
        unused_imports = []
        for name, line in self.imports.items():
            if name not in self.names_used:
                unused_imports.append((name, line, "import"))

        for name, (module, line) in self.from_imports.items():
            if name not in self.names_used:
                unused_imports.append((name, line, f"from {module}"))

        return unused_imports

def analyze_file(filepath):
    """Analyze a single Python file."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        tree = ast.parse(content)
        analyzer = CodeAnalyzer(filepath)
        unused = analyzer.analyze(tree)

        return {
            'filepath': filepath,
            'unused_imports': unused,
            'function_count': len(analyzer.function_defs),
            'class_count': len(analyzer.class_defs),
            'lines': len(content.split('\n'))
        }
    except Exception as e:
        return {'filepath': filepath, 'error': str(e)}

def find_dead_modules():
    """Find modules that are never imported."""
    src_files = list(Path('src').rglob('*.py'))

    # Get all module paths
    modules = {}
    for f in src_files:
        if f.name != '__init__.py':
            # Convert path to import path
            import_path = str(f).replace('\\', '.').replace('/', '.').replace('.py', '')
            modules[import_path] = {'file': str(f), 'imported': False}

    # Check which modules are imported
    for f in src_files:
        try:
            with open(f, 'r', encoding='utf-8') as file:
                content = file.read()
                for module_path in modules.keys():
                    if module_path in content:
                        modules[module_path]['imported'] = True
        except:
            pass

    # Find never-imported modules
    dead_modules = {k: v for k, v in modules.items() if not v['imported']}
    return dead_modules

def main():
    """Run comprehensive code analysis."""
    print("=" * 80)
    print("CODEBASE ANALYSIS - DEAD CODE & REFACTORING OPPORTUNITIES")
    print("=" * 80)
    print()

    # 1. Find potentially dead modules
    print("1. CHECKING FOR DEAD MODULES (never imported)")
    print("-" * 80)
    dead_modules = find_dead_modules()
    if dead_modules:
        for module, info in dead_modules.items():
            print(f"   [WARNING] {info['file']}")
            print(f"      Import path: {module}")
    else:
        print("   [OK] No dead modules found")
    print()

    # 2. Analyze all files for unused imports
    print("2. CHECKING FOR UNUSED IMPORTS")
    print("-" * 80)

    src_files = list(Path('src').rglob('*.py'))
    total_unused = 0
    files_with_issues = []

    for filepath in src_files:
        result = analyze_file(filepath)
        if 'unused_imports' in result and result['unused_imports']:
            files_with_issues.append(result)
            total_unused += len(result['unused_imports'])

    if files_with_issues:
        print(f"   Found {total_unused} unused imports in {len(files_with_issues)} files:")
        print()
        for result in files_with_issues[:10]:  # Show first 10
            print(f"   FILE: {result['filepath']}")
            for name, line, import_type in result['unused_imports'][:5]:  # Show first 5 per file
                print(f"      Line {line}: {import_type} {name}")
            if len(result['unused_imports']) > 5:
                print(f"      ... and {len(result['unused_imports']) - 5} more")
            print()
    else:
        print("   [OK] No unused imports found")

    print()
    print("3. FILE SIZE ANALYSIS (potential refactoring candidates)")
    print("-" * 80)

    # Analyze file sizes
    large_files = []
    for filepath in src_files:
        result = analyze_file(filepath)
        if 'lines' in result and result['lines'] > 500:
            large_files.append(result)

    large_files.sort(key=lambda x: x['lines'], reverse=True)

    if large_files:
        print(f"   Found {len(large_files)} files > 500 lines:")
        print()
        for result in large_files[:10]:
            print(f"   FILE: {result['filepath']}")
            print(f"      {result['lines']} lines, {result['function_count']} functions, {result['class_count']} classes")
        print()

    # Summary
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"   Dead modules: {len(dead_modules)}")
    print(f"   Files with unused imports: {len(files_with_issues)}")
    print(f"   Total unused imports: {total_unused}")
    print(f"   Large files (>500 lines): {len(large_files)}")
    print()

if __name__ == "__main__":
    main()
