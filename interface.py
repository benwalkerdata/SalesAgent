"""
Gradio UI interface for the Sales Agent

Author: Ben Walker (BenRWalker@icloud.com)
"""

import gradio as gr
import asyncio
from agents import Runner, trace
from sales_manager import careful_sales_manager
from agent_setup import (
    BASE_MODEL1, 
    BASE_MODEL2, 
    BASE_MODEL3,
    sales_agent1,
    sales_agent2,
    sales_agent3,
    subject_writer,
    html_converter,
    emailer_agent,
    guardrail_agent
)
from logger_config import setup_logger


# Set up logger for this module
logger = setup_logger(__name__)

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
            logger.debug(f"Result type: {type(result.final_output)}")
            return str(result.final_output)
    except Exception as e:
        logger.error(f"OOPS! Error during agent execution: {e}", exc_info=True)
        return f"An error occurred: {str(e)}\n\nPlease check the logs for more details."

def clear_cache_and_ui():
    """
    Clear LLM cache and reset UI components.
    
    Returns:
        Tuple of empty strings for input and output textboxes
    """
    logger.info("Clearing model and agent caches...")
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
        sales_agent1, 
        sales_agent2, 
        sales_agent3,
        subject_writer,
        html_converter,
        emailer_agent,
        guardrail_agent
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
                
                with gr.Row():
                    submit_btn = gr.Button("Submit", variant="primary")
                    clear_btn = gr.Button("Clear", variant="secondary")
            
            with gr.Column():
                output_textbox = gr.Textbox(
                    label="Agent Response",
                    lines=10
                )
        
        # Examples section - moved outside columns and properly configured
        gr.Examples(
            examples=[
                "Send a cold sales email to introduce our new product to potential clients.",
                "Create a witty cold email about our SOC2 compliance tool",
                "Write a concise sales email for busy executives"
            ],
            inputs=input_textbox,
            outputs=output_textbox,
            fn=lambda msg: asyncio.run(run_sales_agent(msg)),
            cache_examples=False  # Important: disable caching to avoid the error
        )
        
        # Connect submit button
        submit_btn.click(
            fn=lambda msg: asyncio.run(run_sales_agent(msg)),
            inputs=input_textbox,
            outputs=output_textbox
        )
        
        # Connect clear button
        clear_btn.click(
            fn=clear_cache_and_ui,
            inputs=None,
            outputs=[input_textbox, output_textbox]
        )
        
        # Also allow Enter key to submit
        input_textbox.submit(
            fn=lambda msg: asyncio.run(run_sales_agent(msg)),
            inputs=input_textbox,
            outputs=output_textbox
        )
    logger.info("Gradio interface ready")
    return interface

if __name__ == "__main__":
    logger.info("Starting Sales Agent application")
    interface = launch_interface()
    interface.launch()
