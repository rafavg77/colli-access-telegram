# colli-access-telegram

Telegram bot client for ColliCasa access-control backend API.

## Features

- 🤖 Built with python-telegram-bot v20+ (asyncio)
- 🔐 Integrates with ColliCasa access-control backend
- ⚙️ Configuration via environment variables (.env file)
- 🐳 Docker-ready with Dockerfile and docker-compose.yml
- 📝 Comprehensive error handling and logging
- ⏱️ Request timeouts for reliability

## Requirements

- Python 3.8 or higher
- A Telegram Bot Token (obtain from [@BotFather](https://t.me/botfather))
- Access to ColliCasa access-control backend API

## Installation

### Option 1: Local Installation

1. Clone the repository:
```bash
git clone https://github.com/rafavg77/colli-access-telegram.git
cd colli-access-telegram
```

2. Install dependencies:
```bash
pip install -e .
```

3. Configure the bot:
```bash
cp .env.example .env
# Edit .env with your actual credentials
```

4. Run the bot:
```bash
python bot.py
```

### Option 2: Docker

1. Clone the repository:
```bash
git clone https://github.com/rafavg77/colli-access-telegram.git
cd colli-access-telegram
```

2. Configure the bot:
```bash
cp .env.example .env
# Edit .env with your actual credentials
```

3. Build and run with Docker Compose:
```bash
docker-compose up -d
```

Or build and run with Docker directly:
```bash
docker build -t colli-access-telegram .
docker run -d --name colli-bot --env-file .env colli-access-telegram
```

## Configuration

Create a `.env` file in the project root with the following variables:

```env
# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN=your_bot_token_here

# ColliCasa Backend API Configuration
BACKEND_API_BASE_URL=https://api.example.com
SERVICE_TOKEN=your_service_token_here
TENANT_ID=your_tenant_id_here
```

### Configuration Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `TELEGRAM_BOT_TOKEN` | Your Telegram Bot API token from BotFather | Yes |
| `BACKEND_API_BASE_URL` | Base URL of the ColliCasa backend API | Yes |
| `SERVICE_TOKEN` | Authentication token for the backend API | Yes |
| `TENANT_ID` | Your tenant identifier | Yes |

## Usage

### Available Commands

- `/start` - Display welcome message and basic help

## Development

### Project Structure

```
colli-access-telegram/
├── bot.py              # Main bot application
├── pyproject.toml      # Python project dependencies (setuptools format)
├── requirements.txt    # Python dependencies (pip format)
├── Dockerfile          # Docker container definition
├── docker-compose.yml  # Docker Compose configuration
├── .env.example        # Example environment configuration
└── README.md           # This file
```

### Dependencies

- `python-telegram-bot>=20.0` - Telegram Bot API framework (asyncio version)
- `requests>=2.31.0` - HTTP library for API calls
- `python-dotenv>=1.0.0` - Environment variable management

### Logging

The bot logs all important events and errors to the console (stdout). Log format:
```
%(asctime)s - %(name)s - %(levelname)s - %(message)s
```

### Error Handling

- All API calls have timeout protection (10 seconds default)
- Graceful error handling with user-friendly error messages
- Detailed error logging for debugging
- Automatic retry mechanisms for transient failures

## Docker

### Building the Image

```bash
docker build -t colli-access-telegram .
```

### Running the Container

```bash
docker run -d --name colli-bot --env-file .env colli-access-telegram
```

### Viewing Logs

```bash
docker logs -f colli-bot
```

### Stopping the Bot

```bash
docker stop colli-bot
```

## License

This project is open source and available under the MIT License.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
