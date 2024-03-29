virtualenv = .venv
$(virtualenv):
	test -d $(virtualenv) || python3 -m venv $(virtualenv)
	. $(virtualenv)/bin/activate && python -m pip install -U pip
requires: $(virtualenv)
	. $(virtualenv)/bin/activate && python -m pip install -r requirements.txt
upgrade-requirements:
	echo "Current versions"
	. $(virtualenv)/bin/activate && python -m pip freeze
	. $(virtualenv)/bin/activate && python -m pip install --upgrade -r requirements.txt
upgrade-pip3:
	. $(virtualenv)/bin/activate && python -m pip install -U pip
clean:
	find . -name "*.pyc" -exec rm -f {} \;
	rm -rf $(virtualenv) __pycache__ bandit
shell:
	. $(virtualenv)/bin/activate && $(SHELL)
REQUIREMENTS:
	. $(virtualenv)/bin/activate && python -m pip freeze > REQUIREMENTS
lint:
	black .
	ruff .
bandit:
	test -d bandit || mkdir bandit
	rm -rf bandit-env
	python3 -m venv bandit-env
	source bandit-env/bin/activate && python -m pip install bandit
	./bandit-env/bin/bandit ./newsdedup.py > bandit/bandit-newsdedup.py.txt
	./bandit-env/bin/bandit ./unstar.py > bandit/bandit-unstar.py.txt
	./bandit-env/bin/bandit ./list_feeds.py > bandit/bandit-list_feeds.py.txt
	rm -rf bandit-env
show-results:
	grep -A2 "Test results:" bandit/*
tests: lint bandit
all: requires upgrade-requirements tests show-results lint
