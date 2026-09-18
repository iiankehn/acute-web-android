.PHONY: check test package

check:
	python3 scripts/check_project.py

test:
	python3 -m unittest discover -s tests -v

package: check test
	python3 scripts/package.py

