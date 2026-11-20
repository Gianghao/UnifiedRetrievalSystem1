"""Retrieval strategies on a synthetic Vietnamese corpus (N_CHUNKS, default 10k) with planted gold answers.

Strategies: BM25 (pg_textsearch in Postgres), dense BGE-M3, dense top-50 -> bge-reranker-v2-m3 -> top-10,
hybrid RRF (BM25 top-50 + dense top-50 -> top-10), and hybrid RRF top-50 -> reranker -> top-10. Quality uses one planted gold chunk per query
(synthetic labels, not the team's annotation set). Defaults only, nothing tuned on these queries.

Needs the bm25-bench container from bm25_scale_bench.py and: pip install "psycopg[binary]" torch sentence-transformers
Run: python strategies_bench.py > strategies_result.json   (DATASET=chat uses chat_dataset.py; N_CHUNKS=1000000 takes ~3 h of embedding on an M4;
     EMB_CACHE=<dir> keeps embeddings so an interrupted run resumes)
"""
import itertools, json, math, os, platform, random, statistics, subprocess, time

import numpy as np
import psycopg
import torch
from sentence_transformers import SentenceTransformer
from transformers import AutoModelForSequenceClassification, AutoTokenizer

DSN = os.environ.get("BENCH_DSN", "postgresql://postgres:bench@localhost:55434/postgres")
N_CHUNKS = int(os.environ.get("N_CHUNKS", 10_000))
BM25_CONFIG = os.environ.get("BM25_CONFIG", "simple")   # "simple_unaccent": fold accents (ộ->o, đ->d) at index and query time
assert BM25_CONFIG in ("simple", "simple_unaccent"), BM25_CONFIG   # goes into SQL
TS_CONFIG = {"simple": "simple", "simple_unaccent": "public.simple_unaccent"}[BM25_CONFIG]   # pg_textsearch needs custom configs schema-qualified
DATASET = os.environ.get("DATASET", "synthetic")   # "chat": realistic Vietnamese chat from chat_dataset.py
LONG_SHARE = 0.05
CAND_K, TOP_K, RRF_K = 50, 10, 60
RERANK_MAX_LEN = 512
WARMUP = 3
random.seed(11)

# ---------- synthetic conversation ----------
names = ["Minh", "Lan", "Hùng", "Thảo", "Quốc", "Ngọc", "Tuấn", "Hà", "Phương", "Đức"]
things = ["hợp đồng", "hóa đơn", "báo cáo tài chính", "biên bản họp", "kế hoạch dự án", "bản thiết kế", "đơn đặt hàng"]
places = ["Quận 1", "Cầu Giấy", "Đà Nẵng", "Thủ Đức", "Hải Phòng", "Biên Hòa"]
days = ["thứ Hai", "thứ Ba", "thứ Tư", "thứ Năm", "thứ Sáu", "thứ Bảy", "Chủ nhật"]
onsets = ["", "b", "c", "ch", "d", "đ", "g", "gi", "h", "k", "kh", "l", "m", "n", "ng", "nh", "ph", "qu", "r", "s", "t", "th", "tr", "v", "x"]
rhymes = ["a", "á", "à", "ả", "ã", "ạ", "an", "án", "àn", "ang", "áng", "anh", "ành", "ao", "áo", "ào", "âm", "ấm", "ân", "ần", "ây", "ấy",
          "e", "é", "è", "em", "en", "ên", "ết", "i", "í", "ì", "in", "inh", "ính", "o", "ó", "ò", "oa", "oá", "ong", "óng", "ô", "ố", "ồ",
          "ông", "ống", "ơ", "ớ", "ờ", "ơn", "u", "ú", "ù", "ung", "úng", "ư", "ừ", "ương", "ường", "uy", "uyên", "ứng"]
vocab = [o + r for o in onsets for r in rhymes]
random.shuffle(vocab)
zipf_cum = list(itertools.accumulate(1 / (i + 1) for i in range(len(vocab))))
gold_codes = set()

