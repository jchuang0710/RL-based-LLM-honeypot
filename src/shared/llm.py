import torch
import gc
import logging
from openai import OpenAI 
import os
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    pipeline,
    GenerationConfig
)
import time
from src.shared.config import setting
from src.shared.prompts import PromptService
from src.shared.paths import MODELS_DIR, PROJECT_ROOT

logger = logging.getLogger(__name__)


class LLMService:
    """
    Unified LLM service that supports both local models and OpenAI API.
    Use different prompts to achieve different functionalities.
    """
    
    def __init__(self, model_name="../models/Llama-3.1-8B", model_type="local"):
        """
        Initialize LLM service.
        
        Args:
            model_name: Model name or path
                - For local: model name like "Llama-3.1-8B", path like "../models/Llama-3.1-8B", or HuggingFace ID like "meta-llama/Llama-3.1-8B-Instruct"
                - For OpenAI: model name like "gpt-4o-mini-2024-07-18"
            model_type: "local" or "openai" (default: "local")
        """
        self.model_type = model_type
        self.prompt_service = PromptService(setting.system)
        self.SYSTEM_PROMPT = self.prompt_service.get_honeypot_prompt()
        
        if model_type == "local":
            # Handle local model path
            # Priority: 1) Absolute path, 2) Relative path, 3) Check models/ directory, 4) HuggingFace model name
            if os.path.isabs(model_name) and os.path.exists(model_name):
                # Absolute path that exists
                self.BASE_MODEL_NAME = model_name
            elif model_name.startswith("../") or model_name.startswith("./"):
                # Relative path starting with ../ or ./
                model_path = PROJECT_ROOT / model_name.lstrip("./\\")
                if os.path.exists(model_path) and os.path.isdir(model_path):
                    self.BASE_MODEL_NAME = model_path
                else:
                    # If path doesn't exist, treat as HuggingFace model name
                    self.BASE_MODEL_NAME = model_name
            else:
                # Check if model exists in models/ directory
                local_model_path = MODELS_DIR / model_name
                if local_model_path.exists() and local_model_path.is_dir():
                    # Use local model if it exists
                    self.BASE_MODEL_NAME = local_model_path
                else:
                    # Treat as HuggingFace model name (e.g., "meta-llama/Llama-3.1-8B-Instruct")
                    # If it doesn't contain /, try adding meta-llama/ prefix
                    if "/" not in model_name:
                        # Try common HuggingFace formats
                        possible_names = [
                            f"meta-llama/{model_name}-Instruct",
                            f"meta-llama/{model_name}",
                            model_name
                        ]
                        self.BASE_MODEL_NAME = model_name  # Will try to load, error will be raised if invalid
                    else:
                        self.BASE_MODEL_NAME = model_name
            
            # Initialize local model
            gc.collect()
            torch.cuda.empty_cache()
            torch.set_num_threads(8)
            logger.info("Cleared GPU cache")
            logger.info("Loading model from %s", self.BASE_MODEL_NAME)
            
            try:
                # Try loading with safetensors (supports sharded models)
                logger.info("Loading model and tokenizer")
                model = AutoModelForCausalLM.from_pretrained(
                    self.BASE_MODEL_NAME,
                    dtype=torch.bfloat16,
                    device_map="auto",
                    trust_remote_code=True,
                )
                tokenizer = AutoTokenizer.from_pretrained(
                    self.BASE_MODEL_NAME,
                    trust_remote_code=True,
                )
                
                # Create pipeline with loaded model and tokenizer
                # Don't set generation_config here to avoid conflicts with explicit parameters later
                self.pipeline = pipeline(
                    "text-generation",
                    model=model,
                    tokenizer=tokenizer,
                    dtype=torch.bfloat16,
                    device_map="auto",
                )
                logger.info("Model loaded successfully")
            except Exception as e:
                error_msg = str(e).lower()
                if "safetensors" in error_msg or "header too large" in error_msg or "no file named" in error_msg:
                    logger.warning("Primary model loading failed; trying alternative method: %s", e)
                    # Try loading without safetensors (if pytorch_model.bin exists)
                    try:
                        model = AutoModelForCausalLM.from_pretrained(
                            self.BASE_MODEL_NAME,
                            torch_dtype=torch.bfloat16,
                            device_map="auto",
                            use_safetensors=False,
                            trust_remote_code=True,
                        )
                        tokenizer = AutoTokenizer.from_pretrained(
                            self.BASE_MODEL_NAME,
                            trust_remote_code=True,
                        )
                        self.pipeline = pipeline(
                            "text-generation",
                            model=model,
                            tokenizer=tokenizer,
                            dtype=torch.bfloat16,
                            device_map="auto",
                        )
                        logger.info("Model loaded with alternative method")
                    except Exception as e2:
                        logger.exception(
                            "Failed to load model. Verify model files, all shards, and "
                            "model.safetensors.index.json"
                        )
                        raise e2
                else:
                    raise
        elif model_type == "openai":
            # For OpenAI, use model_name as is
            self.BASE_MODEL_NAME = model_name
            # Initialize OpenAI client
            self.client = OpenAI(api_key=os.environ['OPENAI_API_KEY'])
        else:
            raise ValueError(f"Unsupported model_type: {model_type}. Use 'openai' or 'local'")
        
        logger.info("Loaded model (%s): %s", model_type, self.BASE_MODEL_NAME)

    def generate(self, system_prompt, user_prompt, log_history=[], max_tokens=512, temperature=0.01, top_p=0.8, model_override=None):
        """
        Unified generation method that works with both local and OpenAI models.
        
        Args:
            system_prompt: System prompt string
            user_prompt: User prompt string
            log_history: List of previous conversation history (alternating user/assistant)
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            top_p: Top-p sampling parameter
            model_override: Override model for OpenAI (e.g., for fine-tuned models)
        
        Returns:
            str: Generated response
        """
        # Build message history
        message_history = [{"role": "system", "content": system_prompt}]
        if len(log_history) > 0:
            for i, item in enumerate(log_history):
                if i % 2 == 0:
                    message_history.append({"role": "user", "content": item})
                else:
                    message_history.append({"role": "assistant", "content": item})
        
        message_history.append({"role": "user", "content": user_prompt})
        
        if self.model_type == "local":
            return self._generate_local(message_history, max_tokens, temperature, top_p)
        else:
            return self._generate_openai(message_history, max_tokens, temperature, top_p, model_override)

    def _generate_local(self, message_history, max_tokens, temperature, top_p):
        """Generate using local model"""
        # Check if tokenizer has chat_template
        if hasattr(self.pipeline.tokenizer, 'chat_template') and self.pipeline.tokenizer.chat_template is not None:
            # Use chat template if available
            prompt = self.pipeline.tokenizer.apply_chat_template(
                message_history, tokenize=False, add_generation_prompt=True
            )
        else:
            # Fallback: manually construct prompt if no chat_template
            # Format: system prompt + user/assistant messages
            prompt_parts = []
            if self.SYSTEM_PROMPT:
                prompt_parts.append(self.SYSTEM_PROMPT)
            
            for msg in message_history:
                role = msg.get("role", "user")
                content = msg.get("content", "")
                if role == "user":
                    prompt_parts.append(f"User: {content}")
                elif role == "assistant":
                    prompt_parts.append(f"Assistant: {content}")
            
            prompt_parts.append("Assistant:")
            prompt = "\n".join(prompt_parts)
        
        # Prepare generation parameters
        # Use pad_token_id if eos_token_id is None
        pad_token_id = self.pipeline.tokenizer.eos_token_id if self.pipeline.tokenizer.eos_token_id is not None else self.pipeline.tokenizer.pad_token_id
        
        # Create GenerationConfig to avoid deprecation warnings
        # This avoids conflicts between generation_config and explicit parameters
        generation_config = GenerationConfig(
            max_new_tokens=max_tokens,
            pad_token_id=pad_token_id,
            eos_token_id=self.pipeline.tokenizer.eos_token_id,
            do_sample=True,
            temperature=temperature,
            top_p=top_p,
        )
        
        # Call pipeline with GenerationConfig object (avoids deprecation warnings)
        outputs = self.pipeline(
            prompt,
            generation_config=generation_config,
            return_full_text=False,  # Only return generated text, not the prompt
        )
        # With return_full_text=False, the output is already just the generated text
        response = outputs[0]["generated_text"]
        return self._clean_response(response)

    def _generate_openai(self, message_history, max_tokens, temperature, top_p, model_override=None):
        """Generate using OpenAI API"""
        model = model_override or self.BASE_MODEL_NAME
        
        while True:
            try:
                outputs = self.client.chat.completions.create(
                    model=model,
                    messages=message_history,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    top_p=top_p
                )
                response = outputs.choices[0].message.content
                return self._clean_response(response)
            except Exception:
                logger.exception("OpenAI generation failed; retrying in 20 seconds")
                time.sleep(20)
                continue

    def _clean_response(self, response):
        """Clean response by removing unnecessary formatting"""
        if response.startswith("plaintext\n"):
            response = response[9:]
        elif response.startswith("plaintext"):
            response = response[9:]
        if response.startswith("```") and response.endswith("```"):
            response = response[3:-3]
        elif response.startswith("`") and response.endswith("`"):
            response = response[1:-1]
        return response

    # High-level methods using prompts
    def answer(self, action, query, log_history=[], max_tokens=512, temperature=0.01, top_p=0.8):
        """Generate answer with honeypot system prompt"""
        system_prompt = self.SYSTEM_PROMPT
        user_prompt = action + ' ' + query if action else query
        return self.generate(system_prompt, user_prompt, log_history, max_tokens, temperature, top_p)

    def add_system_prompt(self, additional_prompt):
        """Add additional text to system prompt"""
        self.SYSTEM_PROMPT = self.SYSTEM_PROMPT + additional_prompt


# Backward compatibility aliases
class LLM(LLMService):
    """Backward compatibility alias for LLMService with local model"""
    def __init__(self, model_name="../models/Llama-3.1-8B"):
        super().__init__(model_name, model_type="local")


class ChatGPT(LLMService):
    """Backward compatibility alias for LLMService with OpenAI"""
    def __init__(self, model_name="gpt-4o-mini-2024-07-18", model_type="openai"):
        super().__init__(model_name, model_type=model_type)
    
    def add_system_prompt(self, user, password):
        """Add user and password info to system prompt"""
        additional = f"You should print the terminal response and nothing else, final line is the prompt for input like this '{user}@speedlab-ml-3:~$ ' and password is {password}."
        super().add_system_prompt(additional)
