.PHONY: check test audit package upstream-check

check:
	python3 scripts/check_project.py

test:
	python3 -m unittest discover -s tests -v
	node --test tests/extensions.test.cjs

upstream-check:
	python3 scripts/verify_upstream_overlay.py

audit: check test
	python3 -m compileall -q -f scripts tests
	python3 scripts/audit_project.py

package: audit
	python3 scripts/package.py