def code():
    while True:
        c = f"{random.choice(['INV', 'HD', 'PO', 'BB'])}-{random.randint(2023, 2026)}-{random.randint(1, 9999):04d}"
        if c not in gold_codes:
            return c

def filler(n):
    return " ".join(random.choices(vocab, cum_weights=zipf_cum, k=n))

def sentence():
    n, t, p, d = random.choice(names), random.choice(things), random.choice(places), random.choice(days)
    s = random.choice([
        f"{n} sẽ nhận {t} số {code()} vào {d} tại văn phòng {p}.",
        f"Nhớ gửi lại {t} {code()} cho {n} trước {d} nhé.",
        f"Cuộc họp về {t} được dời sang {d}, địa điểm vẫn ở {p}.",
        f"Theo {t}, tổng giá trị là {random.randint(10, 900)} triệu đồng.",
        f"{n} đã ký {t} {code()} ngày {random.randint(1, 28)}/{random.randint(1, 12)}/{random.randint(2023, 2026)}.",
        f"Đổi kế hoạch: {n} sẽ đi lấy {t} vào {d}, không phải {random.choice(names)}.",
    ])
    return s if random.random() < 0.4 else filler(random.randint(3, 20))

def long_chunk():
    return [sentence() for _ in range(25)]   # ~300 words: a PDF page or transcript window

