# Evaluation Module

def evaluate_ranking(predicted_order, relevant_resumes):
    """Precision and recall of a predicted ranking against ground truth.

    predicted_order: list of resume names in ranked order
    relevant_resumes: list of actually relevant resumes (ground truth)
    """
    predicted = list(predicted_order)
    relevant = set(relevant_resumes)

    true_positives = sum(1 for r in predicted if r in relevant)
    false_positives = len(predicted) - true_positives
    false_negatives = sum(1 for r in relevant if r not in set(predicted))

    # An empty prediction or empty ground truth would otherwise divide by zero.
    precision = (
        true_positives / (true_positives + false_positives)
        if (true_positives + false_positives)
        else 0.0
    )
    recall = (
        true_positives / (true_positives + false_negatives)
        if (true_positives + false_negatives)
        else 0.0
    )

    return precision, recall
