def pytest_addoption(parser):  # pragma: no cover - shim
    parser.addoption("--cov", action="append", default=[], help="No-op coverage target")
    parser.addoption("--cov-report", action="append", default=[], help="No-op coverage report")


def pytest_terminal_summary(terminalreporter, exitstatus, config):  # pragma: no cover - shim
    targets = config.getoption("--cov")
    if targets:
        terminalreporter.section("coverage (shim)")
        terminalreporter.write_line(f"targets: {', '.join(targets)}")
