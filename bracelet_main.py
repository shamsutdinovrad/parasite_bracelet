import asyncio
import websockets
import os
import numpy as np
import librosa
from vosk import Model, KaldiRecognizer
import wave
import time
import joblib
import json

WS_PORT = int(os.getenv('WS_PORT', 8888))
HTTP_PORT = int(os.getenv('HTTP_PORT', 8000))

vosk = Model("vosk-model-small-ru-0.22")


def vosk_speech_to_text(audio_path):
    wf = wave.open(audio_path, "rb")
    rec = KaldiRecognizer(vosk, wf.getframerate())

    text_parts = []
    while True:
        data = wf.readframes(4000)
        if len(data) == 0:
            break
        if rec.AcceptWaveform(data):
            text_parts.append(json.loads(rec.Result())["text"])

    text_parts.append(json.loads(rec.FinalResult())["text"])
    return " ".join(text_parts)


connected_clients = set()


async def handle_audio_message(websocket):
    print("Connected")
    connected_clients.add(websocket)

    filename = f"audio_record.raw"

    with open(filename, 'ab') as audio_file:
        try:
            async for message in websocket:
                audio_file.write(message)
                audio_file.flush()

                file_size = audio_file.tell()
                if file_size >= 44100 * 3 * 2: # вот тут можно выбрать длину "буфера", сейчас стоит 3 секунды
                    audio_file.close()

                    with open(filename, 'rb') as f:
                        audio_bytes = f.read()

                    audio_data = np.frombuffer(audio_bytes, dtype=np.int16).astype(np.float32)
                    audio_data = audio_data / 32768.0

                    # b, a = signal.butter(4, 4000 / (44100 / 2), 'low')
                    # audio_clean = signal.filtfilt(b, a, audio_data)
                    audio_clean = audio_data

                    audio_bytes = (audio_clean * 32768).astype(np.int16).tobytes()

                    import wave
                    name = int(time.time())
                    with wave.open(f"voices\\temp_{name}.wav", 'wb') as wav_f:
                        wav_f.setnchannels(1)
                        wav_f.setsampwidth(2)
                        wav_f.setframerate(44100)
                        wav_f.writeframes(audio_bytes)

                    audio_data, sr = librosa.load(f"voices\\temp_{name}.wav", sr=16000)
                    text = vosk_speech_to_text(f"voices\\temp_{name}.wav")
                    print(text)

                    features = extract_features(audio_data, 16000)
                    pred = model.predict([features])[0]
                    proba = model.predict_proba([features])[0][pred]
                    print(f"Pred: {bool(pred)}, Prob: {proba:.3f}")

                    for word in ["типа", "типы", "типу", "ну", "короче", "в общем", "как бы", "так сказать", "вот"]:
                        if word in text and pred:
                            await websocket.send(word)

                    open(filename, 'wb').close()
                    audio_file = open(filename, 'ab')

        except websockets.exceptions.ConnectionClosed:
            print("Client disconnected")
        finally:
            connected_clients.remove(websocket)


async def main():
    print(f"WS server is listening at ws://localhost:{WS_PORT}")

    async with websockets.serve(handle_audio_message, "0.0.0.0", WS_PORT):
        await asyncio.Future() 


def extract_features(audio, sr):
    # достаю спектральные характеристики
    features = []

    mfcc = librosa.feature.mfcc(y=audio, sr=sr, n_mfcc=20, n_fft=2048, hop_length=256)
    features.extend(np.mean(mfcc, axis=1))
    features.extend(np.std(mfcc, axis=1))

    spectral_centroid = librosa.feature.spectral_centroid(y=audio, sr=sr)
    features.extend([np.mean(spectral_centroid), np.std(spectral_centroid)])

    return np.array(features)


# загружаю ранее обученную модель
model = joblib.load("bracelet_model.pkl")
asyncio.run(main())
