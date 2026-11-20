"""BM25 at 1M chunks: brute force vs full-text-search(GIN)+BM25 vs pg_textsearch BM25 index.

Question: does finding candidates with a full-text index first change BM25 results or only speed?
All three use the same tokenizer (Postgres 'simple' config), k1=1.2, b=0.75, and global IDF
ln(1 + (N - df + 0.5) / (df + 0.5)). Synthetic Vietnamese chat corpus only. Measures time and
top-10 agreement, not quality (no relevance labels exist yet).

Setup (disposable DB, not the app's):
  docker build -t bm25-bench:pg17 -f Dockerfile.pg17-bm25 .
  docker run -d --name bm25-bench -p 55434:5432 -e POSTGRES_PASSWORD=bench --shm-size=2g bm25-bench:pg17 \
    postgres -c shared_preload_libraries=pg_textsearch -c shared_buffers=2GB -c maintenance_work_mem=2GB -c work_mem=256MB
  pip install "psycopg[binary]"; python bm25_scale_bench.py > bm25_scale_result.json
"""
import itertools, json, os, random, statistics, time

import psycopg

DSN = os.environ.get("BENCH_DSN", "postgresql://postgres:bench@localhost:55434/postgres")
N_CHUNKS = int(os.environ.get("N_CHUNKS", 1_000_000))
N_CONVS = 1000          # ~1000 chunks per conversation on average
LONG_SHARE = 0.05       # PDF pages / transcript windows; the rest are chat messages
WARMUP, RUNS = 3, int(os.environ.get("RUNS", 30))
K1, B = 1.2, 0.75
random.seed(7)

# --- synthetic corpus: templates (names, codes, dates) + Zipf filler over Vietnamese-like syllables ---
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

def code():
    return f"{random.choice(['INV', 'HD', 'PO', 'BB'])}-{random.randint(2023, 2026)}-{random.randint(1, 9999):04d}"

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

def chunk():
    if random.random() < LONG_SHARE:
        return " ".join(sentence() for _ in range(25))   # ~300 words
    return sentence()

def pct(xs):
    xs = sorted(xs)
    return {"p50_ms": round(statistics.median(xs) * 1000, 1),
            "p95_ms": round(xs[min(len(xs) - 1, int(round(0.95 * (len(xs) - 1))))] * 1000, 1)}

def make_queries(n):
    qs = []
    for _ in range(n):
        qs.append(random.choice([
            f"Ai sẽ nhận {random.choice(things)} vào {random.choice(days)}?",          # common words only
            f"{random.choice(things)} {code()} được ký ngày nào?",                     # rare code
            f"Cuộc họp về {random.choice(things)} ở {random.choice(places)}?",
            f"{random.choice(names)} nói gì về {filler(2)}?",                           # mixed
        ]))
    return qs

# --- shared BM25 SQL: identical scoring; only the candidate filter differs ---
BM25_SQL = """
WITH q AS (SELECT DISTINCT lexeme AS term FROM unnest(to_tsvector('simple', %(q)s))),
qi AS (SELECT q.term, ln(1 + (%(n)s - df.df + 0.5) / (df.df + 0.5)) AS idf FROM q JOIN df USING (term))
SELECT c.id, sum(qi.idf * u.tf * (%(k1)s + 1) / (u.tf + %(k1)s * (1 - %(b)s + %(b)s * c.dl / %(avgdl)s))) AS score
FROM chunks c
CROSS JOIN LATERAL (SELECT lexeme, array_length(positions, 1) AS tf FROM unnest(c.tsv)) u
JOIN qi ON qi.term = u.lexeme
WHERE {filter}
GROUP BY c.id ORDER BY score DESC, c.id LIMIT 10
"""
OR_QUERY = "(SELECT string_agg(quote_literal(lexeme), ' | ')::tsquery FROM unnest(to_tsvector('simple', %(q)s)))"
METHODS = {
    "brute_force": BM25_SQL.format(filter="true"),
    "fts_gin_then_bm25": BM25_SQL.format(filter=f"c.tsv @@ {OR_QUERY}"),
    "pg_textsearch": "SELECT id, -(body <@> to_bm25query(%(q)s, 'chunks_bm25')) AS score FROM chunks c WHERE true "
                     "ORDER BY body <@> to_bm25query(%(q)s, 'chunks_bm25') LIMIT 10",
}

def scoped(sql):  # same query restricted to one conversation (the app's real search scope)
    return sql.replace("WHERE true", "WHERE c.conv_id = %(conv)s").replace("WHERE c.tsv", "WHERE c.conv_id = %(conv)s AND c.tsv")

