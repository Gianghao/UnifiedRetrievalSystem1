"""Latency/memory benchmark for the Week 1 plan: BM25, BGE-M3 dense, dense top-K -> bge-reranker-v2-m3.
Synthetic Vietnamese corpus only. Measures time, not quality (no relevance labels exist yet)."""
import json, platform, random, re, statistics, sys, time, unicodedata

import numpy as np
import psutil
import torch
from rank_bm25 import BM25Okapi
from sentence_transformers import SentenceTransformer
from transformers import AutoModelForSequenceClassification, AutoTokenizer

random.seed(7)
N_SHORT, N_LONG = 1000, 1000
WARMUP, RUNS = 3, 30
RERANK_MAX_LEN = 512

names = ["Minh", "Lan", "Hùng", "Thảo", "Quốc", "Ngọc", "Tuấn", "Hà", "Phương", "Đức"]
things = ["hợp đồng", "hóa đơn", "báo cáo tài chính", "biên bản họp", "kế hoạch dự án", "bản thiết kế", "đơn đặt hàng"]
places = ["Quận 1", "Cầu Giấy", "Đà Nẵng", "Thủ Đức", "Hải Phòng", "Biên Hòa"]
days = ["thứ Hai", "thứ Ba", "thứ Tư", "thứ Năm", "thứ Sáu", "thứ Bảy", "Chủ nhật"]

def code():
    return f"{random.choice(['INV', 'HD', 'PO', 'BB'])}-{random.randint(2023, 2026)}-{random.randint(1, 9999):04d}"

def sentence():
    n, t, p, d = random.choice(names), random.choice(things), random.choice(places), random.choice(days)
    return random.choice([
        f"{n} sẽ nhận {t} số {code()} vào {d} tại văn phòng {p}.",
        f"Nhớ gửi lại {t} {code()} cho {n} trước {d} nhé.",
        f"Cuộc họp về {t} được dời sang {d}, địa điểm vẫn ở {p}.",
        f"Theo {t}, tổng giá trị là {random.randint(10, 900)} triệu đồng, thanh toán trong {random.randint(7, 60)} ngày.",
        f"{n} đã ký {t} {code()} ngày {random.randint(1, 28)}/{random.randint(1, 12)}/{random.randint(2023, 2026)}.",
        f"Đổi kế hoạch: {n} sẽ đi lấy {t} vào {d}, không phải {random.choice(names)}.",
        f"Phần tiếp theo của {t} trình bày chi phí vận chuyển và các điều khoản bảo hành tại {p}.",
        f"Trong đoạn ghi âm, {n} nói rằng {t} cần được kiểm tra lại trước khi nộp.",
    ])

def long_chunk(target_words=300):
    out = []
    while sum(len(s.split()) for s in out) < target_words:
        out.append(sentence())
    return " ".join(out)

short = [sentence() for _ in range(N_SHORT)]               # chat-message-sized
long = [long_chunk() for _ in range(N_LONG)]               # PDF page / transcript window
corpus = short + long
queries = [random.choice([
    f"Ai sẽ nhận {random.choice(things)} vào {random.choice(days)}?",
    f"{random.choice(things)} {code()} được ký ngày nào?",
    f"Tổng giá trị của {random.choice(things)} là bao nhiêu?",
    f"Cuộc họp về {random.choice(things)} ở đâu?",
]) for _ in range(WARMUP + RUNS)]

def tok(text):  # BM25 tokenizer: NFC, lowercase, keep codes whole and also split at hyphens
    text = unicodedata.normalize("NFC", text).lower()
    words = re.findall(r"[\w]+(?:-[\w]+)*", text)
    return words + [p for w in words if "-" in w for p in w.split("-")]

def pct(xs):
    xs = sorted(xs)
    return {"p50_ms": round(statistics.median(xs) * 1000, 1),
            "p95_ms": round(xs[min(len(xs) - 1, int(round(0.95 * (len(xs) - 1))))] * 1000, 1)}

def sync(dev):
    if dev == "mps":
        torch.mps.synchronize()

def timed(fn, dev, items):
    times = []
    for i, item in enumerate(items):
        sync(dev); t = time.perf_counter(); fn(item); sync(dev)
        if i >= WARMUP:
            times.append(time.perf_counter() - t)
    return pct(times)

res = {"machine": {"chip": platform.processor() or platform.machine(), "ram_gb": round(psutil.virtual_memory().total / 2**30),
                   "torch": torch.__version__, "mps": torch.backends.mps.is_available()},
       "corpus": {"short_chunks": N_SHORT, "long_chunks": N_LONG}, "warmup": WARMUP, "measured_queries": RUNS}