# Gold evidence. Paraphrase queries share almost no words with their gold message (except a person's name).
PARAPHRASE = [
    ("Tuấn bị sốt cao từ tối qua nên sáng nay xin nghỉ làm.", "Vì sao Tuấn vắng mặt ở công ty hôm nay?"),
    ("Lan vừa chuyển sang sống ở Đà Lạt cùng gia đình.", "Lan hiện đang cư trú tại thành phố nào?"),
    ("Mật khẩu wifi phòng họp tầng ba là bienxanh2024.", "Cho mình xin pass mạng không dây của phòng meeting trên lầu 3."),
    ("Hùng đã chuyển khoản tiền cọc cho chủ nhà hôm thứ Ba.", "Hùng trả trước khoản đặt cọc thuê căn hộ chưa?"),
    ("Chuyến bay của Thảo bị hủy vì bão, cô ấy phải đổi sang ngày mai.", "Tại sao Thảo không lên máy bay đúng lịch?"),
    ("Quốc đặt bàn ở nhà hàng Sen Vàng lúc bảy giờ tối.", "Tối nay mình ăn ở quán nào vậy Quốc?"),
    ("Ngọc quên chìa khóa xe máy ở quầy lễ tân.", "Ngọc để lạc chìa khóa xe ở đâu?"),
    ("Sếp đồng ý tăng lương cho Phương từ tháng sau.", "Phương có được nâng thu nhập không?"),
    ("Máy in ở tầng hai bị kẹt giấy, đã gọi kỹ thuật đến sửa.", "Thiết bị in ấn trên lầu 2 gặp sự cố gì?"),
    ("Đức sẽ nghỉ phép hai tuần để đi hưởng tuần trăng mật.", "Đức vắng mặt bao lâu sau đám cưới?"),
    ("Hà bị dị ứng hải sản, đừng gọi tôm cua cho bạn ấy.", "Hà không ăn được món gì?"),
    ("Khách hàng phàn nàn vì giao hàng chậm ba ngày.", "Người mua không hài lòng chuyện gì?"),
    ("Minh đã nộp đơn thôi việc, ngày làm cuối là 30/11.", "Khi nào Minh rời công ty?"),
    ("Con mèo nhà Lan bị lạc từ hôm Chủ nhật.", "Thú cưng của Lan mất tích khi nào?"),
    ("Buổi tiệc tất niên tổ chức ở khách sạn Rex.", "Liên hoan cuối năm diễn ra tại đâu?"),
    ("Tuấn đang học thêm tiếng Nhật vào buổi tối.", "Tuấn theo khóa ngoại ngữ nào sau giờ làm?"),
    ("Laptop của Thảo bị đổ cà phê, màn hình không lên.", "Máy tính xách tay của Thảo hỏng do đâu?"),
    ("Quốc mới mua căn hộ ở quận Bình Thạnh.", "Quốc sở hữu nhà mới ở khu vực nào?"),
    ("Phòng kế toán yêu cầu nộp chứng từ trước ngày 25.", "Hạn chót gửi giấy tờ cho bộ phận tài chính là khi nào?"),
    ("Ngọc vừa sinh em bé, cả mẹ và con đều khỏe.", "Ngọc đã lên chức mẹ chưa?"),
]
# Facts buried in the middle of a ~300-word chunk (PDF page / transcript window).
LONG_FACTS = [
    ("Mức phạt khi giao hàng trễ là 2% giá trị đơn hàng cho mỗi tuần chậm.", "Phạt bao nhiêu nếu giao hàng trễ?"),
    ("Thời hạn bảo hành thiết bị là 24 tháng kể từ ngày lắp đặt.", "Thiết bị được bảo hành trong bao lâu?"),
    ("Bên mua được quyền đơn phương chấm dứt hợp đồng nếu bên bán vi phạm quá ba lần.", "Khi nào bên mua có thể hủy hợp đồng?"),
    ("Doanh thu quý ba tăng 18% so với cùng kỳ năm ngoái.", "Doanh thu quý 3 tăng trưởng bao nhiêu phần trăm?"),
    ("Trong ghi âm, giám đốc nói dự án sẽ ra mắt vào tháng Ba năm sau.", "Dự án dự kiến ra mắt khi nào?"),
    ("Chi phí vận chuyển do bên bán chịu đối với đơn hàng trên 50 triệu đồng.", "Ai trả phí ship cho đơn hàng lớn?"),
    ("Nhân viên mới phải hoàn thành khóa đào tạo an toàn trong tuần đầu tiên.", "Người mới vào cần học gì trong tuần đầu?"),
    ("Kho hàng ở Bình Dương sẽ đóng cửa để kiểm kê từ ngày 28 đến 31.", "Kho Bình Dương nghỉ kiểm kê những ngày nào?"),
    ("Lãi suất vay ưu đãi là 6,5% một năm trong 12 tháng đầu.", "Lãi suất ưu đãi năm đầu là bao nhiêu?"),
    ("Mọi tranh chấp sẽ được giải quyết tại Trung tâm Trọng tài Quốc tế Việt Nam.", "Nếu có tranh chấp thì giải quyết ở đâu?"),
    ("Hệ thống sẽ bảo trì định kỳ vào 2 giờ sáng Chủ nhật hằng tuần.", "Lịch bảo trì hệ thống là lúc nào?"),
    ("Ngân sách marketing năm sau được duyệt ở mức 3 tỷ đồng.", "Ngân sách tiếp thị năm tới được phê duyệt bao nhiêu?"),
    ("Đối tác Nhật yêu cầu mẫu thử phải gửi trước ngày 15 tháng 12.", "Hạn gửi mẫu thử cho đối tác Nhật là ngày nào?"),
    ("Trong cuộc gọi, Lan xác nhận đã nhận đủ 500 thùng hàng.", "Lan nhận được bao nhiêu thùng hàng?"),
    ("Tỷ lệ hàng lỗi trong lô tháng 10 là 1,2%.", "Lô hàng tháng 10 có tỷ lệ lỗi bao nhiêu?"),
]