def setup(cur):
    res = {}
    cur.execute("CREATE EXTENSION IF NOT EXISTS pg_textsearch")
    cur.execute("DROP TABLE IF EXISTS chunks, staging, df")
    cur.execute("CREATE UNLOGGED TABLE staging (conv_id int, body text)")
    t = time.perf_counter()
    with cur.copy("COPY staging (conv_id, body) FROM STDIN") as cp:
        for _ in range(N_CHUNKS):
            cp.write_row((random.randrange(N_CONVS), chunk()))
    res["generate_and_copy_s"] = round(time.perf_counter() - t, 1)
    t = time.perf_counter()
    cur.execute("""CREATE TABLE chunks AS
        SELECT row_number() OVER () AS id, conv_id, body, tsv,
               (SELECT coalesce(sum(array_length(positions, 1)), 0) FROM unnest(tsv)) AS dl
        FROM (SELECT conv_id, body, to_tsvector('simple', body) AS tsv FROM staging) s""")
    cur.execute("DROP TABLE staging")
    cur.execute("ALTER TABLE chunks ADD PRIMARY KEY (id)")
    cur.execute("CREATE INDEX ON chunks (conv_id)")
    cur.execute("CREATE TABLE df AS SELECT word AS term, ndoc AS df FROM ts_stat('SELECT tsv FROM chunks')")
    cur.execute("ALTER TABLE df ADD PRIMARY KEY (term)")
    res["tokenize_and_stats_s"] = round(time.perf_counter() - t, 1)
    for name, ddl in [("gin", "CREATE INDEX chunks_gin ON chunks USING gin (tsv)"),
                      ("bm25", "CREATE INDEX chunks_bm25 ON chunks USING bm25 (body) WITH (text_config='simple', k1=1.2, b=0.75)")]:
        t = time.perf_counter()
        cur.execute(ddl)
        res[f"{name}_index_build_s"] = round(time.perf_counter() - t, 1)
    cur.execute("VACUUM ANALYZE chunks")
    cur.execute("ANALYZE df")
    cur.execute("""SELECT count(*), avg(dl), pg_size_pretty(pg_table_size('chunks')),
                   pg_size_pretty(pg_relation_size('chunks_gin')), pg_size_pretty(pg_relation_size('chunks_bm25')),
                   (SELECT count(*) FROM df) FROM chunks""")
    n, avgdl, tsize, gsize, bsize, vocab_n = cur.fetchone()
    res.update(chunks=n, avg_tokens=round(float(avgdl), 1), distinct_terms=vocab_n,
               table_size=tsize, gin_size=gsize, bm25_index_size=bsize)
    return res, n, float(avgdl)

def run(cur, params_list, sqls):
    times = {m: [] for m in sqls}
    tops = {m: [] for m in sqls}
    for i, p in enumerate(params_list):
        for m, sql in sqls.items():
            t = time.perf_counter()
            cur.execute(sql, p)
            rows = cur.fetchall()
            dt = time.perf_counter() - t
            if i >= WARMUP:
                times[m].append(dt)
                tops[m].append([round(float(r[1]), 4) for r in rows])
    out = {m: pct(times[m]) for m in sqls}
    ref = tops["brute_force"]
    for m in sqls:
        if m != "brute_force":  # compare scores, not ids: equal-score chunks are tie-broken differently per method
            out[m]["same_top10_scores_as_brute_force"] = f"{sum(a == b for a, b in zip(tops[m], ref))}/{len(ref)}"
    return out

def main():
    with psycopg.connect(DSN, autocommit=True) as conn, conn.cursor() as cur:
        res = {"tokenizer": "postgres 'simple' (lowercase, no stop words, no stemming; splits by syllable)",
               "k1": K1, "b": B, "idf": "global ln(1+(N-df+0.5)/(df+0.5))", "warmup": WARMUP, "measured_queries": RUNS}
        res["setup"], n, avgdl = setup(cur)
        base = {"n": n, "avgdl": avgdl, "k1": K1, "b": B}
        qs = make_queries(WARMUP + RUNS)
        params = [dict(base, q=q) for q in qs]
        cur.execute(f"SELECT avg((SELECT count(*) FROM chunks c WHERE c.tsv @@ {OR_QUERY.replace('%(q)s', 'x')})) "
                    "FROM unnest(%s::text[]) x", (qs,))
        res["avg_candidates_matching_any_query_term"] = round(float(cur.fetchone()[0]))
        res["whole_corpus"] = run(cur, params, METHODS)
        conv_params = [dict(p, conv=random.randrange(N_CONVS)) for p in params]
        res["one_conversation"] = run(cur, conv_params, {m: scoped(s) for m, s in METHODS.items()})
        print(json.dumps(res, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
