from transformers import AutoTokenizer, AutoModel
import torch
import torch.nn.functional as F

class BiomedicalEmbeddings:
    def __init__(self):
        self.model_name = "PlanTL-GOB-ES/roberta-base-biomedical-es"

        self.tokenizer = AutoTokenizer.from_pretrained(
            self.model_name
        )

        self.model = AutoModel.from_pretrained(
            self.model_name
        )

        self.model.eval()

    def _mean_pooling(self, model_output, attention_mask):
        token_embeddings = model_output.last_hidden_state

        input_mask_expanded = (
            attention_mask.unsqueeze(-1)
            .expand(token_embeddings.size())
            .float()
        )

        return torch.sum(
            token_embeddings * input_mask_expanded,
            dim=1
        ) / torch.clamp(
            input_mask_expanded.sum(dim=1),
            min=1e-9
        )

    def _embed(self, text: str):
        inputs = self.tokenizer(
            text,
            padding=True,
            truncation=True,
            max_length=512,
            return_tensors="pt"
        )

        with torch.no_grad():
            outputs = self.model(**inputs)

        embeddings = self._mean_pooling(
            outputs,
            inputs["attention_mask"]
        )

        embeddings = F.normalize(
            embeddings,
            p=2,
            dim=1
        )

        return embeddings[0].tolist()

    def embed_query(self, text: str):
        return self._embed(text)

    def embed_documents(self, texts):
        inputs = self.tokenizer(
            texts,
            padding=True,
            truncation=True,
            max_length=512,
            return_tensors="pt"
        )

        with torch.no_grad():
            outputs = self.model(**inputs)

        embeddings = self._mean_pooling(
            outputs,
            inputs["attention_mask"]
        )

        embeddings = F.normalize(
            embeddings,
            p=2,
            dim=1
        )

        return embeddings.tolist()


model = BiomedicalEmbeddings()

def generar_embedding(texto: str) -> list[float]:
    return model.embed_query(texto)


def obtener_modelo_de_embeddings():
    return model