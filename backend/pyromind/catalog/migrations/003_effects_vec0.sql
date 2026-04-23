-- Replace placeholder effects_vec (embedding_json) with sqlite-vec vec0 table.

DROP TABLE IF EXISTS effects_vec;

CREATE VIRTUAL TABLE effects_vec USING vec0(
  embedding float[1024] distance_metric=cosine,
  +effect_id TEXT
);
