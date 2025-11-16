"""
Main entry point for the Company Name Sales Agent Application.

Author: Ben Walker (BenRWalker@icloud.com)
"""
import asyncio
from config import setup_env
from agents import Runner, trace
from sales_manager import careful_sales_manager
from logger_config import setup_logger

# Set up logger for main module
logger = setup_logger(__name__)

async def main():
    """
    Main execution function
    """
    logger.info("=" * 60)
    logger.info("Starting Sales Agent Application")
    logger.info("=" * 60)
    
    setup_env()
    
    # Example message
    message = "Send out a cold sales email address to Dear CEO from Alice"
    logger.info(f"Processing message: {message}")
    
    try:
        # Run the Sales Manager Agent
        with trace("Protect Automated SDR"):
            logger.debug("Initializing agent runner")
            result = await Runner.run(careful_sales_manager, message)
            
            logger.info("Agent execution completed successfully")
            logger.debug(f"Final output type: {type(result.final_output)}")
            
            return result
    except Exception as e:
        logger.error(f"Error in main execution: {e}", exc_info=True)
        raise

if __name__ == "__main__":
    try:
        # Run the async function
        result = asyncio.run(main())
        print("Final Output:", result.final_output)
        logger.info("Application finished successfully")
    except KeyboardInterrupt:
        logger.warning("Application interrupted by user")
    except Exception as e:
        logger.critical(f"Application crashed: {e}", exc_info=True)
        raise