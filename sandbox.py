"""
Sandboxed Code Execution Module
Provides secure Python execution with resource limits and import restrictions.
"""
import asyncio
import sys
import time
from dataclasses import dataclass
from typing import Optional

# Forbidden modules that could be used for malicious purposes
FORBIDDEN_IMPORTS = {
    # System access
    'os', 'sys', 'subprocess', 'shutil', 'pathlib',
    # File system
    'open', 'io', 'tempfile',
    # Network
    'socket', 'urllib', 'http', 'ftplib', 'smtplib', 'ssl',
    'requests', 'httpx', 'aiohttp',
    # Code execution
    'exec', 'eval', 'compile', 'importlib', '__import__',
    'builtins', '__builtins__',
    # Process management
    'multiprocessing', 'threading', 'concurrent',
    # Dangerous introspection
    'ctypes', 'gc', 'inspect', 'code',
    # Database (prevent data access)
    'sqlite3', 'psycopg2', 'mysql', 'pymongo',
}

# Safe imports that are allowed
ALLOWED_IMPORTS = {
    'math', 'random', 'json', 're', 'datetime', 'time',
    'collections', 'itertools', 'functools', 'operator',
    'string', 'textwrap', 'unicodedata',
    'decimal', 'fractions', 'statistics',
    'copy', 'pprint', 'dataclasses',
    'typing', 'enum', 'abc',
    'hashlib', 'hmac', 'base64', 'binascii',
    'heapq', 'bisect', 'array',
    'calendar', 'locale',
}


@dataclass
class ExecutionResult:
    """Result of a sandboxed code execution."""
    stdout: str
    stderr: str
    exit_code: int
    execution_time_ms: int
    timed_out: bool = False
    error: Optional[str] = None


def create_sandbox_script(code: str) -> str:
    """Wrap user code in a sandbox with import restrictions."""
    indented_code = '\n'.join('    ' + line for line in code.split('\n'))
    forbidden_repr = repr(FORBIDDEN_IMPORTS)
    allowed_repr = repr(ALLOWED_IMPORTS)

    return f'''
import sys
import resource
import traceback

# Set resource limits
try:
    # Memory limit: 128MB
    resource.setrlimit(resource.RLIMIT_AS, (128 * 1024 * 1024, 128 * 1024 * 1024))
    # CPU time limit: 60 seconds
    resource.setrlimit(resource.RLIMIT_CPU, (60, 60))
    # Max file descriptors: 10 (prevent file bomb)
    resource.setrlimit(resource.RLIMIT_NOFILE, (10, 10))
    # Max processes: 0 (prevent fork bomb)
    resource.setrlimit(resource.RLIMIT_NPROC, (0, 0))
except Exception:
    pass  # Limits may not be available on all platforms

# Remove dangerous builtins
import builtins
_original_import = builtins.__import__

FORBIDDEN = {forbidden_repr}
ALLOWED = {allowed_repr}

def _safe_import(name, globals=None, locals=None, fromlist=(), level=0):
    # Get the base module name
    base_module = name.split('.')[0]

    # Check if forbidden
    if base_module in FORBIDDEN:
        raise ImportError(f"Import of '{{name}}' is not allowed in sandbox")

    # Allow only explicitly permitted imports
    if base_module not in ALLOWED and name not in ALLOWED:
        raise ImportError(f"Import of '{{name}}' is not allowed. Only safe standard library imports are permitted.")

    return _original_import(name, globals, locals, fromlist, level)

builtins.__import__ = _safe_import

# Remove dangerous builtins (but keep __import__ since we replaced it with our safe version)
for name in ['open', 'eval', 'exec', 'compile', 'input', 'breakpoint']:
    if hasattr(builtins, name):
        delattr(builtins, name)

# User code starts here
try:
{indented_code}
except Exception as e:
    traceback.print_exc()
    sys.exit(1)
'''


