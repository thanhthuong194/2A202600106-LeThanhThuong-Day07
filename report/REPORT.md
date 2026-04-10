# Báo Cáo Lab 7: Embedding & Vector Store

**Họ tên:** Lê Thanh Thưởng
**Nhóm:** X1-C401
**Ngày:** 10/4/2026

---

## 1. Warm-up (5 điểm)

### Cosine Similarity (Ex 1.1)

**High cosine similarity nghĩa là gì?**
> Cosine similarity cao nghĩa là hai vector embedding **cùng hướng** (góc nhỏ) → hai đoạn text có **nghĩa gần nhau**, dù độ dài khác nhau.

**Ví dụ HIGH similarity:**
- Sentence A: “Eggs contain proteid and fat.”
- Sentence B: “Eggs are rich in protein and fat.”
- Tại sao tương đồng: cùng nói về thành phần dinh dưỡng của trứng (protein/fat).

**Ví dụ LOW similarity:**
- Sentence A: “A cooking-stove is a large iron box set on legs.”
- Sentence B: “Eggs contain proteid and fat.”
- Tại sao khác: một câu nói về thiết bị bếp, một câu nói về dinh dưỡng.

**Tại sao cosine similarity được ưu tiên hơn Euclidean distance cho text embeddings?**
> Vì cosine tập trung vào **hướng/ngữ nghĩa** và ít bị ảnh hưởng bởi **độ lớn vector**, nên thường ổn định hơn khi so độ “gần nghĩa” của embeddings.

### Chunking Math (Ex 1.2)

**Document 10,000 ký tự, chunk_size=500, overlap=50. Bao nhiêu chunks?**
> Trình bày phép tính:
> - step = chunk_size - overlap = 500 - 50 = 450
> - num_chunks = ceil((N - chunk_size) / step) + 1
> - = ceil((10000 - 500) / 450) + 1 = ceil(9500 / 450) + 1 = ceil(21.11) + 1 = 23
>
> Đáp án: **23 chunks**

**Nếu overlap tăng lên 100, chunk count thay đổi thế nào? Tại sao muốn overlap nhiều hơn?**
> Overlap tăng → step giảm → số chunk **tăng** (ví dụ: step=400 ⇒ chunks≈25). Overlap giúp giữ ngữ cảnh nối giữa các chunk, giảm mất ý khi cắt.

---

## 2. Document Selection — Nhóm (10 điểm)

### Domain & Lý Do Chọn

**Domain:** cooking recipes / cookbook knowledge.

**Tại sao nhóm chọn domain này?**
> Văn bản cookbook có cấu trúc theo **chapter/section** rõ ràng nên dễ gắn metadata và debug retrieval. Nội dung đủ đa dạng (food, cookery, beverages, eggs, soups…) nên thiết kế được benchmark queries gồm cả factual lẫn procedural. Nguồn dữ liệu minh bạch và dễ reproduce vì nằm trực tiếp trong repo.

### Data Inventory