proc = psutil.Process()

# --- BM25 ---
t = time.perf_counter()
bm25 = BM25Okapi([tok(c) for c in corpus], k1=1.2, b=0.75)
res["bm25_index_s"] = round(time.perf_counter() - t, 2)
res["bm25_query_top10"] = timed(lambda q: np.argsort(-bm25.get_scores(tok(q)))[:10], "cpu", queries)

# --- Dense (BGE-M3, fp16 on MPS) ---
dev = "mps" if torch.backends.mps.is_available() else "cpu"
rss0 = proc.memory_info().rss
emb = SentenceTransformer("BAAI/bge-m3", device=dev)
emb.half()
emb.max_seq_length = 512
t = time.perf_counter()
C = emb.encode(corpus, batch_size=32, normalize_embeddings=True, convert_to_numpy=True)
sync(dev)
res["dense_index_s_2000_chunks"] = round(time.perf_counter() - t, 1)
res["dense_dim"] = int(C.shape[1])

def dense_topk(q, k):
    v = emb.encode([q], normalize_embeddings=True, convert_to_numpy=True)[0]
    return np.argsort(-(C @ v))[:k]

res["dense_query_top10"] = timed(lambda q: dense_topk(q, 10), dev, queries)
res["dense_query_top50"] = timed(lambda q: dense_topk(q, 50), dev, queries)
res["dense_mps_alloc_gb"] = round(torch.mps.driver_allocated_memory() / 2**30, 2) if dev == "mps" else None

# --- Reranker ---
rt = AutoTokenizer.from_pretrained("BAAI/bge-reranker-v2-m3")
res["token_len_median"] = {
    "short": int(statistics.median(len(rt(s)["input_ids"]) for s in short[:200])),
    "long": int(statistics.median(len(rt(s)["input_ids"]) for s in long[:200])),
}

def load_reranker(device, half):
    m = AutoModelForSequenceClassification.from_pretrained("BAAI/bge-reranker-v2-m3").eval().to(device)
    return m.half() if half else m

def rerank(model, device, q, docs):
    with torch.no_grad():
        x = rt([[q, d] for d in docs], padding=True, truncation=True, max_length=RERANK_MAX_LEN, return_tensors="pt").to(device)
        return model(**x).logits.view(-1).float().cpu()

pools = {"short": short, "long": long}
rr = {}
for device, half in [(dev, True), (dev, False), ("cpu", False)]:
    if dev == "mps":
        torch.mps.empty_cache()
    model = load_reranker(device, half)
    label = f"{device}_{'fp16' if half else 'fp32'}"
    rr[label] = {}
    for k in ([20, 30, 50] if device != "cpu" else [50]):
        for kind in (["short", "long"] if device != "cpu" else ["long"]):
            cands = [random.sample(pools[kind], k) for _ in queries]
            rr[label][f"top{k}_{kind}"] = timed(lambda i: rerank(model, device, queries[i], cands[i]), device, range(len(queries)))
        if device != "cpu":  # realistic: real dense top-K candidates from the mixed corpus
            cands = [[corpus[j] for j in dense_topk(q, k)] for q in queries]
            rr[label][f"top{k}_dense_mixed"] = timed(lambda i: rerank(model, device, queries[i], cands[i]), device, range(len(queries)))
    if device == "mps":
        rr[label]["mps_alloc_gb_with_bge_m3_loaded"] = round(torch.mps.driver_allocated_memory() / 2**30, 2)
    del model
res["rerank"] = rr

# --- End to end: dense top-50 -> rerank -> top-10 (fp16 MPS), timers kept separate ---
model = load_reranker(dev, True)
tc, tr, tt = [], [], []
for i, q in enumerate(queries):
    sync(dev); t0 = time.perf_counter()
    idx = dense_topk(q, 50); sync(dev); t1 = time.perf_counter()
    s = rerank(model, dev, q, [corpus[j] for j in idx]); top10 = idx[np.argsort(-s.numpy())[:10]]; sync(dev); t2 = time.perf_counter()
    if i >= WARMUP:
        tc.append(t1 - t0); tr.append(t2 - t1); tt.append(t2 - t0)
res["end_to_end_dense50_rerank10_mps_fp16"] = {"t_candidate": pct(tc), "t_rerank": pct(tr), "t_total": pct(tt)}
res["process_rss_gb_end"] = round(proc.memory_info().rss / 2**30, 2)

print(json.dumps(res, ensure_ascii=False, indent=2))
