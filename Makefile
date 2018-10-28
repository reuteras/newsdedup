virtualenv = .env
env = virtualenv-3
pip = pip3
environment: 
	test -d $(virtualenv) || python3 -m venv $(virtualenv)
requires:
	. $(virtualenv)/bin/activate && $(pip) install -r pip-requires.txt
upgrade-requirements:
	echo "Current versions"
	. $(virtualenv)/bin/activate && $(pip) freeze
	. $(virtualenv)/bin/activate && $(pip) install --upgrade -r pip-requires.txt
upgrade-pip3:
	pip3 install -U pip
clean:
	find . -name "*.pyc" -exec rm -f {} \;
	rm -rf $(virtualenv) pylint
shell:
	. $(virtualenv)/bin/activate && $(SHELL)
REQUIREMENTS:
	. $(virtualenv)/bin/activate && $(pip) freeze > REQUIREMENTS
test-pylint:                                                                                                            
	test -d pylint || mkdir pylint
	pylint newsdedup.py > pylint/newsdedup.pylint || exit 0
