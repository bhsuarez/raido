#!/usr/bin/env python3
"""
Raido System Monitor
Monitors services and sends Signal notifications when issues are detected.
"""

import os
import time
import requests
import docker
import schedule
import logging
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class RaidoMonitor:
    def __init__(self):
        # Configuration from environment
        self.signal_api_url = os.getenv('SIGNAL_API_URL', 'http://signal-cli:8080')
        self.phone_number = os.getenv('PHONE_NUMBER', '')
        self.recipient_number = os.getenv('RECIPIENT_NUMBER', '')
        self.raido_api_url = os.getenv('RAIDO_API_URL', 'http://host.docker.internal:8001')
        self.raido_stream_url = os.getenv('RAIDO_STREAM_URL', 'http://host.docker.internal:8000')
        self.github_recovery_url = os.getenv('GITHUB_RECOVERY_URL', 'https://github.com/yourusername/raido/blob/master/RECOVERY.md')
        
        # Docker client
        self.docker_client = docker.from_env()
        
        # State tracking
        self.last_alert_time = {}
        self.alert_cooldown = timedelta(minutes=30)  # Don't spam alerts
        
        # Required services
        self.required_services = [
            'raido-api-1',
            'raido-db-1', 
            'raido-liquidsoap-1',
            'raido-icecast-1'
        ]
        
        # Optional services (warn but don't alert critically)
        self.optional_services = [
            'raido-dj-worker-1',
            'raido-kokoro-tts-1',
            'raido-ollama-1',
            'raido-web-dev-1',
            'raido-proxy-1'
        ]
        
        logger.info(f"Monitor initialized - API: {self.raido_api_url}, Stream: {self.raido_stream_url}")

    def send_signal_message(self, message: str, urgent: bool = False) -> bool:
        """Send a Signal message via the REST API"""
        if not self.phone_number or not self.recipient_number:
            logger.warning("Signal phone numbers not configured")
            return False
            
        try:
            url = f"{self.signal_api_url}/v2/send"
            
            # Add urgency indicator and recovery link
            full_message = message
            if urgent:
                full_message = f"🚨 URGENT: {message}"
            
            full_message += f"\n\n🔧 Recovery Guide: {self.github_recovery_url}"
            
            payload = {
                "message": full_message,
                "number": self.phone_number,
                "recipients": [self.recipient_number]
            }
            
            response = requests.post(url, json=payload, timeout=10)
            response.raise_for_status()
            
            logger.info(f"Signal message sent successfully: {message[:50]}...")
            return True
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to send Signal message: {e}")
            return False

    def should_send_alert(self, alert_key: str) -> bool:
        """Check if enough time has passed since last alert for this issue"""
        now = datetime.now()
        if alert_key in self.last_alert_time:
            if now - self.last_alert_time[alert_key] < self.alert_cooldown:
                return False
        return True

    def record_alert_sent(self, alert_key: str):
        """Record that an alert was sent for this issue"""
        self.last_alert_time[alert_key] = datetime.now()

    def check_docker_services(self) -> Tuple[List[str], List[str]]:
        """Check status of Docker services"""
        down_required = []
        down_optional = []
        
        try:
            containers = self.docker_client.containers.list(all=True)
            container_names = [c.name for c in containers]
            running_containers = [c.name for c in containers if c.status == 'running']
            
            # Check required services
            for service in self.required_services:
                if service not in container_names:
                    down_required.append(f"{service} (missing)")
                elif service not in running_containers:
                    down_required.append(f"{service} (stopped)")
            
            # Check optional services
            for service in self.optional_services:
                if service not in container_names:
                    down_optional.append(f"{service} (missing)")
                elif service not in running_containers:
                    down_optional.append(f"{service} (stopped)")
                    
        except Exception as e:
            logger.error(f"Failed to check Docker services: {e}")
            down_required.append(f"Docker API error: {e}")
        
        return down_required, down_optional

    def check_api_health(self) -> Optional[str]:
        """Check if the Raido API is responding"""
        try:
            response = requests.get(f"{self.raido_api_url}/api/v1/now/", timeout=10)
            if response.status_code != 200:
                return f"API returned {response.status_code}"
            return None
        except requests.exceptions.RequestException as e:
            return f"API unreachable: {e}"

    def check_stream_health(self) -> Optional[str]:
        """Check if the audio stream is available"""
        try:
            response = requests.head(f"{self.raido_stream_url}/stream/raido.mp3", timeout=10)
            if response.status_code != 200:
                return f"Stream returned {response.status_code}"
            return None
        except requests.exceptions.RequestException as e:
            return f"Stream unreachable: {e}"

    def check_recent_activity(self) -> Optional[str]:
        """Check if there has been recent track activity"""
        try:
            response = requests.get(f"{self.raido_api_url}/api/v1/now/history?limit=1", timeout=10)
            if response.status_code != 200:
                return "Cannot check recent activity - API error"
                
            data = response.json()
            if not data.get('tracks'):
                return "No track history found"
                
            # Check if last track was within reasonable time (2 hours)
            last_track = data['tracks'][0]
            if 'play' in last_track and 'started_at' in last_track['play']:
                started_at = datetime.fromisoformat(last_track['play']['started_at'].replace('Z', '+00:00'))
                time_since = datetime.now(started_at.tzinfo) - started_at
                if time_since > timedelta(hours=2):
                    return f"No activity for {time_since} (last: {last_track['track']['artist']} - {last_track['track']['title']})"
                    
            return None
        except Exception as e:
            return f"Activity check failed: {e}"

    def perform_health_check(self):
        """Perform comprehensive health check"""
        logger.info("Starting health check...")
        
        issues = []
        urgent_issues = []
        
        # Check Docker services
        down_required, down_optional = self.check_docker_services()
        if down_required:
            urgent_issues.extend(down_required)
        if down_optional:
            issues.extend(down_optional)
        
        # Check API health
        api_error = self.check_api_health()
        if api_error:
            urgent_issues.append(f"API: {api_error}")
        
        # Check stream health
        stream_error = self.check_stream_health()
        if stream_error:
            urgent_issues.append(f"Stream: {stream_error}")
        
        # Check recent activity
        activity_error = self.check_recent_activity()
        if activity_error:
            issues.append(f"Activity: {activity_error}")
        
        # Send alerts if needed
        if urgent_issues:
            alert_key = "urgent_issues"
            if self.should_send_alert(alert_key):
                message = "Raido system has critical issues:\n\n" + "\n".join([f"• {issue}" for issue in urgent_issues])
                if issues:
                    message += "\n\nAdditional warnings:\n" + "\n".join([f"• {issue}" for issue in issues])
                
                if self.send_signal_message(message, urgent=True):
                    self.record_alert_sent(alert_key)
        
        elif issues:
            alert_key = "minor_issues"
            if self.should_send_alert(alert_key):
                message = "Raido system warnings:\n\n" + "\n".join([f"• {issue}" for issue in issues])
                if self.send_signal_message(message, urgent=False):
                    self.record_alert_sent(alert_key)
        
        else:
            logger.info("All systems healthy ✅")

    def send_startup_message(self):
        """Send a message when monitoring starts"""
        message = f"🎙️ Raido monitoring started at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\nMonitoring services:\n"
        message += "\n".join([f"• {service}" for service in self.required_services + self.optional_services])
        self.send_signal_message(message)

def main():
    """Main monitoring loop"""
    monitor = RaidoMonitor()
    
    # Send startup notification
    monitor.send_startup_message()
    
    # Schedule regular health checks
    check_interval = int(os.getenv('CHECK_INTERVAL', 300))  # Default 5 minutes
    schedule.every(check_interval).seconds.do(monitor.perform_health_check)
    
    logger.info(f"Starting monitoring loop (check every {check_interval} seconds)")
    
    # Run initial check
    monitor.perform_health_check()
    
    # Keep running
    while True:
        try:
            schedule.run_pending()
            time.sleep(30)  # Check for scheduled jobs every 30 seconds
        except KeyboardInterrupt:
            logger.info("Monitoring stopped by user")
            monitor.send_signal_message("🛑 Raido monitoring stopped")
            break
        except Exception as e:
            logger.error(f"Error in monitoring loop: {e}")
            time.sleep(60)  # Wait a minute before retrying

if __name__ == "__main__":
    main()