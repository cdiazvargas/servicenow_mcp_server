"""Main entry point for ServiceNow Knowledge MCP Server."""

import asyncio
import signal
import sys
from typing import Optional

import structlog

from .config import load_settings, setup_logging
from .server import ServiceNowMCPServer

logger = structlog.get_logger(__name__)


class ServiceManager:
    """Manages the ServiceNow MCP Server lifecycle."""
    
    def __init__(self):
        self.server: Optional[ServiceNowMCPServer] = None
        self._shutdown_event = asyncio.Event()
    
    def signal_handler(self, signum: int, frame) -> None:
        """Handle shutdown signals."""
        logger.info("Received shutdown signal", signal=signum)
        self._shutdown_event.set()
    
    async def run(self) -> None:
        """Run the server with proper lifecycle management."""
        try:
            # Setup early logging to stderr for MCP compliance
            # This must happen before any other logging occurs
            import logging
            import sys
            logging.basicConfig(
                level=logging.INFO,
                stream=sys.stderr,
                format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            
            # Configure structlog early with stderr output
            import structlog
            
            class EarlyStderrLoggerFactory:
                def __call__(self, name: str = None):
                    return structlog.PrintLogger(file=sys.stderr)
            
            structlog.configure(
                processors=[
                    structlog.processors.TimeStamper(fmt="iso"),
                    structlog.processors.add_log_level,
                    structlog.dev.ConsoleRenderer()
                ],
                wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
                logger_factory=EarlyStderrLoggerFactory(),
                cache_logger_on_first_use=True,
            )
            
            # Load configuration (this loads .env file via Pydantic)
            settings = load_settings()
            
            # Note: validate_required_env_vars() is redundant since Pydantic 
            # handles validation during settings loading above
            
            # Setup final logging configuration
            setup_logging(settings)
            
            logger.info(
                "Starting ServiceNow Knowledge MCP Server",
                version="1.0.0",
                instance_url=settings.servicenow_instance_url,
                auth_method=settings.auth_method.value,
                log_level=settings.log_level.value
            )
            
            # Create and configure server
            servicenow_config = settings.to_servicenow_config()
            self.server = ServiceNowMCPServer(servicenow_config)
            
            # Setup signal handlers for graceful shutdown
            if sys.platform != "win32":
                loop = asyncio.get_event_loop()
                for sig in (signal.SIGTERM, signal.SIGINT):
                    loop.add_signal_handler(
                        sig, 
                        lambda s=sig: self.signal_handler(s, None)
                    )
            
            # Run server with shutdown handling
            server_task = asyncio.create_task(self.server.run())
            shutdown_task = asyncio.create_task(self._shutdown_event.wait())
            
            # Wait for either server completion or shutdown signal
            done, pending = await asyncio.wait(
                [server_task, shutdown_task],
                return_when=asyncio.FIRST_COMPLETED
            )
            
            # Cancel remaining tasks
            for task in pending:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
            
            # Check if server task completed with exception
            if server_task in done:
                try:
                    await server_task
                except Exception as e:
                    logger.error("Server task failed", error=str(e))
                    raise
            
            logger.info("ServiceNow Knowledge MCP Server shutdown complete")
            
        except KeyboardInterrupt:
            logger.info("Received keyboard interrupt")
        except Exception as e:
            logger.error("Fatal error", error=str(e))
            sys.exit(1)
        finally:
            if self.server:
                await self.server.stop_background_tasks()


def main() -> None:
    """Main entry point."""
    try:
        service_manager = ServiceManager()
        
        if sys.platform == "win32":
            # Use ProactorEventLoop on Windows for better signal handling
            asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
        
        asyncio.run(service_manager.run())
        
    except KeyboardInterrupt:
        print("\nShutdown requested by user")
        sys.exit(0)
    except Exception as e:
        print(f"Fatal error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
