import os
import re
from datetime import datetime, timedelta

import joblib
import numpy as np
import pandas as pd
import torch
from sentence_transformers import SentenceTransformer
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from transformers import BertForSequenceClassification, BertTokenizer


class Model:
    def __init__(self):
        self.model = BertForSequenceClassification.from_pretrained("saved_model")
        self.tokenizer = BertTokenizer.from_pretrained("saved_model")

        self.label_encoder = joblib.load("saved_model/label_encoder.pkl")

        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model.to(self.device)
        self.model.eval()
        
        self.embedding_model = SentenceTransformer('distiluse-base-multilingual-cased-v1')
        
        self.clustering_model = joblib.load("saved_model/clustering_model.joblib")
        self.svm_model = joblib.load("saved_model/one_class_svm_test.joblib")
        self.standard_scaler = joblib.load("saved_model/standard_scaler.joblib")
        
        self.avg_price_by_book_type = dict(pd.read_csv("saved_model/avg_book_type.csv"))

    def predict_book_type(self, title: str):
        inputs = self.tokenizer(title, return_tensors="pt", truncation=True, padding=True, max_length=128)
        inputs = {k: v.to(self.device) for k, v in inputs.items()}

        with torch.no_grad():
            outputs = self.model(**inputs)
            logits = outputs.logits
            predicted_class_id = torch.argmax(logits, dim=1).item()
        
        return self.label_encoder.inverse_transform([predicted_class_id])[0]
    
    def preprocessing(self, data: dict) -> bool:
        book_types = pd.DataFrame({
            "book_type": [
                "диагностические_материалы", "контурные_карты", "прописи",
                "рабочая_тетрадь", "учебник"    
            ],
        })
        warehouse_types = pd.DataFrame({
            "warehouse_type": [
                "fbs", "ozon"
            ]
        })
        
        df = pd.DataFrame(
            columns=[
                "id", "title", "url", "price", "description", "year",
                "pages_count", "circulation", "seller_id", "seller_orders",
                "seller_avg_item_rate", "seller_region", "days_to_deliver",
                "seller_age", "warehouse_type"
            ]
        )
        
        new_row = pd.DataFrame([data])
        df = pd.concat([df, new_row], ignore_index=True)
        
        df["book_type"] = df["title"].apply(lambda x: self.predict_book_type(x))
        df["class"] = df["title"].apply(lambda x: re.findall(r"\d+", x)[0] if len(re.findall(r"\d+", x)) > 0 else 0)
        
        embeddings = self.embedding_model.encode(df['title'], convert_to_tensor=True).cpu().numpy()
        df["embedding"] = list(embeddings)

        embeddings_array = np.stack(df['embedding'].values)
        embedding_dim = embeddings_array.shape[1]
        embedding_df = pd.DataFrame(embeddings_array, columns=[f'emb_{i}' for i in range(embedding_dim)])

        df = pd.concat([
            df.drop(columns=['embedding']),
            embedding_df
        ], axis=1)
        
        df = pd.get_dummies(df, columns=["book_type"])
        book_types = pd.get_dummies(book_types, columns=["book_type"])

        missing_cols = set(book_types.columns) - set(df.columns)
        for col in missing_cols:
            df[col] = 0
        
        df["cluster"] = self.clustering_model.predict(
            df.reindex(columns=list(self.clustering_model.feature_names_in_))
        )
        
        for i in book_types.columns:
            if "book_type_" in i:
                df["true_price"] = df[i].apply(lambda x: self.avg_price_by_book_type[i.replace("book_type_", "")])
                
        df["diff"] = (df["true_price"] - df["price"]) / df["true_price"]
        
        df = pd.get_dummies(df, columns=["warehouse_type"])
        warehouse_types = pd.get_dummies(warehouse_types, columns=["warehouse_type"])
        missing_cols = set(warehouse_types.columns) - set(df.columns)
        for col in missing_cols:
            df[col] = 0

        df.columns = df.columns.astype(str)
        
        columns_to_fill = [
            "year", "pages_count", "seller_orders", "seller_avg_item_rate",
            "days_to_deliver", "seller_age", "class"
        ]

        for c in columns_to_fill:
            df[c] = df[c].fillna(0)

        df_scaled = self.standard_scaler.transform(
            df.reindex(columns=list(self.standard_scaler.feature_names_in_))
        )
        result = self.svm_model.predict(df_scaled)
        
        return bool(result == -1)