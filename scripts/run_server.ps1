Set-Location "C:\Users\shahu\Documents\OneDrive\OPEN CLASSROOMS\PROJET 9\Intelligent_Assistant"
$env:PYTHONPATH = $PWD
poetry run uvicorn src.api.main:app --host 0.0.0.0 --port 8000
