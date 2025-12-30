#!/usr/bin/env python3
"""
ColliCasa Access Control Telegram Bot

A Telegram bot that integrates with the ColliCasa access-control backend API.
"""

import asyncio
import logging
import os
import sys
from typing import Optional

import requests
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


class Config:
    """Configuration loader from environment variables."""
    
    def __init__(self):
        """Load configuration from .env file."""
        load_dotenv()
        
        self.bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
        self.backend_api_base_url = os.getenv('BACKEND_API_BASE_URL')
        self.service_token = os.getenv('SERVICE_TOKEN')
        self.tenant_id = os.getenv('TENANT_ID')
        
        # Validate required configuration
        self._validate()
    
    def _validate(self):
        """Validate that all required configuration is present."""
        if not self.bot_token:
            raise ValueError("TELEGRAM_BOT_TOKEN is required in .env file")
        if not self.backend_api_base_url:
            raise ValueError("BACKEND_API_BASE_URL is required in .env file")
        if not self.service_token:
            raise ValueError("SERVICE_TOKEN is required in .env file")
        if not self.tenant_id:
            raise ValueError("TENANT_ID is required in .env file")
        
        logger.info("Configuration loaded successfully")
        logger.info(f"Backend API URL: {self.backend_api_base_url}")
        logger.info(f"Tenant ID: {self.tenant_id}")


class ColliCasaAPIClient:
    """Client for interacting with ColliCasa access-control backend API."""
    
    def __init__(self, config: Config):
        """
        Initialize the API client.
        
        Args:
            config: Configuration object with API credentials
        """
        self.base_url = config.backend_api_base_url.rstrip('/')
        self.service_token = config.service_token
        self.tenant_id = config.tenant_id
        self.timeout = 10  # seconds
    
    def _get_headers(self) -> dict:
        """Get headers for API requests."""
        return {
            'Authorization': f'Bearer {self.service_token}',
            'Content-Type': 'application/json',
            'X-Tenant-ID': self.tenant_id
        }
    
    async def test_connection(self) -> bool:
        """
        Test the connection to the backend API.
        
        Returns:
            True if connection is successful, False otherwise
        """
        try:
            # Use asyncio to run the blocking request in a thread pool
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: requests.get(
                    f"{self.base_url}/health",
                    headers=self._get_headers(),
                    timeout=self.timeout
                )
            )
            return response.status_code == 200
        except requests.exceptions.Timeout:
            logger.error("Backend API request timed out")
            return False
        except requests.exceptions.RequestException as e:
            logger.error(f"Backend API request failed: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error testing backend connection: {e}")
            return False


class TelegramBot:
    """Telegram bot for ColliCasa access control."""
    
    def __init__(self, config: Config):
        """
        Initialize the bot.
        
        Args:
            config: Configuration object
        """
        self.config = config
        self.api_client = ColliCasaAPIClient(config)
        self.application: Optional[Application] = None
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Handle the /start command.
        
        Args:
            update: Telegram update object
            context: Telegram context object
        """
        try:
            user = update.effective_user
            logger.info(f"User {user.id} ({user.username}) started the bot")
            
            welcome_message = (
                f"👋 Welcome to ColliCasa Access Control Bot!\n\n"
                f"Hi {user.first_name}! I'm here to help you manage access control.\n\n"
                f"📋 Available Commands:\n"
                f"/start - Show this help message\n\n"
                f"🔧 Status: Connected to backend API\n"
                f"Tenant ID: {self.config.tenant_id}"
            )
            
            await update.message.reply_text(welcome_message)
            
        except Exception as e:
            logger.error(f"Error in start_command: {e}", exc_info=True)
            await self._send_error_message(update, "Sorry, an error occurred while processing your request.")
    
    async def _send_error_message(self, update: Update, message: str) -> None:
        """
        Send an error message to the user.
        
        Args:
            update: Telegram update object
            message: Error message to send
        """
        try:
            await update.message.reply_text(f"❌ {message}")
        except Exception as e:
            logger.error(f"Failed to send error message: {e}")
    
    async def error_handler(self, update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Handle errors that occur during update processing.
        
        Args:
            update: Telegram update object
            context: Telegram context object
        """
        logger.error("Exception while handling an update:", exc_info=context.error)
        
        # Try to send error message to user if update is available
        if isinstance(update, Update) and update.effective_message:
            try:
                await update.effective_message.reply_text(
                    "⚠️ An error occurred while processing your request. "
                    "Please try again later or contact support."
                )
            except Exception as e:
                logger.error(f"Failed to send error message to user: {e}")
    
    async def post_init(self, application: Application) -> None:
        """
        Initialize after the application is set up.
        
        Args:
            application: The application instance
        """
        logger.info("Bot initialization complete")
        logger.info("Testing backend API connection...")
        
        # Test backend connection
        if await self.api_client.test_connection():
            logger.info("✓ Backend API connection successful")
        else:
            logger.warning("⚠ Backend API connection failed - bot will continue but API calls may fail")
    
    def setup_handlers(self) -> None:
        """Set up command handlers for the bot."""
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_error_handler(self.error_handler)
        
        logger.info("Command handlers registered")
    
    async def run(self) -> None:
        """Run the bot."""
        try:
            # Build the application
            self.application = (
                Application.builder()
                .token(self.config.bot_token)
                .post_init(self.post_init)
                .build()
            )
            
            # Set up handlers
            self.setup_handlers()
            
            logger.info("Starting bot...")
            
            # Start the bot
            await self.application.initialize()
            await self.application.start()
            await self.application.updater.start_polling(
                allowed_updates=Update.ALL_TYPES,
                drop_pending_updates=True
            )
            
            logger.info("Bot is running. Press Ctrl+C to stop.")
            
            # Keep the bot running and handle shutdown gracefully
            await self.application.updater.idle()
            
        except Exception as e:
            logger.error(f"Fatal error running bot: {e}", exc_info=True)
            raise
        finally:
            if self.application:
                logger.info("Shutting down bot...")
                await self.application.updater.stop()
                await self.application.stop()
                await self.application.shutdown()
                logger.info("Bot shutdown complete")


async def main():
    """Main entry point for the bot."""
    try:
        # Load configuration
        config = Config()
        
        # Create and run bot
        bot = TelegramBot(config)
        await bot.run()
        
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
