# app/config.py
"""Single source of truth for model + scoring configuration."""

# Embedding model used for semantic similarity and skill detection.
MODEL_NAME = "all-mpnet-base-v2"

# Final ATS score weights. Must sum to 1.0.
SEMANTIC_WEIGHT = 0.4
SKILL_WEIGHT = 0.4
EXPERIENCE_WEIGHT = 0.2

# Relative weight of a required vs. a preferred skill.
REQUIRED_SKILL_WEIGHT = 2
PREFERRED_SKILL_WEIGHT = 1
