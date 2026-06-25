import logging

from src.shared.paths import PROMPTS_DIR

logger = logging.getLogger(__name__)


class PromptService:
    """
    Service for loading and managing prompts.
    System type is set during initialization.
    """
    
    def __init__(self, system='linux'):
        """
        Initialize prompt service.
        
        Args:
            system: 'linux' or 'windows'
        """
        self.system = system
    
    def get_prompt(self, prompt_name):
        """
        Read a prompt file from the prompts/ directory.
        
        Args:
            prompt_name: Name of the prompt file (e.g., 'honeypot', 'detector', 'attacker')
                        Can include subdirectory or extension (e.g., 'honeypot_windows.txt')
        
        Returns:
            str: Content of the prompt file, or empty string if file not found
        """
        # Remove .txt extension if present
        if prompt_name.endswith('.txt'):
            prompt_name = prompt_name[:-4]
        
        # Try to find the file
        file_path = PROMPTS_DIR / f"{prompt_name}.txt"
        
        if not file_path.exists():
            logger.warning("Prompt file not found: %s", file_path)
            return ""
        
        try:
            return file_path.read_text(encoding="utf-8").strip()
        except OSError:
            logger.exception("Failed to read prompt file: %s", file_path)
            return ""
    
    def get_honeypot_prompt(self):
        """
        Get the honeypot system prompt based on the system type set in __init__.
        
        Returns:
            str: The honeypot prompt
        """
        if self.system == 'windows':
            return self.get_prompt('honeypot_windows')
        else:
            return self.get_prompt('honeypot_linux')
    
    def get_detector_prompt(self):
        """
        Get the honeypot detector prompt.
        
        Returns:
            str: The detector prompt
        """
        return self.get_prompt('detector')
    
    def get_detector_state_prompt(self):
        """
        Get the state detector prompt for MITRE tactic/technique detection.
        
        Returns:
            str: The state detector prompt
        """
        return self.get_prompt('detector_state')
    
    def get_attacker_prompt(self, technique_list):
        """
        Get the attacker prompt with technique list filled in.
        
        Args:
            technique_list: List or string of technique IDs
        
        Returns:
            str: The attacker prompt with technique list
        """
        prompt_template = self.get_prompt('attacker')
        if isinstance(technique_list, list):
            technique_list = ' '.join(technique_list)
        return prompt_template.format(technique_list=technique_list)


# Backward compatibility: Create a default instance for function-style access
# This allows existing code to continue working
_default_prompt_service = None

def _get_default_service():
    """Get or create default prompt service instance"""
    global _default_prompt_service
    if _default_prompt_service is None:
        from src.shared import setting
        _default_prompt_service = PromptService(setting.system)
    return _default_prompt_service

# Backward compatibility functions
def get_prompt(prompt_name):
    """Backward compatibility: Get prompt using default service"""
    return _get_default_service().get_prompt(prompt_name)

def get_honeypot_prompt(system='linux'):
    """Backward compatibility: Get honeypot prompt"""
    service = PromptService(system)
    return service.get_honeypot_prompt()

def get_detector_prompt():
    """Backward compatibility: Get detector prompt"""
    return _get_default_service().get_detector_prompt()

def get_detector_state_prompt():
    """Backward compatibility: Get detector state prompt"""
    return _get_default_service().get_detector_state_prompt()

def get_attacker_prompt(technique_list):
    """Backward compatibility: Get attacker prompt"""
    return _get_default_service().get_attacker_prompt(technique_list)
