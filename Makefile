virtualenv = .env
environment: 
	test -d $(virtualenv) || python3 -m venv $(virtualenv)
	. $(virtualenv)/bin/activate && python -m pip install -U pip
requires:
	. $(virtualenv)/bin/activate && python -m pip install -r requirements.txt
upgrade-requirements:
	echo "Current versions"
	. $(virtualenv)/bin/activate && python -m pip freeze
	. $(virtualenv)/bin/activate && python -m pip install --upgrade -r requirements.txt
upgrade-pip3:
	. $(virtualenv)/bin/activate && python -m pip install -U pip
clean:
	find . -name "*.pyc" -exec rm -f {} \;
	rm -rf $(virtualenv) pylint __pycache__
shell:
	. $(virtualenv)/bin/activate && $(SHELL)
REQUIREMENTS:
	. $(virtualenv)/bin/activate && python -m pip freeze > REQUIREMENTS
test-pylint:                                                                                                            
	test -d pylint || mkdir pylint
	pylint newsdedup.py > pylint/newsdedup.pylint || exit 0
test-bandit:
	rm -rf bandit-env
	python3 -m venv bandit-env
	source bandit-env/bin/activate && python -m pip install bandit
	./bandit-env/bin/bandit newsdedup.py
	./bandit-env/bin/bandit unstar.py
	rm -rf bandit-env
