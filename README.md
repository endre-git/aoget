# Contribute
## Develop
You can actively develop AOGet. Take a look at the issues, fix one, raise a PR and bug one of the admins to get it reviewed and merged.

### Principles
* OOP Python & clean code please, with type hinting and documenting all visible APIs
* Adhere to Flake8 and Black formatter as per .vscode settings found in the codebase
* Test coverage / vulnerability metrics can only go up

### Setting up VSCode (optional)
This is more notes for me, but you might find it useful if you want to contribute.
* Download VSCode
* Install your favourite virtual env manager (I personally use Anaconda)
* Add the following extensions to VSCode
  * Python extension for Visual Studio Code
  * Black Formatter (find the one with the most downloads)
  * Flake8 - this adds linting support
* Create your virtual environment (my example: conda create --name aoget-venv)
* Activate your virtual environment in VSCode (Ctrl-P then Select Python Interpreter)
* Checkout git from VSCode or from the command line and use Open Folder from VSCode (trust the authors :))
* Run a sanity-check pytest from a terminal
