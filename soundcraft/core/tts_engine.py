import subprocess
import os

def speak_to_wav(text, wav_path, model="en_US-amy-low"):
    home = os.path.expanduser("~")
    model_dir = os.path.join(home, "piper_voices")
    model_path = os.path.join(model_dir, model + ".onnx")
    config_path = model_path + ".json"

    if not os.path.exists(model_path):
        raise FileNotFoundError(f"Piper model not found at {model_path}")

    subprocess.run(
        [
            "piper",
            "--model", model_path,
            "--config", config_path,
            "--output_file", wav_path,
        ],
        input=text.encode(),
        check=True,
    )
    return wav_path
