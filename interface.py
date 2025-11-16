"""
Gradio UI interface for the Sales Agent

Author: Ben Walker (BenRWalker@icloud.com)
"""

import gradio as gr
import asyncio
from agents import Runner, trace
from sales_manager import careful_sales_manager
from agent_setup import (
    BASE_MODEL1, BASE_MODEL2, BASE_MODEL3,
    sales_agent1, sales_agent2, sales_agent3,
    subject_writer, html_converter, emailer_agent, guardrail_agent
)
from logger_config import setup_logger
import time
import threading

# Set up logger for this module
logger = setup_logger(__name__)

# Global variable to track progress (note: spelling fix)
progress_state = {
    "status": "Ready",
    "progress": 0
}

async def run_sales_agent(message: str) -> str:
    """
    Run the sales manager agent with the given message.
    
    Args:
        message: User input message
        
    Returns:
        Agent response as string
    """
    logger.info(f"Received user request: {message[:100]}...")
    
    try:
        with trace("Protected automated SDR"):
            logger.debug("Start agent execution, hold on to your butts!")
            result = await Runner.run(careful_sales_manager, message)
            logger.info("Agent execution completed successfully. Yippee ki yay!")
            
            # NEW: Add detailed logging
            logger.info(f"Result type: {type(result)}")
            logger.info(f"Result.final_output type: {type(result.final_output)}")
            logger.info(f"Result.final_output content (first 200 chars): {str(result.final_output)[:200]}")
            
            # Convert to string explicitly
            output = str(result.final_output)
            logger.info(f"Converted output length: {len(output)}")
            logger.info(f"Output preview: {output[:200]}")
            
            return output
            
    except Exception as e:
        logger.error(f"OOPS! Error during agent execution: {e}", exc_info=True)
        return f"An error occurred: {str(e)}\n\nPlease check the logs for more details."


def _update_status_during_processing(message: str):
    """
    Process the message and update status throughout.
    Returns tuple of (result, status)
    
    Args:
        message: User input message
        
    Returns:
        Tuple of (email_output, status_message)
    """
    logger.info(f"Received user request: {message[:100]}...")
    
    if not message or message.strip() == "":
        return "", "⚠️ Please enter a request"
    
    try:
        # Show initial status
        initial_status = "⏳ Processing your request...\n" \
                        "This typically takes 1-3 minutes.\n" \
                        "🔄 Running guardrails and generating email..."
        
        # Run the agent (this will take time)
        result = asyncio.run(run_sales_agent(message))
        
        # Success status
        final_status = "✅ Complete! Email generated successfully."
        
        return result, final_status
        
    except Exception as e:
        error_msg = f"Error running agent: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return f"❌ {error_msg}", f"❌ Failed: {str(e)[:50]}..."


def _safe_agent_callback_with_progress(message: str):
    """Run agent with real-time progress updates"""
    logger.info(f"Received user request: {message[:100]}...")
    
    if not message or message.strip() == "":
        return "", "⚠️ Please enter a request"
    
    try:
        # Reset progress
        progress_state["status"] = "⏳ Starting..."
        progress_state["progress"] = 10
        
        # Run the agent in a separate thread so we can update progress
        result_container = []
        error_container = []
        
        def run_agent_thread():
            try:
                result = asyncio.run(run_sales_agent(message))
                result_container.append(result)
            except Exception as e:
                error_container.append(e)
        
        # Start agent in background
        thread = threading.Thread(target=run_agent_thread)
        thread.start()
        
        # Simulate progress updates (since we can't track actual agent progress)
        steps = [
            (20, "🛡️ Running input guardrails..."),
            (35, "📝 Sales agent writing email..."),
            (60, "✍️ Creating subject line..."),
            (75, "🎨 Converting to HTML..."),
            (90, "🛡️ Running output guardrails..."),
        ]
        
        for progress, status in steps:
            if not thread.is_alive():
                break
            progress_state["status"] = status
            progress_state["progress"] = progress
            time.sleep(15)  # Wait 15 seconds between updates
        
        # Wait for completion
        thread.join(timeout=180)  # 3 minute timeout
        
        if error_container:
            raise error_container[0]
        
        if result_container:
            return result_container[0], "✅ Complete! Email generated successfully."
        else:
            return "⏱️ Request timed out after 3 minutes", "❌ Timeout"
            
    except Exception as e:
        error_msg = f"Error running agent: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return f"❌ {error_msg}", f"❌ Failed"


def _safe_clear_callback():
    """Clear input, output, and send status boxes"""
    logger.info("Clear button clicked")
    return "", "", "", ""  # ✅ FIXED: Now returns 4 values


def clear_cache_and_ui():
    """
    Clear LLM cache and reset UI components.
    
    Returns:
        Tuple of empty strings for input and output textboxes
    """
    logger.info("Clearing model and agent caches...")
    cleared_count = 0
    
    # Clear model caches if they have cache methods
    models = [BASE_MODEL1, BASE_MODEL2, BASE_MODEL3]
    for model in models:
        try:
            # Clear cache if the model has a cache attribute
            if hasattr(model, 'cache'):
                model.cache = {}
                cleared_count += 1
            
            # Some models might have a clear_cache method
            if hasattr(model, 'clear_cache'):
                model.clear_cache()
                cleared_count += 1
        except Exception as e:
            logger.warning(f"Oh No! Error clearing cache for model {model}: {e}", exc_info=True)
    
    # Clear agent caches
    agents = [
        sales_agent1, sales_agent2, sales_agent3,
        subject_writer, html_converter, emailer_agent, guardrail_agent
    ]
    for agent in agents:
        try:
            if hasattr(agent, 'cache'):
                agent.cache = {}
                cleared_count += 1
            if hasattr(agent, 'clear_cache'):
                agent.clear_cache()
                cleared_count += 1
        except Exception as e:
            logger.warning(f"Error clearing cache for agent {agent.name}: {e}")
    
    logger.info(f"Successfully cleared {cleared_count} caches")
    
    # Return empty strings to clear the UI components
    return "", ""


