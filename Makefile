.PHONY: check test audit package

check:
	python3 scripts/check_project.py

test:
	python3 -m unittest discover -s tests -v

audit: check test
	python3 -m compileall -q -f scripts tests
	python3 scripts/audit_project.py

package: audit
	python3 scripts/package.py
