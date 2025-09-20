#!/bin/bash

# Test script to verify DJ admin settings persistence
echo "=== Testing DJ Admin Settings Persistence ==="
echo

# Function to extract value from JSON response
get_setting() {
    local key="$1"
    curl -s "http://localhost/api/v1/admin/settings" | jq -r ".$key"
}

# Test 1: Test chatterbox voice setting persistence
echo "Test 1: Testing chatterbox_voice persistence"
echo "Current chatterbox_voice: $(get_setting 'chatterbox_voice')"

echo "Setting chatterbox_voice to 'echo'..."
curl -X POST "http://localhost/api/v1/admin/settings" \
  -H "Content-Type: application/json" \
  -d '{"chatterbox_voice": "echo"}' \
  -s > /dev/null

echo "Verifying setting was saved..."
current_voice=$(get_setting 'chatterbox_voice')
if [ "$current_voice" = "echo" ]; then
    echo "✅ PASS: chatterbox_voice correctly saved as 'echo'"
else
    echo "❌ FAIL: chatterbox_voice is '$current_voice', expected 'echo'"
fi
echo

# Test 2: Test voice provider setting persistence
echo "Test 2: Testing dj_voice_provider persistence"
echo "Current dj_voice_provider: $(get_setting 'dj_voice_provider')"

echo "Setting dj_voice_provider to 'chatterbox'..."
curl -X POST "http://localhost/api/v1/admin/settings" \
  -H "Content-Type: application/json" \
  -d '{"dj_voice_provider": "chatterbox"}' \
  -s > /dev/null

echo "Verifying setting was saved..."
current_provider=$(get_setting 'dj_voice_provider')
if [ "$current_provider" = "chatterbox" ]; then
    echo "✅ PASS: dj_voice_provider correctly saved as 'chatterbox'"
else
    echo "❌ FAIL: dj_voice_provider is '$current_provider', expected 'chatterbox'"
fi
echo

# Test 3: Test multiple settings at once
echo "Test 3: Testing multiple settings persistence"
echo "Setting multiple chatterbox parameters..."
curl -X POST "http://localhost/api/v1/admin/settings" \
  -H "Content-Type: application/json" \
  -d '{
    "chatterbox_voice": "nova",
    "chatterbox_exaggeration": 1.5,
    "chatterbox_cfg_weight": 0.7
  }' \
  -s > /dev/null

echo "Verifying all settings were saved..."
voice=$(get_setting 'chatterbox_voice')
exaggeration=$(get_setting 'chatterbox_exaggeration')
cfg_weight=$(get_setting 'chatterbox_cfg_weight')

if [ "$voice" = "nova" ] && [ "$exaggeration" = "1.5" ] && [ "$cfg_weight" = "0.7" ]; then
    echo "✅ PASS: All chatterbox settings correctly saved"
else
    echo "❌ FAIL: Settings not saved correctly"
    echo "  voice: '$voice' (expected 'nova')"
    echo "  exaggeration: '$exaggeration' (expected '1.5')"
    echo "  cfg_weight: '$cfg_weight' (expected '0.7')"
fi
echo

# Test 4: Test TTS endpoint timeout (non-blocking test)
echo "Test 4: Testing TTS endpoint responsiveness"
echo "Testing Chatterbox TTS endpoint (this should take 30-60 seconds)..."
start_time=$(date +%s)

timeout_result=$(timeout 120s curl -X POST "http://localhost/api/v1/admin/tts-test-chatterbox" \
  -H "Content-Type: application/json" \
  -d '{"text": "Quick test", "voice": "nova"}' \
  -s -w "%{http_code}")

end_time=$(date +%s)
duration=$((end_time - start_time))
http_code="${timeout_result: -3}"

echo "Duration: ${duration}s, HTTP Code: $http_code"

if [ "$http_code" = "200" ]; then
    echo "✅ PASS: TTS endpoint responded successfully in ${duration}s"
elif [ "$http_code" = "000" ]; then
    echo "⚠️  TIMEOUT: TTS endpoint took longer than 120s or failed"
else
    echo "❌ FAIL: TTS endpoint returned HTTP $http_code"
fi
echo

echo "=== Settings Persistence Test Summary ==="
echo "Current settings:"
curl -s "http://localhost/api/v1/admin/settings" | jq '{
  dj_voice_provider: .dj_voice_provider,
  chatterbox_voice: .chatterbox_voice,
  chatterbox_exaggeration: .chatterbox_exaggeration,
  chatterbox_cfg_weight: .chatterbox_cfg_weight
}'