
# Filename: Dockerfile
# Full path: C:\Technative\ai-jobmatch-agent\Dockerfile

FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Install the project and its declared dependencies.
COPY . /app
RUN python -m pip install --no-cache-dir .

# Streamlit listens on all container interfaces.
EXPOSE 8501

CMD ["python", "-m", "streamlit", "run", "app.py", "--server.address=0.0.0.0", "--server.port=8501", "--server.headless=true"]
