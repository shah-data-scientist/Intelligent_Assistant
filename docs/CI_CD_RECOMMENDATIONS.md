# CI/CD Recommendations for Test Organization

**Last Updated:** 2026-01-30
**Purpose:** Optimize CI/CD pipeline using organized test structure

---

## Pipeline Strategy

### Current Structure Benefits

With tests organized into `unit/`, `integration/`, `e2e/`, `security/`, and `evaluation/` folders, you can now:

1. **Run tests in parallel** (different stages)
2. **Fail fast** (stop at first failure)
3. **Provide faster feedback** (unit tests run first)
4. **Optimize resource usage** (skip expensive tests early)

---

## GitHub Actions Example

### `.github/workflows/test.yml`

```yaml
name: Test Suite

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  # Stage 1: Fast feedback (< 10s)
  unit-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          pip install poetry
          poetry install
      - name: Run unit tests
        run: poetry run pytest tests/unit/ -v --cov=src
      - name: Upload coverage
        uses: codecov/codecov-action@v3

  # Stage 2: Integration tests (< 30s)
  integration-tests:
    runs-on: ubuntu-latest
    needs: unit-tests  # Only run if unit tests pass
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          pip install poetry
          poetry install
      - name: Run integration tests
        run: poetry run pytest tests/integration/ -v

  # Stage 3: E2E + Security tests (< 1min)
  e2e-and-security:
    runs-on: ubuntu-latest
    needs: integration-tests  # Only run if integration tests pass
    strategy:
      matrix:
        test-group: [e2e, security]
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          pip install poetry
          poetry install
      - name: Run ${{ matrix.test-group }} tests
        run: poetry run pytest tests/${{ matrix.test-group }}/ -v

  # Stage 4: Evaluation tests (optional, can be nightly)
  evaluation-tests:
    runs-on: ubuntu-latest
    needs: e2e-and-security
    if: github.event_name == 'push' && github.ref == 'refs/heads/main'
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          pip install poetry
          poetry install
      - name: Run evaluation tests
        run: poetry run pytest tests/evaluation/ -v
      - name: Run full evaluation
        run: poetry run python scripts/run_evaluation.py
```

---

## GitLab CI Example

### `.gitlab-ci.yml`

```yaml
stages:
  - unit
  - integration
  - e2e
  - security
  - evaluation

# Cache dependencies
cache:
  paths:
    - .venv/

before_script:
  - pip install poetry
  - poetry install

# Stage 1: Unit tests (fast feedback)
unit-tests:
  stage: unit
  script:
    - poetry run pytest tests/unit/ -v --cov=src --cov-report=xml
  coverage: '/TOTAL.*\s+(\d+%)$/'
  artifacts:
    reports:
      coverage_report:
        coverage_format: cobertura
        path: coverage.xml

# Stage 2: Integration tests
integration-tests:
  stage: integration
  script:
    - poetry run pytest tests/integration/ -v
  needs: ["unit-tests"]

# Stage 3: E2E tests
e2e-tests:
  stage: e2e
  script:
    - poetry run pytest tests/e2e/ -v
  needs: ["integration-tests"]

# Stage 3: Security tests (parallel with e2e)
security-tests:
  stage: security
  script:
    - poetry run pytest tests/security/ -v
  needs: ["integration-tests"]

# Stage 4: Evaluation tests (optional)
evaluation-tests:
  stage: evaluation
  script:
    - poetry run pytest tests/evaluation/ -v
    - poetry run python scripts/run_evaluation.py
  needs: ["e2e-tests", "security-tests"]
  only:
    - main
    - develop
```

---

## Jenkins Pipeline Example

### `Jenkinsfile`

