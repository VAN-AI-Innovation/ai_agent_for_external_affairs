from functools import lru_cache

from app.ai.base import AiGenerationError
from app.core.config import Settings


class LocalModelUnavailableError(AiGenerationError):
    pass


class LocalQwenClient:
    def __init__(self, settings: Settings):
        self._model_id = settings.local_model_id
        self._max_new_tokens = settings.local_model_max_new_tokens

    @property
    def is_configured(self) -> bool:
        return True

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        try:
            generator = _load_generator(self._model_id)
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ]
            text = generator.tokenizer.apply_chat_template(
                messages,
                tokenize=False,
                add_generation_prompt=True,
            )
            inputs = generator.tokenizer([text], return_tensors="pt").to(generator.model.device)
            outputs = generator.model.generate(
                **inputs,
                max_new_tokens=self._max_new_tokens,
                do_sample=True,
                temperature=0.3,
                top_p=0.9,
                pad_token_id=generator.tokenizer.eos_token_id,
            )
            generated_ids = outputs[0][inputs.input_ids.shape[-1]:]
            return generator.tokenizer.decode(generated_ids, skip_special_tokens=True).strip()
        except Exception as exc:
            raise LocalModelUnavailableError("로컬 Qwen 모델 실행에 실패했습니다.") from exc


class _Generator:
    def __init__(self, tokenizer, model):
        self.tokenizer = tokenizer
        self.model = model


@lru_cache(maxsize=1)
def _load_generator(model_id: str) -> _Generator:
    try:
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer
    except ImportError as exc:
        raise LocalModelUnavailableError("torch 또는 transformers가 설치되어 있지 않습니다.") from exc

    tokenizer = AutoTokenizer.from_pretrained(model_id)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    torch_dtype = torch.float16 if torch.cuda.is_available() else torch.float32
    model = AutoModelForCausalLM.from_pretrained(model_id, torch_dtype=torch_dtype)
    model.to(device)
    model.eval()
    return _Generator(tokenizer=tokenizer, model=model)