def _safe_send_email_callback(email_draft: str) -> str:
    """
    Safely send an email with error handling.
    Wrapper for the async send_approved_email function.
    
    Args:
        email_draft: The generated email text to send
        
    Returns:
        Status message string
    """
    logger.info("Send email button clicked")
    
    # Check if there's content to send
    if not email_draft or email_draft.strip() == "":
        logger.warning("Attempted to send empty email")
        return "⚠️ No email to send. Please generate an email first."
    
    try:
        # Run the async send function
        result = asyncio.run(send_approved_email(email_draft))
        return result
    except Exception as e:
        error_msg = f"Error in send callback: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return f"❌ {error_msg}"


async def send_approved_email(email_draft: str) -> str:
    """
    Send an email that the user has approved.
    Parses the draft and sends it via SendGrid.
    
    Args:
        email_draft: The complete email text including subject
        
    Returns:
        Success/failure message string
    """
    logger.info("Processing approved email for sending...")
    
    try:
        # Import here to avoid circular dependency
        from email_service import send_html_email
        
        # Parse the draft to extract subject and body
        lines = email_draft.split('\n')
        subject = "Sales Email"  # Default subject
        html_body = email_draft
        
        # Try to find "Subject:" or "Subject Line:" in the draft
        for i, line in enumerate(lines):
            if 'subject' in line.lower() and ':' in line:
                # Extract everything after the colon
                subject = line.split(':', 1)[1].strip()
                # Remove subject line from body
                html_body = '\n'.join(lines[i+1:]).strip()
                logger.debug(f"Extracted subject: {subject}")
                break
        
        # Convert plain text to basic HTML if needed
        if not html_body.startswith('<'):
            # Simple conversion: paragraphs separated by double newlines
            paragraphs = html_body.split('\n\n')
            html_body = ''.join(f'<p>{p.strip()}</p>' for p in paragraphs if p.strip())
            logger.debug("Converted plain text to HTML")
        
        # Send the email
        logger.info(f"Sending email with subject: {subject}")
        result = await send_html_email(subject, html_body)
        
        if result['status'] == 'success':
            success_msg = f"✅ Email sent successfully!\n📧 To: {result.get('to', 'recipient')}\n📋 Status Code: {result['status_code']}"
            logger.info(success_msg)
            return success_msg
        else:
            error_msg = f"❌ Failed to send email: {result['message']}"
            logger.error(error_msg)
            return error_msg
            
    except Exception as e:
        error_msg = f"Error sending email: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return f"❌ {error_msg}"


def launch_interface():
    """
    Launch the gradio interface with Blocks API for more control
    """
    
    logger.info("Launching Gradio interface")

    with gr.Blocks(title="Sales Agent") as interface:
        gr.Markdown("# Sales Agent")
        gr.Markdown("An AI-powered sales agent that crafts and sends cold sales emails.")
        
        with gr.Row():
            with gr.Column():
                input_textbox = gr.Textbox(
                    lines=3,
                    placeholder="Enter your sales request here...",
                    label="Sales Request"
                )
                
                # Status display
                status_box = gr.Textbox(
                    label="⚙️ Processing Status",
                    placeholder="Ready to process your request...",
                    interactive=False,
                    lines=2
                )
                
                with gr.Row():
                    submit_btn = gr.Button("Generate Email", variant="primary")
                    clear_btn = gr.Button("Clear", variant="secondary")
            
            with gr.Column():
                output_textbox = gr.Textbox(
                    label="Agent Response",
                    lines=10
                )
        
        # Email sending section
        gr.Markdown("---")
        gr.Markdown("### 📧 Email Sending")
        
        with gr.Row():
            with gr.Column(scale=3):
                send_status = gr.Textbox(
                    label="Send Status",
                    placeholder="Generate an email first, then click 'Send Email' to deliver it",
                    interactive=False,
                    lines=2
                )
            with gr.Column(scale=1):
                send_btn = gr.Button("📧 Send Email", variant="secondary", size="lg")
        
        # Examples section
        gr.Examples(
            examples=[
                "Send a cold sales email to introduce our new product to potential clients.",
                "Create a witty cold email about our SOC2 compliance tool",
                "Write a concise sales email for busy executives"
            ],
            inputs=input_textbox,
            outputs=output_textbox,
            fn=_update_status_during_processing,  # ✅ FIXED: Now references correct function
            cache_examples=False
        )
        
        # Connect submit button - with status updates
        submit_btn.click(
            fn=_update_status_during_processing,  # ✅ FIXED: Correct function
            inputs=input_textbox,
            outputs=[output_textbox, status_box]
        )
        
        # Connect send email button
        send_btn.click(
            fn=_safe_send_email_callback,
            inputs=output_textbox,
            outputs=send_status
        )
        
        # Connect clear button
        clear_btn.click(
            fn=_safe_clear_callback,
            inputs=None,
            outputs=[input_textbox, output_textbox, send_status, status_box]  # ✅ FIXED: 4 outputs
        )
        
        # Also allow Enter key to submit
        input_textbox.submit(
            fn=_update_status_during_processing,  # ✅ FIXED: Correct function
            inputs=input_textbox,
            outputs=[output_textbox, status_box]
        )
    
    logger.info("Gradio interface ready")
    return interface


if __name__ == "__main__":
    logger.info("Starting Sales Agent application")
    interface = launch_interface()
    interface.launch()
