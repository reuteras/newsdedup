virtualenv = .env
env = virtualenv-3
pip = pip3
environment: 
	test -d $(virtualenv) || python3 -m venv $(virtualenv)
	. $(virtualenv)/bin/activate && pip3 install -U pip
requires:
	. $(virtualenv)/bin/activate && $(pip) install -r requirements.txt
upgrade-requirements:
	echo "Current versions"
	. $(virtualenv)/bin/activate && $(pip) freeze
	. $(virtualenv)/bin/activate && $(pip) install --upgrade -r requirements.txt
upgrade-pip3:
	. $(virtualenv)/bin/activate && pip3 install -U pip
clean:
	find . -name "*.pyc" -exec rm -f {} \;
	rm -rf $(virtualenv) pylint __pycache__
shell:
	. $(virtualenv)/bin/activate && $(SHELL)
REQUIREMENTS:
	. $(virtualenv)/bin/activate && $(pip) freeze > REQUIREMENTS
test-pylint:                                                                                                            
	test -d pylint || mkdir pylint
	pylint newsdedup.py > pylint/newsdedup.pylint || exit 0
test-bandit:
	rm -rf bandit-env
	python3 -m venv bandit-env
	source bandit-env/bin/activate && python3 -m pip install bandit
	./bandit-env/bin/bandit newsdedup.py
	./bandit-env/bin/bandit unstar.py
	rm -rf bandit-env
