"""
Initialization Manager - Centralized service initialization
All services are initialized here for better management and consistency.
"""
import os
import logging
import torch
from typing import Optional

from src.shared.config import setting
from src.shared.llm import LLMService, ChatGPT
from src.shared.prompts import PromptService
from src.shared.paths import CHECKPOINTS_OUTPUT_DIR
# DQN is imported lazily to avoid loading torch models when not needed.

logger = logging.getLogger(__name__)


class InitializationManager:
    """
    Centralized initialization manager for all services.
    Handles initialization of LLM, DQN, PromptService, and other components.
    
    Supports shared LLM instances to save GPU memory when running multiple services.
    """
    
    # Class-level shared LLM instance (singleton pattern)
    _shared_llm_service: Optional[LLMService] = None
    _shared_llm_key: Optional[str] = None  # Key to identify shared instance
    
    def __init__(self, 
                 model_name: str = "../models/Llama-3.1-8B",
                 model_type: str = "local",
                 mode: str = "train",
                 ssh_port: int = 2222,
                 use_shared_llm: bool = True):
        """
        Initialize the manager with configuration.
        
        Args:
            model_name: LLM model name or path
            model_type: "local" or "openai"
            mode: "train" or "test"
            ssh_port: SSH server port (default: 2222)
            use_shared_llm: If True, share LLM instance across multiple managers (default: True)
        """
        self.model_name = model_name
        self.model_type = model_type
        self.mode = mode
        self.ssh_port = ssh_port
        self.use_shared_llm = use_shared_llm
        
        # Services (initialized lazily)
        self._llm_service: Optional[LLMService] = None
        self._prompt_service: Optional[PromptService] = None
        self._dqn = None  # Type: Optional[DQN], but DQN is imported lazily
        self._device: Optional[torch.device] = None
        
        # Set mode in setting (will be used when DQN is initialized)
        setting.mode = mode
        
        # Note: We don't call set_mode from ssh_service to avoid circular import
        # The DQN will be initialized with the correct mode when accessed
    
    @property
    def llm_service(self) -> LLMService:
        """Get or initialize LLM service (shared across instances if use_shared_llm=True)"""
        if self._llm_service is None:
            # Check if we should use shared instance
            if self.use_shared_llm:
                llm_key = f"{self.model_name}:{self.model_type}"
                
                # If shared instance exists and matches, use it
                if InitializationManager._shared_llm_service is not None:
                    if InitializationManager._shared_llm_key == llm_key:
                        logger.info("Reusing shared LLM service: %s (%s)", self.model_name, self.model_type)
                        self._llm_service = InitializationManager._shared_llm_service
                        return self._llm_service
                    else:
                        logger.warning(
                            "Shared LLM config differs: expected %s, got %s",
                            llm_key,
                            InitializationManager._shared_llm_key,
                        )
                
                # Create new shared instance
                logger.info("Initializing shared LLM service")
                if self.model_type == "openai":
                    InitializationManager._shared_llm_service = ChatGPT(self.model_name)
                else:
                    InitializationManager._shared_llm_service = LLMService(self.model_name, model_type=self.model_type)
                InitializationManager._shared_llm_key = llm_key
                self._llm_service = InitializationManager._shared_llm_service
                logger.info("Shared LLM service initialized: %s (%s)", self.model_name, self.model_type)
            else:
                # Create instance-specific LLM
                logger.info("Initializing instance-specific LLM service")
                if self.model_type == "openai":
                    self._llm_service = ChatGPT(self.model_name)
                else:
                    self._llm_service = LLMService(self.model_name, model_type=self.model_type)
                logger.info("LLM service initialized: %s (%s)", self.model_name, self.model_type)
        return self._llm_service
    
    @classmethod
    def clear_shared_llm(cls):
        """Clear the shared LLM instance (useful for cleanup)"""
        cls._shared_llm_service = None
        cls._shared_llm_key = None
        logger.info("Shared LLM instance cleared")
    
    @property
    def prompt_service(self) -> PromptService:
        """Get or initialize Prompt service"""
        if self._prompt_service is None:
            logger.info("Initializing prompt service")
            self._prompt_service = PromptService(setting.system)
            logger.info("Prompt service initialized for system: %s", setting.system)
        return self._prompt_service
    
    @property
    def device(self) -> torch.device:
        """Get or initialize device"""
        if self._device is None:
            self._device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
            logger.info("Device initialized: %s", self._device)
        return self._device
    
    @property
    def dqn(self):
        """Get or initialize DQN model"""
        if self._dqn is None:
            # Lazy import to avoid circular import
            from src.rl.dqn import DQN
            logger.info("Initializing DQN model")
            device = self.device
            n_actions = len(setting.action_set)
            n_states = 203
            self._dqn = DQN(device, n_states, n_actions)
            
            # Load model if in test mode
            if self.mode == "test":
                model_path = self._get_model_path()
                if model_path and os.path.exists(model_path):
                    logger.info("Loading DQN model from %s", model_path)
                    self._dqn.load(model_path)
                    setting.epsilon = 0
                    logger.info("DQN model loaded successfully")
                else:
                    logger.warning("Model not found at %s; continuing in train mode", model_path)
                    self.mode = "train"
                    setting.mode = "train"
                    setting.epsilon = 1
            else:
                setting.epsilon = 1
            
            logger.info("DQN model initialized (mode=%s)", self.mode)
        return self._dqn
    
    def _get_model_path(self) -> Optional[str]:
        """Get model path based on system and action"""
        model_file = None
        if setting.system == 'linux' and setting.action == 'Engage':
            model_file = 'model/02-07-04/model_02-07-04_episode_650'
        elif setting.system == 'linux' and setting.action == 'ABSI':
            model_file = 'model/02-17-18/model_02-17-18_episode_468'
        elif setting.system == 'windows' and setting.action == 'Engage':
            model_file = 'model/04-21-14/model_04-21-14_episode_847'
        elif setting.system == 'windows' and setting.action == 'ABSI':
            model_file = 'model/04-18-17/model_04-18-17_episode_722'
        
        if model_file:
            return os.path.join(CHECKPOINTS_OUTPUT_DIR, model_file)
        return None
    
    def initialize_all(self):
        """Initialize all services at once"""
        logger.info("Initializing all services")
        _ = self.llm_service
        _ = self.prompt_service
        _ = self.dqn
        logger.info("All services initialized successfully")
    
    def get_summary(self) -> dict:
        """Get summary of initialized services"""
        return {
            "mode": self.mode,
            "model_name": self.model_name,
            "model_type": self.model_type,
            "ssh_port": self.ssh_port,
            "system": setting.system,
            "action": setting.action,
            "n_actions": len(setting.action_set),
            "device": str(self.device) if self._device else "Not initialized",
            "llm_initialized": self._llm_service is not None,
            "dqn_initialized": self._dqn is not None,
            "prompt_initialized": self._prompt_service is not None,
        }
