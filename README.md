# 🏴‍☠️ Raido - AI Pirate Radio

A 24/7 AI-powered radio station with live DJ commentary, built with modern web technologies and containerized for easy deployment.

## Features

- **🎵 24/7 Music Streaming**: Continuous music playback from your collection
- **🤖 AI DJ Commentary**: Dynamic commentary generated using OpenAI or Ollama
- **🎙️ Multiple TTS Options**: OpenAI TTS, XTTS, or basic speech synthesis
- **📱 Modern Web Interface**: Responsive React frontend with real-time updates
- **🔄 Live Updates**: WebSocket integration for real-time track changes
- **📊 Admin Dashboard**: Configure DJ settings, monitor stats, manage users
- **🎨 Pirate Theme**: Custom pirate-themed design with dark mode
- **🐳 Docker Ready**: Fully containerized with Docker Compose
- **📈 Observability**: Structured logging and health monitoring

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   React Web     │    │   FastAPI       │    │   DJ Worker     │
│   Frontend      │◄──►│   Backend       │◄──►│   (AI/TTS)      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                        │                        │
         │                        ▼                        │
         │              ┌─────────────────┐                │
         └─────────────►│   PostgreSQL    │                │
                        │   Database      │                │
                        └─────────────────┘                │
                                 ▲                         │
         ┌─────────────────┐     │       ┌─────────────────┐
         │   Icecast       │◄────┼──────►│   Liquidsoap    │
         │   Streaming     │     │       │   Audio Engine  │
         └─────────────────┘     │       └─────────────────┘
                  ▲              │                ▲
                  │              │                │
         ┌─────────────────┐     │       ┌─────────────────┐
         │   Caddy Proxy   │     │       │   Music Files   │
         │   (HTTPS)       │     │       │   (/music)      │
         └─────────────────┘     │       └─────────────────┘
                                 │
                        ┌─────────────────┐
                        │   Redis Cache   │
                        │   (Optional)    │
                        └─────────────────┘
```

## Quick Start

### Prerequisites

- Docker and Docker Compose
- At least 2GB RAM
- Music files (MP3, FLAC, OGG, WAV)

### Installation

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd raido
   ```

2. **Initial setup**:
   ```bash
   make setup
   ```

3. **Configure environment**:
   Edit `.env` file with your settings:
   ```bash
   # Required for AI commentary
   OPENAI_API_KEY=sk-your-openai-api-key-here
   
   # Database password
   POSTGRES_PASSWORD=your_secure_password
   
   # Other settings...
   ```

4. **Add music**:
   ```bash
   mkdir -p music
   # Copy your music files to ./music directory
   ```

5. **Start Raido**:
   ```bash
   make up
   ```

6. **Run database migrations**:
   ```bash
   make migrate
   ```

### Access Points

- **Web Interface**: http://localhost:3000
- **Radio Stream**: http://localhost:8000/stream/raido.mp3
- **API Documentation**: http://localhost:8000/docs
- **Database Admin**: http://localhost:8080

## Development

### Development Setup

```bash
make dev-setup
```

This will:
- Set up the environment
- Build all containers
- Start services in development mode
- Run database migrations
- Enable live reload for code changes

### Available Commands

```bash
make help              # Show all available commands
make up               # Start all services
make down             # Stop all services
make logs             # Show all logs
make logs-api         # Show API logs
make logs-dj          # Show DJ worker logs
make shell-api        # Open shell in API container
make health           # Check service health
make backup-db        # Backup database
```

## Configuration

### DJ Settings

Configure AI commentary in `.env`:

```bash
# AI Provider (openai or ollama)
DJ_PROVIDER=openai
OPENAI_API_KEY=your-key-here

# TTS Provider (openai_tts, liquidsoap, or xtts)
DJ_VOICE_PROVIDER=openai_tts

# Commentary frequency (1 = after every song)
DJ_COMMENTARY_INTERVAL=1

# Max commentary length in seconds
DJ_MAX_SECONDS=30

# DJ personality
DJ_TONE=energetic
STATION_NAME="Raido Pirate Radio"
```

### Stream Settings

```bash
# Stream quality
ICECAST_BITRATE=128
STREAM_FORMAT=mp3

# Crossfade between tracks
CROSSFADE_DURATION=2.0
```

### Security

For production deployment:

```bash
# Use strong passwords
POSTGRES_PASSWORD=very-secure-password
JWT_SECRET=very-long-random-secret-key

# Set allowed origins
CORS_ORIGINS=https://yourdomain.com

# Configure HTTPS in Caddy
```

## Music Library

Raido supports:
- **MP3** (recommended)
- **FLAC** (high quality)
- **OGG Vorbis**
- **WAV**

### File Organization

```
music/
├── Artist1/
│   ├── Album1/
│   │   ├── 01 - Song1.mp3
│   │   ├── 02 - Song2.mp3
│   └── Album2/
├── Artist2/
└── Various/
```

### Metadata

Raido reads ID3 tags for:
- Title, Artist, Album
- Year, Genre
- Embedded artwork
- Duration

## API Documentation

### Core Endpoints

- `GET /api/v1/now` - Current playing track
- `GET /api/v1/now/history` - Play history
- `GET /api/v1/now/next` - Upcoming tracks
- `WS /ws` - Real-time updates

### Admin Endpoints

- `GET /api/v1/admin/settings` - Get settings
- `POST /api/v1/admin/settings` - Update settings
- `GET /api/v1/admin/stats` - System statistics

See `/docs` endpoint for full API documentation.

## Troubleshooting

### Common Issues

**No audio playing:**
```bash
make logs-liquidsoap
# Check for music files in ./music directory
# Verify file permissions
```

**DJ commentary not working:**
```bash
make logs-dj
# Check OPENAI_API_KEY in .env
# Verify AI provider settings
```

**Database connection issues:**
```bash
make logs-api
# Check POSTGRES_PASSWORD in .env
# Ensure database container is running
```

**Web interface not loading:**
```bash
make logs-web
# Check if port 3000 is available
# Verify proxy configuration
```

### Debugging

Enable debug logging:
```bash
# In .env
APP_DEBUG=true
LOG_LEVEL=debug
```

Check service status:
```bash
make status
make health
```

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Make your changes
4. Run tests: `make test`
5. Format code: `make format`
6. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- **Liquidsoap**: Audio streaming engine
- **Icecast**: Streaming server
- **FastAPI**: Modern Python web framework
- **React**: Frontend library
- **OpenAI**: AI commentary generation
- **Docker**: Containerization platform

---

**🏴‍☠️ Ahoy! Set sail with your own AI pirate radio station!**

For support, issues, or feature requests, please visit our GitHub repository.