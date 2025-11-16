"""
Email sending functionality using SendGrid.

Author : Ben Walker (BenRWalker@icloud.com)
"""

# Modules
import asyncio
import os
from typing import Dict, Optional

import sendgrid
from dotenv import load_dotenv
from sendgrid.helpers.mail import Content, Email, Mail, To

from agents import function_tool
from logger_config import setup_logger

# Set up logger for this module
logger = setup_logger(__name__)

# Load environment variables
load_dotenv()

# Get email configuration from environment
from_email: Optional[str] = os.environ.get('FROM_EMAIL')
to_email: Optional[str] = os.environ.get('TO_EMAIL')

logger.info(f"Email service configured - From: {from_email}, To: {to_email}")

@function_tool
async def send_html_email(subject: str, html_body: str) -> Dict[str, str]:
    """Send an email with the given subject and HTML body to all sales prospects."""
    logger.info(f"Attempting to send email with subject: {subject}")
    logger.debug(f"Email body length: {len(html_body)} characters")
    
    sendgrid_api_key = os.environ.get('SENDGRID')
    if not sendgrid_api_key:
        logger.error("SENDGRID API key not found in environment variables")
        return {"status": "error", "message": "SENDGRID API key not found in environment variables"}
    
    if not from_email or not to_email:
        logger.error("FROM_EMAIL or TO_EMAIL not configured")
        return {"status": "error", "message": "FROM_EMAIL or TO_EMAIL not configured"}
    
    def _send_email_request() -> int:
        sg = sendgrid.SendGridAPIClient(api_key=sendgrid_api_key)
        from_email_obj = Email(from_email)
        to_email_obj = To(to_email)
        content = Content("text/html", html_body)
        mail = Mail(from_email_obj, to_email_obj, subject, content)
        response = sg.client.mail.send.post(request_body=mail.get())
        return response.status_code
    
    try:
        status_code = await asyncio.to_thread(_send_email_request)
        logger.info(
            "Email sent successfully",
            extra={
                'subject': subject,
                'status_code': status_code,
                'to': to_email
            }
        )
        return {
            "status": "success",
            "status_code": status_code
        }
    except Exception as e:
        logger.error(
            f"Failed to send email: {e}",
            exc_info=True,
            extra={
                'subject': subject,
                'to': to_email
            }
        )
        return {
            "status": "error",
            "message": str(e)
        }