def build():
    corpus, queries = [], []   # queries: (type, text, gold_index)
    for _ in range(20 + WARMUP):
        gold_codes.add(f"{random.choice(['INV', 'HD', 'PO', 'BB'])}-{random.randint(2023, 2026)}-{random.randint(1, 9999):04d}")
    for i, c in enumerate(sorted(gold_codes)):
        n, m, t = random.choice(names), random.choice(names), random.choice(things)
        corpus.append(f"{n} đã gửi {t} số {c} cho {m} qua email.")
        queries.append(("warmup" if i < WARMUP else "exact_code", f"{t} số {c} đã gửi cho ai?", len(corpus) - 1))
    for gold, q in PARAPHRASE:
        corpus.append(gold)
        queries.append(("paraphrase", q, len(corpus) - 1))
    for fact, q in LONG_FACTS:
        parts = long_chunk()
        parts.insert(len(parts) // 2, fact)
        corpus.append(" ".join(parts))
        queries.append(("long_chunk_fact", q, len(corpus) - 1))
    while len(corpus) < N_CHUNKS:
        corpus.append(" ".join(long_chunk()) if random.random() < LONG_SHARE else sentence())
    order = list(range(len(corpus)))   # shuffle so gold chunks are not at the front
    random.shuffle(order)
    pos = {old: new for new, old in enumerate(order)}
    return [corpus[i] for i in order], [(t, q, pos[g], None) for t, q, g in queries]

def load_dataset():   # -> corpus, [(type, query, gold or None, stale or None)]
    if DATASET == "chat":
        import chat_dataset
        corpus, qs = chat_dataset.build(N_CHUNKS)
        return corpus, [(q["type"], q["text"], q["gold"], q["stale"]) for q in qs]
    return build()

# ---------- helpers ----------
def pct(xs):
    xs = sorted(xs)
    return {"p50_ms": round(statistics.median(xs) * 1000, 1),
            "p95_ms": round(xs[min(len(xs) - 1, int(round(0.95 * (len(xs) - 1))))] * 1000, 1)}

def sync():
    if torch.cuda.is_available():
        torch.cuda.synchronize()
    elif torch.backends.mps.is_available():
        torch.mps.synchronize()

def rank_of(gold, ranked):
    return ranked.index(gold) + 1 if gold in ranked else None

def quality(ranks):   # one gold per query: Recall@10 = Complete Evidence@10
    hit = [r is not None and r <= TOP_K for r in ranks]
    return {"recall_at_10": round(sum(hit) / len(ranks), 3),
            "mrr_at_10": round(sum(1 / r for r, h in zip(ranks, hit) if h) / len(ranks), 3),
            "ndcg_at_10": round(sum(1 / math.log2(r + 1) for r, h in zip(ranks, hit) if h) / len(ranks), 3)}

def main():
    dev = "cuda" if torch.cuda.is_available() else "mps" if torch.backends.mps.is_available() else "cpu"
    chip = torch.cuda.get_device_name(0) if dev == "cuda" else \
        subprocess.run(["sysctl", "-n", "machdep.cpu.brand_string"], capture_output=True, text=True).stdout.strip()
    corpus, queries = load_dataset()
    res = {"machine": {"chip": chip or platform.machine(),
                       "device": dev, "torch": torch.__version__},
           "corpus": {"chunks": len(corpus), "long_chunk_share": LONG_SHARE, "dataset": DATASET, "note": "one synthetic conversation; gold answers planted"},
           "config": {"bm25": f"pg_textsearch 1.5.1, text_config={BM25_CONFIG}, k1=1.2, b=0.75",
                      "dense": "BAAI/bge-m3 fp16, cosine, exact search on the GPU (torch)",
                      "reranker": f"BAAI/bge-reranker-v2-m3 fp16, max_len={RERANK_MAX_LEN}",
                      "candidate_k": CAND_K, "top_k": TOP_K, "rrf_k": RRF_K},
           "queries": {t: sum(1 for x in queries if x[0] == t) for t in dict.fromkeys(x[0] for x in queries) if t != "warmup"}}

    with psycopg.connect(DSN, autocommit=True) as conn, conn.cursor() as cur:
        cur.execute("CREATE EXTENSION IF NOT EXISTS pg_textsearch")
        cur.execute("DROP TABLE IF EXISTS conv_chunks")
        if BM25_CONFIG == "simple_unaccent":
            cur.execute("CREATE EXTENSION IF NOT EXISTS unaccent")
            cur.execute("DROP TEXT SEARCH CONFIGURATION IF EXISTS simple_unaccent")
            cur.execute("CREATE TEXT SEARCH CONFIGURATION simple_unaccent (COPY = simple)")
            cur.execute("ALTER TEXT SEARCH CONFIGURATION simple_unaccent ALTER MAPPING FOR asciiword, asciihword, hword_asciipart, "
                        "word, hword, hword_part, numword, numhword, hword_numpart WITH unaccent, simple")
        cur.execute("CREATE TABLE conv_chunks (id int PRIMARY KEY, body text)")
        with cur.copy("COPY conv_chunks (id, body) FROM STDIN") as cp:
            for i, b in enumerate(corpus):
                cp.write_row((i, b))
        t = time.perf_counter()
        cur.execute(f"CREATE INDEX conv_bm25 ON conv_chunks USING bm25 (body) WITH (text_config='{TS_CONFIG}', k1=1.2, b=0.75)")
        res["index_build_s"] = {"bm25": round(time.perf_counter() - t, 2)}
        cur.execute("VACUUM ANALYZE conv_chunks")

        def bm25(q, k):
            cur.execute("SELECT id FROM conv_chunks ORDER BY body <@> to_bm25query(%s, 'conv_bm25') LIMIT %s", (q, k))
            return [r[0] for r in cur.fetchall()]

        emb = SentenceTransformer("BAAI/bge-m3", device=dev)
        emb.half()
        emb.max_seq_length = 512
        # Embed in slices saved to disk, so a crash during a multi-hour 1M run resumes instead of restarting.
        cache = os.path.join(os.environ.get("EMB_CACHE", "emb_cache"), f"{DATASET}_n{len(corpus)}")   # keyed by dataset too: a chat run must not reuse synthetic embeddings
        os.makedirs(cache, exist_ok=True)
        parts, spent, done = [], 0.0, 0
        for s in range(0, len(corpus), 50_000):
            f = os.path.join(cache, f"{s}.npy")
            if not os.path.exists(f):
                t = time.perf_counter()
                np.save(f, emb.encode(corpus[s:s + 50_000], batch_size=32, normalize_embeddings=True, convert_to_numpy=True))
                sync()
                spent += time.perf_counter() - t
                done += len(corpus[s:s + 50_000])
            parts.append(np.load(f))
        C = torch.from_numpy(np.concatenate(parts)).to(dev).float()   # fp32 on the GPU: search runs there, not on the CPU
        del parts
        res["index_build_s"]["dense_embeddings"] = round(spent, 1)
        res["index_build_s"]["dense_chunks_embedded_this_run"] = done

        def dense(q, k):
            v = emb.encode([q], normalize_embeddings=True, convert_to_tensor=True)[0].float()
            return torch.topk(C @ v, k).indices.tolist()

        rt = AutoTokenizer.from_pretrained("BAAI/bge-reranker-v2-m3")
        rm = AutoModelForSequenceClassification.from_pretrained("BAAI/bge-reranker-v2-m3").eval().to(dev).half()

        def rerank(q, ids):
            with torch.no_grad():
                x = rt([[q, corpus[i]] for i in ids], padding=True, truncation=True, max_length=RERANK_MAX_LEN, return_tensors="pt").to(dev)
                s = rm(**x).logits.view(-1).float().cpu().numpy()
            return [ids[i] for i in np.argsort(-s)[:TOP_K]], float(s.max())

        def timed(fn, *a):
            sync(); t = time.perf_counter(); out = fn(*a); sync()
            return out, time.perf_counter() - t

        strategies = ["bm25", "dense", "dense50_rerank10", "hybrid_rrf", "hybrid_rrf50_rerank10"]
        lat = {s: {"total": []} for s in strategies}
        lat["dense50_rerank10"].update(candidates=[], rerank=[])
        lat["hybrid_rrf50_rerank10"].update(candidates=[], rerank=[])
        lat["hybrid_rrf"].update(bm25_part=[], dense_part=[])
        per_query = []
        for qtype, q, gold, stale in queries:
            b10, tb10 = timed(bm25, q, TOP_K)
            d10, td10 = timed(dense, q, TOP_K)
            d50, td50 = timed(dense, q, CAND_K)
            (rr, rr_top), trr = timed(rerank, q, d50)
            b50, tb50 = timed(bm25, q, CAND_K)
            t = time.perf_counter()
            fused = {}
            for lst in (b50, d50):
                for r, i in enumerate(lst, 1):
                    fused[i] = fused.get(i, 0) + 1 / (RRF_K + r)
            hy50 = sorted(fused, key=lambda i: -fused[i])[:CAND_K]
            hy = hy50[:TOP_K]
            tfuse = time.perf_counter() - t
            (hr, hr_top), thr = timed(rerank, q, hy50)
            if qtype == "warmup":
                continue
            lat["bm25"]["total"].append(tb10)
            lat["dense"]["total"].append(td10)
            lat["dense50_rerank10"]["candidates"].append(td50)
            lat["dense50_rerank10"]["rerank"].append(trr)
            lat["dense50_rerank10"]["total"].append(td50 + trr)
            lat["hybrid_rrf"]["bm25_part"].append(tb50)
            lat["hybrid_rrf"]["dense_part"].append(td50)
            lat["hybrid_rrf"]["total"].append(tb50 + td50 + tfuse)   # sequential; running both in parallel would cut this
            lat["hybrid_rrf50_rerank10"]["candidates"].append(tb50 + td50 + tfuse)
            lat["hybrid_rrf50_rerank10"]["rerank"].append(thr)
            lat["hybrid_rrf50_rerank10"]["total"].append(tb50 + td50 + tfuse + thr)
            tops = {"bm25": b10, "dense": d10, "dense50_rerank10": rr, "hybrid_rrf": hy, "hybrid_rrf50_rerank10": hr}
            per_query.append({"type": qtype, "query": q, "gold_id": gold,
                              "gold_is_long": gold is not None and len(corpus[gold].split()) > 100,
                              "rank": {k: rank_of(gold, v) for k, v in tops.items()},
                              "stale_rank": {k: rank_of(stale, v) for k, v in tops.items()} if stale is not None else None,
                              "rerank_top1_score": {"dense50_rerank10": rr_top, "hybrid_rrf50_rerank10": hr_top},
                              "gold_in_dense_top50": rank_of(gold, d50), "gold_in_bm25_top50": rank_of(gold, b50),
                              "gold_in_rrf_top50": rank_of(gold, hy50)})

    res["latency"] = {s: {part: pct(v) for part, v in parts.items()} for s, parts in lat.items()}
    res["quality"] = {}
    answerable = [p for p in per_query if p["gold_id"] is not None]   # unanswerable queries have no gold to rank
    for qtype in ["all"] + list(dict.fromkeys(p["type"] for p in answerable)):
        rows = [p for p in answerable if qtype == "all" or p["type"] == qtype]
        res["quality"][qtype] = {s: quality([p["rank"][s] for p in rows]) for s in strategies}
        for src in ["dense", "bm25", "rrf"]:
            res["quality"][qtype][f"{src}_candidate_recall_at_50"] = round(sum(p[f"gold_in_{src}_top50"] is not None for p in rows) / len(rows), 3)
    corr = [p for p in per_query if p["stale_rank"]]
    if corr:   # outdated message ranked above its correction (or correction missing from top-10)
        res["quality"]["correction_stale_above_gold"] = {s: round(sum(
            p["stale_rank"][s] is not None and (p["rank"][s] is None or p["stale_rank"][s] < p["rank"][s]) for p in corr) / len(corr), 3)
            for s in strategies}
    if any(p["gold_id"] is None for p in per_query):   # can the reranker score tell "no answer" apart? (abstention threshold)
        res["quality"]["rerank_top1_score_median"] = {s: {
            "answerable": round(statistics.median(p["rerank_top1_score"][s] for p in answerable), 3),
            "unanswerable": round(statistics.median(p["rerank_top1_score"][s] for p in per_query if p["gold_id"] is None), 3)}
            for s in ["dense50_rerank10", "hybrid_rrf50_rerank10"]}
    res["per_query"] = per_query
    print(json.dumps(res, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
