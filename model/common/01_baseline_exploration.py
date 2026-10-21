"""01_baseline_exploration.py

Eksplorasi baseline model (M1: TF-IDF + Logistic Regression).
Eksperimen offline riset model terisolasi dari runtime backend.
Jalankan dengan: /home/josjiez/my_env/ai_env/bin/python model/common/01_baseline_exploration.py
"""

from typing import List, Optional, Tuple

from model.common.baseline import BaselineTfidfSentiment
from model.common.metrics import evaluate_predictions


def run_experiment(
    sample_data: Optional[List[Tuple[str, int]]] = None,
    max_features: int = 5000,
) -> dict:
    """
    Menjalankan pelatihan dan evaluasi baseline sentiment.
    Labels: 0 = Negative, 1 = Neutral, 2 = Positive
    """
    if sample_data is None:
        sample_data = [
            ("Laba bersih emiten melonjak didukung ekspansi operasional", 2),
            ("Kinerja kuartal ketiga tercatat melampaui ekspektasi konsensus", 2),
            ("Bank Sentral mempertahankan suku bunga acuan pada level stabil", 1),
            ("Perdagangan saham ditutup mendatar minim katalis baru", 1),
            ("Penjualan merosot tajam tertekan pelemahan daya beli", 0),
            ("Risiko gagal bayar membayangi sektor properti komersial", 0),
        ]

    texts = [item[0] for item in sample_data]
    labels = [item[1] for item in sample_data]

    # Inisialisasi model
    model = BaselineTfidfSentiment(model_version=f"tfidf-lr-feat{max_features}")
    model.fit(texts, labels)

    # Prediksi
    probs = model.predict_probs(texts)
    preds = []
    for p in probs:
        if p.p_pos > p.p_neu and p.p_pos > p.p_neg:
            preds.append(2)
        elif p.p_neg > p.p_neu and p.p_neg > p.p_pos:
            preds.append(0)
        else:
            preds.append(1)

    metrics = evaluate_predictions(labels, preds)
    return {
        "metrics": metrics,
        "sample_count": len(sample_data),
        "classes": [0, 1, 2],
    }


if __name__ == "__main__":
    print("Menjalankan eksperimen baseline TF-IDF + LR...")
    res = run_experiment()
    print("Hasil Evaluasi:", res["metrics"])
