-- Legacy PyroMind "checkpoints" table collided with LangGraph's checkpoint schema
-- (same table name, incompatible columns). LangGraph creates checkpoints + writes.
DROP TABLE IF EXISTS checkpoints;
