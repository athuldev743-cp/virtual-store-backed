# app/utils/twilio_utils.py
import os
import logging
import asyncio
from twilio.rest import Client

# -------------------------
# Load credentials from environment
# -------------------------
TWILIO_SID = os.getenv("TWILIO_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_WHATSAPP_NUMBER = os.getenv("TWILIO_WHATSAPP_NUMBER")
TWILIO_WHATSAPP_ADMIN = os.getenv("TWILIO_WHATSAPP_NUMBER_ADMIN")  # optional admin

# Initialize Twilio client
client = Client(TWILIO_SID, TWILIO_AUTH_TOKEN)

# -------------------------
# WhatsApp Sending Utility
# -------------------------
async def send_whatsapp(to: str, message: str, retries: int = 3, delay: int = 5) -> bool:
    """
    Send a WhatsApp message via Twilio with async retry.

    :param to: Recipient number (e.g., 'whatsapp:+91XXXXXXXXXX')
    :param message: Message text
    :param retries: Number of retries if sending fails
    :param delay: Seconds to wait between retries
    :return: True if sent successfully, False if all retries fail
    """
    if not to:
        logging.warning("No recipient provided, skipping WhatsApp message.")
        return False

    if not all([TWILIO_SID, TWILIO_AUTH_TOKEN, TWILIO_WHATSAPP_NUMBER]):
        logging.warning("Twilio credentials missing, skipping WhatsApp message.")
        return False

    for attempt in range(1, retries + 1):
        try:
            # Run blocking Twilio call in separate thread
            await asyncio.to_thread(
                client.messages.create,
                from_=TWILIO_WHATSAPP_NUMBER,
                body=message,
                to=to
            )
            logging.info(f"WhatsApp message sent to {to}")
            return True
        except Exception as e:
            logging.error(f"Attempt {attempt} failed to send WhatsApp: {e}")
            if attempt < retries:
                logging.info(f"Retrying in {delay} seconds...")
                await asyncio.sleep(delay)
            else:
                logging.error(f"All {retries} attempts failed for {to}")
    return False


# -------------------------
# Optional Admin Notification Helper
# -------------------------
async def notify_admin(message: str):
    """
    Send a WhatsApp message to the admin if the number is configured.
    """
    if TWILIO_WHATSAPP_ADMIN:
        success = await send_whatsapp(TWILIO_WHATSAPP_ADMIN, message)
        if not success:
            logging.warning("Failed to notify admin via WhatsApp")
