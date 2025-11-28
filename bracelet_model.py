import numpy as np
import soundfile as sf
import librosa
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics.pairwise import cosine_similarity
import os
import warnings
warnings.filterwarnings('ignore', category=FutureWarning)
warnings.filterwarnings('ignore', category=UserWarning)

def extract_features(audio, sr):
    # достаю спектральные характеристики

    features = []

    mfcc = librosa.feature.mfcc(y=audio, sr=sr, n_mfcc=20, n_fft=2048, hop_length=256)
    features.extend(np.mean(mfcc, axis=1))
    features.extend(np.std(mfcc, axis=1))


    spectral_centroid = librosa.feature.spectral_centroid(y=audio, sr=sr)
    features.extend([np.mean(spectral_centroid), np.std(spectral_centroid)])

    return np.array(features)

def train_model_with_negatives(my_files, other_male_files):
    # создаю датасет с голосом пользователя и с чужими голосами
    X, y = [], []

    # загружаю свой голос
    for f in my_files:
        audio, sr = librosa.load(f, sr=16000)
        features = extract_features(audio, sr)
        X.append(features)
        y.append(1) # единица для моего голоса
        print(f"Мой голос: {f}")

    # загружаю чужие голоса
    for f in other_male_files:
        audio, sr = librosa.load(f, sr=16000)
        features = extract_features(audio, sr)
        X.append(features)
        y.append(0) # ноль для чужого
        print(f"Чужой голос: {f}")

    model = RandomForestClassifier(n_estimators=50, max_depth=10)
    model.fit(X, y)

    print(f"Обучено на {len(my_files)} ваших и {len(other_male_files)} чужих голосов")
    return model


my_voices = ["my_voice" + str(i) + ".wav" for i in range(1, 50)]
other_voices = ["other_voice" + str(i) + ".wav" for i in range(1, 50)]

model = train_model_with_negatives(my_voices, other_voices)

import pickle
with open("bracelet_model.pkl", 'wb') as f:
    pickle.dump(model, f)


# тестируем на голосе пользователя и чужих голосах
test_files = ["my_voice48.wav", "my_voice49.wav", "other_voice48.wav", "other_voice49.wav"]
for test_file in test_files:
    audio, sr = librosa.load(test_file, sr=16000)
    features = extract_features(audio, sr)

    prediction = model.predict([features])[0]
    probability = model.predict_proba([features])[0]

    print(f"\n{test_file}:")
    print(f"Результат: {'мой' if prediction == 1 else 'чужой'}")
    print(f"Уверенность: {probability[prediction]:.3f}")
