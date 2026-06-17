import asyncio
import logging
import os
import shutil
import subprocess
import tempfile
import threading
from typing import Dict, List, Optional

import torch
from fastapi import UploadFile
from omnilingual_asr.models.inference.pipeline import (
    ASRInferencePipeline,
)

from app.config import (
    SHORT_ASR_MODEL,
    SHORT_ASR_MODEL_CACHE_DIR,
)

logger = logging.getLogger(__name__)

# Performance tuning
torch.backends.cudnn.benchmark = True
torch.set_num_threads(1)

# Native formats
NATIVE_AUDIO_FORMATS = {
    ".wav", ".flac", ".ogg", ".oga", ".opus",
    ".aiff", ".aif", ".aifc",
    ".au", ".snd",
    ".caf",
    ".w64", ".rf64",
    ".mp3",
    ".nist", ".sph",
    ".voc", ".svx",
}

# Requires ffmpeg
CONVERTIBLE_AUDIO_FORMATS = {
    ".mp4", ".m4a", ".aac", ".wma", ".webm",
    ".amr", ".3gp", ".mka", ".ac3", ".ape",
    ".wv", ".tta", ".spx",
}

SUPPORTED_AUDIO_FORMATS = (
    NATIVE_AUDIO_FORMATS
    | CONVERTIBLE_AUDIO_FORMATS
)


def get_file_extension(audio_filename: str) -> str:
    return os.path.splitext(
        audio_filename
    )[1].lower()


def _prepare_cache_dir(cache_dir: str) -> str:
    path = os.path.expanduser(cache_dir)

    os.makedirs(
        path,
        exist_ok=True,
    )

    return path


def _get_inference_device() -> torch.device:

    if torch.cuda.is_available():
        return torch.device("cuda")

    if (
        hasattr(torch.backends, "mps")
        and torch.backends.mps.is_available()
    ):
        return torch.device("mps")

    return torch.device("cpu")


def _convert_to_wav(
    input_path: str,
) -> str:

    output_path = (
        input_path
        + ".converted.wav"
    )

    try:

        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-i",
                input_path,
                "-ar",
                "16000",
                "-ac",
                "1",
                "-f",
                "wav",
                output_path,
            ],
            check=True,
            capture_output=True,
            timeout=120,
        )

        return output_path

    except FileNotFoundError:

        raise RuntimeError(
            "ffmpeg is not installed."
        )

    except subprocess.CalledProcessError as e:

        raise RuntimeError(
            "ffmpeg conversion failed: "
            f"{e.stderr.decode(errors='replace')}"
        )


class ASRModelManager:
    """
    Thread-safe singleton manager.
    """

    def __init__(self):

        self._model: Optional[
            ASRInferencePipeline
        ] = None

        self._device = (
            _get_inference_device()
        )

        self._load_lock = threading.Lock()
        self._infer_lock = threading.Lock()

        logger.info(
            f"ASR inference device: "
            f"{self._device}"
        )
    def inference_lock(self):
        return self._infer_lock  # ✅ add this method

    def get_model(
        self,
    ) -> ASRInferencePipeline:

        # Fast path
        if self._model is not None:
            return self._model

        with self._load_lock:

            # Double check
            if self._model is not None:
                return self._model

            self._load_model()

        return self._model

    def _cleanup_temp_downloads(
        self,
        cache_path: str,
    ):

        if not os.path.exists(cache_path):
            return

        for item in os.listdir(cache_path):

            if item.endswith(".download.tmp"):

                item_path = os.path.join(
                    cache_path,
                    item,
                )

                logger.warning(
                    "Removing broken temp "
                    f"download: {item_path}"
                )

                shutil.rmtree(
                    item_path,
                    ignore_errors=True,
                )

    def _load_model(self):
        cache_path = _prepare_cache_dir(SHORT_ASR_MODEL_CACHE_DIR)
        os.environ["FAIRSEQ2_CACHE_DIR"] = cache_path

        try:
            self._model = ASRInferencePipeline(
                model_card=SHORT_ASR_MODEL,
                device=self._device,
            )
            print("ASR model load: success")

        except Exception as e:
            error_str = str(e)
            print(f"ASR model load: failed — {error_str}")

            # Don't retry on network errors — they won't resolve themselves
            if "No route to host" in error_str or "URLError" in error_str:
                raise RuntimeError(
                    "Model download failed due to network error. "
                    "Pre-download the model on the host and mount the cache directory."
                ) from e

            print("ASR model load: cleaning broken downloads and retrying")
            self._cleanup_temp_downloads(cache_path)

            self._model = ASRInferencePipeline(
                model_card=SHORT_ASR_MODEL,
                device=self._device,
            )
            print("ASR model load: retry success")


# Global singleton
model_manager = ASRModelManager()


class AudioService:

    def __init__(self, manager: ASRModelManager = model_manager):
        self.manager = manager

    def inference_lock(self):
        return self.manager._infer_lock  # ✅ delegate to manager

    async def transcribe_file(
        self,
        file: UploadFile,
        languages: List[str],
    ) -> Dict:

        ext = get_file_extension(
            file.audio_filename or "audio.wav"
        )

        if (
            ext
            and ext not in SUPPORTED_AUDIO_FORMATS
        ):
            raise ValueError(
                f"Unsupported audio format "
                f"'{ext}'."
            )

        suffix = ext or ".wav"

        with tempfile.NamedTemporaryFile(
            delete=False,
            suffix=suffix,
        ) as tmp:

            shutil.copyfileobj(
                file.file,
                tmp,
            )

            tmp_path = tmp.name

        converted_path = None

        try:

            if (
                ext in CONVERTIBLE_AUDIO_FORMATS
                or not ext
            ):

                logger.info(
                    f"Converting {ext} "
                    "via ffmpeg"
                )

                converted_path = (
                    _convert_to_wav(
                        tmp_path
                    )
                )

                transcribe_path = (
                    converted_path
                )

            else:
                transcribe_path = tmp_path

            model = (
                self.manager.get_model()
            )

            loop = (
                asyncio.get_running_loop()
            )

            results = await loop.run_in_executor(
                None,
                lambda: model.transcribe(
                    [transcribe_path],
                    lang=languages,
                    batch_size=1,
                ),
            )

            transcription = (
                results[0]
                if results
                else ""
            )

            return {
                "audio_filename": file.audio_filename,
                "model_used": SHORT_ASR_MODEL,
                "transcription": transcription,
            }

        finally:

            if os.path.exists(tmp_path):
                os.remove(tmp_path)

            if (
                converted_path
                and os.path.exists(
                    converted_path
                )
            ):
                os.remove(converted_path)


async def transcribe(
    audio_path: str,
    languages: List[str] = ["eng_Latn"],
) -> str:

    model = model_manager.get_model()

    loop = asyncio.get_running_loop()

    def run_safe():

        with model_manager.inference_lock():

            result = model.transcribe(
                [audio_path],
                lang=languages,
                batch_size=1,
            )

            if torch.cuda.is_available():
                torch.cuda.empty_cache()

            try:
                torch.mps.empty_cache()
            except Exception:
                pass

            return result

    result = await loop.run_in_executor(
        None,
        run_safe,
    )

    return result[0] if result else ""