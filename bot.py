#!/usr/bin/env python3
"""
ColliCasa Access Control Telegram Bot

A Telegram bot that integrates with the ColliCasa access-control backend API.
"""

import asyncio
import json
import logging
import os
import sys
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any

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
        # NOTE: Tokens are stored in memory for simplicity. In a production environment
        # with multiple bot instances, consider using a secure distributed cache (Redis, etc.)
        # or database for token storage with encryption.
        self.user_tokens: Dict[int, Dict[str, Any]] = {}  # Store user JWT tokens
    
    def _get_headers(self, user_token: Optional[str] = None) -> dict:
        """
        Get headers for API requests.
        
        Args:
            user_token: Optional JWT token for authenticated user requests
        
        Returns:
            Dictionary of headers
        """
        headers = {
            'Content-Type': 'application/json',
            'X-Tenant-ID': self.tenant_id
        }
        
        if user_token:
            headers['Authorization'] = f'Bearer {user_token}'
        else:
            headers['Authorization'] = f'Bearer {self.service_token}'
        
        return headers
    
    async def verify_telegram_user(self, telegram_id: int) -> Optional[Dict[str, Any]]:
        """
        Verify a Telegram user and get their JWT token.
        
        Args:
            telegram_id: The Telegram user ID
        
        Returns:
            Dictionary with token and user info, or None if verification fails
        """
        try:
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: requests.post(
                    f"{self.base_url}/api/v1/auth/verify/telegram",
                    headers=self._get_headers(),
                    json={"telegram_id": str(telegram_id)},
                    timeout=self.timeout
                )
            )
            
            if response.status_code == 200:
                data = response.json()
                logger.info(f"User {telegram_id} verified successfully")
                return data
            else:
                logger.warning(f"User verification failed with status {response.status_code}: {response.text}")
                return None
                
        except requests.exceptions.Timeout:
            logger.error("User verification request timed out")
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"User verification request failed: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error during user verification: {e}")
            return None
    
    def get_user_token(self, telegram_id: int) -> Optional[str]:
        """
        Get the stored JWT token for a user.
        
        Args:
            telegram_id: The Telegram user ID
        
        Returns:
            JWT token string or None if not found or expired
        """
        user_data = self.user_tokens.get(telegram_id)
        if user_data:
            # Check if token is expired (using UTC time)
            expires_at = user_data.get('expires_at')
            if expires_at and datetime.fromisoformat(expires_at) > datetime.now(timezone.utc):
                return user_data.get('token')
            else:
                # Token expired, remove it
                logger.info(f"Token for user {telegram_id} has expired")
                del self.user_tokens[telegram_id]
        return None
    
    def store_user_token(self, telegram_id: int, token_data: Dict[str, Any]) -> None:
        """
        Store a user's JWT token.
        
        Args:
            telegram_id: The Telegram user ID
            token_data: Token data from verification response
        """
        # Use 7 days default expiration (UTC time)
        # TODO: Extract actual expiration from JWT token if available
        expires_at = datetime.now(timezone.utc) + timedelta(days=7)
        
        self.user_tokens[telegram_id] = {
            'token': token_data.get('access_token'),
            'expires_at': expires_at.isoformat(),
            'resident_id': token_data.get('resident_id'),
            'permissions': token_data.get('permissions', [])
        }
        logger.info(f"Stored token for user {telegram_id}, expires at {expires_at}")
    
    async def open_pedestrian_gate(self, telegram_id: int) -> Dict[str, Any]:
        """
        Open the pedestrian gate.
        
        Args:
            telegram_id: The Telegram user ID making the request
        
        Returns:
            Response data from the API
        """
        token = self.get_user_token(telegram_id)
        if not token:
            return {'success': False, 'error': 'User not authenticated'}
        
        try:
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: requests.post(
                    f"{self.base_url}/api/v1/gate/sip/open/pedestrian",
                    headers=self._get_headers(token),
                    timeout=self.timeout
                )
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                return {'success': False, 'error': f'API returned status {response.status_code}', 'details': response.text}
                
        except requests.exceptions.Timeout:
            return {'success': False, 'error': 'Request timed out'}
        except requests.exceptions.RequestException as e:
            return {'success': False, 'error': f'Request failed: {str(e)}'}
        except Exception as e:
            return {'success': False, 'error': f'Unexpected error: {str(e)}'}
    
    async def open_visits_gate(self, telegram_id: int) -> Dict[str, Any]:
        """
        Open the visits gate.
        
        Args:
            telegram_id: The Telegram user ID making the request
        
        Returns:
            Response data from the API
        """
        token = self.get_user_token(telegram_id)
        if not token:
            return {'success': False, 'error': 'User not authenticated'}
        
        try:
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: requests.post(
                    f"{self.base_url}/api/v1/gate/sip/open/visits",
                    headers=self._get_headers(token),
                    timeout=self.timeout
                )
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                return {'success': False, 'error': f'API returned status {response.status_code}', 'details': response.text}
                
        except requests.exceptions.Timeout:
            return {'success': False, 'error': 'Request timed out'}
        except requests.exceptions.RequestException as e:
            return {'success': False, 'error': f'Request failed: {str(e)}'}
        except Exception as e:
            return {'success': False, 'error': f'Unexpected error: {str(e)}'}
    
    async def get_camera_snapshot(self, telegram_id: int, camera_type: str) -> Dict[str, Any]:
        """
        Get a camera snapshot.
        
        Args:
            telegram_id: The Telegram user ID making the request
            camera_type: Type of camera ('pedestrian', 'visits', 'front_door')
        
        Returns:
            Response data with image bytes or error
        """
        token = self.get_user_token(telegram_id)
        if not token:
            return {'success': False, 'error': 'User not authenticated'}
        
        try:
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: requests.get(
                    f"{self.base_url}/api/v1/camera/snapshot/{camera_type}",
                    headers=self._get_headers(token),
                    timeout=self.timeout
                )
            )
            
            if response.status_code == 200:
                return {'success': True, 'image_data': response.content}
            else:
                return {'success': False, 'error': f'API returned status {response.status_code}', 'details': response.text}
                
        except requests.exceptions.Timeout:
            return {'success': False, 'error': 'Request timed out'}
        except requests.exceptions.RequestException as e:
            return {'success': False, 'error': f'Request failed: {str(e)}'}
        except Exception as e:
            return {'success': False, 'error': f'Unexpected error: {str(e)}'}
    
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
            
            # Try to authenticate the user
            token_data = await self.api_client.verify_telegram_user(user.id)
            
            if token_data and token_data.get('access_token'):
                self.api_client.store_user_token(user.id, token_data)
                
                welcome_message = (
                    f"👋 Welcome to ColliCasa Access Control Bot!\n\n"
                    f"Hi {user.first_name}! You've been successfully authenticated.\n\n"
                    f"📋 Available Commands:\n"
                    f"/start - Show this help message\n"
                    f"/open_pedestrian - Open the pedestrian gate\n"
                    f"/open_visits - Open the visits gate\n"
                    f"/snapshot_pedestrian - Get pedestrian camera snapshot\n"
                    f"/snapshot_visits - Get visits camera snapshot\n"
                    f"/snapshot_front_door - Get front door camera snapshot (admin only)\n\n"
                    f"🔧 Status: ✅ Authenticated\n"
                    f"Tenant ID: {self.config.tenant_id}"
                )
            else:
                welcome_message = (
                    f"👋 Welcome to ColliCasa Access Control Bot!\n\n"
                    f"Hi {user.first_name}!\n\n"
                    f"⚠️ You are not registered in the system.\n"
                    f"Please contact your administrator to register your Telegram account.\n\n"
                    f"Your Telegram ID: {user.id}"
                )
            
            await update.message.reply_text(welcome_message)
            
        except Exception as e:
            logger.error(f"Error in start_command: {e}", exc_info=True)
            await self._send_error_message(update, "Sorry, an error occurred while processing your request.")
    
    async def open_pedestrian_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Handle the /open_pedestrian command.
        
        Args:
            update: Telegram update object
            context: Telegram context object
        """
        try:
            user = update.effective_user
            logger.info(f"User {user.id} requested to open pedestrian gate")
            
            # Check authentication
            if not self.api_client.get_user_token(user.id):
                await update.message.reply_text(
                    "❌ You are not authenticated. Please use /start to authenticate first."
                )
                return
            
            await update.message.reply_text("🔄 Opening pedestrian gate...")
            
            result = await self.api_client.open_pedestrian_gate(user.id)
            
            if result.get('success'):
                await update.message.reply_text(
                    "✅ Pedestrian gate opened successfully!"
                )
            else:
                error_msg = result.get('error', 'Unknown error')
                if 'permission' in error_msg.lower() or 'forbidden' in error_msg.lower():
                    await update.message.reply_text(
                        "❌ You don't have permission to open the pedestrian gate.\n"
                        "Please contact your administrator."
                    )
                else:
                    await update.message.reply_text(
                        f"❌ Failed to open pedestrian gate: {error_msg}"
                    )
            
        except Exception as e:
            logger.error(f"Error in open_pedestrian_command: {e}", exc_info=True)
            await self._send_error_message(update, "Sorry, an error occurred while processing your request.")
    
    async def open_visits_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Handle the /open_visits command.
        
        Args:
            update: Telegram update object
            context: Telegram context object
        """
        try:
            user = update.effective_user
            logger.info(f"User {user.id} requested to open visits gate")
            
            # Check authentication
            if not self.api_client.get_user_token(user.id):
                await update.message.reply_text(
                    "❌ You are not authenticated. Please use /start to authenticate first."
                )
                return
            
            await update.message.reply_text("🔄 Opening visits gate...")
            
            result = await self.api_client.open_visits_gate(user.id)
            
            if result.get('success'):
                await update.message.reply_text(
                    "✅ Visits gate opened successfully!"
                )
            else:
                error_msg = result.get('error', 'Unknown error')
                if 'permission' in error_msg.lower() or 'forbidden' in error_msg.lower():
                    await update.message.reply_text(
                        "❌ You don't have permission to open the visits gate.\n"
                        "Please contact your administrator."
                    )
                else:
                    await update.message.reply_text(
                        f"❌ Failed to open visits gate: {error_msg}"
                    )
            
        except Exception as e:
            logger.error(f"Error in open_visits_command: {e}", exc_info=True)
            await self._send_error_message(update, "Sorry, an error occurred while processing your request.")
    
    async def snapshot_pedestrian_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Handle the /snapshot_pedestrian command.
        
        Args:
            update: Telegram update object
            context: Telegram context object
        """
        try:
            user = update.effective_user
            logger.info(f"User {user.id} requested pedestrian camera snapshot")
            
            # Check authentication
            if not self.api_client.get_user_token(user.id):
                await update.message.reply_text(
                    "❌ You are not authenticated. Please use /start to authenticate first."
                )
                return
            
            await update.message.reply_text("📷 Capturing pedestrian camera snapshot...")
            
            result = await self.api_client.get_camera_snapshot(user.id, 'pedestrian')
            
            if result.get('success'):
                # Send the image
                await update.message.reply_photo(
                    photo=result.get('image_data'),
                    caption="📸 Pedestrian camera snapshot"
                )
            else:
                error_msg = result.get('error', 'Unknown error')
                if 'permission' in error_msg.lower() or 'forbidden' in error_msg.lower():
                    await update.message.reply_text(
                        "❌ You don't have permission to view the pedestrian camera.\n"
                        "Please contact your administrator."
                    )
                else:
                    await update.message.reply_text(
                        f"❌ Failed to get camera snapshot: {error_msg}"
                    )
            
        except Exception as e:
            logger.error(f"Error in snapshot_pedestrian_command: {e}", exc_info=True)
            await self._send_error_message(update, "Sorry, an error occurred while processing your request.")
    
    async def snapshot_visits_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Handle the /snapshot_visits command.
        
        Args:
            update: Telegram update object
            context: Telegram context object
        """
        try:
            user = update.effective_user
            logger.info(f"User {user.id} requested visits camera snapshot")
            
            # Check authentication
            if not self.api_client.get_user_token(user.id):
                await update.message.reply_text(
                    "❌ You are not authenticated. Please use /start to authenticate first."
                )
                return
            
            await update.message.reply_text("📷 Capturing visits camera snapshot...")
            
            result = await self.api_client.get_camera_snapshot(user.id, 'visits')
            
            if result.get('success'):
                # Send the image
                await update.message.reply_photo(
                    photo=result.get('image_data'),
                    caption="📸 Visits camera snapshot"
                )
            else:
                error_msg = result.get('error', 'Unknown error')
                if 'permission' in error_msg.lower() or 'forbidden' in error_msg.lower():
                    await update.message.reply_text(
                        "❌ You don't have permission to view the visits camera.\n"
                        "Please contact your administrator."
                    )
                else:
                    await update.message.reply_text(
                        f"❌ Failed to get camera snapshot: {error_msg}"
                    )
            
        except Exception as e:
            logger.error(f"Error in snapshot_visits_command: {e}", exc_info=True)
            await self._send_error_message(update, "Sorry, an error occurred while processing your request.")
    
    async def snapshot_front_door_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Handle the /snapshot_front_door command.
        
        Args:
            update: Telegram update object
            context: Telegram context object
        """
        try:
            user = update.effective_user
            logger.info(f"User {user.id} requested front door camera snapshot")
            
            # Check authentication
            if not self.api_client.get_user_token(user.id):
                await update.message.reply_text(
                    "❌ You are not authenticated. Please use /start to authenticate first."
                )
                return
            
            await update.message.reply_text("📷 Capturing front door camera snapshot...")
            
            result = await self.api_client.get_camera_snapshot(user.id, 'front_door')
            
            if result.get('success'):
                # Send the image
                await update.message.reply_photo(
                    photo=result.get('image_data'),
                    caption="📸 Front door camera snapshot"
                )
            else:
                error_msg = result.get('error', 'Unknown error')
                if 'permission' in error_msg.lower() or 'forbidden' in error_msg.lower():
                    await update.message.reply_text(
                        "❌ You don't have permission to view the front door camera.\n"
                        "This camera is restricted to administrators only."
                    )
                else:
                    await update.message.reply_text(
                        f"❌ Failed to get camera snapshot: {error_msg}"
                    )
            
        except Exception as e:
            logger.error(f"Error in snapshot_front_door_command: {e}", exc_info=True)
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
        self.application.add_handler(CommandHandler("open_pedestrian", self.open_pedestrian_command))
        self.application.add_handler(CommandHandler("open_visits", self.open_visits_command))
        self.application.add_handler(CommandHandler("snapshot_pedestrian", self.snapshot_pedestrian_command))
        self.application.add_handler(CommandHandler("snapshot_visits", self.snapshot_visits_command))
        self.application.add_handler(CommandHandler("snapshot_front_door", self.snapshot_front_door_command))
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
