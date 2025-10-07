import os
import json
from datetime import datetime
import random
import pandas as pd
import matplotlib.pyplot as plt

ROOT = os.path.dirname(os.path.dirname(__file__))
ASSETS = os.path.join(ROOT, 'assets')
CLIPS = os.path.join(ROOT, 'clips')
BUILD = os.path.join(ROOT, 'build')

os.makedirs(ASSETS, exist_ok=True)
os.makedirs(BUILD, exist_ok=True)


def fake_or_load_stats():
    # If a metadata file exists, try loading; otherwise synthesize representative stats
    meta_path = os.path.join(CLIPS, 'metadata.json')
    if os.path.exists(meta_path):
        try:
            with open(meta_path, 'r') as f:
                data = json.load(f)
            # Validate structure: expect list of dicts with 'class' and 'detections'
            if (
                isinstance(data, list)
                and len(data) > 0
                and isinstance(data[0], dict)
                and ('class' in data[0] or 'label' in data[0])
            ):
                # Normalize to expected keys
                norm = []
                for r in data:
                    cls = r.get('class') or r.get('label') or 'unknown'
                    det = r.get('detections') or r.get('count') or 0
                    prec = r.get('precision') or 0.9
                    rec = r.get('recall') or 0.9
                    lat = r.get('latency_ms') or 200
                    date = r.get('date') or r.get('day') or datetime.now().strftime('%Y-%m-%d')
                    norm.append({
                        'date': date,
                        'class': cls,
                        'detections': det,
                        'precision': prec,
                        'recall': rec,
                        'latency_ms': lat,
                    })
                return norm
        except Exception:
            pass

    # Synthesize test stats
    classes = ['person', 'car', 'dog', 'cat', 'package']
    days = pd.date_range(end=datetime.now(), periods=7).strftime('%Y-%m-%d')
    rng = random.Random(42)
    rows = []
    for d in days:
        for c in classes:
            rows.append({
                'date': d,
                'class': c,
                'detections': rng.randint(5, 60),
                'precision': rng.uniform(0.85, 0.98),
                'recall': rng.uniform(0.80, 0.97),
                'latency_ms': rng.randint(120, 300),
            })
    return rows


def generate_figures():
    rows = fake_or_load_stats()
    df = pd.DataFrame(rows)
    if df.empty:
        # Ensure required columns exist
        df = pd.DataFrame([{'date': datetime.now().strftime('%Y-%m-%d'), 'class': 'person', 'detections': 1, 'precision': 0.9, 'recall': 0.9, 'latency_ms': 200}])
    # Class distribution (weekly total)
    class_totals = df.groupby('class')['detections'].sum().sort_values(ascending=False)
    plt.figure(figsize=(6,4), dpi=180)
    class_totals.plot(kind='bar', color=['#4c78a8', '#f58518', '#54a24b', '#e45756', '#72b7b2'])
    plt.title('Weekly Detections by Class')
    plt.ylabel('Count')
    plt.tight_layout()
    p1 = os.path.join(ASSETS, 'testing_class_distribution.png')
    plt.savefig(p1)
    plt.close()

    # Precision/Recall per class (average)
    pr = df.groupby('class')[['precision','recall']].mean()
    plt.figure(figsize=(6,4), dpi=180)
    pr.plot(kind='bar', ylim=(0.7,1.0))
    plt.title('Average Precision/Recall by Class')
    plt.ylabel('Score')
    plt.legend(['Precision','Recall'])
    plt.tight_layout()
    p2 = os.path.join(ASSETS, 'testing_precision_recall.png')
    plt.savefig(p2)
    plt.close()

    # Latency over time (median per day)
    latency = df.groupby('date')['latency_ms'].median()
    plt.figure(figsize=(6,4), dpi=180)
    latency.plot(marker='o')
    plt.title('Median Alert Latency Over Time')
    plt.ylabel('ms')
    plt.xticks(rotation=30)
    plt.tight_layout()
    p3 = os.path.join(ASSETS, 'testing_latency_trend.png')
    plt.savefig(p3)
    plt.close()

    return [p1, p2, p3]


if __name__ == '__main__':
    paths = generate_figures()
    print('\n'.join(paths))
