"""Microphone recording with WebRTC voice activity detection."""

import numpy as np


def record() -> np.ndarray:
    """Record mono 16 kHz audio and stop after speech silence or 15 seconds."""
    import sounddevice as sd
    import webrtcvad

    sample_rate = 16000
    frame_duration_ms = 30
    frame_size = int(sample_rate * frame_duration_ms / 1000)
    vad = webrtcvad.Vad(2)

    chunks: list[np.ndarray] = []
    silence_seconds = 0.0
    speech_started = False
    elapsed_seconds = 0.0

    def callback(indata: np.ndarray, frames: int, time_info: object, status: object) -> None:
        del frames, time_info, status
        chunks.append(indata.copy().reshape(-1))

    with sd.InputStream(
        samplerate=sample_rate,
        channels=1,
        dtype="int16",
        blocksize=frame_size,
        callback=callback,
    ):
        while elapsed_seconds < 15.0:
            sd.sleep(frame_duration_ms)
            elapsed_seconds += frame_duration_ms / 1000

            if not chunks:
                continue

            pcm = chunks[-1].tobytes()
            is_speech = vad.is_speech(pcm, sample_rate)

            if is_speech:
                speech_started = True
                silence_seconds = 0.0
            elif speech_started:
                silence_seconds += frame_duration_ms / 1000
                if silence_seconds >= 0.8:
                    break

    if not chunks:
        return np.empty(0, dtype=np.float32)

    pcm = np.concatenate(chunks)
    return pcm.astype(np.float32) / 32768.0
