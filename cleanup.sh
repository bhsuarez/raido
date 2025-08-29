#!/bin/bash
# Automated cleanup script for Raido

echo "Starting cleanup..."

# Clean old TTS files (older than 7 days)
find /var/lib/docker/volumes/raido_shared/_data/tts -name "*.mp3" -mtime +7 -delete
echo "Cleaned old TTS files"

# Docker cleanup
docker system prune -f
docker image prune -f
echo "Docker cleanup complete"

# Show disk usage
df -h /
echo "Cleanup finished"