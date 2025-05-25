import joblib
import pandas as pd
import torch
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from torch.utils.data import Dataset
from transformers import (AutoModelForSequenceClassification, AutoTokenizer,
                          Trainer, TrainingArguments)

# === 1. Загрузка данных ===
# Пример: замени на загрузку из файла, если нужно
df = pd.read_csv("marked_train_type.csv", header=0)
# === 2. Кодируем метки ===
label_encoder = LabelEncoder()
df["label_id"] = label_encoder.fit_transform(df["label"])

# === 3. Разделение на train/test ===
train_df, test_df = train_test_split(df, test_size=0.2, random_state=42)

# === 4. Класс PyTorch Dataset ===
class BookDataset(Dataset):
    def __init__(self, dataframe, tokenizer, max_len=128):
        self.df = dataframe
        self.tokenizer = tokenizer
        self.max_len = max_len

    def __len__(self):
        return len(self.df)

    def __getitem__(self, idx):
        text = self.df.iloc[idx]["title"]
        label = self.df.iloc[idx]["label_id"]
        encodings = self.tokenizer(
            text,
            truncation=True,
            padding="max_length",
            max_length=self.max_len,
            return_tensors="pt"
        )
        item = {key: val.squeeze(0) for key, val in encodings.items()}
        item["labels"] = torch.tensor(label)
        return item

# === 5. Инициализация модели и токенизатора ===
model_name = "ai-forever/ruBert-base"
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForSequenceClassification.from_pretrained(model_name, num_labels=len(label_encoder.classes_))

# === 6. Подготовка датасетов ===
train_dataset = BookDataset(train_df, tokenizer)
test_dataset = BookDataset(test_df, tokenizer)

# === 7. Обучение ===
training_args = TrainingArguments(
    output_dir="./results",
    num_train_epochs=3,
    per_device_train_batch_size=8,
    per_device_eval_batch_size=8,
    logging_dir="./logs",
    logging_steps=10,
)

trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=train_dataset,
    eval_dataset=test_dataset
)

trainer.train()

# === 8. Предсказание типа книги ===
def predict_book_type(title: str):
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model.to(device)  # Перемещаем модель на GPU или CPU

    inputs = tokenizer(title, return_tensors="pt", truncation=True, padding=True, max_length=128)
    inputs = {k: v.to(device) for k, v in inputs.items()}  # Перемещаем входы на то же устройство

    with torch.no_grad():
        outputs = model(**inputs)
        logits = outputs.logits
        predicted_class_id = torch.argmax(logits, dim=1).item()
    return label_encoder.inverse_transform([predicted_class_id])[0]


# === Пример ===
print(predict_book_type("Математика. Рабочая тетрадь 7 класс"))

model.save_pretrained("saved_model")
tokenizer.save_pretrained("saved_model")
joblib.dump(label_encoder, "saved_model/label_encoder.pkl")