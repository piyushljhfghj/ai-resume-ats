# Intelligent Resume Screening System

## Overview
This project compares multiple resume ranking approaches:

1. TF-IDF based ranking
2. Semantic embedding based ranking
3. Hybrid intelligent ranking (semantic + skill weighting)

## Approach

### TF-IDF
Word frequency based similarity.

### Sentence Transformers
Semantic understanding using pretrained BERT embeddings.

### Intelligent Ranking
Final Score = 
0.7 * Semantic Similarity +
0.3 * Weighted Skill Score

## Evaluation

Used Precision and Recall to simulate recruiter ground truth.

## Limitations

- No labeled dataset
- Manual skill weights
- No bias mitigation

## Future Improvements

- Fine-tuned embedding model
- Larger evaluation dataset
- Bias reduction strategies
- Deploy as REST API

### Fairness Consideration

The system may introduce bias due to:
- Manual skill weighting
- Keyword-based matching
- Lack of demographic fairness testing

Future versions should include bias audits and fairness metrics.