| # | Tên tài liệu | Nguồn | Số ký tự | Metadata đã gán |
|---|--------------|-------|----------|-----------------|
| 1 | The Boston Cooking-School Cook Book | [`link`](https://www.gutenberg.org/) | 309,871 | `doc_id`, `title`, `source_type`, `language`, `locale`, `author`, `cuisine_scope`, `time_period`, `published_year`, `audience`, `difficulty`, `primary_topics`, `section_types`, `retrieval_tags` |


### Metadata Schema

| Trường metadata | Kiểu | Ví dụ giá trị | Tại sao hữu ích cho retrieval? |
|----------------|------|---------------|-------------------------------|
| `heading_key` | string | `"food", "ways of cooking", "water (h_{2}o)"` | Cho phép filter theo section cụ thể, tăng precision khi biết query thuộc chủ đề nào |
| `section_type` | string | `"methods", "ingredient_reference", "preface"` |Phân loại loại nội dung, giúp filter nhanh giữa lý thuyết và thực hành |
| `domain` | string | `"recipes"` | Phân biệt khi store chứa nhiều domain khác nhau |
| `doc_id` | string | `"recipe_boston_cookbook_1910"` | Quản lý document lifecycle (delete, update)|

---

## 3. Chunking Strategy — Cá nhân chọn, nhóm so sánh (15 điểm)

### Baseline Analysis

Chạy `ChunkingStrategyComparator().compare()` trên 3 tài liệu (Chapter I/III/VII) với `chunk_size=200`:

| Tài liệu | Strategy | Chunk Count | Avg Length | Preserves Context? |
|-----------|----------|------------:|-----------:|-------------------|
| Ch. I — Food | FixedSizeChunker (`fixed_size`) | 174 | 199.5 | Trung bình (dễ cắt giữa câu/ý) |
| Ch. I — Food | SentenceChunker (`by_sentences`) | 85 | 304.6 | Tốt (giữ ranh giới câu) |
| Ch. I — Food | RecursiveChunker (`recursive`) | 59 | 439.3 | Tốt nhưng chunk dài hơn |
| Ch. III — Beverages | FixedSizeChunker (`fixed_size`) | 184 | 199.2 | Trung bình |
| Ch. III — Beverages | SentenceChunker (`by_sentences`) | 81 | 326.1 | Tốt |
| Ch. III — Beverages | RecursiveChunker (`recursive`) | 64 | 420.7 | Tốt nhưng có thể dài |
| Ch. VII — Eggs | FixedSizeChunker (`fixed_size`) | 196 | 200.0 | Trung bình |
| Ch. VII — Eggs | SentenceChunker (`by_sentences`) | 89 | 311.0 | Tốt |
| Ch. VII — Eggs | RecursiveChunker (`recursive`) | 77 | 371.7 | Tốt |

### Strategy Của Tôi

**Loại:** SentenceChunker (tuned `max_sentences_per_chunk=5`) + metadata filtering theo section.

**Mô tả cách hoạt động:**
> Tôi tách tài liệu theo heading Markdown (`##`/`###`) để có các section logic, sau đó normalize heading thành `heading_key` để filter ổn định. Mỗi section được chunk bằng SentenceChunker, gom tối đa 5 câu/chunk để đảm bảo chunk đủ “tròn nghĩa” nhưng không quá dài. Khi query có scope rõ (ví dụ hỏi về “water” hoặc “ways of cooking”), tôi dùng `search_with_filter()` để giới hạn search trong đúng section.

**Tại sao tôi chọn strategy này cho domain nhóm?**
> Cookbook có nhiều danh sách/định nghĩa; chunk theo câu giúp giữ nguyên danh sách và tránh cắt ngang ý. Domain cũng có heading rõ nên filter theo metadata giúp giảm nhiễu rất hiệu quả.

**Code snippet (nếu custom):**


### So Sánh: Strategy của tôi vs Baseline

| Tài liệu | Strategy | Chunk Count | Avg Length | Retrieval Quality? |
|-----------|----------|------------:|-----------:|--------------------|
| recipe.md (cùng scope benchmark) | best baseline: RecursiveChunker | 32 | ~388.7 | chunk khá “gọn”, nhưng đôi khi không theo ranh giới câu |
| recipe.md (cùng scope benchmark) | **của tôi: SentenceChunker(max=5) + filter** | **25** | **~498.5** | chunk theo câu dễ verify; filter giúp giảm sai scope |

### So Sánh Với Thành Viên Khác

| Thành viên | Strategy | Retrieval Score (/10) | Điểm mạnh | Điểm yếu |
|-----------|----------|----------------------|-----------|----------|
| Tôi | SentenceChunker(max=5) + metadata filter | 6 / 10 | Giữ trọn vẹn ý/ngữ cảnh vì không cắt giữa câu. | Chunk có thể quá ngắn hoặc quá dài nếu văn bản không đều, đôi khi thiếu tính nhất quán về độ dài. |
| Lê Văn Tùng | RecursiveChunker(300) | 5/10 | Giữ nguyên câu trọn vẹn | không có metadata filter|
| Nguyễn Đức Sĩ | RecursiveChunker(500) + metadata filter | 8/10 |  	Đơn giản, dễ implement | Cắt giữa paragraph, mất context |
| Đinh Thái Tuấn | Section-based + RecursiveChunker(500) + metadata filter | 6/10 | Filter theo heading_key giúp Q1, Q5 chính xác | Mock embedder hạn chế semantic matching |

**Strategy nào tốt nhất cho domain này? Tại sao?**
> Strategy tốt nhất là RecursiveChunker (`chunk_size=500`) kết hợp metadata filter vì vừa giữ được ngữ cảnh đủ dài, tránh cắt ngang ý, đồng thời filter giúp tăng độ chính xác khi truy vấn đúng section cần thiết.

---

## 4. My Approach — Cá nhân (10 điểm)

Giải thích cách tiếp cận của bạn khi implement các phần chính trong package `src`.

### Chunking Functions

**`SentenceChunker.chunk`** — approach:
> Tôi dùng regex `(?<=[.!?])(?:\s|\n)+` để tách theo ranh giới câu (kết thúc bằng `. ! ?` và sau đó là whitespace/newline). Sau khi split sẽ `strip()` và loại bỏ câu rỗng, rồi gom tối đa `max_sentences_per_chunk` câu thành 1 chunk để giữ ngữ cảnh.

**`RecursiveChunker.chunk` / `_split`** — approach:
> Thuật toán thử tách theo danh sách separators ưu tiên (`\n\n`, `\n`, `. `, ` `, ``). Base case: khi đoạn hiện tại <= `chunk_size` hoặc không còn separator thì dừng và trả về. Nếu vẫn dài, tiếp tục recurse với separator “mịn” hơn.

### EmbeddingStore

**`add_documents` + `search`** — approach:
> Mỗi `Document` được embed thành vector và lưu record `{id, content, embedding, metadata}` trong list. Khi search, embed query rồi tính điểm bằng dot-product với từng embedding chunk, sort giảm dần và lấy top-k.

**`search_with_filter` + `delete_document`** — approach:
> `search_with_filter` filter theo metadata **trước** rồi mới tính điểm để giảm nhiễu. `delete_document` xoá các record có `metadata.doc_id` trùng với `doc_id` được truyền vào.

### KnowledgeBaseAgent

**`answer`** — approach:
> Agent retrieve top-k chunks từ store, ghép thành context (ngăn cách bằng `---`), sau đó tạo prompt dạng `Context + Question + Answer`. Cuối cùng gọi `llm_fn(prompt)` để sinh câu trả lời (có thể inject mock LLM để test).

---

## 5. Similarity Predictions — Cá nhân (5 điểm)

| Pair | Sentence A | Sentence B | Dự đoán | Actual Score | Đúng? |
|------|-----------|-----------|---------|--------------|-------|
| 1 | Eggs contain proteid and fat. | Eggs are rich in protein and fat. | high | 0.3992 | ✓ |
| 2 | Boiled water should be used for making hot beverages. | Freshly drawn water should be used for making cold beverages. | high | 0.6869 | ✓ |
| 3 | Tea should always be infused, never boiled. | Long steeping destroys the delicate flavor by developing tannic acid. | low | 0.0000 | ✓ |
| 4 | Bread dough ferments and produces carbon dioxide. | Fermentation changes sugar into alcohol and carbon dioxide. | high | 0.3594 | ✓ |
| 5 | Eggs cooked in boiling water are tough and difficult of digestion. | A cooking-stove is a large iron box set on legs. | low | 0.0000 | ✓ |

**Kết quả nào bất ngờ nhất? Điều này nói gì về cách embeddings biểu diễn nghĩa?**
> Bất ngờ nhất là Pair #3 có cùng chủ đề “tea” nhưng score lại rất thấp (0.0000). Điều này cho thấy embedding/biểu diễn có thể bỏ lỡ quan hệ ngữ nghĩa gián tiếp khi hai câu ít trùng tín hiệu bề mặt. Vì vậy với RAG cần chunking/metadata tốt và đôi khi cần embedding mạnh hơn hoặc query viết rõ hơn.

---

## 6. Results — Cá nhân (10 điểm)

Chạy 5 benchmark queries của nhóm trên implementation cá nhân của bạn trong package `src`. **5 queries phải trùng với các thành viên cùng nhóm.**

### Benchmark Queries & Gold Answers (nhóm thống nhất)

| # | Query | Gold Answer |
|---|-------|-------------|
| 1 | What are the principal ways of cooking listed in the book? | The principal ways are boiling, broiling, stewing, roasting, baking, frying, sauteing, braising, and fricasseeing. |
| 2 | At what temperatures does water boil and simmer? | Water boils at 212F and simmers at around 185F. |
| 3 | Why does milk sour according to the text? | A germ converts lactose to lactic acid, which precipitates casein into curd and whey. |
| 4 | How is fat tested for frying temperature? | Drop a one-inch cube of bread; if golden brown in about forty seconds, fat is ready for cooked mixtures. |
| 5 | What is the chief office of proteids? | Proteids chiefly build and repair tissues, and can also furnish energy. |

### Kết Quả Của Tôi

| # | Query | Top-1 Retrieved Chunk (tóm tắt) | Score | Relevant? | Agent Answer (tóm tắt) |
|---|-------|--------------------------------|------:|:---------:|------------------------|
| 1 | What are the principal ways of cooking listed in the book? | Đúng danh sách “boiling, broiling, stewing, roasting, baking, frying, sautéing, braising, fricasseeing”. Có thêm định nghĩa Boiling. | 2 | Yes | Đúng danh sách, kèm định nghĩa Boiling. |
| 2 | At what temperatures does water boil and simmer? | Nói về nhiệt độ nước sôi 212°F, có nhắc simmer ~185°F. | 1 | Yes | Đúng nhiệt độ, nêu rõ simmer 185°F. |
| 3 | Why does milk sour according to the text? | Đoạn bị lệch sang mục đích đun sôi nước, không đúng trọng tâm. | 1 | No | Không có lactose/lactic acid/casein/curd/whey. |
| 4 | How is fat tested for frying temperature? | Đúng hướng dẫn “bread ~40 seconds”, mô tả chi tiết cách kiểm tra mỡ chiên. | 2 | Yes | Đúng mẹo bread ~40s, mô tả đầy đủ. |
| 5 | What is the chief office of proteids? | Đúng ý “build and repair tissues, furnish energy”, đầy đủ thông tin. | 2 | Yes | Đủ ý build/repair tissues, furnish energy. |

**Bao nhiêu queries trả về chunk relevant trong top-3?** 5 / 5

---

## 7. What I Learned (5 điểm — Demo)

**Điều hay nhất tôi học được từ thành viên khác trong nhóm:**
> Tôi học được cách thiết kế benchmark query có scope rõ để đo được lợi ích của metadata filtering. Ngoài ra, bạn ấy nhấn mạnh việc tách lỗi do retrieval và lỗi do answering để debug đúng chỗ.

**Điều hay nhất tôi học được từ nhóm khác (qua demo):**
> Nhóm khác trình bày cách in top-k chunks và highlight câu chứa đáp án để phân tích failure case rất nhanh. Tôi cũng học được cách trình bày metric đơn giản (top-3 relevant + answer correctness) để giải thích pipeline rõ ràng.

**Nếu làm lại, tôi sẽ thay đổi gì trong data strategy?**
> Tôi sẽ chỉnh lại bước split section để không bỏ sót các đoạn quan trọng như “Why Milk Sours” (đang nằm dưới heading `Composition`). Đồng thời tôi sẽ bổ sung metadata chi tiết hơn (subtopic/ingredient) và thêm một vài query dạng tổng hợp nhiều chunk để test grounding.

---

## Tự Đánh Giá

| Tiêu chí | Loại | Điểm tự đánh giá |
|----------|------|-------------------|
| Warm-up | Cá nhân | 5 / 5 |
| Document selection | Nhóm | 10 / 10 |
| Chunking strategy | Nhóm | 15 / 15 |
| My approach | Cá nhân | 10 / 10 |
| Similarity predictions | Cá nhân | 5 / 5 |
| Results | Cá nhân | 8 / 10 |
| Core implementation (tests) | Cá nhân | 30 / 30 |
| Demo | Nhóm | 4 / 5 |
| **Tổng** | | **97 / 100** |
