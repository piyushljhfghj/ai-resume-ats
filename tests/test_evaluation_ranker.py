from app.evaluation_ranker import evaluate_ranking


class TestEvaluateRanking:
    def test_perfect_prediction(self):
        precision, recall = evaluate_ranking(["a", "b"], ["a", "b"])
        assert precision == 1.0
        assert recall == 1.0

    def test_partial(self):
        precision, recall = evaluate_ranking(["a", "x"], ["a", "b"])
        assert precision == 0.5
        assert recall == 0.5

    def test_empty_prediction_does_not_raise(self):
        precision, recall = evaluate_ranking([], ["a"])
        assert precision == 0.0
        assert recall == 0.0

    def test_both_empty_does_not_raise(self):
        assert evaluate_ranking([], []) == (0.0, 0.0)
