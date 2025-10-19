#!/usr/bin/env python3
"""
Generate docker-compose services for all stations defined in stations.yml

Usage:
    python scripts/generate-station-services.py

This will create docker-compose.stations.yml with all station-specific services.
Include it in your docker-compose command:
    docker compose -f docker-compose.yml -f docker-compose.stations.yml up
"""

import yaml
import sys
from pathlib import Path

def load_stations_config():
    """Load stations configuration from stations.yml"""
    config_path = Path(__file__).parent.parent / "stations.yml"

    if not config_path.exists():
        print(f"Error: {config_path} not found", file=sys.stderr)
        sys.exit(1)

    with open(config_path) as f:
        return yaml.safe_load(f)

def generate_liquidsoap_service(station_id, config):
    """Generate liquidsoap service configuration"""
    liq_config = config['liquidsoap']

    service = {
        'image': 'savonet/liquidsoap:v2.2.5',
        'restart': 'unless-stopped',
        'depends_on': ['icecast'],
        'volumes': [
            f"{config['music']['path']}:{config['music']['path']}:ro",
            f"{liq_config['config_file']}:/{station_id}.liq:ro",
            'shared:/shared'
        ],
        'command': ['liquidsoap', f'/{station_id}.liq'],
        'ports': [f"{liq_config['telnet_port']}:{liq_config['telnet_port']}"]
    }

    # Add HTTP port if configured
    if liq_config.get('http_port'):
        service['ports'].append(f"{liq_config['http_port']}:{liq_config['http_port']}")

    return service

def generate_dj_worker_service(station_id, config):
    """Generate DJ worker service configuration"""
    if not config['dj_worker']['enabled']:
        return None

    dj_config = config['dj_worker']
    liq_config = config['liquidsoap']

    service = {
        'build': './services/dj-worker',
        'restart': 'unless-stopped',
        'env_file': '.env',
        'depends_on': {
            'api': {'condition': 'service_healthy'}
        },
        'volumes': ['shared:/shared'],
        'environment': [
            f"STATION_NAME={station_id}",
            f"LIQUIDSOAP_HOST={station_id}-liquidsoap",
            f"LIQUIDSOAP_PORT={liq_config['telnet_port']}"
        ],
        'healthcheck': {
            'test': ['CMD', 'curl', '-f', 'http://api:8000/health'],
            'interval': '30s',
            'timeout': '10s',
            'retries': 3,
            'start_period': '40s'
        },
        'mem_limit': dj_config.get('memory_limit', '1g'),
        'cpus': str(dj_config.get('cpu_limit', '0.50'))
    }

    return service

def generate_frontend_service(station_id, config):
    """Generate frontend web service configuration"""
    if not config['frontend']['enabled']:
        return None

    frontend_config = config['frontend']

    # Determine build context
    if station_id == 'main':
        build_context = './web'
    else:
        build_context = f'./web-{station_id}'

    service = {
        'build': build_context,
        'restart': 'unless-stopped',
        'depends_on': ['api']
    }

    # Add port mapping if specified
    if frontend_config.get('port'):
        service['ports'] = [f"{frontend_config['port']}:80"]

    return service

def generate_docker_compose(stations_config):
    """Generate complete docker-compose configuration for all stations"""
    compose = {
        'version': '3.8',
        'services': {}
    }

    stations = stations_config['stations']

    for station_id, station_config in stations.items():
        # Generate liquidsoap service
        liquidsoap_service = generate_liquidsoap_service(station_id, station_config)
        compose['services'][f'{station_id}-liquidsoap'] = liquidsoap_service

        # Generate DJ worker service
        dj_worker_service = generate_dj_worker_service(station_id, station_config)
        if dj_worker_service:
            compose['services'][f'{station_id}-dj-worker'] = dj_worker_service

        # Generate frontend service
        frontend_service = generate_frontend_service(station_id, station_config)
        if frontend_service:
            if station_id == 'main':
                compose['services']['web'] = frontend_service
            else:
                compose['services'][f'{station_id}-web'] = frontend_service

    return compose

def main():
    """Main entry point"""
    print("🎵 Raido Station Service Generator")
    print("=" * 50)

    # Load configuration
    print("📖 Loading stations.yml...")
    config = load_stations_config()

    stations = config['stations']
    print(f"✅ Found {len(stations)} stations: {', '.join(stations.keys())}")

    # Generate docker-compose
    print("\n🔧 Generating docker-compose.stations.yml...")
    compose_config = generate_docker_compose(config)

    # Write output
    output_path = Path(__file__).parent.parent / "docker-compose.stations.yml"
    with open(output_path, 'w') as f:
        yaml.dump(compose_config, f, default_flow_style=False, sort_keys=False, indent=2)

    print(f"✅ Generated {output_path}")

    # Print summary
    print("\n📊 Generated services:")
    for service_name in compose_config['services'].keys():
        print(f"  - {service_name}")

    print("\n🚀 To start all stations:")
    print("   docker compose -f docker-compose.yml -f docker-compose.stations.yml up -d")

    print("\n📝 To add a new station:")
    print("   1. Edit stations.yml")
    print("   2. Run this script again")
    print("   3. Create liquidsoap config: infra/liquidsoap/<station>.liq")
    print("   4. (Optional) Create frontend: web-<station>/")
    print("   5. Restart services")

if __name__ == '__main__':
    main()
