# Evaluation Module 

import numpy as np


def evaluate_ranking(predicted_order, relevant_resumes):
    """
    predicted_order: list of resume names in ranked order
    relevant_resumes: list of actually relevant resumes (ground truth)
    """

    true_positives = 0
    false_positives = 0
    false_negatives = 0

    for resume in predicted_order:
        if resume in relevant_resumes:
            true_positives += 1
        else:
            false_positives += 1

    for resume in relevant_resumes:
        if resume not in predicted_order:
            false_negatives += 1

    precision = true_positives / (true_positives + false_positives)
    recall = true_positives / (true_positives + false_negatives)

    return precision, recall