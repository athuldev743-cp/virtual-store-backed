import os
import logging
import asyncio
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException

# Load credentials from environment
TWILIO_SID = os.getenv("TWILIO_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_WHATSAPP_NUMBER = os.getenv("TWILIO_WHATSAPP_NUMBER")

# Initialize client only if credentials exist
client = None
if all([TWILIO_SID, TWILIO_AUTH_TOKEN, TWILIO_WHATSAPP_NUMBER]):
    client = Client(TWILIO_SID, TWILIO_AUTH_TOKEN)
else:
    logging.warning("Twilio credentials missing - WhatsApp notifications disabled")

async def send_whatsapp(to: str, message: str, retries: int = 3, delay: int = 5) -> bool:
    """
    Send a WhatsApp message via Twilio with async retry.
    Returns True if successful, False otherwise.

    :param to: Recipient number (e.g., 'whatsapp:+91XXXXXXXXXX')
    :param message: Message text
    :param retries: Number of retries if sending fails
    :param delay: Seconds to wait between retries
    """
    if not to:
        logging.warning("No recipient provided, skipping WhatsApp message.")
        return False

    if not client:
        logging.warning("Twilio client not initialized, skipping WhatsApp message.")
        return False

    # Validate WhatsApp number format
    if not to.startswith('whatsapp:+'):
        logging.warning(f"Invalid WhatsApp number format: {to}. Should be 'whatsapp:+countrycodeNumber'")
        return False

    for attempt in range(1, retries + 1):
        try:
            # Use asyncio.to_thread to make Twilio sync call async
            message_obj = await asyncio.to_thread(
                client.messages.create,
                from_=TWILIO_WHATSAPP_NUMBER,
                body=message,
                to=to
            )
            logging.info(f"WhatsApp message sent to {to} - SID: {message_obj.sid}")
            return True
            
        except TwilioRestException as e:
            logging.error(f"Twilio error (attempt {attempt}/{retries}) for {to}: {e}")
            if attempt < retries:
                logging.info(f"Retrying in {delay} seconds...")
                await asyncio.sleep(delay)
            else:
                logging.error(f"All {retries} attempts failed for {to}")
                return False
                
        except Exception as e:
            logging.error(f"Unexpected error (attempt {attempt}/{retries}) for {to}: {e}")
            if attempt < retries:
                await asyncio.sleep(delay)
            else:
                return False
    
    return False