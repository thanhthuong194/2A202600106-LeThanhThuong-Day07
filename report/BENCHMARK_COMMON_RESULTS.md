# Common Benchmark Results

Dataset: `data/recipe.md`
Chunking strategy: `FixedSizeChunker(chunk_size=500)`
Embedding backend: `openai:text-embedding-3-small`
Indexed chunks: 25

## Benchmark Definition

| # | Query | Gold Answer | Metadata Filter |
|---|-------|-------------|-----------------|
| 1 | What are the principal ways of cooking listed in the book? | The principal ways are boiling, broiling, stewing, roasting, baking, frying, sauteing, braising, and fricasseeing. | `{'heading_key': 'ways of cooking'}` |
| 2 | At what temperatures does water boil and simmer? | Water boils at 212F and simmers at around 185F. | `{'heading_key': 'water (h_{2}o)'}` |
| 3 | Why does milk sour according to the text? | A germ converts lactose to lactic acid, which precipitates casein into curd and whey. | `{}` |
| 4 | How is fat tested for frying temperature? | Drop a one-inch cube of bread; if golden brown in about forty seconds, fat is ready for cooked mixtures. | `{'heading_key': 'ways of cooking'}` |
| 5 | What is the chief office of proteids? | Proteids chiefly build and repair tissues, and can also furnish energy. | `{'heading_key': 'food'}` |

## Results

| # | Relevant in Top-3 (search) | Relevant in Top-3 (filtered) | Agent answer correct? | Query score (0-2) |
|---|----------------------------|------------------------------|----------------------|------------------|
| 1 | 3/3 | 3/3 | Yes | 2 |
- Q1 top-1 (filtered): The principal ways of cooking are boiling, broiling, stewing, roasting, baking, frying, sautéing, braising, and fricasseeing. =Boiling= is cooking in boiling water. Solid food so c...
- Q1 agent answer: The principal ways of cooking are boiling, broiling, stewing, roasting, baking, frying, sautéing, braising, and fricasseeing. =Boiling= is cooking in boiling water.
| 2 | 1/3 | 1/3 | Yes | 1 |
- Q2 top-1 (filtered): From 32° to 65° F. water is termed cold; from 65° to 92° F., tepid; 92° to 100° F., warm; over that temperature, hot. Boiled water is freed from all organic impurities, and salts o...
- Q2 agent answer: (sea level), and simmers at 185° F. Slowly boiling water has the same temperature as rapidly boiling water, consequently is able to do the same work,—a fact often forgotten by the cook, who is too apt “to wood” the fire 
| 3 | 1/3 | 1/3 | No | 1 |
- Q3 top-1 (filtered): Water is boiled for two purposes: first, cooking of itself to destroy organic impurities; second, for cooking foods. Boiling water toughens and hardens albumen in eggs; toughens fi...
- Q3 agent answer: Water is boiled for two purposes: first, cooking of itself to destroy organic impurities; second, for cooking foods. Boiling water toughens and hardens albumen in eggs; toughens fibrin and dissolves tissues in meat; burs
| 4 | 3/3 | 3/3 | No | 1 |
- Q4 top-1 (filtered): Great care must be taken that too much is not put into the fat at one time, not only because it lowers the temperature of the fat, but because it causes it to bubble and go over th...
- Q4 agent answer: Great care must be taken that too much is not put into the fat at one time, not only because it lowers the temperature of the fat, but because it causes it to bubble and go over the sides of the kettle. It is not fat tha
| 5 | 2/3 | 2/3 | No | 1 |
- Q5 top-1 (filtered): INORGANIC          1. Mineral matter                         2. Water  The chief office of proteids is to build and repair tissues. They furnish energy, but at greater cost than ca...
- Q5 agent answer: INORGANIC          1. Mineral matter                         2.

## Aggregate Metrics

- Retrieval Precision (search): 10/15 relevant chunks in top-3
- Retrieval Precision (filtered): 10/15 relevant chunks in top-3
- Benchmark Score: 6/10
- Note: Query score follows rubric in `docs/SCORING.md` (0-2 points/query).