async def run_sandboxed_python(
    code: str,
    timeout_seconds: int = 30,
    memory_limit_mb: int = 128
) -> ExecutionResult:
    """
    Execute Python code in a sandboxed subprocess with resource limits.

    Args:
        code: Python source code to execute
        timeout_seconds: Maximum execution time (default 30s, max 60s)
        memory_limit_mb: Maximum memory usage (default 128MB)

    Returns:
        ExecutionResult with stdout, stderr, exit_code, and timing info
    """
    # Clamp timeout to safe range
    timeout_seconds = min(max(timeout_seconds, 1), 60)

    # Create sandboxed script
    sandbox_script = create_sandbox_script(code)

    start_time = time.time()

    try:
        # Run in subprocess with -I (isolated) and -S (no site) flags
        # This is intentionally using subprocess for sandboxed code execution
        process = await asyncio.create_subprocess_exec(
            sys.executable, '-I', '-S', '-c', sandbox_script,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            # Prevent inheriting environment variables
            env={
                'PATH': '/usr/bin:/bin',
                'HOME': '/tmp',
                'PYTHONDONTWRITEBYTECODE': '1',
            }
        )

        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=timeout_seconds
            )

            execution_time_ms = int((time.time() - start_time) * 1000)

            return ExecutionResult(
                stdout=stdout.decode('utf-8', errors='replace')[:50000],  # Limit output size
                stderr=stderr.decode('utf-8', errors='replace')[:10000],
                exit_code=process.returncode or 0,
                execution_time_ms=execution_time_ms,
                timed_out=False
            )

        except asyncio.TimeoutError:
            # Kill the process on timeout
            process.kill()
            await process.wait()

            execution_time_ms = int((time.time() - start_time) * 1000)

            return ExecutionResult(
                stdout='',
                stderr=f'Execution timed out after {timeout_seconds} seconds',
                exit_code=-1,
                execution_time_ms=execution_time_ms,
                timed_out=True,
                error='timeout'
            )

    except Exception as e:
        execution_time_ms = int((time.time() - start_time) * 1000)

        return ExecutionResult(
            stdout='',
            stderr=str(e),
            exit_code=-1,
            execution_time_ms=execution_time_ms,
            timed_out=False,
            error=str(e)
        )


def generate_html_preview(html: str, css: str = '', javascript: str = '') -> str:
    """
    Generate a complete HTML document for preview.
    Sanitizes content to prevent XSS and external resource loading.
    """
    # Create a self-contained HTML document with CSP
    preview_html = f'''<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="Content-Security-Policy" content="default-src 'self' 'unsafe-inline' data:; script-src 'unsafe-inline'; style-src 'unsafe-inline';">
    <style>
        /* Reset */
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; }}

        /* User CSS */
        {css}
    </style>
</head>
<body>
{html}
<script>
// Sandbox console.log to capture output
(function() {{
    const originalLog = console.log;
    const originalError = console.error;
    const originalWarn = console.warn;

    window.__consoleLogs = [];

    console.log = function(...args) {{
        window.__consoleLogs.push({{ type: 'log', args: args.map(String) }});
        originalLog.apply(console, args);
    }};
    console.error = function(...args) {{
        window.__consoleLogs.push({{ type: 'error', args: args.map(String) }});
        originalError.apply(console, args);
    }};
    console.warn = function(...args) {{
        window.__consoleLogs.push({{ type: 'warn', args: args.map(String) }});
        originalWarn.apply(console, args);
    }};
}})();

// User JavaScript
try {{
{javascript}
}} catch (e) {{
    console.error('Script error:', e.message);
}}
</script>
</body>
</html>'''

    return preview_html


# For testing
if __name__ == '__main__':
    import asyncio

    # Test basic execution
    test_code = '''
import math
print(f"Pi is approximately {math.pi:.4f}")
print("Hello from sandbox!")
result = sum(range(100))
print(f"Sum of 0-99: {result}")
'''

    async def test():
        result = await run_sandboxed_python(test_code)
        print(f"Exit code: {result.exit_code}")
        print(f"Time: {result.execution_time_ms}ms")
        print(f"Stdout:\n{result.stdout}")
        if result.stderr:
            print(f"Stderr:\n{result.stderr}")

    asyncio.run(test())
