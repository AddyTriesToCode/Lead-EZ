# Start n8n with Python environment configured
# This script ensures n8n can find Python for task runners

Write-Host "Setting up Python environment for n8n..." -ForegroundColor Cyan

# Clear any conflicting n8n environment variables from previous sessions
Remove-Item Env:\N8N_RUNNERS_MODE -ErrorAction SilentlyContinue
Remove-Item Env:\N8N_RUNNERS_AUTH_TOKEN -ErrorAction SilentlyContinue
Remove-Item Env:\N8N_RUNNERS_PYTHON_PATH -ErrorAction SilentlyContinue

# Add virtual environment Python to PATH
$env:PATH = "E:\AIML-Projects\Lead-EZ\.venv\Scripts;$env:PATH"

# Verify Python is accessible
$pythonVersion = python --version 2>&1
Write-Host "Python detected: $pythonVersion" -ForegroundColor Green

# Start n8n
Write-Host "`nStarting n8n..." -ForegroundColor Cyan
Write-Host "(Note: Python runner warning is harmless - your workflow uses HTTP/JS nodes)" -ForegroundColor Yellow
n8n
