python -m venv venv
call venv\Scripts\activate.bat
python -m pip install --upgrade pip
python -m pip install -U setuptools
python -m pip install -r requirements.txt
REM python -m pip install -r requirements_advanced.txt