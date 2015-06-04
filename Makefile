virtualenv = .env
env = virtualenv
environment: 
	test -d $(virtualenv) || $(env) --no-site-packages $(virtualenv)
requires:
	. $(virtualenv)/bin/activate && pip install -r pip-requires.txt --allow-external pygmaps --allow-unverified pygmaps
upgrade-requirements:
	echo "Current versions"
	. $(virtualenv)/bin/activate && pip freeze
	. $(virtualenv)/bin/activate && pip install --upgrade -r pip-requires.txt
clean:
	find . -name "*.pyc" -exec rm -f {} \;
	rm -rf $(virtualenv) pylint
shell:
	. $(virtualenv)/bin/activate && $(SHELL)
REQUIREMENTS:
	. $(virtualenv)/bin/activate && pip freeze > REQUIREMENTS
test-pylint:                                                                                                            
	test -d pylint || mkdir pylint
	pylint newsdedup.py > pylint/newsdedup.pylint || exit 0
