# GitHub release checklist

- [x] Source, tests, wheel and documentation extracted from v1.21.2 archive
- [x] MIT LICENSE added at repository root
- [x] `.gitignore` excludes databases, environments and credentials
- [x] SECURITY.md added with credential and deployment guidance
- [x] Wheel rebuild succeeds without dependencies
- [ ] Fix three Windows SQLite cleanup failures in `test_adaptive.py`
- [ ] Re-run all 203 tests with zero errors
- [ ] Confirm third-party dependency/license inventory
- [ ] Choose final GitHub owner and repository name
- [ ] Create public repository and push after final review

Current verification: 200 tests completed successfully; 3 tests fail during
TemporaryDirectory cleanup because SQLite database files remain open on
Windows. This is a release blocker, not a cosmetic warning.
