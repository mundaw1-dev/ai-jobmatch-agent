docker --version
docker compose version
docker compose config
docker compose build
pause
docker compose up -d
docker compose exec ollama ollama pull deepseek-r1:1.5b
docker compose exec ollama ollama list
docker compose exec ollama ollama run deepseek-r1:1.5b "Reply with just OK"
pause



docker compose up -d --force-recreate jobmatch-agent


docker compose exec ollama ollama pull deepseek-r1:1.5b