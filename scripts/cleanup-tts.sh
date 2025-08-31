#!/bin/bash

# TTS Cache Cleanup Script
# Removes TTS files older than 5 days to free up disk space

TTS_DIR="/shared/tts"
MAX_AGE_DAYS=5

echo "$(date): Starting TTS cleanup - removing files older than ${MAX_AGE_DAYS} days"

if [ ! -d "$TTS_DIR" ]; then
    echo "$(date): TTS directory $TTS_DIR not found, exiting"
    exit 1
fi

# Count files before cleanup
TOTAL_FILES_BEFORE=$(find "$TTS_DIR" -name "*.mp3" -type f | wc -l)
TOTAL_SIZE_BEFORE=$(du -sh "$TTS_DIR" 2>/dev/null | cut -f1)

echo "$(date): Before cleanup: $TOTAL_FILES_BEFORE files, $TOTAL_SIZE_BEFORE total size"

# Remove files older than MAX_AGE_DAYS
# Remove files older than MAX_AGE_DAYS and count them
DELETED_COUNT=$(find "$TTS_DIR" -name "*.mp3" -type f -mtime +${MAX_AGE_DAYS} -print | wc -l)
find "$TTS_DIR" -name "*.mp3" -type f -mtime +${MAX_AGE_DAYS} -delete

# Count files after cleanup
TOTAL_FILES_AFTER=$(find "$TTS_DIR" -name "*.mp3" -type f | wc -l)
TOTAL_SIZE_AFTER=$(du -sh "$TTS_DIR" 2>/dev/null | cut -f1)

echo "$(date): After cleanup: $TOTAL_FILES_AFTER files, $TOTAL_SIZE_AFTER total size"
echo "$(date): Deleted $DELETED_COUNT old TTS files"
echo "$(date): TTS cleanup completed"