"""
Master Test Execution Suite for SupportRAG
Runs all unit, integration, build, and live production tests across Frontend, Backend, and Cloud.
"""

import os
import sys
import time
import subprocess
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

REPO_ROOT = Path(__file__).resolve().parent.parent
is_windows = sys.platform.startswith("win")

def resolve_python():
    candidates = [
        REPO_ROOT / "backend" / ".venv" / ("Scripts" if is_windows else "bin") / ("python.exe" if is_windows else "python"),
        REPO_ROOT / "backend" / "venv" / ("Scripts" if is_windows else "bin") / ("python.exe" if is_windows else "python"),
    ]
    for c in candidates:
        if c.exists():
            return c
    return Path(sys.executable)

def resolve_pytest():
    candidates = [
        REPO_ROOT / "backend" / ".venv" / ("Scripts" if is_windows else "bin") / ("pytest.exe" if is_windows else "pytest"),
        REPO_ROOT / "backend" / "venv" / ("Scripts" if is_windows else "bin") / ("pytest.exe" if is_windows else "pytest"),
    ]
    for c in candidates:
        if c.exists():
            return str(c)
    return "pytest"

PYTHON_EXE = resolve_python()
PYTEST_EXE = resolve_pytest()
BUILD_CMD = "cmd /c npm run build" if is_windows else "npm run build"

def log_header(title):
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)

def run_step(step_name, cmd, cwd):
    print(f"\n[*] Executing: {step_name}")
    print(f"    Command: {' '.join(cmd) if isinstance(cmd, list) else cmd}")
    print(f"    Working Dir: {cwd}")
    start = time.perf_counter()
    res = subprocess.run(cmd, cwd=cwd, shell=isinstance(cmd, str), capture_output=True, text=True, encoding="utf-8", errors="replace")
    elapsed = time.perf_counter() - start
    
    if res.returncode == 0:
        print(f"  [SUCCESS] {step_name} completed in {elapsed:.2f}s")
        if res.stdout.strip():
            lines = res.stdout.strip().splitlines()
            for line in lines[-10:]:
                print(f"    {line}")
        return True, elapsed
    else:
        print(f"  [FAILED] {step_name} failed with exit code {res.returncode}")
        if res.stderr.strip():
            print("  --- Error Output ---")
            for line in res.stderr.strip().splitlines()[-15:]:
                print(f"    {line}")
        if res.stdout.strip():
            print("  --- Standard Output ---")
            for line in res.stdout.strip().splitlines()[-15:]:
                print(f"    {line}")
        return False, elapsed

def main():
    log_header("SupportRAG - Full End-to-End Master Test Runner")
    print(f"Repository Root: {REPO_ROOT}")
    total_start = time.perf_counter()
    results = []

    # 1. Frontend Unit Tests (Node 24 Native Test Runner)
    frontend_dir = REPO_ROOT / "frontend"
    passed, dur = run_step(
        "Frontend TypeScript Unit Tests (node --test)",
        "npm test",
        cwd=frontend_dir
    )
    results.append(("Frontend Unit Tests (22 tests)", passed, dur))

    # 2. Frontend Production Build (Next.js 14 App Router)
    passed, dur = run_step(
        "Frontend Production Build (next build)",
        BUILD_CMD,
        cwd=frontend_dir
    )
    results.append(("Frontend Production Build", passed, dur))

    # 3. Backend Pytest Suite (FastAPI, VectorService, RAGPipeline, Scripts, RAG Eval)
    backend_dir = REPO_ROOT / "backend"
    passed, dur = run_step(
        "Backend Pytest Suite (35 tests)",
        f'"{PYTEST_EXE}" tests/ -v',
        cwd=backend_dir
    )
    results.append(("Backend Pytest Suite (35 tests)", passed, dur))

    # 4. Live Cloud Production Integration Tests
    passed, dur = run_step(
        "Live Production Cloud Verification (Vercel, Qdrant, Groq)",
        f'"{PYTHON_EXE}" "{REPO_ROOT / "scripts" / "test_live_production.py"}"',
        cwd=REPO_ROOT
    )
    results.append(("Live Production Cloud Verification (7 tests)", passed, dur))

    total_duration = time.perf_counter() - total_start
    log_header("Master Test Execution Summary")
    all_passed = True
    for name, success, dur in results:
        status_str = "[PASS]" if success else "[FAIL]"
        if not success:
            all_passed = False
        print(f"  {status_str:8s} {name:50s} ({dur:.2f}s)")
    
    print("-" * 70)
    print(f"Total Test Execution Time: {total_duration:.2f}s")
    if all_passed:
        print("🎉 ALL PROJECT TEST SUITES PASSED 100% WITHOUT ERRORS!")
        return 0
    else:
        print("❌ SOME TEST SUITES FAILED. PLEASE REVIEW LOGS.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