```groovy
pipeline {
    agent any

    stages {
        stage('Setup') {
            steps {
                sh 'pip install poetry'
                sh 'poetry install'
            }
        }

        stage('Unit Tests') {
            steps {
                sh 'poetry run pytest tests/unit/ -v --cov=src --cov-report=xml'
            }
            post {
                always {
                    junit 'test-results.xml'
                    cobertura coberturaReportFile: 'coverage.xml'
                }
            }
        }

        stage('Integration Tests') {
            when {
                expression { currentBuild.result != 'FAILURE' }
            }
            steps {
                sh 'poetry run pytest tests/integration/ -v'
            }
        }

        stage('E2E & Security') {
            when {
                expression { currentBuild.result != 'FAILURE' }
            }
            parallel {
                stage('E2E Tests') {
                    steps {
                        sh 'poetry run pytest tests/e2e/ -v'
                    }
                }
                stage('Security Tests') {
                    steps {
                        sh 'poetry run pytest tests/security/ -v'
                    }
                }
            }
        }

        stage('Evaluation') {
            when {
                branch 'main'
                expression { currentBuild.result != 'FAILURE' }
            }
            steps {
                sh 'poetry run pytest tests/evaluation/ -v'
                sh 'poetry run python scripts/run_evaluation.py'
            }
        }
    }
}
```

---

## Local Development Workflow

### Fast Iteration Cycle

```bash
# During development - Run only unit tests (< 5s)
pytest tests/unit/ -v

# Before committing - Run unit + integration (< 30s)
pytest tests/unit/ tests/integration/ -v

# Before pushing - Run all tests (< 2min)
pytest tests/ -v

# Weekly - Run with coverage
pytest tests/ --cov=src --cov-report=html
```

### Pre-commit Hook (Already in Global Policy)

Create `.git/hooks/pre-commit`:
```bash
#!/bin/bash
# Run fast tests before committing
pytest tests/unit/ tests/integration/ -v || exit 1
```

Make executable:
```bash
chmod +x .git/hooks/pre-commit
```

---

## Performance Optimization Tips

### 1. Parallel Execution

```bash
# Install pytest-xdist
poetry add --group dev pytest-xdist

# Run tests in parallel (4 workers)
pytest tests/ -n 4
```

### 2. Run Only Changed Tests

```bash
# Install pytest-testmon
poetry add --group dev pytest-testmon

# Run only tests affected by code changes
pytest --testmon
```

### 3. Skip Slow Tests in CI

```bash
# Skip evaluation tests in PR builds
pytest tests/ -m "not slow" -v
```

### 4. Fail Fast

```bash
# Stop on first failure
pytest tests/ -x -v
```

---

## Coverage Requirements by Stage

### Minimum Coverage Thresholds

```ini
# pytest.ini or pyproject.toml
[coverage:report]
fail_under = 80

# Different thresholds per module
[coverage:paths]
src/api/ = 95
src/security/ = 92
src/retrieval/ = 82
src/utils/ = 75
```

### CI Coverage Enforcement

```yaml
# GitHub Actions
- name: Check coverage
  run: |
    pytest tests/ --cov=src --cov-fail-under=80
```

---

## Monitoring & Reporting

### Test Metrics to Track

1. **Test Execution Time**
   - Unit tests: < 10s
   - Integration tests: < 30s
   - E2E tests: < 1min
   - Full suite: < 2min

2. **Test Coverage**
   - Overall: ≥80%
   - Critical modules (API, security): ≥90%

3. **Test Stability**
   - Flaky test rate: <5%
   - Pass rate: >95%

### Dashboard Example

```markdown
## Test Suite Metrics

| Metric | Target | Current | Status |
|--------|--------|---------|--------|
| Unit Test Time | <10s | 5s | ✅ |
| Integration Time | <30s | 28s | ✅ |
| E2E Time | <1min | 58s | ✅ |
| Coverage | ≥80% | 85% | ✅ |
| Pass Rate | >95% | 98% | ✅ |
```

---

## Troubleshooting

### Common Issues

**1. Tests slow in CI but fast locally**
- Check if CI is running tests sequentially
- Enable parallel execution: `pytest -n auto`

**2. Flaky tests failing randomly**
- Move to `tests/integration/` or `tests/e2e/`
- Add proper test isolation
- Use fixtures for setup/teardown

**3. Coverage drops unexpectedly**
- Check if new code added without tests
- Run: `pytest --cov=src --cov-report=html`
- Open `htmlcov/index.html` to see uncovered lines

---

## Summary

✅ **Organized tests** enable better CI/CD
✅ **Parallel execution** reduces build time
✅ **Fail fast** provides quick feedback
✅ **Clear stages** make debugging easier
✅ **Coverage tracking** ensures quality

**Next Steps:**
1. Implement GitHub Actions workflow
2. Set up coverage reporting (Codecov/Coveralls)
3. Configure pre-commit hooks
4. Monitor test execution times
